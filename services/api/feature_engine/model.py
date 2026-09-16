import logging
import pandas as pd
import numpy as np
import xgboost as xgb
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class XGBoostRanker:
    """
    XGBoost-based ranking model to score stocks before sending them to the LLM agent pipeline.
    This model attempts to predict the probability of a positive outcome (e.g., T+20 returns > NIFTY).
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.is_trained = False
        self.model_path = model_path
        
        if self.model_path:
            self._load_model()

    def _load_model(self):
        try:
            self.model = xgb.XGBClassifier()
            self.model.load_model(self.model_path)
            self.is_trained = True
            logger.info(f"Loaded pre-trained XGBoost model from {self.model_path}")
        except Exception as e:
            logger.warning(f"Failed to load XGBoost model from {self.model_path}. Will use fallback ranking. Error: {e}")

    def extract_features(self, symbol_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Converts raw screening data into a feature row for XGBoost.
        """
        features = {
            "rsi": symbol_data.get("technical", {}).get("rsi", 50),
            "adx": symbol_data.get("technical", {}).get("adx", 20),
            "macd_hist": symbol_data.get("technical", {}).get("macd_hist", 0),
            "pe_ratio": symbol_data.get("fundamental", {}).get("pe_ratio", 20),
            "peg_ratio": symbol_data.get("fundamental", {}).get("peg_ratio", 1.5),
            "fcf_yield": symbol_data.get("fundamental", {}).get("fcf_yield", 0.02),
            "rs_vs_nifty_20d": symbol_data.get("relative_strength", {}).get("rs_vs_nifty_20d", 1.0),
        }
        return pd.DataFrame([features])

    def predict(self, candidate_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of pre-screened stocks and ranks them using XGBoost.
        Returns the list sorted by the predicted probability of success (highest first).
        """
        if not candidate_stocks:
            return []

        # If model is not trained (e.g. cold start), fallback to a simple heuristic ranking
        if not self.is_trained or self.model is None:
            logger.info("XGBoost model not trained yet. Falling back to heuristic ranking (RSI + Momentum).")
            return self._heuristic_rank(candidate_stocks)

        # Build feature dataframe
        feature_dfs = []
        for stock in candidate_stocks:
            feature_dfs.append(self.extract_features(stock))
        
        X = pd.concat(feature_dfs, ignore_index=True)
        
        # Predict probability of class 1 (success)
        try:
            probs = self.model.predict_proba(X)[:, 1]
            
            # Attach score and sort
            for i, stock in enumerate(candidate_stocks):
                stock["ml_score"] = float(probs[i])
                
            ranked = sorted(candidate_stocks, key=lambda x: x.get("ml_score", 0), reverse=True)
            return ranked
        except Exception as e:
            logger.error(f"XGBoost inference failed: {e}. Falling back to heuristic ranking.")
            return self._heuristic_rank(candidate_stocks)

    def _heuristic_rank(self, candidate_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback rule-based ranking if ML model is unavailable."""
        def heuristic_score(stock):
            rsi = stock.get("technical", {}).get("rsi", 50)
            adx = stock.get("technical", {}).get("adx", 20)
            rs = stock.get("relative_strength", {}).get("rs_vs_nifty_20d", 1.0)
            
            # Prefer strong momentum (high ADX), relative outperformance, and not extremely overbought
            rsi_score = max(0, 100 - rsi) if rsi > 70 else rsi
            return (rs * 0.4) + (adx / 100 * 0.4) + (rsi_score / 100 * 0.2)
            
        for stock in candidate_stocks:
            stock["ml_score"] = heuristic_score(stock)
            
        return sorted(candidate_stocks, key=lambda x: x.get("ml_score", 0), reverse=True)

# Singleton instance
xgboost_ranker = XGBoostRanker()
