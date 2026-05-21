
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tavily import TavilyClient
from state import AgentState

# Load API keys from .env file
load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def clarity_agent(state: AgentState) -> dict:
    print("--- CLARITY AGENT RUNNING ---")
    
    # Get the user's query from state
    query = state["user_query"]
    
    history = ""
    for msg in state.get("conversation_history", []):
        history += f"{msg['role']}: {msg['content']}\n"
    

    prompt = f"""
You are a query clarity evaluator. Your ONLY job is to check if a user's query 
is specific enough to research a company.

Conversation history so far:
{history}

Current query: "{query}"

Rules:
- If a specific company name is mentioned → respond with exactly: clear
- If the query is too vague or no company is named → respond with exactly: needs_clarification
- Respond with ONLY one of those two words, nothing else.
"""
    
    # Send prompt to the LLM and get response
    response = llm.invoke(prompt)
    

    result = response.content.strip().lower()
    
    print(f"Clarity Agent result: {result}")
    
   
    return {"clarity_status": result}

def research_agent(state: AgentState) -> dict:
    print("--- RESEARCH AGENT RUNNING ---")
    
    query = state["user_query"]
    current_attempts = state.get("attempts", 0)
    
    print(f"Searching for: {query}")
    search_results = tavily.search(query=query, max_results=5)
    
    research_text = "\n\n".join([
        f"Source: {r['url']}\n{r['content']}" 
        for r in search_results["results"]
    ])
    
   # asking to rate confidence
    confidence_prompt = f"""
You are a research quality evaluator.

User's question: "{query}"

Search results found:
{research_text}

Rate the quality of these search results on a scale of 0-10:
- 10 = Perfect, comprehensive information found
- 6-9 = Good information, enough to answer the question  
- 3-5 = Some relevant info but incomplete
- 0-2 = Almost nothing useful found

Respond with ONLY a single number (0-10), nothing else.
"""
    
    confidence_response = llm.invoke(confidence_prompt)
    
    try:
        confidence = int(confidence_response.content.strip())
        # Making sure it iss between 0 and 10
        confidence = max(0, min(10, confidence))
    except ValueError:
        # If LLM returned something weird, default to 5
        confidence = 5
    
    print(f"Research done. Confidence: {confidence}/10, Attempt: {current_attempts + 1}")
    
    return {
        "research_data": research_text,
        "confidence_score": confidence,
        "attempts": current_attempts + 1  # increment counter
    }




def validator_agent(state: AgentState) -> dict:
    print("--- VALIDATOR AGENT RUNNING ---")
    
    query = state["user_query"]
    research = state["research_data"]
    
    prompt = f"""
You are a research quality validator.

Original question: "{query}"

Research data collected:
{research}

Evaluate if this research is sufficient to give a good answer.

Ask yourself:
- Does the research actually relate to the company asked about?
- Is there enough detail to answer the question meaningfully?
- Is the information recent and relevant?

Respond with ONLY one of these two words:
- sufficient   (if the research can answer the question)
- insufficient (if the research is poor, irrelevant, or missing key info)
"""
    
    response = llm.invoke(prompt)
    result = response.content.strip().lower()
    
    # Clean up in case LLM added extra words
    # We check if "sufficient" appears in the response
    if "insufficient" in result:
        validation = "insufficient"
    else:
        validation = "sufficient"
    
    print(f"Validator result: {validation}")
    
    return {"validation_result": validation}


def synthesis_agent(state: AgentState) -> dict:
    print("--- SYNTHESIS AGENT RUNNING ---")
    
    query = state["user_query"]
    research = state["research_data"]
    
    history = ""
    for msg in state.get("conversation_history", []):
        history += f"{msg['role'].upper()}: {msg['content']}\n"
    
    prompt = f"""
You are a professional business research analyst.

Conversation history:
{history}

Current question: "{query}"

Research data collected:
{research}

Write a comprehensive, well-structured answer. Format it like this:

## Company Overview
[Brief intro about the company]

## Key Findings
[Main points from the research, using the bullet points]

## Recent Developments
[Latest news or updates]

## Summary
[2-3 sentence conclusion]

Be factuala and professional, and cite specific details from the research.
If some information is missing, acknowledge it honestly.
"""
    
    response = llm.invoke(prompt)
    final = response.content.strip()
    
    print("Synthesis complete. Final answer ready.")
    
    return {"final_answer": final}