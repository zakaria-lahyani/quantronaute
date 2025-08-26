"""Unit tests for regime state machine."""

import unittest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.regime.regime_state_machine import RegimeStateMachine, StateMachineState


class TestStateMachineState(unittest.TestCase):
    """Test StateMachineState data structure."""
    
    def test_default_initialization(self):
        """Test default StateMachineState initialization."""
        state = StateMachineState()
        
        self.assertEqual(state.current_regime, "warming_up")
        self.assertIsNone(state.pending_regime)
        self.assertEqual(state.pending_count, 0)
        self.assertEqual(state.transition_countdown, 0)
    
    def test_custom_initialization(self):
        """Test StateMachineState with custom values."""
        state = StateMachineState(
            current_regime="bull_expansion",
            pending_regime="bear_contraction",
            pending_count=2,
            transition_countdown=3
        )
        
        self.assertEqual(state.current_regime, "bull_expansion")
        self.assertEqual(state.pending_regime, "bear_contraction")
        self.assertEqual(state.pending_count, 2)
        self.assertEqual(state.transition_countdown, 3)
    
    def test_state_modification(self):
        """Test that StateMachineState can be modified."""
        state = StateMachineState()
        
        # Modify values
        state.current_regime = "bull_expansion"
        state.pending_regime = "bear_contraction"
        state.pending_count = 1
        state.transition_countdown = 2
        
        self.assertEqual(state.current_regime, "bull_expansion")
        self.assertEqual(state.pending_regime, "bear_contraction")
        self.assertEqual(state.pending_count, 1)
        self.assertEqual(state.transition_countdown, 2)


class TestRegimeStateMachine(unittest.TestCase):
    """Test RegimeStateMachine functionality."""
    
    def test_initialization_default(self):
        """Test RegimeStateMachine default initialization."""
        sm = RegimeStateMachine()
        
        self.assertEqual(sm.persist_n, 2)
        self.assertEqual(sm.transition_bars, 3)
        self.assertIsInstance(sm.state, StateMachineState)
        self.assertEqual(sm.state.current_regime, "warming_up")
    
    def test_initialization_custom(self):
        """Test RegimeStateMachine with custom parameters."""
        sm = RegimeStateMachine(persist_n=5, transition_bars=7)
        
        self.assertEqual(sm.persist_n, 5)
        self.assertEqual(sm.transition_bars, 7)
        self.assertEqual(sm.state.current_regime, "warming_up")


class TestRegimeStateMachineUpdate(TestRegimeStateMachine):
    """Test RegimeStateMachine update functionality."""
    
    def test_first_update_from_warming_up(self):
        """Test first update from warming_up state."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=3)
        
        regime, is_transition = sm.update("bull_expansion")
        
        # Should immediately set regime from warming_up
        self.assertEqual(regime, "bull_expansion")
        self.assertFalse(is_transition)
        self.assertEqual(sm.state.current_regime, "bull_expansion")
        self.assertIsNone(sm.state.pending_regime)
        self.assertEqual(sm.state.pending_count, 0)
    
    def test_first_update_from_none(self):
        """Test first update from None state."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=3)
        sm.state.current_regime = None
        
        regime, is_transition = sm.update("bear_contraction")
        
        # Should immediately set regime from None
        self.assertEqual(regime, "bear_contraction")
        self.assertFalse(is_transition)
        self.assertEqual(sm.state.current_regime, "bear_contraction")
    
    def test_same_regime_update(self):
        """Test update with same regime (no change)."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=3)
        
        # Initialize regime
        sm.update("bull_expansion")
        
        # Update with same regime
        regime, is_transition = sm.update("bull_expansion")
        
        self.assertEqual(regime, "bull_expansion")
        self.assertFalse(is_transition)
        self.assertIsNone(sm.state.pending_regime)
        self.assertEqual(sm.state.pending_count, 0)
    
    def test_new_regime_first_occurrence(self):
        """Test update with new regime (first occurrence)."""
        sm = RegimeStateMachine(persist_n=3, transition_bars=2)
        
        # Initialize regime
        sm.update("bull_expansion")
        
        # Update with new regime
        regime, is_transition = sm.update("bear_contraction")
        
        # Should not change yet, but set pending
        self.assertEqual(regime, "bull_expansion")  # Still current
        self.assertFalse(is_transition)
        self.assertEqual(sm.state.pending_regime, "bear_contraction")
        self.assertEqual(sm.state.pending_count, 1)
    
    def test_new_regime_persistence_required(self):
        """Test that regime change requires persistence."""
        sm = RegimeStateMachine(persist_n=3, transition_bars=2)
        
        # Initialize regime
        sm.update("bull_expansion")
        
        # First occurrence of new regime
        regime1, trans1 = sm.update("bear_contraction")
        self.assertEqual(regime1, "bull_expansion")  # No change yet
        self.assertFalse(trans1)
        
        # Second occurrence of new regime
        regime2, trans2 = sm.update("bear_contraction")
        self.assertEqual(regime2, "bull_expansion")  # Still no change
        self.assertFalse(trans2)
        
        # Third occurrence (meets persistence requirement)
        regime3, trans3 = sm.update("bear_contraction")
        self.assertEqual(regime3, "bear_contraction")  # Should change now
        self.assertTrue(trans3)  # Should be in transition
        
        # Verify state
        self.assertEqual(sm.state.current_regime, "bear_contraction")
        self.assertIsNone(sm.state.pending_regime)
        self.assertEqual(sm.state.pending_count, 0)
        self.assertEqual(sm.state.transition_countdown, 1)  # transition_bars - 1 (decremented)
    
    def test_interrupted_pending_regime(self):
        """Test that pending regime can be interrupted by different regime."""
        sm = RegimeStateMachine(persist_n=3, transition_bars=2)
        
        # Initialize regime
        sm.update("bull_expansion")
        
        # Start pending towards bear_contraction
        sm.update("bear_contraction")
        sm.update("bear_contraction")
        self.assertEqual(sm.state.pending_count, 2)
        
        # Interrupt with different regime
        regime, is_transition = sm.update("neutral_expansion")
        
        # Should reset pending and start new pending
        self.assertEqual(regime, "bull_expansion")  # Still current
        self.assertEqual(sm.state.pending_regime, "neutral_expansion")
        self.assertEqual(sm.state.pending_count, 1)  # Reset to 1
    
    def test_return_to_current_regime_resets_pending(self):
        """Test that returning to current regime resets pending."""
        sm = RegimeStateMachine(persist_n=3, transition_bars=2)
        
        # Initialize regime
        sm.update("bull_expansion")
        
        # Start pending towards new regime
        sm.update("bear_contraction")
        sm.update("bear_contraction")
        self.assertEqual(sm.state.pending_count, 2)
        
        # Return to current regime
        regime, is_transition = sm.update("bull_expansion")
        
        # Should reset pending
        self.assertEqual(regime, "bull_expansion")
        self.assertFalse(is_transition)
        self.assertIsNone(sm.state.pending_regime)
        self.assertEqual(sm.state.pending_count, 0)


class TestTransitionHandling(TestRegimeStateMachine):
    """Test transition countdown handling."""
    
    def test_transition_countdown_decreases(self):
        """Test that transition countdown decreases over time."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=4)
        
        # Initialize and change regime to trigger transition
        sm.update("bull_expansion")
        sm.update("bear_contraction")  # First occurrence
        sm.update("bear_contraction")  # Second occurrence - should trigger change
        
        # Should be in transition  
        regime, is_transition = sm.update("bear_contraction")
        self.assertTrue(is_transition)
        # The countdown decrements AFTER checking is_transition and BEFORE returning
        self.assertEqual(sm.state.transition_countdown, 2)  # 4 - 1 - 1 (decrements each call)
        
        # Continue with same regime
        regime, is_transition = sm.update("bear_contraction")
        self.assertTrue(is_transition)
        self.assertEqual(sm.state.transition_countdown, 1)  # 2 - 1
        
        regime, is_transition = sm.update("bear_contraction")
        self.assertTrue(is_transition)
        self.assertEqual(sm.state.transition_countdown, 0)  # 1 - 1
        
        regime, is_transition = sm.update("bear_contraction")
        self.assertFalse(is_transition)  # Should end transition
        self.assertEqual(sm.state.transition_countdown, 0)
    
    def test_new_regime_change_during_transition(self):
        """Test regime change during existing transition period."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=3)
        
        # Initial regime change
        sm.update("bull_expansion")
        sm.update("bear_contraction")
        sm.update("bear_contraction")  # Triggers change and transition
        
        # Verify in transition
        regime, is_transition = sm.update("bear_contraction")
        self.assertTrue(is_transition)
        self.assertEqual(sm.state.transition_countdown, 1)  # Decremented after check
        
        # Start new regime change during transition
        regime, is_transition = sm.update("neutral_contraction")
        self.assertTrue(is_transition)  # Still in transition from previous change
        self.assertEqual(sm.state.pending_regime, "neutral_contraction")
        self.assertEqual(sm.state.pending_count, 1)
        
        # Complete new regime change
        regime, is_transition = sm.update("neutral_contraction")
        self.assertTrue(is_transition)  # New transition started
        self.assertEqual(regime, "neutral_contraction")
        self.assertEqual(sm.state.transition_countdown, 2)  # New transition countdown - 1
    
    def test_transition_with_zero_transition_bars(self):
        """Test transition behavior with zero transition bars."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=0)
        
        # Trigger regime change
        sm.update("bull_expansion")
        sm.update("bear_contraction")
        regime, is_transition = sm.update("bear_contraction")
        
        # Should change but still be in transition initially (changed=True triggers is_transition)
        # The logic is: return changed or is_transition, where changed=True when regime just changed
        self.assertEqual(regime, "bear_contraction")
        self.assertTrue(is_transition)  # changed=True, so is_transition=True even with 0 transition_bars
        self.assertEqual(sm.state.transition_countdown, 0)
        
        # Next update should not be in transition
        regime2, is_transition2 = sm.update("bear_contraction")
        self.assertEqual(regime2, "bear_contraction") 
        self.assertFalse(is_transition2)  # No longer in transition


class TestEdgeCases(TestRegimeStateMachine):
    """Test edge cases and special scenarios."""
    
    def test_persist_n_one(self):
        """Test state machine with persist_n=1."""
        sm = RegimeStateMachine(persist_n=1, transition_bars=2)
        
        # Initialize regime
        sm.update("bull_expansion")
        
        # First occurrence sets pending, but doesn't change yet
        regime1, is_transition1 = sm.update("bear_contraction")
        self.assertEqual(regime1, "bull_expansion")  # Still previous regime
        self.assertFalse(is_transition1)
        
        # Second occurrence (persist_n=1 means need 1 additional occurrence)
        regime2, is_transition2 = sm.update("bear_contraction")
        self.assertEqual(regime2, "bear_contraction")  # Should change now
        self.assertTrue(is_transition2)
    
    def test_persist_n_zero(self):
        """Test state machine with persist_n=0."""
        sm = RegimeStateMachine(persist_n=0, transition_bars=2)
        
        # Initialize regime
        sm.update("bull_expansion")
        
        # With current implementation, even persist_n=0 requires the regime
        # to appear twice due to the state machine logic structure
        regime1, is_transition1 = sm.update("bear_contraction")
        self.assertEqual(regime1, "bull_expansion")  # Still previous regime
        self.assertFalse(is_transition1)
        
        # Second occurrence should change immediately since pending_count=1 >= persist_n=0  
        regime2, is_transition2 = sm.update("bear_contraction")
        self.assertEqual(regime2, "bear_contraction")
        self.assertTrue(is_transition2)
    
    def test_many_rapid_regime_changes(self):
        """Test rapid succession of different regimes."""
        sm = RegimeStateMachine(persist_n=3, transition_bars=2)
        
        # Initialize
        sm.update("bull_expansion")
        
        # Rapid changes that don't meet persistence
        regimes = ["bear_contraction", "neutral_expansion", "bull_contraction", 
                  "bear_expansion", "neutral_contraction"]
        
        for regime in regimes:
            result_regime, is_transition = sm.update(regime)
            # Should remain bull_expansion since no regime persisted long enough
            self.assertEqual(result_regime, "bull_expansion")
            self.assertFalse(is_transition)
        
        # Final state should show the last regime as pending
        self.assertEqual(sm.state.pending_regime, "neutral_contraction")
        self.assertEqual(sm.state.pending_count, 1)
    
    def test_alternating_regimes(self):
        """Test alternating between two regimes."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=1)
        
        # Initialize
        sm.update("bull_expansion")
        
        # Alternate between two regimes
        for i in range(10):
            if i % 2 == 0:
                regime, is_transition = sm.update("bear_contraction")
            else:
                regime, is_transition = sm.update("neutral_expansion")
        
        # Should never change due to alternation
        self.assertEqual(regime, "bull_expansion")
        self.assertFalse(is_transition)
    
    def test_long_persistence_requirement(self):
        """Test with very long persistence requirement."""
        sm = RegimeStateMachine(persist_n=10, transition_bars=2)
        
        # Initialize
        sm.update("bull_expansion")
        
        # Apply new regime 9 times (not enough)
        for i in range(9):
            regime, is_transition = sm.update("bear_contraction")
            self.assertEqual(regime, "bull_expansion")  # Should not change
            self.assertFalse(is_transition)
        
        self.assertEqual(sm.state.pending_count, 9)
        
        # 10th time should trigger change
        regime, is_transition = sm.update("bear_contraction")
        self.assertEqual(regime, "bear_contraction")
        self.assertTrue(is_transition)


class TestStateMachineIntegration(TestRegimeStateMachine):
    """Test state machine integration and realistic scenarios."""
    
    def test_realistic_regime_sequence(self):
        """Test realistic sequence of regime changes."""
        sm = RegimeStateMachine(persist_n=3, transition_bars=2)
        
        # Simulate realistic trading scenario
        regime_sequence = [
            # Startup
            "bull_expansion", "bull_expansion", "bull_expansion",  # Establish bull trend
            
            # Trending phase
            "bull_expansion", "bull_expansion", "bull_expansion",
            "bull_expansion", "bull_expansion",
            
            # Consolidation
            "bull_contraction", "bull_contraction", "bull_contraction",  # Change to contraction
            "bull_contraction", "bull_contraction",
            
            # Market reversal
            "bear_contraction", "bear_contraction", "bear_contraction",  # Change to bear
            "bear_contraction", "bear_contraction",
            
            # Volatile phase
            "bear_expansion", "bear_expansion", "bear_expansion",  # Change to expansion
            "bear_expansion",
        ]
        
        results = []
        for new_regime in regime_sequence:
            regime, is_transition = sm.update(new_regime)
            results.append((regime, is_transition))
        
        # Verify we had some regime changes
        regime_changes = [i for i, (regime, _) in enumerate(results) 
                         if i > 0 and results[i][0] != results[i-1][0]]
        
        self.assertGreater(len(regime_changes), 0, "Should have some regime changes")
        
        # Verify transitions occurred
        transitions = [is_transition for _, is_transition in results]
        self.assertIn(True, transitions, "Should have some transitions")
    
    def test_state_consistency_after_operations(self):
        """Test that state remains consistent after many operations."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=3)
        
        # Perform many operations
        regimes = ["bull_expansion", "bear_contraction", "neutral_expansion", 
                  "bull_contraction", "bear_expansion"]
        
        for _ in range(100):
            for regime in regimes:
                sm.update(regime)
        
        # State should be consistent
        self.assertIsNotNone(sm.state.current_regime)
        self.assertIsInstance(sm.state.current_regime, str)
        self.assertGreaterEqual(sm.state.pending_count, 0)
        self.assertGreaterEqual(sm.state.transition_countdown, 0)
        
        # Pending count should not exceed persist_n
        self.assertLessEqual(sm.state.pending_count, sm.persist_n)
        
        # Transition countdown should not exceed transition_bars
        self.assertLessEqual(sm.state.transition_countdown, sm.transition_bars)
    
    def test_state_machine_determinism(self):
        """Test that state machine is deterministic."""
        sm1 = RegimeStateMachine(persist_n=2, transition_bars=3)
        sm2 = RegimeStateMachine(persist_n=2, transition_bars=3)
        
        test_sequence = ["bull_expansion", "bear_contraction", "bear_contraction", 
                        "neutral_expansion", "neutral_expansion", "bull_expansion"]
        
        results1 = []
        results2 = []
        
        for regime in test_sequence:
            result1 = sm1.update(regime)
            result2 = sm2.update(regime)
            results1.append(result1)
            results2.append(result2)
        
        # Results should be identical
        self.assertEqual(results1, results2)


class TestStateMachineResetPending(TestRegimeStateMachine):
    """Test _reset_pending method."""
    
    def test_reset_pending_method(self):
        """Test that _reset_pending method works correctly."""
        sm = RegimeStateMachine(persist_n=3, transition_bars=2)
        
        # Set up pending state
        sm.state.pending_regime = "bear_contraction"
        sm.state.pending_count = 2
        
        # Reset pending
        sm._reset_pending()
        
        # Should be reset
        self.assertIsNone(sm.state.pending_regime)
        self.assertEqual(sm.state.pending_count, 0)
    
    def test_reset_pending_called_appropriately(self):
        """Test that _reset_pending is called at appropriate times."""
        sm = RegimeStateMachine(persist_n=2, transition_bars=1)
        
        # Initialize
        sm.update("bull_expansion")
        
        # Create pending state
        sm.update("bear_contraction")
        self.assertIsNotNone(sm.state.pending_regime)
        
        # Return to current regime should reset pending
        sm.update("bull_expansion")
        self.assertIsNone(sm.state.pending_regime)
        self.assertEqual(sm.state.pending_count, 0)


if __name__ == '__main__':
    unittest.main()