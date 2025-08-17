"""
Test runner for the data package tests.
"""

import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_all_tests():
    """Run all data package tests."""
    print("=" * 80)
    print("Running ALL Data Package Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_unit_tests():
    """Run only unit tests."""
    print("=" * 80)
    print("Running Data Package Unit Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data/unit",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_integration_tests():
    """Run only integration tests."""
    print("=" * 80)
    print("Running Data Package Integration Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data/integration",
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
    print("Running Data Package Tests with Coverage")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data",
        "-v",
        "--tb=short",
        "--color=yes",
        "--cov=app.strategy_builder.data",
        "--cov-report=term-missing",
        "--cov-report=html:tests/data/coverage_report"
    ])
    
    print("\nCoverage report generated in: tests/data/coverage_report/index.html")
    
    return exit_code


def run_performance_tests():
    """Run performance-related tests."""
    print("=" * 80)
    print("Running Data Package Performance Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data",
        "-v",
        "--tb=short",
        "--color=yes",
        "-k", "large_dataset or performance"
    ])
    
    return exit_code


def run_validation_tests():
    """Run data validation tests specifically."""
    print("=" * 80)
    print("Running Data Validation Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data/unit/test_validation_serialization.py",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_dto_tests():
    """Run DTO tests specifically."""
    print("=" * 80)
    print("Running DTO Tests")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data/unit/test_dtos.py",
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    return exit_code


def run_verbose():
    """Run tests with verbose output."""
    print("=" * 80)
    print("Running Data Package Tests (Verbose)")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data",
        "-vv",
        "--tb=long",
        "--color=yes",
        "-s"  # Show print statements
    ])
    
    return exit_code


def run_quick():
    """Run tests with minimal output for quick feedback."""
    print("=" * 80)
    print("Running Data Package Tests (Quick)")
    print("=" * 80)
    
    exit_code = pytest.main([
        "tests/data",
        "-q",
        "--tb=line",
        "--color=yes"
    ])
    
    return exit_code


def run_with_markers():
    """Run tests with specific markers."""
    print("=" * 80)
    print("Running Data Package Tests with Markers")
    print("=" * 80)
    
    print("Available markers:")
    print("  -m slow : Run slow tests")
    print("  -m fast : Run fast tests")
    print("  -m integration : Run integration tests")
    print("  -m unit : Run unit tests")
    
    exit_code = pytest.main([
        "tests/data",
        "-v",
        "--tb=short",
        "--color=yes",
        "--markers"
    ])
    
    return exit_code


def run_parallel():
    """Run tests in parallel (requires pytest-xdist)."""
    print("=" * 80)
    print("Running Data Package Tests in Parallel")
    print("=" * 80)
    
    try:
        exit_code = pytest.main([
            "tests/data",
            "-v",
            "--tb=short",
            "--color=yes",
            "-n", "auto"  # Auto-detect number of CPUs
        ])
    except SystemExit as e:
        if "unrecognized arguments: -n" in str(e):
            print("pytest-xdist not installed. Install with: pip install pytest-xdist")
            print("Running tests sequentially instead...")
            exit_code = run_all_tests()
        else:
            exit_code = e.code
    
    return exit_code


def run_with_profiling():
    """Run tests with profiling (requires pytest-profiling)."""
    print("=" * 80)
    print("Running Data Package Tests with Profiling")
    print("=" * 80)
    
    try:
        exit_code = pytest.main([
            "tests/data",
            "-v",
            "--tb=short",
            "--color=yes",
            "--profile"
        ])
    except SystemExit as e:
        if "unrecognized arguments: --profile" in str(e):
            print("pytest-profiling not installed. Install with: pip install pytest-profiling")
            print("Running tests without profiling...")
            exit_code = run_all_tests()
        else:
            exit_code = e.code
    
    return exit_code


def main():
    """Main entry point for test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run data package tests")
    parser.add_argument(
        "--mode",
        choices=[
            "all", "unit", "integration", "coverage", "performance", 
            "validation", "dto", "verbose", "quick", "markers", 
            "parallel", "profiling"
        ],
        default="all",
        help="Test mode to run"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Specific test file or test case to run"
    )
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List all available tests without running them"
    )
    
    args = parser.parse_args()
    
    if args.list_tests:
        print("=" * 80)
        print("Available Tests in Data Package")
        print("=" * 80)
        pytest.main([
            "tests/data",
            "--collect-only",
            "-q"
        ])
        return 0
    
    if args.test:
        exit_code = run_specific_test(args.test)
    elif args.mode == "unit":
        exit_code = run_unit_tests()
    elif args.mode == "integration":
        exit_code = run_integration_tests()
    elif args.mode == "coverage":
        exit_code = run_with_coverage()
    elif args.mode == "performance":
        exit_code = run_performance_tests()
    elif args.mode == "validation":
        exit_code = run_validation_tests()
    elif args.mode == "dto":
        exit_code = run_dto_tests()
    elif args.mode == "verbose":
        exit_code = run_verbose()
    elif args.mode == "quick":
        exit_code = run_quick()
    elif args.mode == "markers":
        exit_code = run_with_markers()
    elif args.mode == "parallel":
        exit_code = run_parallel()
    elif args.mode == "profiling":
        exit_code = run_with_profiling()
    else:
        exit_code = run_all_tests()
    
    if exit_code == 0:
        print("\n[PASS] All tests passed!")
    else:
        print(f"\n[FAIL] Tests failed with exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())