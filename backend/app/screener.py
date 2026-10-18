import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.risk import RiskParameters, risk_plan


class BreakoutParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    min_base_sessions: int = Field(default=10, ge=10, le=40)
    max_base_sessions: int = Field(default=40, ge=10, le=40)
    min_return63: float = Field(default=0.30, ge=0)
    min_return126: float = Field(default=0.50, ge=0)
    min_rs_percentile: float = Field(default=70, ge=0, le=100)
    min_prior_advance: float = Field(default=0.20, ge=0)
    prior_advance_sessions: int = Field(default=21, ge=5, le=63)
    max_base_depth: float = Field(default=0.25, gt=0, le=0.5)
    max_range_contraction: float = Field(default=0.85, gt=0, le=2)
    max_volume_contraction: float = Field(default=0.85, gt=0, le=2)
    higher_low_tolerance: float = Field(default=0.02, ge=0, le=0.2)
    min_avg_dollar_volume: float = Field(default=10_000_000, ge=0)
    min_price: float = Field(default=5, gt=0)
    min_breakout_rvol: float = Field(default=1.5, gt=0)
    entry_buffer_pct: float = Field(default=0.001, ge=0, le=0.05)
    ready_distance_pct: float = Field(default=0.05, gt=0, le=0.2)
    max_extension_pct: float = Field(default=0.05, gt=0, le=0.5)

    @model_validator(mode="after")
    def ordered_window(self):
        if self.min_base_sessions > self.max_base_sessions:
            raise ValueError("min_base_sessions must not exceed max_base_sessions")
        return self


def detect_breakout(
    frame: pd.DataFrame,
    rs_percentile: float | None,
    regime: str | None,
    p: BreakoutParameters,
    risk: RiskParameters,
) -> dict:
    if len(frame) < max(128, p.max_base_sessions + p.prior_advance_sessions + 1):
        return {
            "status": "BUILDING",
            "qualified": False,
            "score": 0,
            "checks": {"sufficient_history": False},
            "plan": {"eligible": False, "shares": 0},
            "reason": "At least 128 completed sessions are required",
        }
    today, prior = frame.iloc[-1], frame.iloc[-2]
    prior_previous = frame.iloc[-3]
    options = []
    for length in range(p.min_base_sessions, p.max_base_sessions + 1):
        base = frame.iloc[-length - 1 : -1]  # Never include the signal bar in the pivot.
        pre_base = frame.iloc[-length - p.prior_advance_sessions - 1 : -length - 1]
        pivot, floor = float(base.high.max()), float(base.low.min())
        half = length // 2
        early, late = base.iloc[:half], base.iloc[-half:]
        early_range = ((early.high - early.low) / early.close).mean()
        late_range = ((late.high - late.low) / late.close).mean()
        range_ratio = late_range / early_range if early_range > 0 else np.inf
        vol_ratio = late.volume.mean() / early.volume.mean() if early.volume.mean() > 0 else np.inf
        advance = base.iloc[0].close / pre_base.iloc[0].close - 1
        checks = {
            "momentum": bool(prior.return_63 >= p.min_return63 or prior.return_126 >= p.min_return126),
            "relative_strength": rs_percentile is not None and rs_percentile >= p.min_rs_percentile,
            "prior_advance": bool(advance >= p.min_prior_advance),
            "orderly_depth": bool((pivot - floor) / pivot <= p.max_base_depth),
            "range_contraction": bool(range_ratio <= p.max_range_contraction),
            "volume_contraction": bool(vol_ratio <= p.max_volume_contraction),
            "higher_lows": bool(late.low.min() >= early.low.min() * (1 - p.higher_low_tolerance)),
            "rising_averages": bool(
                prior.sma10 > prior_previous.sma10 and prior.sma20 > prior_previous.sma20
            ),
            "liquidity": bool(prior.avg_dollar_volume20 >= p.min_avg_dollar_volume),
            "minimum_price": bool(prior.close >= p.min_price),
        }
        options.append(
            (
                sum(checks.values()),
                length,
                pivot,
                float(base.low.iloc[-5:].min()),
                checks,
                {
                    "depth": (pivot - floor) / pivot,
                    "base_low": floor,
                    "range_ratio": float(range_ratio) if np.isfinite(range_ratio) else None,
                    "volume_ratio": float(vol_ratio) if np.isfinite(vol_ratio) else None,
                    "prior_advance": float(advance),
                },
            )
        )
    score, length, pivot, stop, checks, evidence = max(options, key=lambda x: (x[0], -x[1]))
    qualified = all(checks.values())
    entry = pivot * (1 + p.entry_buffer_pct)
    price_confirmed = bool(today.close >= entry)
    volume_confirmed = bool(pd.notna(today.rvol) and today.rvol >= p.min_breakout_rvol)
    status = "BUILDING"
    if qualified:
        if today.close < stop:
            status = "FAILED"
        elif today.close > entry * (1 + p.max_extension_pct):
            status = "EXTENDED"
        elif price_confirmed and volume_confirmed:
            status = "TRIGGERED"
        elif entry * (1 - p.ready_distance_pct) <= today.close < entry:
            status = "READY"
    # If the completed bar gapped above the conditional trigger, budget from the
    # observed close; this is an EOD research plan, never an assumed historical fill.
    planning_entry = max(entry, float(today.close)) if price_confirmed else entry
    plan = risk_plan(planning_entry, stop, risk, regime)
    actionable = status in ("READY", "TRIGGERED") and qualified
    if not actionable:
        plan["eligible"] = False
        plan["shares"] = 0
        plan.setdefault("reasons", []).append(f"Setup status {status} is not actionable")
    return {
        "status": status,
        "qualified": qualified,
        "score": score,
        "checks": checks,
        "base_sessions": length,
        "pivot": pivot,
        "base_low": evidence["base_low"],
        "entry_trigger": entry,
        "price_confirmed": price_confirmed,
        "volume_confirmed": volume_confirmed,
        "evidence": evidence,
        "plan": plan,
        "reason": "Daily close confirmation only; intraday entry ordering is not inferred",
    }


class RegimeParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    green_min_votes: int = Field(default=3, ge=1, le=3)
    yellow_min_votes: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def ordered_votes(self):
        if self.yellow_min_votes > self.green_min_votes:
            raise ValueError("yellow_min_votes must not exceed green_min_votes")
        return self


def market_regime(frames: dict[str, pd.DataFrame], parameters: RegimeParameters | None = None) -> dict:
    p = parameters or RegimeParameters()
    evidence = {}
    for symbol, frame in frames.items():
        if frame.empty:
            continue
        row = frame.iloc[-1]
        ready = pd.notna(row.sma50) and pd.notna(row.sma20)
        evidence[symbol] = {
            "close": float(row.close),
            "above_sma20": bool(ready and row.close > row.sma20),
            "above_sma50": bool(ready and row.close > row.sma50),
            "sufficient_history": bool(ready),
        }
    required = ["SPY", "QQQ", "IWM"]
    missing = [s for s in required if s not in evidence or not evidence[s]["sufficient_history"]]
    if missing:
        return {
            "regime": None,
            "reason": "Missing benchmark history: " + ", ".join(missing),
            "evidence": evidence,
        }
    votes = sum(evidence[s]["above_sma20"] and evidence[s]["above_sma50"] for s in required)
    regime = "GREEN" if votes >= p.green_min_votes else "YELLOW" if votes >= p.yellow_min_votes else "RED"
    return {
        "regime": regime,
        "votes": votes,
        "evidence": evidence,
        "parameters": p.model_dump(),
        "reason": "Votes require both close > SMA20 and close > SMA50 for SPY, QQQ, IWM",
    }
