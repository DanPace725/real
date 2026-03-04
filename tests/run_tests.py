"""
Phase 3 test runner.

Usage:
    python tests/run_tests.py              # run all tests, verbose
    python tests/run_tests.py --fast       # skip the integration test
    python tests/run_tests.py --list       # list test names and exit
    python tests/run_tests.py -k PATTERN  # run tests matching substring

The suite is designed to run from the project root (Phase 2/), since
all REAL imports use `real.*` paths.
"""

from __future__ import annotations

import argparse
import sys
import time
import unittest
from pathlib import Path

# Ensure project root is on sys.path so `real.*` imports work
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Import all test classes
from tests.test_phase3 import (
    TestWorldPruning,
    TestAVIAStaging,
    TestRegulatoryMesh,
    TestMetabolicBudgeting,
    TestEnvironmentDynamics,
    TestFullRunIntegration,
)

_ALL_CLASSES = [
    TestWorldPruning,
    TestAVIAStaging,
    TestRegulatoryMesh,
    TestMetabolicBudgeting,
    TestEnvironmentDynamics,
    TestFullRunIntegration,
]

_FAST_CLASSES = [
    TestWorldPruning,
    TestAVIAStaging,
    TestRegulatoryMesh,
    TestMetabolicBudgeting,
    TestEnvironmentDynamics,
]


def _collect(classes, pattern=None):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in classes:
        loaded = loader.loadTestsFromTestCase(cls)
        if pattern:
            loaded = unittest.TestSuite(
                t for t in loaded
                if pattern.lower() in t.id().lower()
            )
        suite.addTests(loaded)
    return suite


def _list_tests(classes):
    loader = unittest.TestLoader()
    for cls in classes:
        for t in loader.loadTestsFromTestCase(cls):
            print(t.id())


def main():
    parser = argparse.ArgumentParser(description="Phase 3 test runner")
    parser.add_argument("--fast", action="store_true",
                        help="Skip long integration tests (~20s)")
    parser.add_argument("--list", action="store_true",
                        help="List test names and exit")
    parser.add_argument("-k", "--pattern", default=None,
                        help="Only run tests whose name contains PATTERN")
    args = parser.parse_args()

    classes = _FAST_CLASSES if args.fast else _ALL_CLASSES

    if args.list:
        _list_tests(classes)
        return 0

    suite = _collect(classes, pattern=args.pattern)
    test_count = suite.countTestCases()

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  REAL Phase 3 Test Suite")
    print(f"  Tests collected: {test_count}")
    print(f"  Mode: {'fast (no integration)' if args.fast else 'full'}")
    print(f"{sep}\n")

    t0 = time.time()
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    elapsed = time.time() - t0

    print(f"\n{sep}")
    print(f"  Ran {result.testsRun} tests in {elapsed:.1f}s")
    if result.wasSuccessful():
        print("  Result: ALL PASSED (OK)")
    else:
        n_fail = len(result.failures)
        n_err = len(result.errors)
        print(f"  Result: FAILED -- {n_fail} failures, {n_err} errors")
    print(f"{sep}\n")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
