"""Investigate daily changes in a partitioned Azure actual-cost CSV export."""

import argparse
import csv
import gzip
import html
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from pathlib import Path, PurePosixPath


WINDOW = 7
FIELDS = {"date", "subscriptionid", "resourcegroup", "metercategory",
          "costinbillingcurrency", "billingcurrencycode"}
EXIT_CODES = {"within_range": 0, "spike": 1, "insufficient_data": 2}


def decimal_value(text):
    try:
        number = Decimal(text)
    except DecimalException as exc:
        raise ValueError(f"invalid decimal {text!r}") from exc
    if not number.is_finite():
        raise ValueError(f"non-finite decimal {text!r}")
    return number


def csv_date(text):
    if "/" in text:
        return datetime.strptime(text, "%m/%d/%Y").date()
    return date.fromisoformat(text)


def load_manifest(path):
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict):
        raise ValueError("expected a JSON export manifest")
    config = manifest.get("exportConfig")
    if not isinstance(config, dict) or config.get("type") != "ActualCost":
        raise ValueError("expected an ActualCost export manifest")
    blobs = manifest.get("blobs")
    count = manifest.get("blobCount")
    if not isinstance(blobs, list) or not blobs or type(count) is not int or count != len(blobs):
        raise ValueError("manifest blobCount must match its nonempty list of partitions")
    total = manifest.get("dataRowCount")
    if type(total) is not int or total < 0:
        raise ValueError("manifest dataRowCount must be a nonnegative integer")
    parts = []
    for blob in blobs:
        name = blob.get("blobName") if isinstance(blob, dict) else None
        if not isinstance(name, str) or not name.lower().endswith((".csv", ".csv.gz")):
            raise ValueError("expected a CSV or CSV.GZ partition name")
        # An Azure blob name can include the full container-relative prefix.
        part = path.parent / PurePosixPath(name).name
        if part.resolve().parent != path.parent.resolve():
            raise ValueError("partition resolves outside the local export directory")
        rows = blob.get("dataRowCount")
        if rows is not None and (type(rows) is not int or rows < 0):
            raise ValueError(f"invalid partition row count for {part.name}")
        parts.append((part, rows))
    return parts, total


def read_window(parts, expected_rows, start, target):
    prior = defaultdict(Decimal)
    current = defaultdict(Decimal)
    dates_seen = set()
    files_seen = set()
    currency = None
    total_rows = 0

    for path, expected_part_rows in parts:
        stat = path.stat()
        identity = (stat.st_dev, stat.st_ino)
        if identity in files_seen:
            raise ValueError(f"input partition supplied twice: {path}")
        files_seen.add(identity)
        opener = gzip.open if path.suffix.lower() == ".gz" else open
        with opener(path, "rt", newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            headers = [name.strip().lower() for name in reader.fieldnames or []]
            missing = FIELDS.difference(headers)
            if missing or len(set(headers)) != len(headers):
                detail = ", ".join(sorted(missing)) if missing else "duplicate column names"
                raise ValueError(f"{path}: invalid header ({detail})")
            reader.fieldnames = headers
            row_count = 0
            try:
                for row in reader:
                    row_count += 1
                    if None in row or None in row.values():
                        raise ValueError("row has the wrong number of fields")
                    day = csv_date(row["date"].strip())
                    if not start <= day <= target:
                        continue
                    code = row["billingcurrencycode"].strip().upper()
                    if len(code) != 3 or not code.isascii() or not code.isalpha():
                        raise ValueError(f"invalid billing currency {code!r}")
                    if currency is not None and code != currency:
                        raise ValueError(f"mixed billing currencies {currency} and {code}")
                    currency = code
                    key = (row["subscriptionid"].strip().lower(),
                           row["resourcegroup"].strip().lower(),
                           row["metercategory"].strip())
                    bucket = current if day == target else prior
                    bucket[key] += decimal_value(row["costinbillingcurrency"].strip())
                    dates_seen.add(day)
            except (ValueError, csv.Error) as exc:
                raise ValueError(f"{path}, line {reader.line_num}: {exc}") from exc
            if expected_part_rows is not None and row_count != expected_part_rows:
                raise ValueError(f"{path}: expected {expected_part_rows} data rows, read {row_count}")
            total_rows += row_count
    if total_rows != expected_rows:
        raise ValueError(f"manifest expected {expected_rows} data rows, read {total_rows}")
    return prior, current, dates_seen, currency


def display_amount(value):
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(abs(rounded) if rounded.is_zero() else rounded, "f")


def analyze(parts, expected_rows, target, min_rise, min_percent):
    start = target - timedelta(days=WINDOW)
    prior, current, seen, currency = read_window(parts, expected_rows, start, target)
    report = {
        "day": target.isoformat(),
        "baseline_start": start.isoformat(),
        "baseline_end": (target - timedelta(days=1)).isoformat(),
        "billing_currency": currency,
        "min_rise": str(min_rise),
        "min_percent": str(min_percent),
        "partitions": len(parts),
        "source_rows": expected_rows,
    }
    expected = [start + timedelta(days=offset) for offset in range(WINDOW + 1)]
    missing = [day.isoformat() for day in expected if day not in seen]
    if missing:
        return {**report, "status": "insufficient_data", "missing_dates": missing}

    prior_sum = sum(prior.values(), Decimal(0))
    today = sum(current.values(), Decimal(0))
    # Compare before rounding, without dividing a seven-day sum into a repeating decimal.
    scaled_rise = today * WINDOW - prior_sum
    large_enough = scaled_rise >= min_rise * WINDOW
    relative_hit = prior_sum <= 0 or scaled_rise * 100 >= min_percent * prior_sum
    spike = today > 0 and scaled_rise > 0 and large_enough and relative_hit
    changes = []
    for key in current.keys() | prior.keys():
        difference = current.get(key, 0) * WINDOW - prior.get(key, 0)
        if difference:
            changes.append((difference, key))

    contributors = []
    for difference, key in sorted(changes, key=lambda change: (-change[0], change[1])):
        subscription, group, meter = key
        contributors.append({
            "subscription_id": subscription or None, "resource_group": group or None,
            "meter_category": meter or None,
            "change": display_amount(difference / WINDOW),
        })
    return {
        **report, "status": "spike" if spike else "within_range",
        "actual": display_amount(today), "baseline_mean": display_amount(prior_sum / WINDOW),
        "change": display_amount(scaled_rise / WINDOW),
        "change_percent": display_amount(scaled_rise * 100 / prior_sum) if prior_sum > 0 else None,
        "contributors": contributors,
    }


def markdown(report):
    title = f"### Azure cost check for {report['day']}\n\n"
    if report["status"] == "insufficient_data":
        return title + "Insufficient data. Missing billing dates: " + ", ".join(report["missing_dates"]) + ".\n\n"
    currency = report["billing_currency"]
    status = "Cost spike" if report["status"] == "spike" else "Within range"
    percent = f" ({report['change_percent']}%)" if report["change_percent"] is not None else ""
    lines = [
        f"**{status}** · Actual {report['actual']} {currency} · "
        f"Seven-day mean {report['baseline_mean']} {currency} · Change {report['change']} {currency}{percent}",
    ]
    if report["contributors"]:
        lines.extend(["", "| Subscription | Resource group | Meter category | Change |",
                      "| --- | --- | --- | ---: |"])
    for row in report["contributors"]:
        cells = []
        for name in ("subscription_id", "resource_group", "meter_category"):
            value = " ".join((row[name] or "(unassigned)").splitlines())
            cells.append("<code>" + html.escape(value).replace("|", "&#124;") + "</code>")
        lines.append("| " + " | ".join([*cells, row["change"]]) + " |")
    return title + "\n".join(lines) + "\n\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="manifest.json alongside the CSV or CSV.GZ partitions")
    parser.add_argument("--day", type=date.fromisoformat, required=True, help="past UTC date, YYYY-MM-DD")
    parser.add_argument("--min-rise", type=decimal_value, default=Decimal("50"), help="minimum rise in billing-currency units")
    parser.add_argument("--min-percent", type=decimal_value, default=Decimal("30"), help="minimum percentage rise")
    parser.add_argument("--summary", type=Path, help="append a Markdown summary to this file")
    args = parser.parse_args(argv)
    if args.day >= datetime.now(timezone.utc).date():
        parser.error("--day must be earlier than the current UTC date")
    if args.min_rise < 0 or args.min_percent < 0:
        parser.error("thresholds must be nonnegative")
    try:
        parts, expected_rows = load_manifest(args.manifest)
        inputs = [args.manifest, *(part for part, _ in parts)]
        if args.summary and args.summary.exists() and any(args.summary.samefile(path) for path in inputs):
            raise ValueError("choose a summary file separate from the export inputs")
        report = analyze(parts, expected_rows, args.day, args.min_rise, args.min_percent)
        if args.summary:
            with args.summary.open("a", encoding="utf-8") as target:
                target.write(markdown(report))
    except (OSError, EOFError, ValueError, csv.Error, DecimalException, OverflowError) as exc:
        print(f"cost check failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return EXIT_CODES[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
