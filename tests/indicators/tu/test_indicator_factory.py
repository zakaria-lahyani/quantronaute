import pytest
from app.indicators.indicator_factory import IndicatorFactory
from app.indicators.indicator_handler import IndicatorHandler


class TestIndicatorFactory:

    class DummyMACD:
        def __init__(self, fast=12, slow=26, signal=9):
            self.fast = fast
            self.slow = slow
            self.signal = signal

    class DummyRSI:
        def __init__(self, period=14):
            self.period = period

    @pytest.fixture(autouse=True)
    def dummy_indicators(self):
        return {
            'macd': self.DummyMACD,
            'rsi': self.DummyRSI
        }

    @pytest.fixture(autouse=True)
    def dummy_defaults(self):
        return {
            'macd': {'fast': 12, 'slow': 26, 'signal': 9},
            'rsi': {'period': 14}
        }

    def test_merges_params_correctly(self, monkeypatch, dummy_indicators, dummy_defaults):
        monkeypatch.setattr('app.indicators.indicator_factory.INDICATOR_CLASSES', dummy_indicators)
        monkeypatch.setattr('app.indicators.indicator_factory.DEFAULT_PARAMETERS', dummy_defaults)

        config = {'macd_1h': {'slow': 30, 'signal': 7}}
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()

        assert 'macd_1h' in handlers
        handler = handlers['macd_1h']
        assert isinstance(handler, IndicatorHandler)

        indicator = handler.indicator
        assert isinstance(indicator, self.DummyMACD)
        assert indicator.fast == 12  # from default
        assert indicator.slow == 30  # overridden
        assert indicator.signal == 7  # overridden

    def test_creates_multiple_indicators(self, monkeypatch, dummy_indicators, dummy_defaults):
        monkeypatch.setattr('app.indicators.indicator_factory.INDICATOR_CLASSES', dummy_indicators)
        monkeypatch.setattr('app.indicators.indicator_factory.DEFAULT_PARAMETERS', dummy_defaults)

        config = {
            'rsi_15m': {},
            'rsi_1h': {'period': 21},
            'macd_4h': {'signal': 6}
        }

        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()

        assert set(handlers.keys()) == {'rsi_15m', 'rsi_1h', 'macd_4h'}
        assert handlers['rsi_15m'].indicator.period == 14
        assert handlers['rsi_1h'].indicator.period == 21
        assert handlers['macd_4h'].indicator.signal == 6

    def test_skips_unknown_indicator(self, monkeypatch, dummy_indicators, dummy_defaults):
        monkeypatch.setattr('app.indicators.indicator_factory.INDICATOR_CLASSES', dummy_indicators)
        monkeypatch.setattr('app.indicators.indicator_factory.DEFAULT_PARAMETERS', dummy_defaults)

        config = {
            'unknown_5m': {'foo': 1},
            'rsi_1h': {'period': 20}
        }

        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()

        assert 'rsi_1h' in handlers
        assert 'unknown_5m' not in handlers

    def test_end_to_end_factory(self, monkeypatch):
        class DummyStoch:
            def __init__(self, k=14, d=3):
                self.k = k
                self.d = d

        INDICATOR_CLASSES = {'stoch': DummyStoch}
        DEFAULT_PARAMETERS = {'stoch': {'k': 14, 'd': 3}}

        monkeypatch.setattr('app.indicators.indicator_factory.INDICATOR_CLASSES', INDICATOR_CLASSES)
        monkeypatch.setattr('app.indicators.indicator_factory.DEFAULT_PARAMETERS', DEFAULT_PARAMETERS)

        config = {'stoch_1h': {'k': 10}}
        factory = IndicatorFactory(config)
        handlers = factory.create_handlers()

        assert 'stoch_1h' in handlers
        ind = handlers['stoch_1h'].indicator
        assert isinstance(ind, DummyStoch)
        assert ind.k == 10  # overridden
        assert ind.d == 3   # default
