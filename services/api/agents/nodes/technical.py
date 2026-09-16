from typing import Dict, Any
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.state import GraphState, AgentEvidence

TECHNICAL_PROMPT = """You are the Technical Agent for an Indian Equity Intelligence Platform.
Evaluate current price action, momentum, and trends based on provided technical indicators.
You must output ONLY valid JSON matching the following schema exactly:
{
  "thesis": "A concise paragraph summarizing current technical state",
  "signals": {
    "trend": "bullish | bearish | neutral",
    "momentum": "strong | weak",
    "volume": "positive | negative | neutral"
  },
  "confidence": 0.0 to 1.0
}
"""

async def technical_node(state: GraphState) -> Dict[str, Any]:
    llm = get_llm()
    symbol = state.get("symbol", "UNKNOWN")
    market_context = state.get("market_data", {})
    
    context_str = json.dumps(market_context.get("technicals", {"RSI": 55, "MACD": "Bullish Crossover", "Price": "Above 50-EMA"}))
    
    messages = [
        SystemMessage(content=TECHNICAL_PROMPT),
        HumanMessage(content=f"Technical Data for {symbol}:\n{context_str}")
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
            raw_evidence=[{"source": "technical_indicators", "data": context_str}]
        )
    except Exception as e:
        evidence = AgentEvidence(
            thesis=f"Failed to parse technicals. Error: {str(e)}",
            signals={"trend": "neutral", "momentum": "weak", "volume": "neutral"},
            confidence=0.0,
            raw_evidence=[]
        )
        
    return {"technical_evidence": evidence}
