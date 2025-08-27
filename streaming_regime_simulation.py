#!/usr/bin/env python3
"""
Streaming regime detection with separate warmup and streaming phases.
"""

import pandas as pd
import numpy as np
import time
from typing import Generator
import sys
import os

# Add the project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.regime.regime_detector import RegimeDetector
from app.regime.data_structure import BarData

def load_and_prepare_data(data_file: str, warmup_bars: int = 500):
    """Load data and split into warmup and streaming portions."""
    print(f"Loading data from: {data_file}")
    
    df_input = pd.read_parquet(data_file)
    print(f"Loaded {len(df_input)} total bars")
    print(f"Columns: {list(df_input.columns)}")
    print(f"Date range: {df_input.index[0]} to {df_input.index[-1]}")
    
    # Prepare data format
    df_prepared = prepare_dataframe(df_input)
    
    # Split data
    df_historical = df_prepared.head(warmup_bars)  # First N rows for warmup
    df_to_stream = df_prepared.iloc[warmup_bars:]  # Rest for streaming
    
    print(f"\nData split:")
    print(f"  Historical (warmup): {len(df_historical)} bars ({df_historical.iloc[0]['timestamp']} to {df_historical.iloc[-1]['timestamp']})")
    print(f"  Streaming: {len(df_to_stream)} bars ({df_to_stream.iloc[0]['timestamp']} to {df_to_stream.iloc[-1]['timestamp']})")
    
    return df_historical, df_to_stream

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare DataFrame with standardized column names."""
    
    # Reset index to ensure we have timestamps as a column
    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()
    
    # Handle timestamp
    if 'timestamp' not in df.columns:
        if 'time' in df.columns:
            df['timestamp'] = df['time']
        elif 'Date' in df.columns:
            df['timestamp'] = df['Date']
        elif pd.api.types.is_datetime64_any_dtype(df.index):
            df = df.reset_index()
            df.rename(columns={df.columns[0]: 'timestamp'}, inplace=True)
        else:
            # Use index as timestamp
            df['timestamp'] = df.index
    
    # Handle price columns - map to standardized names
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'open' in col_lower and 'open' not in df.columns:
            column_mapping[col] = 'open'
        elif 'high' in col_lower and 'high' not in df.columns:
            column_mapping[col] = 'high'
        elif 'low' in col_lower and 'low' not in df.columns:
            column_mapping[col] = 'low'
        elif 'close' in col_lower and 'close' not in df.columns:
            column_mapping[col] = 'close'
    
    if column_mapping:
        df = df.rename(columns=column_mapping)
    
    # Validate required columns
    required_cols = ['timestamp', 'open', 'high', 'low', 'close']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Available columns: {list(df.columns)}")
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Convert timestamp
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        if df['timestamp'].dtype in ['int64', 'float64']:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df[required_cols].sort_values('timestamp').reset_index(drop=True)

def df_to_bar_data(df: pd.DataFrame) -> list[BarData]:
    """Convert DataFrame to list of BarData objects."""
    bars = []
    for i, row in df.iterrows():
        try:
            bar = BarData(
                timestamp=row['timestamp'],
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                bar_index=i
            )
            bars.append(bar)
        except Exception as e:
            print(f"Error creating bar {i}: {e}")
            continue
    return bars

def warmup_regime_detector(detector: RegimeDetector, historical_bars: list[BarData]) -> RegimeDetector:
    """Warmup the regime detector with historical data."""
    print(f"\nWarming up regime detector with {len(historical_bars)} bars...")
    
    for i, bar in enumerate(historical_bars):
        snapshot = detector.process_bar(bar)
        if i % 100 == 0:
            print(f"  Warmup progress: {i}/{len(historical_bars)} ({i/len(historical_bars)*100:.1f}%)")
    
    print(f"Warmup completed!")
    print(f"  Final warmup regime: {detector.history[-1].regime}")
    print(f"  Final warmup confidence: {detector.history[-1].confidence:.3f}")
    
    return detector

def stream_bars(detector: RegimeDetector, streaming_bars: list[BarData], 
                delay: float = 0.0, show_every: int = 1, show_indicators: bool = False):
    """Stream bars through the regime detector."""
    print(f"\nStarting streaming simulation...")
    print(f"  Stream bars: {len(streaming_bars)}")
    print(f"  Delay: {delay}s per bar")
    print(f"  Show every: {show_every} bars")
    print(f"  Show indicators: {show_indicators}")
    print("-" * 80)
    
    # Track streaming statistics
    regime_changes = 0
    last_regime = detector.history[-1].regime if detector.history else None
    
    for i, bar in enumerate(streaming_bars):
        snapshot = detector.process_bar(bar)
        
        # Track regime changes
        if last_regime and last_regime != snapshot.regime:
            regime_changes += 1
        last_regime = snapshot.regime
        
        # Display update
        if (i + 1) % show_every == 0:
            display_streaming_update(snapshot, regime_changes, show_indicators)
        
        # Stream delay
        if delay > 0:
            time.sleep(delay)
    
    return detector

def display_streaming_update(snapshot, regime_changes: int, show_indicators: bool = False):
    """Display a streaming update."""
    # Status indicators
    transition_marker = "[T]" if snapshot.is_transition else "[ ]"
    
    # Format output
    timestamp_str = snapshot.timestamp.strftime('%Y-%m-%d %H:%M')
    regime_str = f"{snapshot.regime:20s}"
    confidence_str = f"{snapshot.confidence:.3f}"
    
    print(f"{transition_marker} {timestamp_str} | {regime_str} | {confidence_str} | Changes: {regime_changes:4d}")
    
    if show_indicators:
        indicators = snapshot.indicators
        print(f"    RSI: {indicators.rsi:6.1f} | ATR: {indicators.atr_ratio:.2f} | BB: {indicators.bb_width:.4f}")

def run_complete_simulation():
    """Run the complete streaming simulation setup."""
    data_file = r"C:\Users\zak\Desktop\workspace\datalake\raw\xauusd\brut\XAUUSD_240.parquet"
    
    print("XAUUSD Streaming Regime Detection - Complete Setup")
    print("=" * 60)
    
    # Configuration
    warmup_bars = 300  # Warmup with 300 historical bars
    simulation_config = {
        'warmup': 200,          # Internal warmup within regime detector
        'persist_n': 3,         # Require 3 confirmations
        'transition_bars': 5,   # 5 bar transition period
        'bb_threshold_len': 100,
        'htf_rule': None
    }
    
    try:
        # Step 1: Load and prepare data
        df_historical, df_to_stream = load_and_prepare_data(data_file, warmup_bars)
        
        # Step 2: Convert to BarData
        historical_bars = df_to_bar_data(df_historical)
        streaming_bars = df_to_bar_data(df_to_stream)
        
        print(f"\nConversion completed:")
        print(f"  Historical bars: {len(historical_bars)}")
        print(f"  Streaming bars: {len(streaming_bars)}")
        
        # Step 3: Initialize regime detector
        print(f"\nInitializing regime detector...")
        print("Configuration:")
        for key, value in simulation_config.items():
            print(f"  {key}: {value}")
        
        detector = RegimeDetector(**simulation_config)
        
        # Step 4: Warmup phase
        detector = warmup_regime_detector(detector, historical_bars)
        
        # Step 5: Streaming phase (simulate real-time bar by bar)
        detector = stream_bars(detector, streaming_bars, 
                             delay=0.1, show_every=1, show_indicators=True)
        
        # Step 6: Final results
        print(f"\n{'='*60}")
        print("STREAMING SIMULATION COMPLETED")
        print(f"{'='*60}")
        
        final_stats = detector.stats()
        if final_stats:
            print(f"Total bars processed: {len(detector.history)}")
            print(f"Final regime: {detector.history[-1].regime}")
            print(f"Final confidence: {detector.history[-1].confidence:.3f}")
            print(f"Number of transitions: {final_stats['num_transitions']}")
            print(f"Average regime duration: {final_stats['avg_duration']:.1f} bars")
            
            print(f"\nRegime Distribution:")
            total_count = sum(final_stats['counts'].values())
            for regime, count in sorted(final_stats['counts'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_count) * 100
                avg_conf = final_stats['avg_confidence'].get(regime, 0)
                print(f"  {regime:20s}: {count:5,} bars ({percentage:5.1f}%) - Confidence: {avg_conf:.3f}")
        
        return detector
        
    except Exception as e:
        print(f"Error during simulation: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    run_complete_simulation()

