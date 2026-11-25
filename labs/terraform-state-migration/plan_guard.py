"""Accept only the explicitly reviewed address moves in a Terraform JSON plan."""

import argparse
import json
import sys
from pathlib import Path


class Rejected(ValueError):
    """The plan does not meet the conditions for an address-only migration."""


def verify(plan, expected):
    if not isinstance(expected, dict) or not expected:
        raise Rejected("supply a nonempty map of source and destination addresses")
    for source, target in expected.items():
        if not isinstance(source, str) or not source or not isinstance(target, str) or not target or source == target:
            raise Rejected("each move needs two distinct, nonempty addresses")
    if len(set(expected.values())) != len(expected):
        raise Rejected("two moves share a destination")

    if not isinstance(plan, dict) or not str(plan.get("format_version", "")).startswith("1."):
        raise Rejected("unsupported Terraform JSON plan format")
    if plan.get("errored") is not False or plan.get("complete") is not True or plan.get("deferred_changes"):
        raise Rejected("the plan must be complete and free of errors")
    if plan.get("applyable") is not True:
        raise Rejected("Terraform did not mark this plan as applicable")

    def require_noop(change, address):
        actions = change.get("actions") if isinstance(change, dict) else None
        if actions != ["no-op"]:
            raise Rejected(f"{address} has actions {actions!r}")
        if change.get("importing") is not None:
            raise Rejected(f"{address} imports an object")

    drift = plan.get("resource_drift", [])
    outputs = plan.get("output_changes", {})
    changes = plan.get("resource_changes")
    if not isinstance(drift, list) or not isinstance(outputs, dict) or not isinstance(changes, list):
        raise Rejected("invalid plan change collections")
    for record in drift:
        if not isinstance(record, dict):
            raise Rejected("invalid drift entry")
        require_noop(record.get("change"), f"drift at {record.get('address')}")
    for name, change in outputs.items():
        require_noop(change, f"output {name}")

    found = {}
    for record in changes:
        if not isinstance(record, dict) or not isinstance(record.get("address"), str):
            raise Rejected("invalid resource change entry")
        target = record["address"]
        require_noop(record.get("change"), target)
        if "previous_address" in record:
            source = record["previous_address"]
            if not isinstance(source, str) or expected.get(source) != target or record.get("mode") != "managed":
                raise Rejected(f"unexpected move from {source} to {target}")
            if source in found:
                raise Rejected(f"duplicate move from {source}")
            found[source] = target
    if found != expected:
        missing = ", ".join(sorted(expected.keys() - found.keys()))
        raise Rejected(f"missing expected moves from {missing}")
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_json", type=Path, help="output of terraform show -json on a saved plan")
    parser.add_argument("moves_json", type=Path, help="reviewed source-to-destination map")
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan_json.read_text())
        moves = json.loads(args.moves_json.read_text())
        accepted = verify(plan, moves)
    except (ValueError, OSError) as exc:
        print(f"Rejected: {exc}", file=sys.stderr)
        return 1
    print(f"Accepted {len(accepted)} address moves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
