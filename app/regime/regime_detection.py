import argparse
import json
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ================= Utilities =================

def ema_update(prev: float, price: float, period: int) -> float:
    alpha = 2.0 / (period + 1.0)
    return price if prev is None else (alpha * price + (1 - alpha) * prev)

def wilder_update(prev: float, value: float, period: int) -> float:
    # Wilder's smoothing: prev + (value - prev)/period
    return value if prev is None else (prev + (value - prev) / period)

def true_range(high: float, low: float, prev_close: Optional[float]) -> float:
    if prev_close is None:
        return high - low
    return max(high - low, abs(high - prev_close), abs(low - prev_close))

def bb_width_from_window(prices_window: deque, period: int = 20, k: float = 2.0) -> float:
    if len(prices_window) == 0:
        return 0.0
    n = min(period, len(prices_window))
    arr = np.array(list(prices_window)[-n:])
    mean = arr.mean()
    std = arr.std(ddof=0)
    if mean == 0.0:
        return 0.0
    upper = mean + k * std
    lower = mean - k * std
    return (upper - lower) / mean


# ================= Data structures =================

@dataclass
class RegimeSnapshot:
    timestamp: pd.Timestamp
    bar_index: int
    regime: str
    confidence: float
    indicators: Dict
    is_transition: bool = False
    htf_bias: str = "neutral"

    def to_dict(self):
        return {
            "timestamp": str(self.timestamp),
            "bar_index": self.bar_index,
            "regime": self.regime,
            "confidence": float(self.confidence),
            "indicators": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                           for k, v in self.indicators.items()},
            "is_transition": bool(self.is_transition),
            "htf_bias": self.htf_bias,
        }


class PITRegimeDetector:
    def __init__(self, warmup: int = 500, persist_n: int = 2, transition_bars: int = 3,
                 bb_threshold_len: int = 200, htf_rule: Optional[str] = None):
        self.warmup = warmup
        self.persist_n = persist_n
        self.transition_bars = transition_bars
        self.bb_threshold_len = bb_threshold_len

        # Buffers
        self.close_win = deque(maxlen=200)  # for BB/std window
        self.bb_hist = deque(maxlen=bb_threshold_len)

        # Incremental states
        self.prev_close = None
        self.ema = {"ema12": None, "ema26": None, "ema20": None, "ema50": None, "ema200": None}
        self.macd_signal = None
        self.rsi_avg_gain = None
        self.rsi_avg_loss = None
        self.atr14 = None
        self.atr50 = None

        # Regime state & persistence
        self.current_regime = "warming_up"
        self.pending_regime = None
        self.pending_count = 0
        self.transition_countdown = 0

        # HTF bias state (incremental aggregation)
        self.htf_rule = htf_rule
        self._htf_bucket = None
        self._htf_last_close = None
        self.htf_ema200 = None
        self.htf_macd_signal = None
        self.htf_ema12 = None
        self.htf_ema26 = None
        self.htf_bias = "neutral"

        # Output
        self.history: List[RegimeSnapshot] = []

    # ---------- Incremental indicators ----------

    def _update_htf(self, ts: pd.Timestamp, close: float):
        if not self.htf_rule:
            return

        bucket = ts.floor(self.htf_rule)
        if self._htf_bucket is None:
            self._htf_bucket = bucket
            self._htf_last_close = close
            return

        if bucket != self._htf_bucket:
            # HTF bar closed -> update HTF indicators with the last HTF close
            c = self._htf_last_close
            self.htf_ema12 = ema_update(self.htf_ema12, c, 12)
            self.htf_ema26 = ema_update(self.htf_ema26, c, 26)
            h_macd_line = (self.htf_ema12 - self.htf_ema26) if (self.htf_ema12 is not None and self.htf_ema26 is not None) else None
            if h_macd_line is not None:
                self.htf_macd_signal = ema_update(self.htf_macd_signal, h_macd_line, 9)
            self.htf_ema200 = ema_update(self.htf_ema200, c, 200)

            # Compute bias
            if self.htf_ema200 is not None and self.htf_macd_signal is not None and h_macd_line is not None:
                # Momentum sign by hist
                hist = h_macd_line - self.htf_macd_signal
                if c > self.htf_ema200 and hist > 0:
                    self.htf_bias = "bull"
                elif c < self.htf_ema200 and hist < 0:
                    self.htf_bias = "bear"
                else:
                    self.htf_bias = "neutral"

            # Move to new bucket
            self._htf_bucket = bucket
            self._htf_last_close = close
        else:
            # still in same HTF bucket; just track last close
            self._htf_last_close = close

    def _update_incrementals(self, o: float, h: float, l: float, c: float, ts: pd.Timestamp):
        # EMA
        self.ema["ema12"] = ema_update(self.ema["ema12"], c, 12)
        self.ema["ema26"] = ema_update(self.ema["ema26"], c, 26)
        self.ema["ema20"] = ema_update(self.ema["ema20"], c, 20)
        self.ema["ema50"] = ema_update(self.ema["ema50"], c, 50)
        self.ema["ema200"] = ema_update(self.ema["ema200"], c, 200)

        # MACD (stateful signal)
        macd_line = None
        macd_hist = None  # None when not available instead of 0.0
        if self.ema["ema12"] is not None and self.ema["ema26"] is not None:
            macd_line = self.ema["ema12"] - self.ema["ema26"]
            self.macd_signal = ema_update(self.macd_signal, macd_line, 9)
            if self.macd_signal is not None:
                macd_hist = macd_line - self.macd_signal

        # ATR (Wilder)
        tr = true_range(h, l, self.prev_close)
        self.atr14 = wilder_update(self.atr14, tr, 14)
        self.atr50 = wilder_update(self.atr50, tr, 50)
        # Better handling of ATR ratio with proper None check and zero protection
        if self.atr14 is not None and self.atr50 not in (None, 0.0):
            atr_ratio = self.atr14 / self.atr50
        else:
            atr_ratio = 1.0

        # RSI (Wilder)
        if self.prev_close is None:
            gain = loss = 0.0
        else:
            delta = c - self.prev_close
            gain = max(delta, 0.0)
            loss = max(-delta, 0.0)
        self.rsi_avg_gain = wilder_update(self.rsi_avg_gain, gain, 14)
        self.rsi_avg_loss = wilder_update(self.rsi_avg_loss, loss, 14)
        # Better RSI edge case handling
        if (self.rsi_avg_loss is None) or (self.rsi_avg_gain is None):
            rsi = 50.0
        elif self.rsi_avg_loss == 0:
            rsi = 100.0 if self.rsi_avg_gain > 0 else 50.0
        else:
            rs = self.rsi_avg_gain / self.rsi_avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        # BB width from short window (period=20)
        self.close_win.append(c)
        bb_width = bb_width_from_window(self.close_win, 20, 2.0)
        self.bb_hist.append(bb_width)
        # Percentile threshold from *past only* (exclude current value)
        if len(self.bb_hist) > 1:
            bb_thresh = float(np.percentile(list(self.bb_hist)[:-1], 70))
        else:
            bb_thresh = 0.04

        # Direction & Volatility heuristic
        # EMA slope calculation (simple approach using recent price vs EMA)
        ema_slope = 0.0
        if self.ema["ema20"] is not None and len(self.close_win) >= 2:
            # Simple slope: compare current close to EMA20
            # Positive if price above EMA20, negative if below
            ema_slope = 1 if c > self.ema["ema20"] else -1
        
        # compute direction score
        dir_score = 0
        if self.ema["ema20"] is not None and self.ema["ema50"] is not None and self.ema["ema200"] is not None:
            dir_score += 1 if c > self.ema["ema20"] else -1
            dir_score += 2 if c > self.ema["ema50"] else -2
            dir_score += 3 if c > self.ema["ema200"] else -3
        # momentum
        dir_score += 2 if rsi > 55 else (-2 if rsi < 45 else 0)
        dir_score += 1 if rsi > 70 else (-1 if rsi < 30 else 0)
        # Only add MACD contribution if available
        if macd_hist is not None:
            dir_score += 2 if macd_hist > 0 else -2
        # Add EMA slope contribution
        dir_score += int(ema_slope)

        direction = "bull" if dir_score > 0 else ("bear" if dir_score < 0 else "neutral")
        is_expand = (atr_ratio > 1.1) or (bb_width > bb_thresh)
        volatility = "expansion" if is_expand else "contraction"
        regime_heur = f"{direction}_{volatility}"

        # Apply HTF bias: downgrade counter-trend to neutral_*
        final_regime = regime_heur
        if self.htf_rule and self.htf_bias in ("bull", "bear"):
            if (direction == "bull" and self.htf_bias == "bear") or (direction == "bear" and self.htf_bias == "bull"):
                final_regime = f"neutral_{volatility}"

        # Confidence proxy (adaptive based on available signals)
        # Calculate total weight based on actually available signals
        total_weight = 0
        if self.ema["ema20"] is not None and self.ema["ema50"] is not None and self.ema["ema200"] is not None:
            total_weight += 1 + 2 + 3  # EMA contributions
        total_weight += 2 + 1  # RSI always available after warmup
        if macd_hist is not None:
            total_weight += 2  # MACD contribution
        total_weight += 1  # EMA slope contribution
        
        confidence = min(1.0, abs(dir_score) / total_weight) if total_weight > 0 else 0.0

        # Indicators to attach
        indicators = {
            "rsi": rsi,
            "atr_ratio": float(atr_ratio if isinstance(atr_ratio, (int, float)) else 1.0),
            "bb_width": float(bb_width),
            "macd_hist": float(macd_hist) if macd_hist is not None else None,  # Export as None when unavailable
            "ema20": float(self.ema["ema20"]) if self.ema["ema20"] is not None else None,
            "ema50": float(self.ema["ema50"]) if self.ema["ema50"] is not None else None,
            "ema200": float(self.ema["ema200"]) if self.ema["ema200"] is not None else None,
            "ema_slope": float(ema_slope),  # Add ema_slope to indicators
        }

        # Update HTF aggregator last (uses this bar's close for in-bucket last_close)
        self._update_htf(ts, c)

        self.prev_close = c
        return final_regime, confidence, indicators

    # ---------- Persistence & transitions ----------

    def _apply_persistence(self, new_regime: str) -> Tuple[str, bool]:
        changed = False
        if self.current_regime in ("warming_up", None):
            self.current_regime = new_regime
            self.pending_regime = None
            self.pending_count = 0
            return self.current_regime, False

        if new_regime != self.current_regime:
            if self.pending_regime != new_regime:
                self.pending_regime = new_regime
                self.pending_count = 1
            else:
                self.pending_count += 1
                if self.pending_count >= self.persist_n:
                    # Commit change
                    self.current_regime = new_regime
                    self.pending_regime = None
                    self.pending_count = 0
                    self.transition_countdown = self.transition_bars
                    changed = True
        else:
            self.pending_regime = None
            self.pending_count = 0
        is_transition = self.transition_countdown > 0
        if self.transition_countdown > 0:
            self.transition_countdown -= 1
        return self.current_regime, changed or is_transition

    # ---------- Public API ----------

    def process_bar(self, ts: pd.Timestamp, o: float, h: float, l: float, c: float, i: int) -> RegimeSnapshot:
        # Warmup: gather state but output warming_up
        if i < self.warmup:
            # still update HTF to keep buckets aligned
            self._update_htf(ts, c)
            # Update incrementals BEFORE setting prev_close to avoid forcing delta=0
            regime_new, conf, indicators = self._update_incrementals(o, h, l, c, ts)
            # But override regime to warming_up during warmup period
            snap = RegimeSnapshot(ts, i, "warming_up", 0.0, indicators, False, self.htf_bias)
            self.history.append(snap)
            return snap

        regime_new, conf, indicators = self._update_incrementals(o, h, l, c, ts)
        regime_final, is_transition = self._apply_persistence(regime_new)

        snap = RegimeSnapshot(ts, i, regime_final, conf, indicators, is_transition, self.htf_bias)
        self.history.append(snap)
        return snap

    def stats(self) -> Dict:
        regs = [s.regime for s in self.history if s.regime != "warming_up"]
        if not regs:
            return {}
        ser = pd.Series(regs)
        counts = ser.value_counts().to_dict()
        confs = {}
        for r in set(regs):
            confs[r] = float(np.mean([s.confidence for s in self.history if s.regime == r]))
        # durations
        durations = []
        cur = None; dur = 0
        for s in self.history:
            if s.regime == "warming_up":
                continue
            if cur != s.regime:
                if cur is not None:
                    durations.append(dur)
                cur = s.regime; dur = 1
            else:
                dur += 1
        if dur > 0: durations.append(dur)
        return {
            "counts": counts,
            "avg_confidence": confs,
            "avg_duration": float(np.mean(durations)) if durations else 0.0,
            "max_duration": int(np.max(durations)) if durations else 0,
            "min_duration": int(np.min(durations)) if durations else 0,
            "num_transitions": int(sum(1 for s in self.history if s.is_transition))
        }

    def export(self, path_json: str):
        data = {
            "metadata": {
                "warmup": self.warmup,
                "persist_n": self.persist_n,
                "transition_bars": self.transition_bars,
                "bb_threshold_len": self.bb_threshold_len,
                "htf_rule": self.htf_rule,
                "total_bars": len(self.history)
            },
            "stats": self.stats(),
            "history": [s.to_dict() for s in self.history],
        }
        with open(path_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# ================= Runner =================

def run_pit(df: pd.DataFrame, warmup: int, persist: int, transition: int, htf: Optional[str], export_parquet: str):
    det = PITRegimeDetector(warmup=warmup, persist_n=persist, transition_bars=transition, htf_rule=htf)

    for i, (ts, row) in enumerate(df.iterrows()):
        det.process_bar(ts, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), i)

    out = df.copy()
    out["regime"] = [s.regime for s in det.history]
    out["regime_confidence"] = [s.confidence for s in det.history]
    out["is_transition"] = [s.is_transition for s in det.history]
    out["htf_bias"] = [s.htf_bias for s in det.history]
    # optional indicator columns
    keys = set().union(*[set(s.indicators.keys()) for s in det.history if s.indicators])
    for k in keys:
        out[k] = [s.indicators.get(k, np.nan) for s in det.history]

    # Preserve the index (time column) in the parquet file
    out.reset_index().to_parquet(export_parquet, index=False)
    det.export("regime_backtest_results.json")
    return out, det


def main():
    ap = argparse.ArgumentParser(description="Point-in-Time Regime Detector (Corrected)")
    ap.add_argument("--parquet", required=True, help="Input Parquet with columns: time/open/high/low/close")
    ap.add_argument("--time-col", default=None, help="Datetime column (if not index)")
    ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--persist", type=int, default=2, help="Bars required to confirm regime change")
    ap.add_argument("--transition", type=int, default=3, help="Bars to mark as transition *after* change (no retro edits)")
    ap.add_argument("--htf", default=None, help='Optional higher timeframe e.g. "1H" (PIT-safe aggregation)')
    ap.add_argument("--export", default="regime_backtest.parquet")
    args = ap.parse_args()

    df = pd.read_parquet(args.parquet)
    if args.time_col and args.time_col in df.columns:
        df[args.time_col] = pd.to_datetime(df[args.time_col])
        df = df.set_index(args.time_col).sort_index()
    elif not isinstance(df.index, (pd.DatetimeIndex, pd.PeriodIndex)):
        # try to auto-detect
        for col in ["time","timestamp","datetime","date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
                df = df.set_index(col).sort_index()
                break
    # ensure required columns
    req = {"open","high","low","close"}
    missing = req - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {missing}")

    out, det = run_pit(df, args.warmup, args.persist, args.transition, args.htf, args.export)

    # Print summary
    print("\n=== PIT Regime Backtest Complete ===")
    st = det.stats()
    if st:
        print("Regime counts:", st["counts"])
        print("Avg duration:", st["avg_duration"], "bars")
        print("Transitions:", st["num_transitions"])
    print(f"Exported: {args.export}")
    print("Details: regime_backtest_results.json")


if __name__ == "__main__":
    main()

