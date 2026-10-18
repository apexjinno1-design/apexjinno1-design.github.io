import pytest
from pydantic import ValidationError

from app.risk import RiskParameters, risk_plan
from app.screener import BreakoutParameters, RegimeParameters, detect_breakout, market_regime


def parameters():
    return BreakoutParameters(min_base_sessions=20, max_base_sessions=20)


def test_confirmed_setup_requires_all_quality_checks_and_volume(setup_frame):
    result = detect_breakout(setup_frame, 95, "GREEN", parameters(), RiskParameters())
    assert result["qualified"], result["checks"]
    assert result["status"] == "TRIGGERED"
    assert result["plan"]["eligible"]
    assert result["pivot"] == setup_frame.high.iloc[-21:-1].max()
    assert result["plan"]["entry"] == setup_frame.close.iloc[-1]


def test_price_cross_with_weak_volume_is_not_confirmed(setup_frame):
    setup_frame.loc[setup_frame.index[-1], "rvol"] = 0.8
    result = detect_breakout(setup_frame, 95, "GREEN", parameters(), RiskParameters())
    assert result["price_confirmed"]
    assert not result["volume_confirmed"]
    assert result["status"] == "BUILDING"
    assert not result["plan"]["eligible"]


@pytest.mark.parametrize("factor,expected", [(0.99, "READY"), (1.10, "EXTENDED"), (0.9, "FAILED")])
def test_setup_states(setup_frame, factor, expected):
    pivot = setup_frame.high.iloc[-21:-1].max()
    setup_frame.loc[setup_frame.index[-1], "close"] = pivot * 1.001 * factor
    result = detect_breakout(setup_frame, 95, "GREEN", parameters(), RiskParameters())
    assert result["status"] == expected
    if expected != "READY":
        assert result["plan"]["shares"] == 0


def test_no_quality_no_trigger_and_no_ranking_no_confirmation(setup_frame):
    for rank in (None, 10):
        result = detect_breakout(setup_frame, rank, "GREEN", parameters(), RiskParameters())
        assert result["status"] == "BUILDING"
        assert not result["qualified"]
        assert result["plan"]["shares"] == 0


def test_warmup_is_not_qualified(setup_frame):
    assert not detect_breakout(setup_frame.iloc[:100], 100, "GREEN", parameters(), RiskParameters())[
        "qualified"
    ]


def test_risk_uses_floor_and_both_budgets():
    result = risk_plan(100, 96, RiskParameters(), "GREEN")
    assert result["risk_per_share"] == 4
    assert result["stop_pct"] == 4
    assert result["target"] == 112
    assert result["upside_pct"] == 12
    assert result["reward_risk"] == 3
    assert result["max_shares_risk"] == 125
    assert result["max_shares_allocation"] == 150
    assert result["shares"] == 125
    assert risk_plan(100, 99, RiskParameters(), "GREEN")["shares"] == 150
    assert risk_plan(100, 96, RiskParameters(), "YELLOW")["shares"] == 62


def test_wide_stop_is_preserved_and_rejected():
    result = risk_plan(100, 80, RiskParameters(), "GREEN")
    assert result["stop"] == 80
    assert not result["eligible"]
    assert result["shares"] == 0


@pytest.mark.parametrize("regime", ["RED", None])
def test_regime_blocks_sizing(regime):
    result = risk_plan(100, 96, RiskParameters(), regime)
    assert not result["eligible"] and result["shares"] == 0


@pytest.mark.parametrize(
    "entry,stop,target",
    [(100, 101, None), (100, 0, None), (-1, 0, None), (100, 96, 99), (float("nan"), 90, None)],
)
def test_invalid_risk_inputs(entry, stop, target):
    assert not risk_plan(entry, stop, RiskParameters(), "GREEN", target)["eligible"]


def test_low_objective_reward_is_rejected():
    result = risk_plan(100, 96, RiskParameters(), "GREEN", target=104)
    assert result["reward_risk"] == 1 and result["shares"] == 0


def test_market_votes_and_missing_data(setup_frame):
    assert market_regime({})["regime"] is None
    frames = {s: setup_frame.copy() for s in ("SPY", "QQQ", "IWM")}
    assert market_regime(frames)["regime"] == "GREEN"
    for s in ("SPY", "IWM"):
        frames[s].loc[frames[s].index[-1], "close"] = 1
    assert market_regime(frames)["regime"] == "YELLOW"
    frames["QQQ"].loc[frames["QQQ"].index[-1], "close"] = 1
    assert market_regime(frames)["regime"] == "RED"


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValidationError):
        BreakoutParameters(min_base_sessions=30, max_base_sessions=10)
    with pytest.raises(ValidationError):
        RiskParameters(account_equity=-1)
    with pytest.raises(ValidationError):
        RiskParameters(risk_fraction=float("inf"))
    with pytest.raises(ValidationError):
        RegimeParameters(green_min_votes=1, yellow_min_votes=3)
