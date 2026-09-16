from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.state import GraphState, AgentEvidence

MARKET_REGIME_PROMPT = """You are the Market Regime Agent for an Indian Equity Intelligence Platform.
Your job is to evaluate the overall market conditions based on the provided index and volatility data, and determine if the market is favorable for long/short positions.
You must output ONLY valid JSON matching the following schema exactly:
{
  "thesis": "A concise paragraph summarizing your market regime view",
  "signals": {
    "trend": "bullish | bearish | neutral",
    "volatility": "high | medium | low"
  },
  "confidence": 0.0 to 1.0
}
"""

async def market_regime_node(state: GraphState) -> Dict[str, Any]:
    """
    Evaluates the overall market regime.
    In a full implementation, this queries the `market_regime_features` table.
    For now, we use the injected market context or a placeholder.
    """
    llm = get_llm()
    
    # Mocking some context for V2 pipeline if not present in state
    market_context = state.get("market_data", {})
    context_str = json.dumps(market_context) if market_context else "NIFTY 50: 24500, India VIX: 14.5 (Neutral trend, moderate volatility)"
    
    messages = [
        SystemMessage(content=MARKET_REGIME_PROMPT),
        HumanMessage(content=f"Current Market Data:\n{context_str}")
    ]
    
    # Use LLM to get the structured JSON (using structured output if available, but for fallback compatibility across providers, we can prompt for JSON and parse it).
    # Since we are using standard BaseChatModel, we rely on the prompt to format JSON.
    response = llm.invoke(messages)
    
    try:
        content = response.content
        # Simple extraction in case LLM wraps in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        parsed = json.loads(content)
        evidence = AgentEvidence(
            thesis=parsed.get("thesis", "No thesis provided."),
            signals=parsed.get("signals", {}),
            confidence=float(parsed.get("confidence", 0.5)),
            raw_evidence=[{"source": "market_regime", "data": context_str}]
        )
    except Exception as e:
        # Fallback on failure
        evidence = AgentEvidence(
            thesis=f"Failed to parse market regime. Error: {str(e)}",
            signals={"trend": "neutral", "volatility": "medium"},
            confidence=0.0,
            raw_evidence=[]
        )
        
    return {"market_regime_evidence": evidence}
