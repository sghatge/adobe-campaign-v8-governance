import argparse
import json
from pathlib import Path
from .engine import evaluate, load_json


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic campaign pre-flight QA"
    )
    parser.add_argument("campaign", help="Campaign JSON input")
    parser.add_argument(
        "--policy",
        default="config/policy.json",
        help="Policy JSON path"
    )
    parser.add_argument(
        "--output",
        default="reports/latest-report.json",
        help="Evidence report path"
    )
    args = parser.parse_args()

    campaign = load_json(args.campaign)
    policy = load_json(args.policy)
    report = evaluate(campaign, policy)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))

    if report["decision"] == "BLOCK":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
