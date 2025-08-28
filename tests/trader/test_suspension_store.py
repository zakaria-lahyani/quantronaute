"""
Unit tests for SuspensionStore.
"""

import pytest
from unittest.mock import Mock

from app.trader.suspension_store import SuspensionStore, SuspendedItem


class TestSuspensionStore:
    """Test cases for SuspensionStore."""
    
    def test_init_empty_store(self):
        """Test SuspensionStore initialization."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        assert store.is_empty()
        assert store.count() == 0
        assert store.all() == []
    
    def test_add_suspended_item(self):
        """Test adding a suspended item."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        item: SuspendedItem = {
            'ticket': 12345,
            'kind': 'pending_order',
            'original_sl': 1.1000,
            'original_tp': 1.1200,
            'symbol': 'EURUSD',
            'order_type': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1.1050,
            'magic': 123456
        }
        
        store.add(item)
        
        assert not store.is_empty()
        assert store.count() == 1
        assert store.has_ticket(12345)
        assert item in store.all()
    
    def test_add_duplicate_ticket(self):
        """Test adding item with duplicate ticket."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        item1: SuspendedItem = {
            'ticket': 12345,
            'kind': 'pending_order',
            'original_sl': None,
            'original_tp': None,
            'symbol': 'EURUSD',
            'order_type': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1.1050,
            'magic': 123456
        }
        
        item2: SuspendedItem = {
            'ticket': 12345,  # Same ticket
            'kind': 'position_sl_tp',
            'original_sl': 1.1000,
            'original_tp': 1.1200,
            'symbol': 'EURUSD',
            'order_type': None,
            'volume': None,
            'price': None,
            'magic': 123456
        }
        
        store.add(item1)
        store.add(item2)  # Should be ignored
        
        assert store.count() == 1
        logger.warning.assert_called_with("Ticket 12345 already exists in suspension store")
    
    def test_get_by_kind(self):
        """Test filtering items by kind."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        pending_item: SuspendedItem = {
            'ticket': 12345,
            'kind': 'pending_order',
            'original_sl': None,
            'original_tp': None,
            'symbol': 'EURUSD',
            'order_type': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1.1050,
            'magic': 123456
        }
        
        position_item: SuspendedItem = {
            'ticket': 67890,
            'kind': 'position_sl_tp',
            'original_sl': 1.1000,
            'original_tp': 1.1200,
            'symbol': 'EURUSD',
            'order_type': None,
            'volume': None,
            'price': None,
            'magic': 123456
        }
        
        store.add(pending_item)
        store.add(position_item)
        
        pending_orders = store.get_by_kind('pending_order')
        position_sl_tp = store.get_by_kind('position_sl_tp')
        
        assert len(pending_orders) == 1
        assert len(position_sl_tp) == 1
        assert pending_orders[0] == pending_item
        assert position_sl_tp[0] == position_item
    
    def test_get_by_symbol(self):
        """Test filtering items by symbol."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        eurusd_item: SuspendedItem = {
            'ticket': 12345,
            'kind': 'pending_order',
            'original_sl': None,
            'original_tp': None,
            'symbol': 'EURUSD',
            'order_type': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1.1050,
            'magic': 123456
        }
        
        gbpusd_item: SuspendedItem = {
            'ticket': 67890,
            'kind': 'pending_order',
            'original_sl': None,
            'original_tp': None,
            'symbol': 'GBPUSD',
            'order_type': 'SELL_LIMIT',
            'volume': 0.2,
            'price': 1.2500,
            'magic': 123456
        }
        
        store.add(eurusd_item)
        store.add(gbpusd_item)
        
        eurusd_items = store.get_by_symbol('EURUSD')
        gbpusd_items = store.get_by_symbol('GBPUSD')
        
        assert len(eurusd_items) == 1
        assert len(gbpusd_items) == 1
        assert eurusd_items[0] == eurusd_item
        assert gbpusd_items[0] == gbpusd_item
    
    def test_remove_ticket(self):
        """Test removing a specific ticket."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        item: SuspendedItem = {
            'ticket': 12345,
            'kind': 'pending_order',
            'original_sl': None,
            'original_tp': None,
            'symbol': 'EURUSD',
            'order_type': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1.1050,
            'magic': 123456
        }
        
        store.add(item)
        assert store.has_ticket(12345)
        
        success = store.remove_ticket(12345)
        assert success
        assert not store.has_ticket(12345)
        assert store.is_empty()
        
        # Try removing non-existent ticket
        success = store.remove_ticket(99999)
        assert not success
    
    def test_clear(self):
        """Test clearing all items."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        # Add multiple items
        for i in range(3):
            item: SuspendedItem = {
                'ticket': 12345 + i,
                'kind': 'pending_order',
                'original_sl': None,
                'original_tp': None,
                'symbol': 'EURUSD',
                'order_type': 'BUY_LIMIT',
                'volume': 0.1,
                'price': 1.1050,
                'magic': 123456
            }
            store.add(item)
        
        assert store.count() == 3
        
        store.clear()
        
        assert store.is_empty()
        assert store.count() == 0
        logger.info.assert_called_with("Cleared 3 items from suspension store")
    
    def test_get_summary(self):
        """Test getting summary of items by kind."""
        logger = Mock()
        store = SuspensionStore(logger)
        
        # Add 2 pending orders and 1 position SL/TP
        for i in range(2):
            pending_item: SuspendedItem = {
                'ticket': 12345 + i,
                'kind': 'pending_order',
                'original_sl': None,
                'original_tp': None,
                'symbol': 'EURUSD',
                'order_type': 'BUY_LIMIT',
                'volume': 0.1,
                'price': 1.1050,
                'magic': 123456
            }
            store.add(pending_item)
        
        position_item: SuspendedItem = {
            'ticket': 67890,
            'kind': 'position_sl_tp',
            'original_sl': 1.1000,
            'original_tp': 1.1200,
            'symbol': 'EURUSD',
            'order_type': None,
            'volume': None,
            'price': None,
            'magic': 123456
        }
        store.add(position_item)
        
        summary = store.get_summary()
        
        assert summary['total'] == 3
        assert summary['pending_order'] == 2
        assert summary['position_sl_tp'] == 1
    
    def test_store_with_default_logger(self):
        """Test store creation with default logger."""
        store = SuspensionStore()
        
        item: SuspendedItem = {
            'ticket': 12345,
            'kind': 'pending_order',
            'original_sl': None,
            'original_tp': None,
            'symbol': 'EURUSD',
            'order_type': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1.1050,
            'magic': 123456
        }
        
        # Should work without errors
        store.add(item)
        assert store.count() == 1