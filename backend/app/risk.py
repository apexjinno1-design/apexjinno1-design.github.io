from decimal import ROUND_FLOOR, Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    account_equity: float = Field(default=100_000, gt=0)
    risk_fraction: float = Field(default=0.005, gt=0, le=0.05)
    allocation_fraction: float = Field(default=0.15, gt=0, le=1)
    max_stop_pct: float = Field(default=8, gt=0, le=50)
    min_reward_risk: float = Field(default=2, gt=0)
    target_multiple: float = Field(default=3, gt=0)
    horizon_sessions: int = Field(default=5, ge=1, le=5)

    @model_validator(mode="after")
    def validate_multiple(self):
        if self.target_multiple < self.min_reward_risk:
            raise ValueError("target_multiple must meet min_reward_risk")
        return self


def risk_plan(
    entry: float, stop: float, parameters: RiskParameters, regime: str | None, target: float | None = None
) -> dict:
    e, s = Decimal(str(entry)), Decimal(str(stop))
    if not e.is_finite() or not s.is_finite() or e <= 0 or s <= 0 or s >= e:
        return {
            "eligible": False,
            "reasons": ["Technical stop must be positive and below entry"],
            "shares": 0,
        }
    risk = e - s
    t = Decimal(str(target)) if target is not None else e + risk * Decimal(str(parameters.target_multiple))
    if not t.is_finite() or t <= e:
        return {"eligible": False, "reasons": ["Target must be finite and above entry"], "shares": 0}
    stop_pct = risk / e * 100
    rr = (t - e) / risk
    multiplier = {"GREEN": Decimal(1), "YELLOW": Decimal("0.5"), "RED": Decimal(0)}.get(regime, Decimal(0))
    equity = Decimal(str(parameters.account_equity))
    risk_budget = equity * Decimal(str(parameters.risk_fraction)) * multiplier
    allocation_budget = equity * Decimal(str(parameters.allocation_fraction)) * multiplier
    max_risk = int((risk_budget / risk).to_integral_value(rounding=ROUND_FLOOR))
    max_allocation = int((allocation_budget / e).to_integral_value(rounding=ROUND_FLOOR))
    reasons = []
    if stop_pct > Decimal(str(parameters.max_stop_pct)):
        reasons.append("Technical stop exceeds maximum stop distance; stop was not tightened")
    if rr < Decimal(str(parameters.min_reward_risk)):
        reasons.append("Reward/risk below configured minimum")
    if multiplier == 0:
        reasons.append("Market regime is RED or unavailable")
    if min(max_risk, max_allocation) < 1:
        reasons.append("Risk or allocation budget cannot fund one share")
    return {
        "entry": float(e),
        "stop": float(s),
        "target": float(t),
        "risk_per_share": float(risk),
        "stop_pct": float(stop_pct),
        "upside_pct": float((t / e - 1) * 100),
        "reward_risk": float(rr),
        "max_shares_risk": max_risk,
        "max_shares_allocation": max_allocation,
        "shares": 0 if reasons else min(max_risk, max_allocation),
        "eligible": not reasons,
        "reasons": reasons,
        "regime_multiplier": float(multiplier),
        "horizon_sessions": parameters.horizon_sessions,
        "target_basis": "user_objective" if target is not None else "hypothetical_R_multiple_not_forecast",
    }
