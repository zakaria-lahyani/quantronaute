"""
Centralized warnings configuration for the application.
"""

import warnings
import logging

logger = logging.getLogger(__name__)

def configure_warnings():
    """
    Configure application-wide warning filters.
    Call this early in your application startup.
    """
    
    # Suppress ast.Str deprecation warning from dependencies
    warnings.filterwarnings(
        "ignore",
        message="ast.Str is deprecated and will be removed in Python 3.14; use ast.Constant instead",
        category=DeprecationWarning
    )
    
    # You can add more specific warning filters here
    # Example: Suppress pandas future warnings if they become noisy
    # warnings.filterwarnings("ignore", category=pandas.errors.PerformanceWarning)
    
    # Log that warnings have been configured
    logger.info("Warning filters configured")

def configure_test_warnings():
    """
    Configure warnings for test environment.
    More permissive to catch potential issues.
    """
    
    # In tests, you might want to be more strict
    # Only suppress the most problematic warnings
    warnings.filterwarnings(
        "ignore",
        message="ast.Str is deprecated.*",
        category=DeprecationWarning
    )
    
    logger.debug("Test warning filters configured")

# Auto-configure warnings when this module is imported
configure_warnings()