"""Run a required stdlib unittest module without treating empty/skip as success.

Usage: python deploy/hosted/tests/run_required.py test_compose_profile.py
"""

import argparse
from pathlib import Path
import sys
import unittest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="one existing test_*.py filename in this directory")
    args = parser.parse_args(argv)
    directory = Path(__file__).resolve().parent
    module = args.module
    if Path(module).name != module or not module.startswith("test_") or not module.endswith(".py"):
        parser.error("requested module must be a test_*.py filename")
    if not (directory / module).is_file():
        parser.error(f"requested module does not exist: {module}")

    suite = unittest.defaultTestLoader.discover(str(directory), pattern=module, top_level_dir=str(directory))
    count = suite.countTestCases()
    if count == 0:
        print(f"REQUIRED TESTS FAILED: zero tests discovered in {module}", file=sys.stderr)
        return 1
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        f"Required tests: discovered={count}, ran={result.testsRun}, "
        f"failures={len(result.failures)}, errors={len(result.errors)}, "
        f"skipped={len(result.skipped)}",
        file=sys.stderr,
    )
    if not result.wasSuccessful() or result.skipped or result.testsRun != count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
