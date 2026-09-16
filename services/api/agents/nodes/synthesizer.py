from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.state import GraphState, OpportunityState

SYNTHESIZER_PROMPT = """You are the Decision Synthesizer Agent for an Indian Equity Intelligence Platform.
Your job is to combine the structured evidence from all agents and the critic's feedback into a final user-facing opportunity state.

IMPORTANT CONTEXT: You will receive sector_valuation data showing how the stock is priced vs its sector peers.
- "CHEAP" (pe_percentile <= 33): Relative valuation is a tailwind — weight supporting factors higher
- "EXPENSIVE" (pe_percentile >= 67): Relative valuation is a headwind — be more conservative on confidence
- discount_to_median_pct < -15%: Significant sector discount — potential catalyst for mean reversion

You must output ONLY valid JSON matching the following schema exactly:
{
  "opportunity_level": "LOW | MODERATE | HIGH",
  "confidence": 0.0 to 1.0,
  "risk_level": "LOW | MEDIUM | HIGH",
  "time_horizon": "INTRADAY | SWING | 1-3M | 6-12M | 3-5Y",
  "evidence_strength": 0.0 to 1.0,
  "supporting_factors": ["list of strings"],
  "contradictory_factors": ["list of strings"],
  "invalidation_conditions": ["list of strings"]
}
"""

async def synthesizer_node(state: GraphState) -> Dict[str, Any]:
    llm = get_llm()
    
    # Collect all evidence
    payload = {
        "market": state.get("market_regime_evidence"),
        "historical": state.get("historical_evidence"),
        "technical": state.get("technical_evidence"),
        "fundamental": state.get("fundamental_evidence"),
        "entry": state.get("entry_evidence"),
        "risk": state.get("risk_evidence"),
        "critic_feedback": state.get("critic_feedback"),
        "is_valid": state.get("is_valid"),
        # GAP-13: sector-relative valuation context
        "sector_valuation": state.get("sector_valuation"),
    }
    
    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=f"Synthesize the following validated evidence into a final opportunity state:\n{json.dumps(payload, default=str)}")
    ]
    
    response = llm.invoke(messages)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        parsed = json.loads(content)
        
        opportunity = OpportunityState(
            opportunity_level=parsed.get("opportunity_level", "LOW"),
            confidence=float(parsed.get("confidence", 0.0)),
            risk_level=parsed.get("risk_level", "HIGH"),
            time_horizon=parsed.get("time_horizon", "UNKNOWN"),
            evidence_strength=float(parsed.get("evidence_strength", 0.0)),
            supporting_factors=parsed.get("supporting_factors", []),
            contradictory_factors=parsed.get("contradictory_factors", []),
            invalidation_conditions=parsed.get("invalidation_conditions", [])
        )
    except Exception as e:
        # Fallback on parse failure
        opportunity = OpportunityState(
            opportunity_level="LOW",
            confidence=0.0,
            risk_level="HIGH",
            time_horizon="UNKNOWN",
            evidence_strength=0.0,
            supporting_factors=[],
            contradictory_factors=[f"Failed to synthesize: {str(e)}"],
            invalidation_conditions=[]
        )
        
    return {"opportunity_state": opportunity}
