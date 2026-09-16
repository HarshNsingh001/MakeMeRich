from typing import TypedDict, List, Dict, Any, Optional

class OpportunityState(TypedDict):
    """Final output structure of the multi-agent decision synthesis."""
    opportunity_level: str  # LOW | MODERATE | HIGH
    confidence: float       # 0.0 to 1.0
    risk_level: str         # LOW | MEDIUM | HIGH
    time_horizon: str       # INTRADAY | SWING | 1-3M | 6-12M | 3-5Y
    evidence_strength: float # 0.0 to 1.0
    supporting_factors: List[str]
    contradictory_factors: List[str]
    invalidation_conditions: List[str]

class AgentEvidence(TypedDict):
    """Standardized output from an individual agent."""
    thesis: str
    signals: Dict[str, str]
    confidence: float
    raw_evidence: List[Dict[str, Any]]

class GraphState(TypedDict):
    """The state that flows through the LangGraph pipeline."""
    # Inputs
    symbol: str
    market_data: Dict[str, Any]  # Snapshot of current price and volume
    screener_context: Optional[Dict[str, Any]] # Quantitative screen results
    is_backtest: Optional[bool]  # Flag to indicate PiT mode

    # GAP-13: Sector-relative valuation context injected before agent execution
    # Shape: { pe_percentile, valuation_label, sector_pe_median, discount_to_median_pct, peer_count }
    sector_valuation: Optional[Dict[str, Any]]

    # Execution Tracking
    agent_status: Optional[str]  # e.g., AgentStatusEnum.SUCCESS

    # Intermediate evidence produced by parallel agents
    market_regime_evidence: Optional[AgentEvidence]
    historical_evidence: Optional[AgentEvidence]
    technical_evidence: Optional[AgentEvidence]
    fundamental_evidence: Optional[AgentEvidence]
    entry_evidence: Optional[AgentEvidence]
    risk_evidence: Optional[AgentEvidence]

    # Validation
    critic_feedback: Optional[str]
    is_valid: bool

    # Final Output
    opportunity_state: Optional[OpportunityState]
