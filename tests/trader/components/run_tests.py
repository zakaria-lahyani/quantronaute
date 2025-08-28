"""
Test runner for trader components.
Run this script to execute all component tests.
"""

import pytest
import sys
import warnings
from pathlib import Path

# Suppress ast.Str deprecation warning during tests
warnings.filterwarnings(
    "ignore",
    message="ast.Str is deprecated and will be removed in Python 3.14; use ast.Constant instead",
    category=DeprecationWarning
)


def run_component_tests():
    """Run all trader component tests."""
    
    # Get the current directory (tests/trader/components)
    current_dir = Path(__file__).parent
    
    # Test configuration
    pytest_args = [
        str(current_dir),  # Run tests in this directory
        "-v",              # Verbose output
        "--tb=short",      # Short traceback format
        "--color=yes",     # Colored output
        # "-x",              # Stop on first failure (optional)
    ]
    
    print("🧪 Running Trader Component Tests...")
    print(f"📁 Test directory: {current_dir}")
    print("-" * 50)
    
    # Run the tests
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_component_tests()
    sys.exit(exit_code)