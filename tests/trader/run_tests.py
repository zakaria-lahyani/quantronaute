"""
Test runner for the trader package tests.
"""

import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_all_tests():
    """Run all trader tests."""
    print("=" * 80)
    print("Running ALL Trader Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/trader",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_unit_tests():
    """Run only unit tests."""
    print("=" * 80)
    print("Running Trader Unit Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/trader/unit",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_integration_tests():
    """Run only integration tests."""
    print("=" * 80)
    print("Running Trader Integration Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/trader/integration",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_specific_test(test_path):
    """Run a specific test file or test case."""
    print("=" * 80)
    print(f"Running Specific Test: {test_path}")
    print("=" * 80)
    
    exit_code = pytest.main([
        test_path,
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_with_coverage():
    """Run tests with coverage report."""
    print("=" * 80)
    print("Running Trader Tests with Coverage")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/trader",
        "-v",
        "--tb=short",
        "--color=yes",
        "--cov=app.trader",
        "--cov-report=term-missing",
        "--cov-report=html:tests/trader/coverage_report"
    ])
    
    print("\nCoverage report generated in: tests/trader/coverage_report/index.html")
    
    return exit_code


def run_verbose():
    """Run tests with verbose output."""
    print("=" * 80)
    print("Running Trader Tests (Verbose)")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/trader",
        "-vv",
        "--tb=long",
        "--color=yes",
        "-s"  # Show print statements
    ])
    
    return exit_code


def main():
    """Main entry point for test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run trader package tests")
    parser.add_argument(
        "--mode",
        choices=["all", "unit", "integration", "coverage", "verbose"],
        default="all",
        help="Test mode to run"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Specific test file or test case to run"
    )
    
    args = parser.parse_args()
    
    if args.test:
        exit_code = run_specific_test(args.test)
    elif args.mode == "unit":
        exit_code = run_unit_tests()
    elif args.mode == "integration":
        exit_code = run_integration_tests()
    elif args.mode == "coverage":
        exit_code = run_with_coverage()
    elif args.mode == "verbose":
        exit_code = run_verbose()
    else:
        exit_code = run_all_tests()
    
    if exit_code == 0:
        print("\n[PASS] All tests passed!")
    else:
        print(f"\n[FAIL] Tests failed with exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())