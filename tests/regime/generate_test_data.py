"""Generate test data files for regime detection testing."""

import pandas as pd
import numpy as np
import os


def generate_test_data_file():
    """Generate a test parquet file with various market conditions."""
    np.random.seed(42)
    
    data = []
    
    # Phase 1: Strong uptrend (200 bars)
    base = 100
    for i in range(200):
        trend = base + i * 0.2
        noise = np.random.normal(0, 0.5)
        close = trend + noise
        
        open_price = close - np.random.uniform(-0.3, 0.3)
        high = max(open_price, close) + np.random.uniform(0, 0.5)
        low = min(open_price, close) - np.random.uniform(0, 0.5)
        
        data.append({
            'time': pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(1000, 5000)
        })
    
    # Phase 2: High volatility ranging (200 bars)
    base = close
    for i in range(200):
        cycle = 15 * np.sin(i * 2 * np.pi / 30)
        noise = np.random.normal(0, 3)
        close = base + cycle + noise
        
        open_price = close - np.random.uniform(-2, 2)
        high = max(open_price, close) + np.random.uniform(0, 3)
        low = min(open_price, close) - np.random.uniform(0, 3)
        
        data.append({
            'time': pd.Timestamp('2024-01-09') + pd.Timedelta(hours=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(3000, 10000)
        })
    
    # Phase 3: Strong downtrend (200 bars)
    base = close
    for i in range(200):
        trend = base - i * 0.3
        noise = np.random.normal(0, 0.7)
        close = trend + noise
        
        open_price = close + np.random.uniform(-0.3, 0.3)
        high = max(open_price, close) + np.random.uniform(0, 0.5)
        low = min(open_price, close) - np.random.uniform(0, 0.5)
        
        data.append({
            'time': pd.Timestamp('2024-01-17') + pd.Timedelta(hours=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(2000, 8000)
        })
    
    # Phase 4: Low volatility consolidation (200 bars)
    base = close
    for i in range(200):
        noise = np.random.normal(0, 0.2)
        close = base + noise
        
        open_price = close - np.random.uniform(-0.1, 0.1)
        high = max(open_price, close) + np.random.uniform(0, 0.15)
        low = min(open_price, close) - np.random.uniform(0, 0.15)
        
        data.append({
            'time': pd.Timestamp('2024-01-25') + pd.Timedelta(hours=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(500, 1500)
        })
    
    # Phase 5: Recovery with increasing volatility (200 bars)
    base = close
    for i in range(200):
        trend = base + i * 0.15
        vol_increase = i / 200 * 2  # Gradually increasing volatility
        noise = np.random.normal(0, 0.5 + vol_increase)
        close = trend + noise
        
        open_price = close - np.random.uniform(-0.5 - vol_increase/2, 0.5 + vol_increase/2)
        high = max(open_price, close) + np.random.uniform(0, 0.5 + vol_increase)
        low = min(open_price, close) - np.random.uniform(0, 0.5 + vol_increase)
        
        data.append({
            'time': pd.Timestamp('2024-02-02') + pd.Timedelta(hours=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.uniform(1500, 6000)
        })
    
    df = pd.DataFrame(data)
    df.set_index('time', inplace=True)
    
    # Save to parquet
    output_path = os.path.join(os.path.dirname(__file__), 'test_data.parquet')
    df.to_parquet(output_path)
    
    print(f"Test data generated: {output_path}")
    print(f"Shape: {df.shape}")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print("\nMarket phases:")
    print("1. Days 1-8: Strong uptrend")
    print("2. Days 9-16: High volatility ranging")
    print("3. Days 17-24: Strong downtrend")
    print("4. Days 25-32: Low volatility consolidation")
    print("5. Days 33-40: Recovery with increasing volatility")
    
    return df


def generate_minimal_test_data():
    """Generate minimal test data for unit tests."""
    data = []
    
    for i in range(100):
        close = 100 + np.sin(i * 0.1) * 5
        open_price = close - 0.5
        high = close + 1
        low = close - 1
        
        data.append({
            'time': pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close
        })
    
    df = pd.DataFrame(data)
    df.set_index('time', inplace=True)
    
    output_path = os.path.join(os.path.dirname(__file__), 'minimal_test_data.parquet')
    df.to_parquet(output_path)
    
    print(f"\nMinimal test data generated: {output_path}")
    print(f"Shape: {df.shape}")
    
    return df


if __name__ == "__main__":
    # Generate both datasets
    full_df = generate_test_data_file()
    minimal_df = generate_minimal_test_data()
    
    # Display some statistics
    print("\n" + "="*50)
    print("Full dataset statistics:")
    print(full_df.describe())
    
    print("\n" + "="*50)
    print("Minimal dataset statistics:")
    print(minimal_df.describe())