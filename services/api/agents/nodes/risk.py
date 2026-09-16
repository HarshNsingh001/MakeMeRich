from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.state import GraphState, AgentEvidence

RISK_PROMPT = """You are the Risk & Bear Agent for an Indian Equity Intelligence Platform.
Your job is to actively search for evidence that would invalidate a bullish or positive thesis.
You must output ONLY valid JSON matching the following schema exactly:
{
  "thesis": "A concise paragraph summarizing the bear case and risks",
  "signals": {
    "downside_risk": "high | medium | low",
    "invalidation_conditions": "List of strings describing conditions that invalidate the bull thesis"
  },
  "confidence": 0.0 to 1.0
}
"""

async def risk_node(state: GraphState) -> Dict[str, Any]:
    llm = get_llm()
    symbol = state.get("symbol", "UNKNOWN")
    
    # Needs to see all other evidence to find holes
    # But for parallel execution, it just looks at raw data.
    context_str = json.dumps(state.get("market_data", {}))
    
    messages = [
        SystemMessage(content=RISK_PROMPT),
        HumanMessage(content=f"Raw Data Context for {symbol}:\n{context_str}")
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
            raw_evidence=[{"source": "risk_analysis", "data": context_str}]
        )
    except Exception as e:
        evidence = AgentEvidence(
            thesis=f"Failed to parse risk analysis. Error: {str(e)}",
            signals={"downside_risk": "medium", "invalidation_conditions": "Unknown"},
            confidence=0.0,
            raw_evidence=[]
        )
        
    return {"risk_evidence": evidence}
