from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.risk import RiskParameters
from app.screener import BreakoutParameters, RegimeParameters


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: AwareDatetime | None = None
    breakout: BreakoutParameters = Field(default_factory=BreakoutParameters)
    risk: RiskParameters = Field(default_factory=RiskParameters)
    regime: RegimeParameters = Field(default_factory=RegimeParameters)

    @field_validator("as_of")
    @classmethod
    def no_future(cls, value):
        from datetime import UTC

        if value and value > datetime.now(UTC):
            raise ValueError("as_of cannot be in the future")
        return value


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbols: list[str] = Field(min_length=1, max_length=100)
    start: date
    end: date
    adjusted: bool = True

    @field_validator("symbols")
    @classmethod
    def valid_symbols(cls, values):
        import re

        values = [v.upper().strip() for v in values]
        if any(not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", v) for v in values):
            raise ValueError("Invalid US ticker symbol")
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def valid_range(self):
        if self.start > self.end or (self.end - self.start).days > 3650:
            raise ValueError("Date range must be ordered and at most ten years")
        return self
