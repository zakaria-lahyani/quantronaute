"""
Quick test runner for the core functionality.
Tests the most important components to verify they work.
"""

import subprocess
import sys

# List of core tests to run
CORE_TESTS = [
    "tests/trader/components/test_exit_manager.py::TestExitManager::test_process_exits_successful_long_exit",
    "tests/trader/components/test_duplicate_filter.py::TestDuplicateFilter::test_filter_entries_duplicate_in_pending_orders",
    "tests/trader/components/test_order_executor.py::TestOrderExecutor::test_execute_entries_successful",
    "tests/trader/components/test_order_executor.py::TestOrderExecutor::test_execute_entries_multiple_risk_entries",
    "tests/trader/components/test_risk_monitor.py::TestRiskMonitor::test_check_catastrophic_loss_limit_breach",
    "tests/trader/components/test_pnl_calculator.py::TestPnLCalculator::test_calculate_floating_pnl_with_positions"
]

def run_core_tests():
    """Run core functionality tests."""
    print("🧪 Running Core Functionality Tests...")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test in CORE_TESTS:
        print(f"\n🔍 Testing: {test.split('::')[-1]}")
        
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest", test, "-v", "--tb=no", "-q"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ PASSED")
                passed += 1
            else:
                print("❌ FAILED")
                if result.stdout:
                    print(f"   Output: {result.stdout.strip()}")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All core functionality tests PASSED!")
        print("✨ Your single responsibility architecture is working correctly!")
    else:
        print(f"⚠️  {failed} tests need attention")
        
    return failed == 0

if __name__ == "__main__":
    success = run_core_tests()
    sys.exit(0 if success else 1)