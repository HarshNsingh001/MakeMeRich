from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.state import GraphState, AgentEvidence

HISTORICAL_PROMPT = """You are the Historical Stock Agent for an Indian Equity Intelligence Platform.
Evaluate long-term historical behavior of the given stock based on provided data.
You must output ONLY valid JSON matching the following schema exactly:
{
  "thesis": "A concise paragraph summarizing long-term historical performance",
  "signals": {
    "historical_trend": "up | down | sideways",
    "volatility_regime": "high | medium | low"
  },
  "confidence": 0.0 to 1.0
}
"""

async def historical_node(state: GraphState) -> Dict[str, Any]:
    llm = get_llm()
    symbol = state.get("symbol", "UNKNOWN")
    
    # Mocking context
    context_str = f"Symbol: {symbol}. 5-year CAGR: 12%, Max Drawdown: 25%. Historically strong support near 200-WMA."
    
    messages = [
        SystemMessage(content=HISTORICAL_PROMPT),
        HumanMessage(content=f"Historical Data:\n{context_str}")
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
            raw_evidence=[{"source": "historical_data", "data": context_str}]
        )
    except Exception as e:
        evidence = AgentEvidence(
            thesis=f"Failed to parse historical data. Error: {str(e)}",
            signals={"historical_trend": "sideways", "volatility_regime": "medium"},
            confidence=0.0,
            raw_evidence=[]
        )
        
    return {"historical_evidence": evidence}
