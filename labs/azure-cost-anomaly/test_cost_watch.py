import csv
import gzip
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


LAB = Path(__file__).resolve().parent
EXAMPLES = LAB / "examples"
DAY = date(2025, 3, 12)
HEADER = ["Date", "SubscriptionId", "ResourceGroup", "MeterCategory",
          "CostInBillingCurrency", "BillingCurrencyCode"]


def daily_rows(history="100", current="100"):
    return [[(DAY - timedelta(days=n)).isoformat(), "sub-a", "rg-web", "Compute",
             history if n else current, "USD"] for n in range(7, -1, -1)]


class CostCheckTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.manifest = self.root / "manifest.json"

    def make_export(self, rows, compressed=False):
        part = self.root / ("part.csv.gz" if compressed else "part.csv")
        opener = gzip.open if compressed else open
        with opener(part, "wt", newline="", encoding="utf-8-sig") as target:
            writer = csv.writer(target)
            writer.writerow(HEADER)
            writer.writerows(rows)
        self.manifest.write_text(json.dumps({
            "exportConfig": {"type": "ActualCost"}, "blobCount": 1, "dataRowCount": len(rows),
            "blobs": [{"blobName": "exports/run/" + part.name, "dataRowCount": len(rows)}],
        }))

    def invoke(self, *options, manifest=None, day=DAY):
        return subprocess.run(
            [sys.executable, str(LAB / "cost_watch.py"), str(manifest or self.manifest),
             "--day", day.isoformat(), *map(str, options)],
            capture_output=True, text=True, timeout=8, check=False,
        )

    def result(self, expected, *args, **kwargs):
        process = self.invoke(*args, **kwargs)
        self.assertEqual(process.returncode, expected, process.stderr or process.stdout)
        return json.loads(process.stdout)

    def error(self, message, *args, **kwargs):
        process = self.invoke(*args, **kwargs)
        self.assertEqual(process.returncode, 2, process.stdout)
        self.assertEqual(process.stdout, "")
        self.assertIn(message, process.stderr)

    def test_demo_steady_day_and_spike_after_refund(self):
        summary = self.root / "summary.md"
        options = {"manifest": EXAMPLES / "manifest.json"}
        steady = self.result(0, "--summary", summary, day=date(2026, 11, 16), **options)
        self.assertEqual((steady["actual"], steady["change"]), ("120.00", "0.00"))
        spike = self.result(1, "--summary", summary, day=date(2026, 11, 17), **options)
        self.assertEqual((spike["partitions"], spike["source_rows"]), (2, 28))
        self.assertEqual((spike["baseline_mean"], spike["actual"], spike["change"],
                          spike["change_percent"]), ("120.00", "312.00", "192.00", "160.00"))
        self.assertEqual([(r["resource_group"], r["meter_category"], r["change"])
                          for r in spike["contributors"]],
                         [("rg-analytics", "Virtual Machines", "180.00"), ("rg-api", "App Service", "12.00")])
        self.assertEqual(summary.read_text().count("### Azure cost check"), 2)

    def test_exact_thresholds_and_subcent_precision(self):
        for cost, expected in [("150", 1), ("149.9999", 0), ("130", 0)]:
            with self.subTest(cost=cost):
                self.make_export(daily_rows(current=cost))
                self.result(expected, "--min-percent", 50)
        self.make_export(daily_rows(history="1000", current="1050"))
        self.result(0)
        self.make_export(daily_rows(history="10", current="15"))
        self.result(0)

    def test_zero_and_negative_baselines(self):
        for before, now, expected in [("0", "50", 1), ("0", "49", 0), ("-10", "40", 1), ("-100", "0", 0)]:
            with self.subTest(before=before, now=now):
                self.make_export(daily_rows(before, now))
                self.assertIsNone(self.result(expected)["change_percent"])

    def test_missing_dates_are_reported_even_when_manifest_counts_match(self):
        rows = daily_rows()
        self.make_export(rows[:2] + rows[3:-1])
        report = self.result(2)
        self.assertEqual(report["status"], "insufficient_data")
        self.assertEqual(report["missing_dates"], [rows[2][0], DAY.isoformat()])
        self.assertNotIn("actual", report)

    def test_missing_export_part_fails_even_if_other_part_has_all_eight_days(self):
        shutil.copytree(EXAMPLES, self.root, dirs_exist_ok=True)
        (self.root / "part-1.csv").unlink()
        self.error("part-1.csv", day=date(2026, 11, 17))

    def test_integrity_counts_cover_rows_outside_the_window(self):
        rows = daily_rows()
        rows.append(["2024-01-01", "sub-a", "rg-web", "Compute", "1", "USD"])
        self.make_export(rows)
        part = self.root / "part.csv"
        part.write_text("\n".join(part.read_text().splitlines()[:-1]) + "\n")
        self.error("expected 9 data rows, read 8")
        manifest = json.loads(self.manifest.read_text())
        manifest["blobs"][0].pop("dataRowCount")
        self.manifest.write_text(json.dumps(manifest))
        self.error("manifest expected 9 data rows, read 8")

    def test_mixed_currency_cannot_generate_a_spike(self):
        rows = daily_rows()
        rows[-1][-1] = "EUR"
        self.make_export(rows)
        self.error("mixed billing currencies")

    def test_repeated_partition_is_rejected_and_equal_line_items_still_count(self):
        rows = daily_rows()
        rows.append(rows[-1].copy())
        self.make_export(rows)
        self.assertEqual(self.result(1)["actual"], "200.00")
        manifest = json.loads(self.manifest.read_text())
        manifest["blobs"] *= 2
        manifest["blobCount"] = 2
        self.manifest.write_text(json.dumps(manifest))
        self.error("supplied twice")

    def test_gzip_blank_group_and_offsets_across_subscriptions(self):
        rows = daily_rows("50", "160")
        for row in rows:
            row[2] = ""
        other = [[day, "sub-b", "", meter, "15" if day == DAY.isoformat() else "50", code]
                 for day, _, _, meter, _, code in rows]
        self.make_export(rows + other, compressed=True)
        report = self.result(1)
        self.assertEqual(report["change"], "75.00")
        self.assertEqual([(r["subscription_id"], r["resource_group"], r["change"]) for r in report["contributors"]],
                         [("sub-a", None, "110.00"), ("sub-b", None, "-35.00")])

    def test_invalid_or_nonfinite_costs_report_the_line(self):
        for amount in ["", "not-a-cost", "NaN", "Infinity"]:
            with self.subTest(amount=amount):
                self.make_export(daily_rows(current=amount))
                self.error("line 9")

    def test_requires_actual_cost_and_consistent_manifest_blob_count(self):
        self.make_export(daily_rows())
        manifest = json.loads(self.manifest.read_text())
        manifest["blobCount"] = 2
        self.manifest.write_text(json.dumps(manifest))
        self.error("blobCount")
        manifest["exportConfig"]["type"] = "AmortizedCost"
        self.manifest.write_text(json.dumps(manifest))
        self.error("ActualCost")

    def test_current_utc_day_and_invalid_thresholds_are_rejected(self):
        self.make_export(daily_rows())
        self.error("current UTC date", day=datetime.now(timezone.utc).date())
        self.error("nonnegative", "--min-rise", "-1")
        self.error("invalid", "--min-percent", "NaN")

    def test_summary_cannot_overwrite_inputs(self):
        self.make_export(daily_rows())
        part = self.root / "part.csv"
        before = part.read_bytes()
        self.error("separate from the export inputs", "--summary", part)
        self.assertEqual(before, part.read_bytes())


if __name__ == "__main__":
    unittest.main()
