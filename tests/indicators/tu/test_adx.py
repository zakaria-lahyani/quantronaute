import numpy as np
from app.indicators.incremental.adx import ADX

class TestADX:
    """
    Unit tests for the ADX (Average Directional Index) class.

    Test Cases Covered:
    - Comparison of incremental vs batch update accuracy
    - Flat market data (constant OHLC)
    - Handling of insufficient data (fewer than `period` bars)
    - Capping of DI values (plus_di, minus_di) and ADX itself
    """

    def run_incremental_adx(self, high, low, close, period=14, max_di=100.0):
        """Helper method to compute ADX incrementally over a dataset."""
        adx_calc = ADX(period=period, max_di=max_di)
        results = []
        for h, l, c in zip(high, low, close):
            results.append(adx_calc.update(h, l, c))
        return results

    def test_incremental_vs_batch(self):
        """
        Test that the incremental update and batch update produce similar results.

        This test generates random OHLC data and compares the incremental results
        against the vectorized batch implementation, allowing for minor floating-point
        differences.
        """
        np.random.seed(42)
        size = 100
        high = np.random.uniform(100, 120, size)
        low = high - np.random.uniform(1, 5, size)
        close = low + np.random.uniform(0.5, 4, size)

        adx_obj = ADX(period=14)
        inc_results = self.run_incremental_adx(high, low, close, period=14)
        batch_results = adx_obj.batch_update(high, low, close)

        inc_filtered = np.array([r if r is not None else (np.nan, np.nan, np.nan) for r in inc_results])
        inc_adx, inc_plus, inc_minus = inc_filtered.T
        batch_adx, batch_plus, batch_minus = batch_results

        for i in range(30, size):
            assert np.isclose(inc_adx[i], batch_adx[i], atol=1e-4, equal_nan=True)
            assert np.isclose(inc_plus[i], batch_plus[i], atol=1e-4, equal_nan=True)
            assert np.isclose(inc_minus[i], batch_minus[i], atol=1e-4, equal_nan=True)

    def test_flat_data(self):
        """
        Test that the ADX implementation handles flat price data correctly.

        ADX and DIs should remain within [0, 100] even when there's no price change.
        """
        high = [100.0] * 50
        low = [99.0] * 50
        close = [99.5] * 50

        results = self.run_incremental_adx(high, low, close, period=14)

        for res in results:
            if res:
                adx, plus_di, minus_di = res
                assert adx <= 100
                assert 0 <= plus_di <= 100
                assert 0 <= minus_di <= 100

    def test_insufficient_data(self):
        """
        Test that ADX returns None for the first `period`-1 updates.

        Ensures that premature results are not emitted before smoothing begins.
        """
        high = [110, 111, 112]
        low = [109, 108, 107]
        close = [109.5, 110.5, 111.5]

        adx = ADX(period=14)
        results = [adx.update(h, l, c) for h, l, c in zip(high, low, close)]

        assert all(r is None for r in results)

    def test_value_capping(self):
        """
        Test that DI values are capped by `max_di` and ADX is within theoretical bounds.

        Ensures numerical stability during extreme trends.
        """
        high = [100, 150, 200, 250, 300] * 5
        low = [99, 140, 190, 240, 290] * 5
        close = [99.5, 145, 195, 245, 295] * 5

        results = self.run_incremental_adx(high, low, close, period=14, max_di=80.0)

        for res in results:
            if res:
                adx, plus_di, minus_di = res
                assert 0 <= plus_di <= 80
                assert 0 <= minus_di <= 80
                assert 0 <= adx <= 100
