from langgraph.graph import StateGraph, START, END
from agents.state import GraphState
from agents.nodes.market_regime import market_regime_node
from agents.nodes.historical import historical_node
from agents.nodes.technical import technical_node
from agents.nodes.fundamental import fundamental_node
from agents.nodes.entry import entry_node
from agents.nodes.risk import risk_node
from agents.nodes.critic import critic_node
from agents.nodes.synthesizer import synthesizer_node

# Create the graph
workflow = StateGraph(GraphState)

# Add all nodes
workflow.add_node("market_regime", market_regime_node)
workflow.add_node("historical", historical_node)
workflow.add_node("technical", technical_node)
workflow.add_node("fundamental", fundamental_node)
workflow.add_node("entry", entry_node)
workflow.add_node("risk", risk_node)
workflow.add_node("critic", critic_node)
workflow.add_node("synthesizer", synthesizer_node)

# Define the edges
# Phase 1: Parallel Evidence Gathering
workflow.add_edge(START, "market_regime")
workflow.add_edge(START, "historical")
workflow.add_edge(START, "technical")
workflow.add_edge(START, "fundamental")
workflow.add_edge(START, "entry")
workflow.add_edge(START, "risk")

# Phase 2: Wait for all evidence, then run Critic
# In LangGraph, when multiple nodes point to a single node, 
# it implicitly waits for all upstream nodes to finish.
workflow.add_edge("market_regime", "critic")
workflow.add_edge("historical", "critic")
workflow.add_edge("technical", "critic")
workflow.add_edge("fundamental", "critic")
workflow.add_edge("entry", "critic")
workflow.add_edge("risk", "critic")

# Phase 3: Synthesizer
workflow.add_edge("critic", "synthesizer")
workflow.add_edge("synthesizer", END)

# Compile the graph
agent_pipeline = workflow.compile()
