from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.state import GraphState, AgentEvidence

FUNDAMENTAL_PROMPT = """You are the Fundamental Agent for an Indian Equity Intelligence Platform.
Evaluate business quality, financial health, and valuation context based on provided fundamentals.
You must output ONLY valid JSON matching the following schema exactly:
{
  "thesis": "A concise paragraph summarizing fundamental and valuation thesis",
  "signals": {
    "valuation": "undervalued | fair | overvalued",
    "growth": "high | stable | declining",
    "profitability": "strong | average | weak"
  },
  "confidence": 0.0 to 1.0
}
"""

async def fundamental_node(state: GraphState) -> Dict[str, Any]:
    llm = get_llm()
    symbol = state.get("symbol", "UNKNOWN")
    market_context = state.get("market_data", {})
    
    context_str = json.dumps(market_context.get("fundamentals", {"PE": 25, "ROE": "18%", "Debt_to_Equity": 0.4}))
    
    messages = [
        SystemMessage(content=FUNDAMENTAL_PROMPT),
        HumanMessage(content=f"Fundamental Data for {symbol}:\n{context_str}")
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
            raw_evidence=[{"source": "fundamentals", "data": context_str}]
        )
    except Exception as e:
        evidence = AgentEvidence(
            thesis=f"Failed to parse fundamentals. Error: {str(e)}",
            signals={"valuation": "fair", "growth": "stable", "profitability": "average"},
            confidence=0.0,
            raw_evidence=[]
        )
        
    return {"fundamental_evidence": evidence}
