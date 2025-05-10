# realestate_agent.py - Core agent implementation

import os
import sys
from typing import List, Dict, Any
from langchain.agents import Tool, AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.property_tools import PropertyRecommendationTools
from prompts.system_prompts import SYSTEM_PROMPT
from config import MODEL_NAME, TEMPERATURE, MAX_TOKENS

def create_real_estate_agent(property_tools: PropertyRecommendationTools):
    """
    Create a LangChain agent for the real estate chatbot
    
    Args:
        property_tools: An instance of PropertyRecommendationTools
        
    Returns:
        AgentExecutor: The configured chatbot agent
    """
    # Define tools
    tools = [
        Tool(
            name="search_properties",
            func=property_tools.search_properties,
            description="Search for properties based on criteria like area, property type, budget, configurations, etc."
        ),
        Tool(
            name="get_areas",
            func=property_tools.get_unique_areas,
            description="Get a list of all available areas/locations."
        ),
        Tool(
            name="get_property_types",
            func=property_tools.get_property_types,
            description="Get a list of all available property types."
        ),
        Tool(
            name="get_configurations",
            func=property_tools.get_configurations,
            description="Get a list of all available BHK configurations."
        ),
        Tool(
            name="get_price_range",
            func=property_tools.get_price_range,
            description="Get the minimum and maximum property prices available."
        )
    ]
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )
    
    # Create memory
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    # Create agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor

# Simple CLI for direct testing
if __name__ == "__main__":
    from utils.data_loader import load_property_data
    from config import DATA_PATH
    
    # Load data
    property_df = load_property_data(DATA_PATH)
    
    # Create property tools
    property_tools = PropertyRecommendationTools(property_df)
    
    # Create agent
    agent = create_real_estate_agent(property_tools)
    
    # Simple CLI for testing
    print("Real Estate Assistant is ready! Type 'exit' to quit.")
    print("=" * 50)
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Real Estate Assistant: Thank you for using our service. Goodbye!")
            break
        
        try:
            response = agent.invoke({"input": user_input})
            print("Real Estate Assistant:", response["output"])
        except Exception as e:
            print(f"Error: {e}")
            print("Real Estate Assistant: I'm sorry, I encountered an error. Let's try again.")