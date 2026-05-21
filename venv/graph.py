

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import AgentState
from agents import clarity_agent, research_agent, validator_agent, synthesis_agent


def route_after_clarity(state: AgentState) -> str:
    """
    Called after Clarity Agent finishes.
    Decides: should we research, or ask user to clarify?
    """
    if state["clarity_status"] == "clear":
        # Query is specific enough → go research it
        print("Routing: clarity → research_agent")
        return "research_agent"
    else:
        # Query is vague → interrupt and ask user
        print("Routing: clarity → needs clarification (interrupt)")
        return "clarification_needed"


def route_after_research(state: AgentState) -> str:
    """
    Called after Research Agent finishes.
    Decides: is research good enough, or does it need validation?
    
    confidence >= 6 → good enough, skip validation, go synthesize
    confidence < 6  → not great, send to validator first
    """
    confidence = state.get("confidence_score", 0)
    
    if confidence >= 6:
        print(f"Routing: research → synthesis (confidence {confidence} is good)")
        return "synthesis_agent"
    else:
        print(f"Routing: research → validator (confidence {confidence} is low)")
        return "validator_agent"


def route_after_validation(state: AgentState) -> str:
    """
    Called after Validator Agent finishes.
    Decides: retry research, or synthesize what we have?
    
    Two conditions to retry:
      1. validation_result == "insufficient" (research was bad)
      2. attempts < 3 (haven't tried 3 times yet)
    
    If attempts >= 3, we give up retrying and synthesize anyway
    (to avoid infinite loops)
    """
    validation = state.get("validation_result", "sufficient")
    attempts = state.get("attempts", 0)
    
    if validation == "insufficient" and attempts < 3:
        print(f"Routing: validator → research again (attempt {attempts}/3)")
        return "research_agent"
    else:
        if attempts >= 3:
            print("Routing: validator → synthesis (max attempts reached)")
        else:
            print("Routing: validator → synthesis (research is sufficient)")
        return "synthesis_agent"


# ============================================================
# BUILD THE GRAPH
# ============================================================

def build_graph():
    """
    Assembles all agents into a LangGraph pipeline.
    Returns a compiled, runnable graph.
    """

    graph = StateGraph(AgentState)
    

    # Second argument = the function to call
    graph.add_node("clarity_agent", clarity_agent)
    graph.add_node("research_agent", research_agent)
    graph.add_node("validator_agent", validator_agent)
    graph.add_node("synthesis_agent", synthesis_agent)

    graph.add_edge(START, "clarity_agent")
    
    graph.add_conditional_edges(
        "clarity_agent",          # FROM this node
        route_after_clarity,      # CALL this function to decide
        {
            "research_agent": "research_agent",
            "clarification_needed": END
        }
    )
    
    # After Research Agent: route based on confidence_score
    graph.add_conditional_edges(
        "research_agent",
        route_after_research,
        {
            "validator_agent": "validator_agent",
            "synthesis_agent": "synthesis_agent"
        }
    )
    
    # After Validator Agent: route based on validation_result and attempts
    graph.add_conditional_edges(
        "validator_agent",
        route_after_validation,
        {
            "research_agent": "research_agent",   # retry
            "synthesis_agent": "synthesis_agent"  # done
        }
    )
    

    graph.add_edge("synthesis_agent", END)
    
    memory = MemorySaver()
    
   
    compiled = graph.compile(checkpointer=memory)
    
    print("Graph built successfully!")
    return compiled


# ============================================================
# CONVENIENCE FUNCTION USED BY app.py
# ============================================================

def run_graph(graph, user_query: str, conversation_history: list, thread_id: str = "default"):
    """
    Runs the graph with a user query.
    
    Arguments:
        graph             → the compiled LangGraph object
        user_query        → what the user typed
        conversation_history → list of previous messages
        thread_id         → unique ID for this conversation session
    
    Returns:
        The final state after all agents have run
    """
    

    initial_state = {
        "user_query": user_query,
        "conversation_history": conversation_history,
        "clarity_status": "",
        "research_data": "",
        "confidence_score": 0,
        "validation_result": "",
        "attempts": 0,
        "final_answer": ""
    }
    
    config = {"configurable": {"thread_id": thread_id}}
     
    final_state = graph.invoke(initial_state, config)
    
    return final_state