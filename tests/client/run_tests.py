#!/usr/bin/env python3
"""
Test runner for MT5 client tests.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False, pattern=None):
    """Run client tests with specified options."""
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test paths based on type
    if test_type == "unit":
        cmd.append("tests/client/mt5/unit/")
    elif test_type == "integration":
        cmd.append("tests/client/mt5/integration/")
    elif test_type == "models":
        cmd.append("tests/client/mt5/unit/test_models.py")
    elif test_type == "client":
        cmd.append("tests/client/mt5/unit/test_client.py")
    elif test_type == "base":
        cmd.append("tests/client/mt5/unit/test_base_client.py")
    elif test_type == "utils":
        cmd.append("tests/client/mt5/unit/test_utils.py")
    elif test_type == "account":
        cmd.append("tests/client/mt5/unit/test_account_client.py")
    elif test_type == "positions":
        cmd.append("tests/client/mt5/unit/test_positions_client.py")
    else:  # all
        cmd.append("tests/client/")
    
    # Add pattern filter if provided
    if pattern:
        cmd.extend(["-k", pattern])
    
    # Add verbose output if requested
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=app.clients",
            "--cov-report=html:htmlcov/client",
            "--cov-report=term-missing",
            "--cov-branch"
        ])
    
    # Add other useful options
    cmd.extend([
        "--tb=short",  # Shorter tracebacks
        "--strict-markers",  # Strict marker handling
        "--disable-warnings",  # Disable warnings for cleaner output
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Run MT5 client tests")
    
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "models", "client", "base", "utils", "account", "positions"],
        help="Type of tests to run (default: all)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    
    parser.add_argument(
        "-k", "--pattern",
        help="Run tests matching pattern"
    )
    
    args = parser.parse_args()
    
    # Display banner
    print("MT5 Client Test Runner")
    print("=" * 60)
    print(f"Test type: {args.type}")
    if args.pattern:
        print(f"Pattern: {args.pattern}")
    if args.coverage:
        print("Coverage: Enabled")
    print()
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        pattern=args.pattern
    )
    
    # Display results
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("All tests PASSED!")
        if args.coverage:
            print("Coverage report generated in htmlcov/client/")
    else:
        print("Some tests FAILED!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()