"""
Comprehensive test runner for entry manager tests.
"""

import sys
import os
from pathlib import Path
import subprocess
import argparse
from typing import List, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def run_command(command: List[str], description: str) -> int:
    """Run a command and return the exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print('='*60)
    
    result = subprocess.run(command, capture_output=False)
    
    if result.returncode == 0:
        print(f"[PASS] {description} - PASSED")
    else:
        print(f"[FAIL] {description} - FAILED")
    
    return result.returncode


def install_dependencies():
    """Install required test dependencies."""
    dependencies = [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-mock>=3.10.0",
        "pytest-benchmark>=4.0.0"
    ]
    
    print("Installing test dependencies...")
    for dep in dependencies:
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[OK] Installed {dep}")
            else:
                print(f"[WARN] Failed to install {dep}: {result.stderr}")
        except Exception as e:
            print(f"[ERROR] Error installing {dep}: {e}")


def run_unit_tests() -> int:
    """Run all unit tests."""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/entry_manager/unit/",
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ], "Unit Tests")


def run_integration_tests() -> int:
    """Run all integration tests."""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/entry_manager/integration/",
        "-v",
        "--tb=short",
        "-x"
    ], "Integration Tests")


def run_all_tests() -> int:
    """Run all tests."""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/entry_manager/",
        "-v",
        "--tb=short"
    ], "All Tests")


def run_tests_with_coverage() -> int:
    """Run tests with coverage reporting."""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/entry_manager/",
        "--cov=app.entry_manager",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=80",
        "-v"
    ], "Tests with Coverage")


def run_performance_tests() -> int:
    """Run performance tests."""
    return run_command([
        sys.executable, "-m", "pytest",
        "tests/entry_manager/",
        "-m", "performance",
        "--benchmark-only",
        "-v"
    ], "Performance Tests")


def run_specific_test(test_path: str) -> int:
    """Run a specific test file or function."""
    return run_command([
        sys.executable, "-m", "pytest",
        test_path,
        "-v",
        "--tb=long"
    ], f"Specific Test: {test_path}")


def run_smoke_tests() -> int:
    """Run quick smoke tests to verify basic functionality."""
    print("\n[TEST] Running Smoke Tests...")
    
    try:
        # Import key components to verify they work
        from app.entry_manager.manager import EntryManager
        from app.entry_manager.position_sizing.factory import create_position_sizer
        from app.entry_manager.stop_loss.factory import create_stop_loss_calculator
        from app.entry_manager.take_profit.factory import create_take_profit_calculator
        print("[OK] All imports successful")
        
        # Test basic factory creation
        from app.strategy_builder.core.domain.models import (
            PositionSizing, FixedStopLoss, FixedTakeProfit
        )
        from app.strategy_builder.core.domain.enums import PositionSizingTypeEnum
        
        # Test position sizer
        ps_config = PositionSizing(type=PositionSizingTypeEnum.FIXED, value=1000.0)
        sizer = create_position_sizer(ps_config)
        size = sizer.calculate_position_size(entry_price=1.1000)
        assert abs(size - 1000.0) < 0.0001
        print("[OK] Position sizing works")
        
        # Test stop loss calculator
        sl_config = FixedStopLoss(type="fixed", value=50.0)
        sl_calc = create_stop_loss_calculator(sl_config, pip_value=10000.0)
        sl_result = sl_calc.calculate_stop_loss(entry_price=1.1000, is_long=True)
        expected_sl = 1.1000 - 0.0050
        assert abs(sl_result.level - expected_sl) < 0.0001
        print("[OK] Stop loss calculation works")
        
        # Test take profit calculator
        tp_config = FixedTakeProfit(type="fixed", value=100.0)
        tp_calc = create_take_profit_calculator(tp_config, pip_value=10000.0)
        tp_result = tp_calc.calculate_take_profit(entry_price=1.1000, is_long=True)
        expected_tp = 1.1000 + 0.0100
        assert abs(tp_result.level - expected_tp) < 0.0001
        print("[OK] Take profit calculation works")
        
        print("[SUCCESS] All smoke tests passed!")
        return 0
        
    except Exception as e:
        print(f"[ERROR] Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def run_linting() -> int:
    """Run code linting if available."""
    linters = [
        (["python", "-m", "flake8", "app/entry_manager/"], "Flake8 Linting"),
        (["python", "-m", "black", "--check", "app/entry_manager/"], "Black Formatting Check"),
        (["python", "-m", "mypy", "app/entry_manager/"], "MyPy Type Checking")
    ]
    
    exit_codes = []
    for command, description in linters:
        try:
            exit_code = run_command(command, description)
            exit_codes.append(exit_code)
        except FileNotFoundError:
            print(f"[WARN] Skipping {description} - tool not installed")
            
    return max(exit_codes) if exit_codes else 0


def generate_test_report():
    """Generate a comprehensive test report."""
    print("\n[INFO] Generating Test Report...")
    
    report_commands = [
        ([
            sys.executable, "-m", "pytest",
            "tests/entry_manager/",
            "--html=test_report.html",
            "--self-contained-html"
        ], "HTML Test Report"),
        ([
            sys.executable, "-m", "pytest",
            "tests/entry_manager/",
            "--junitxml=test_results.xml"
        ], "JUnit XML Report")
    ]
    
    for command, description in report_commands:
        try:
            run_command(command, description)
        except Exception as e:
            print(f"[WARN] Failed to generate {description}: {e}")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Entry Manager Test Runner")
    parser.add_argument(
        "command",
        choices=[
            "smoke", "unit", "integration", "all", "coverage", 
            "performance", "lint", "report", "install", "specific"
        ],
        help="Test command to run"
    )
    parser.add_argument(
        "--test-path",
        help="Specific test path for 'specific' command"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies before running tests"
    )
    
    args = parser.parse_args()
    
    if args.install_deps:
        install_dependencies()
    
    exit_code = 0
    
    if args.command == "smoke":
        exit_code = run_smoke_tests()
    elif args.command == "unit":
        exit_code = run_unit_tests()
    elif args.command == "integration":
        exit_code = run_integration_tests()
    elif args.command == "all":
        exit_code = run_all_tests()
    elif args.command == "coverage":
        exit_code = run_tests_with_coverage()
    elif args.command == "performance":
        exit_code = run_performance_tests()
    elif args.command == "lint":
        exit_code = run_linting()
    elif args.command == "report":
        generate_test_report()
    elif args.command == "install":
        install_dependencies()
    elif args.command == "specific":
        if not args.test_path:
            print("[ERROR] --test-path required for 'specific' command")
            exit_code = 1
        else:
            exit_code = run_specific_test(args.test_path)
    
    print(f"\n{'='*60}")
    if exit_code == 0:
        print("[SUCCESS] TEST EXECUTION COMPLETED SUCCESSFULLY!")
    else:
        print("[ERROR] TEST EXECUTION FAILED!")
        print("Please review the test output above for details.")
    print(f"{'='*60}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())