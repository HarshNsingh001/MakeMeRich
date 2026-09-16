import logging
from typing import Dict, Any, List, Optional
from evaluation.backtester import HistoricalSnapshot

logger = logging.getLogger(__name__)


class StrategyEngine:
    """
    Evaluates quantitative strategies against a Point-in-Time HistoricalSnapshot.
    All logic is configuration-driven — rules never hard-coded in business logic.

    Supported operators:
        >=, >, <=, <, ==      — single-value comparisons
        between               — { "op": "between", "min": X, "max": Y }
        not_none              — { "op": "not_none" }  checks field exists
    """
    def __init__(self, strategies_config: Dict[str, Any]):
        self.config = strategies_config

    def evaluate(self, snapshot: HistoricalSnapshot, strategy_name: str) -> Dict[str, Any]:
        """Evaluates a single strategy against the snapshot."""
        if strategy_name not in self.config:
            raise ValueError(f"Strategy {strategy_name} not found in configuration.")

        strategy = self.config[strategy_name]
        version = strategy.get("version", "1.0")
        rules = strategy.get("rules", {})
        # Optional: require only N-of-M rules to pass (default: all)
        min_pass_pct = strategy.get("min_pass_pct", 1.0)  # 1.0 = 100% rules must pass

        matched_rules = []
        failed_rules = []

        # Combine all features for easy lookup
        fundamentals = snapshot.fundamentals
        technicals = snapshot.technicals
        features = {**fundamentals, **technicals, "ltp": snapshot.price}

        total_rules = len(rules)
        if total_rules == 0:
            return {
                "strategy": strategy_name,
                "strategy_version": version,
                "score": 0,
                "is_match": False,
                "matched_rules": [],
                "failed_rules": ["No rules defined"]
            }

        score_weight = 100 / total_rules
        score = 0

        for feature_name, condition in rules.items():
            op = condition.get("op")
            actual_val = features.get(feature_name)

            if actual_val is None:
                failed_rules.append(f"{feature_name}: missing data")
                continue

            try:
                actual_val = float(actual_val)
            except (TypeError, ValueError):
                failed_rules.append(f"{feature_name}: non-numeric value '{actual_val}'")
                continue

            passed = False
            rule_str = ""

            if op == "not_none":
                passed = actual_val is not None
                rule_str = f"{feature_name} exists (Actual: {actual_val})"
            elif op == "between":
                lo, hi = condition.get("min"), condition.get("max")
                passed = lo <= actual_val <= hi
                rule_str = f"{feature_name} between {lo} and {hi} (Actual: {actual_val:.2f})"
            else:
                target = condition.get("value")
                if   op == ">=": passed = actual_val >= target
                elif op == ">":  passed = actual_val >  target
                elif op == "<=": passed = actual_val <= target
                elif op == "<":  passed = actual_val <  target
                elif op == "==": passed = actual_val == target
                else:
                    failed_rules.append(f"{feature_name}: unknown op '{op}'")
                    continue
                rule_str = f"{feature_name} {op} {target} (Actual: {actual_val:.2f})"

            if passed:
                matched_rules.append(rule_str)
                score += score_weight
            else:
                failed_rules.append(rule_str)

        # Flexible pass threshold (default: all rules must pass)
        pass_ratio = len(matched_rules) / total_rules if total_rules else 0
        is_match = pass_ratio >= min_pass_pct

        return {
            "strategy": strategy_name,
            "strategy_version": version,
            "is_match": is_match,
            "score": round(score, 2),
            "pass_ratio": round(pass_ratio, 3),
            "matched_rules": matched_rules,
            "failed_rules": failed_rules,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Default strategy configurations
# Version-controlled — bump version when rules change so backtests are reproducible
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_STRATEGIES = {
    # GARP: Growth at a Reasonable Price
    # Finds profitable, low-leverage stocks not yet overvalued
    "GARP": {
        "version": "1.1",
        "rules": {
            "roe": {"op": ">=", "value": 15},           # Return on equity ≥ 15%
            "pe_ratio": {"op": "<=", "value": 25},      # P/E ≤ 25 (not overvalued)
            "debt_to_equity": {"op": "<", "value": 1.0}, # Low leverage
        }
    },

    # Momentum: stocks in confirmed uptrends with institutional volume
    # ADX ≥ 25 means trend is strong (not just ranging)
    # RSI 55-75 = trending but not overbought
    # Volume Ratio > 1.2 = above-average participation
    "Momentum": {
        "version": "1.1",
        "rules": {
            "rsi_14": {"op": "between", "min": 55, "max": 75},   # Trending, not overbought
            "adx_14": {"op": ">=", "value": 25},                  # Strong trend (GAP-11)
            "volume_ratio": {"op": ">", "value": 1.2},            # Institutional participation
        },
        "min_pass_pct": 0.67,  # 2-of-3 rules required (ADX data may be missing)
    },

    # Value: statistically cheap stocks
    "Value": {
        "version": "1.1",
        "rules": {
            "pe_ratio": {"op": "<", "value": 15},       # Cheap on earnings
            "pb_ratio": {"op": "<", "value": 2.0},      # Cheap on book value
        },
        "min_pass_pct": 0.5,  # Either condition is sufficient
    },

    # Mean Reversion: oversold stocks that may bounce
    # RSI < 35 AND above a key moving average (not in a death spiral)
    "Mean_Reversion": {
        "version": "1.1",
        "rules": {
            "rsi_14": {"op": "<", "value": 35},  # Oversold
        }
    },

    # Quality: High-quality businesses — high ROE, high ROCE, low debt
    "Quality": {
        "version": "1.0",
        "rules": {
            "roe": {"op": ">=", "value": 20},             # High return on equity
            "roce": {"op": ">=", "value": 15},            # High return on capital
            "debt_to_equity": {"op": "<", "value": 0.5},  # Very low leverage
            "ebitda_margin": {"op": ">=", "value": 15},   # Healthy margin
        },
        "min_pass_pct": 0.75,  # 3-of-4 rules
    },
}
