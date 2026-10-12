#!/usr/bin/env python3
"""Run the deterministic Starbloom Survivor balance benchmark."""

import argparse
import json
import os
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT_ROOT = os.path.join(REPO_ROOT, "Project", "Scripts")
if SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, SCRIPT_ROOT)

from SurvivorBalance import build_report, validate_balance_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=os.path.join(
            REPO_ROOT, "out", "agent", "telemetry", "survivor-balance.json",
        ),
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    report = build_report()
    if arguments.check:
        validate_balance_report(report)
    os.makedirs(os.path.dirname(os.path.abspath(arguments.output)), exist_ok=True)
    temporary = arguments.output + ".tmp." + str(os.getpid())
    with open(temporary, "w", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, arguments.output)
    print(json.dumps({
        "result": "PASS" if report["passed"] else "FAIL",
        "output": os.path.abspath(arguments.output),
        "assertions": report["assertions"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
