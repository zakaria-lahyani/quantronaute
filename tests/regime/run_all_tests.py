"""Run all regime detection tests."""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def run_all_tests():
    """Discover and run all tests in the regime directory."""
    
    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Discover all test files
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern='test_*.py')
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[FAILED] Some tests failed.")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # First, generate test data if needed
    from generate_test_data import generate_test_data_file, generate_minimal_test_data
    
    print("Generating test data files...")
    print("="*70)
    
    try:
        generate_test_data_file()
        generate_minimal_test_data()
        print("\n[SUCCESS] Test data generated successfully!")
    except Exception as e:
        print(f"\n[ERROR] Error generating test data: {e}")
    
    print("\n" + "="*70)
    print("Running all regime detection tests...")
    print("="*70 + "\n")
    
    success = run_all_tests()
    sys.exit(0 if success else 1)