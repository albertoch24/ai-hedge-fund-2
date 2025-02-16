
"""Constants and utilities related to analysts configuration."""
from langgraph.graph import END, StateGraph
from graph.state import AgentState, start
from agents.bill_ackman import bill_ackman_agent
from agents.fundamentals import fundamentals_agent
from agents.portfolio_manager import portfolio_management_agent
from agents.technicals import technical_analyst_agent
from agents.risk_manager import risk_management_agent
from agents.sentiment import sentiment_agent
from agents.warren_buffett import warren_buffett_agent
from agents.valuation import valuation_agent

# Define analyst order - single source of truth
ANALYST_ORDER = [
    ("Bill Ackman", "bill_ackman"),
    ("Warren Buffett", "warren_buffett"),
    ("Technical Analyst", "technical_analyst"),
    ("Fundamentals Analyst", "fundamentals_analyst"),
    ("Sentiment Analyst", "sentiment_analyst"),
    ("Valuation Analyst", "valuation_analyst"),
]

def create_workflow(selected_analysts=None):
    """Create the workflow with selected analysts."""
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)

    # Dictionary of all available analysts
    analyst_nodes = {
        "technical_analyst": ("technical_analyst_agent", technical_analyst_agent),
        "fundamentals_analyst": ("fundamentals_agent", fundamentals_agent),
        "sentiment_analyst": ("sentiment_agent", sentiment_agent),
        "valuation_analyst": ("valuation_agent", valuation_agent),
        "warren_buffett": ("warren_buffett_agent", warren_buffett_agent),
        "bill_ackman": ("bill_ackman_agent", bill_ackman_agent),
    }

    # Default to all analysts if none selected
    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())
    
    # Add selected analyst nodes
    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)
        workflow.add_edge("start_node", node_name)

    # Always add risk and portfolio management
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_management_agent", portfolio_management_agent)

    # Connect selected analysts to risk management
    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge(node_name, "risk_management_agent")

    workflow.add_edge("risk_management_agent", "portfolio_management_agent")
    workflow.add_edge("portfolio_management_agent", END)

    workflow.set_entry_point("start_node")
    return workflow
