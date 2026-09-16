from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.state import GraphState, AgentEvidence

ENTRY_PROMPT = """You are the Entry Price Agent for an Indian Equity Intelligence Platform.
Analyze potential entry zones based on current price, support levels, and volatility.
You must output ONLY valid JSON matching the following schema exactly:
{
  "thesis": "A concise paragraph summarizing entry zone scenarios",
  "signals": {
    "entry_zones": "List of strings describing zones, e.g., '1400-1420 Primary'",
    "risk_reward_profile": "favorable | neutral | unfavorable"
  },
  "confidence": 0.0 to 1.0
}
"""

async def entry_node(state: GraphState) -> Dict[str, Any]:
    llm = get_llm()
    symbol = state.get("symbol", "UNKNOWN")
    market_context = state.get("market_data", {})
    
    # Needs to see price and technical context
    price = market_context.get("ltp", 100)
    context_str = f"LTP: {price}. Volatility (ATR): 2%. Nearest Support: {price * 0.95}."
    
    messages = [
        SystemMessage(content=ENTRY_PROMPT),
        HumanMessage(content=f"Price Context for {symbol}:\n{context_str}")
    ]
    
    response = llm.invoke(messages)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        parsed = json.loads(content)
        evidence = AgentEvidence(
            thesis=parsed.get("thesis", "No thesis provided."),
            signals=parsed.get("signals", {}),
            confidence=float(parsed.get("confidence", 0.5)),
            raw_evidence=[{"source": "entry_analysis", "data": context_str}]
        )
    except Exception as e:
        evidence = AgentEvidence(
            thesis=f"Failed to parse entry zones. Error: {str(e)}",
            signals={"entry_zones": "Unknown", "risk_reward_profile": "neutral"},
            confidence=0.0,
            raw_evidence=[]
        )
        
    return {"entry_evidence": evidence}
