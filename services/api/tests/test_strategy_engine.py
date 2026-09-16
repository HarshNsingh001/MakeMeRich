import pytest
from datetime import datetime
from evaluation.backtester import HistoricalSnapshot
from feature_engine.strategy_engine import StrategyEngine, DEFAULT_STRATEGIES

def get_mock_snapshot(pe: float, roe: float, de: float, rsi: float, vol: float) -> HistoricalSnapshot:
    return HistoricalSnapshot(
        symbol="RELIANCE",
        target_date=datetime.utcnow(),
        price=2500.0,
        technicals={"RSI": rsi, "Volume_Ratio": vol},
        fundamentals={"PE": pe, "ROE": roe, "Debt_to_Equity": de},
        market_regime={"regime": "BULL", "vix": 14.0}
    )

def test_garp_strategy_exact_match():
    engine = StrategyEngine(DEFAULT_STRATEGIES)
    
    # Boundary test: ROE = 15, PE = 25
    snapshot = get_mock_snapshot(pe=25, roe=15, de=0.5, rsi=50, vol=1.0)
    
    result = engine.evaluate(snapshot, "GARP")
    assert result["is_match"] is True
    assert result["score"] == 100.0
    assert len(result["failed_rules"]) == 0

def test_garp_strategy_failure():
    engine = StrategyEngine(DEFAULT_STRATEGIES)
    
    # PE too high, Debt too high
    snapshot = get_mock_snapshot(pe=30, roe=20, de=1.5, rsi=50, vol=1.0)
    
    result = engine.evaluate(snapshot, "GARP")
    assert result["is_match"] is False
    assert result["score"] < 100.0
    assert len(result["failed_rules"]) == 2

def test_momentum_strategy():
    engine = StrategyEngine(DEFAULT_STRATEGIES)
    
    snapshot = get_mock_snapshot(pe=10, roe=10, de=1.0, rsi=60, vol=2.0)
    
    result = engine.evaluate(snapshot, "Momentum")
    assert result["is_match"] is True
    assert result["score"] == 100.0
