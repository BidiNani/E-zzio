"""
Construction et compilation du StateGraph LangGraph avec persistance de mémoire d'état.
"""

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ezzio.graph.nodes import direct_node, rag_node, router_node, self_repair_node
from ezzio.schemas import AgentState


def route_decision(state: AgentState) -> Literal["rag_node", "direct_node", "self_repair_node"]:
    route = state.get("route", "direct")
    if route == "rag":
        return "rag_node"
    elif route == "self_repair":
        return "self_repair_node"
    return "direct_node"


def build_workflow(checkpointer=None):
    workflow = StateGraph(AgentState)

    # Ajout des nœuds
    workflow.add_node("router_node", router_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("direct_node", direct_node)
    workflow.add_node("self_repair_node", self_repair_node)

    # Arêtes
    workflow.add_edge(START, "router_node")
    workflow.add_conditional_edges(
        "router_node",
        route_decision,
        {
            "rag_node": "rag_node",
            "direct_node": "direct_node",
            "self_repair_node": "self_repair_node",
        }
    )
    workflow.add_edge("rag_node", END)
    workflow.add_edge("direct_node", END)
    workflow.add_edge("self_repair_node", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


# Instance partagée de l'application compilée
app = build_workflow()


def get_workflow():
    return app
