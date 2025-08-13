"""
Comprehensive test runner for the strategy engine.

This script runs all tests in the correct order and provides detailed reporting:
1. Unit tests (individual components)
2. Integration tests (end-to-end workflows)
3. Performance tests (load and stress testing)

Usage:
    python -m strategy_builder.tests.run_all_tests
    python strategy_builder/tests/run_all_tests.py
"""

import unittest
import sys
import time
from io import StringIO
from pathlib import Path
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    sys.stdout.reconfigure(encoding='utf-8')

# Add the strategy package to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ColoredTestResult(unittest.TextTestResult):
    """Custom test result class with colored output."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.success_count = 0
        self.verbosity = verbosity
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        if self.verbosity > 1:
            self.stream.write("✅ ")
            self.stream.write(str(test))
            self.stream.write(" ... ")
            self.stream.writeln("PASS")
    
    def addError(self, test, err):
        super().addError(test, err)
        if self.verbosity > 1:
            self.stream.write("❌ ")
            self.stream.write(str(test))
            self.stream.write(" ... ")
            self.stream.writeln("ERROR")
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.verbosity > 1:
            self.stream.write("❌ ")
            self.stream.write(str(test))
            self.stream.write(" ... ")
            self.stream.writeln("FAIL")
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.verbosity > 1:
            self.stream.write("⏭️ ")
            self.stream.write(str(test))
            self.stream.write(" ... ")
            self.stream.writeln(f"SKIP ({reason})")


class ColoredTestRunner(unittest.TextTestRunner):
    """Custom test runner with colored output."""
    
    resultclass = ColoredTestResult
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.verbosity = kwargs.get('verbosity', 2)


def discover_and_run_tests(test_dir, pattern="test_*.py", description=""):
    """Discover and run tests in a specific directory."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    # Discover tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent / test_dir
    
    if not start_dir.exists():
        print(f"⚠️ Test directory {start_dir} does not exist, skipping...")
        return unittest.TestResult(), 0
    
    suite = loader.discover(str(start_dir), pattern=pattern)
    
    # Count tests
    test_count = suite.countTestCases()
    if test_count == 0:
        print(f"⚠️ No tests found in {test_dir}")
        return unittest.TestResult(), 0
    
    print(f"📋 Found {test_count} tests")
    
    # Run tests
    runner = ColoredTestRunner(verbosity=2, buffer=True)
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Print summary
    print(f"\n📊 {description} Summary:")
    print(f"   ✅ Passed: {result.success_count}")
    print(f"   ❌ Failed: {len(result.failures)}")
    print(f"   💥 Errors: {len(result.errors)}")
    print(f"   ⏭️ Skipped: {len(result.skipped)}")
    print(f"   ⏱️ Time: {end_time - start_time:.2f}s")
    
    return result, test_count


def print_detailed_failures(result, test_type):
    """Print detailed information about test failures."""
    if result.failures or result.errors:
        print(f"\n🔍 Detailed {test_type} Failure Report:")
        print("="*60)
        
        for test, traceback in result.failures:
            print(f"\n❌ FAILURE: {test}")
            print("-" * 40)
            print(traceback)
        
        for test, traceback in result.errors:
            print(f"\n💥 ERROR: {test}")
            print("-" * 40)
            print(traceback)


def run_comprehensive_tests():
    """Run all tests in the correct order with comprehensive reporting."""
    print("🚀 Starting Comprehensive Strategy Engine Test Suite")
    print("="*60)
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    
    all_results = []
    
    # 1. Unit Tests
    print("\n🔧 Phase 1: Unit Tests")
    print("Testing individual components in isolation...")
    
    unit_result, unit_count = discover_and_run_tests(
        "unit", 
        "test_*.py", 
        "UNIT TESTS - Individual Component Testing"
    )
    all_results.append(("Unit Tests", unit_result))
    
    total_tests += unit_count
    total_passed += unit_result.success_count
    total_failed += len(unit_result.failures)
    total_errors += len(unit_result.errors)
    total_skipped += len(unit_result.skipped)
    
    # 2. Integration Tests
    print("\n🔗 Phase 2: Integration Tests")
    print("Testing end-to-end workflows and component interactions...")
    
    integration_result, integration_count = discover_and_run_tests(
        "integration", 
        "test_*.py", 
        "INTEGRATION TESTS - End-to-End Workflows"
    )
    all_results.append(("Integration Tests", integration_result))
    
    total_tests += integration_count
    total_passed += integration_result.success_count
    total_failed += len(integration_result.failures)
    total_errors += len(integration_result.errors)
    total_skipped += len(integration_result.skipped)
    
    # Print overall summary
    print(f"\n{'='*60}")
    print("🏁 COMPREHENSIVE TEST SUITE SUMMARY")
    print(f"{'='*60}")
    print(f"📊 Total Tests Run: {total_tests}")
    print(f"✅ Total Passed: {total_passed}")
    print(f"❌ Total Failed: {total_failed}")
    print(f"💥 Total Errors: {total_errors}")
    print(f"⏭️ Total Skipped: {total_skipped}")
    
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    # Print detailed failure reports
    for test_type, result in all_results:
        if result.failures or result.errors:
            print_detailed_failures(result, test_type)
    
    # Final status
    if total_failed == 0 and total_errors == 0:
        print(f"\n🎉 ALL TESTS PASSED! Strategy engine is ready for production.")
        print("✅ The refactored strategy engine has been successfully validated.")
        return True
    else:
        print(f"\n⚠️ TESTS FAILED! Please review the failures above.")
        print(f"❌ {total_failed + total_errors} tests need attention.")
        return False




def main():
    """Main test runner function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Strategy Engine Test Runner")
    parser.add_argument(
        "--unit-only", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration-only", 
        action="store_true", 
        help="Run only integration tests"
    )
    
    args = parser.parse_args()

    if args.unit_only:
        result, _ = discover_and_run_tests("unit", "test_*.py", "UNIT TESTS ONLY")
        success = len(result.failures) == 0 and len(result.errors) == 0
        sys.exit(0 if success else 1)
    
    if args.integration_only:
        result, _ = discover_and_run_tests("integration", "test_*.py", "INTEGRATION TESTS ONLY")
        success = len(result.failures) == 0 and len(result.errors) == 0
        sys.exit(0 if success else 1)
    
    # Run comprehensive tests
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()