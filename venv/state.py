

from typing import TypedDict, List, Optional


class AgentState(TypedDict):
   
    user_query: str

    
    conversation_history: List[dict]

    
    clarity_status: str

   
    research_data: str


    confidence_score: int

   
    validation_result: str

    
    attempts: int

    
    final_answer: str