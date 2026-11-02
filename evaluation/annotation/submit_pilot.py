"""Create a checksum-verified, append-only snapshot of an annotator submission."""
import argparse
import json
import sys

from evaluation.annotation.submission_integrity import record_submission
from evaluation.annotation.validate_pilot import DEFAULT_PILOT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default=str(DEFAULT_PILOT), help="Pilot folder")
    parser.add_argument("--annotator", required=True, help="Manifest alias, for example annotator_1")
    parser.add_argument("--supersedes", help="Latest prior integrity-manifest path for an intentional revision")
    args = parser.parse_args(argv)
    try:
        result = record_submission(args.directory, args.annotator, supersedes=args.supersedes)
        print(json.dumps(result, indent=2))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("Submission not recorded: {0}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
