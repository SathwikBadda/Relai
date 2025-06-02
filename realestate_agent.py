# realestate_agent.py - Updated to use StructuredTool instead of Tool

import os
import sys
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import StructuredTool
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.property_tools import PropertyRecommendationTools
from prompts.system_prompts import SYSTEM_PROMPT
from config import MODEL_NAME, TEMPERATURE, MAX_TOKENS

# Define input schema for search_properties
class SearchPropertiesInput(BaseModel):
    area: Optional[str] = Field(None, description="Location/area in Hyderabad (e.g., 'Gachibowli', 'Bachupally')")
    property_type: Optional[str] = Field(None, description="Type of property (e.g., 'Apartment', 'Villa')")
    min_budget: Optional[float] = Field(None, description="Minimum budget in rupees (e.g., 5000000 for 50 lakhs)")
    max_budget: Optional[float] = Field(None, description="Maximum budget in rupees (e.g., 10000000 for 1 crore)")
    configurations: Optional[str] = Field(None, description="BHK configuration (e.g., '2BHK', '3BHK')")
    possession_date: Optional[str] = Field(None, description="When the property will be available (e.g., '2025', '1/1/2025', 'ready')")
    min_size: Optional[float] = Field(None, description="Minimum property size in sqft (e.g., 1000)")
    max_size: Optional[float] = Field(None, description="Maximum property size in sqft (e.g., 2000)")

def create_real_estate_agent(property_tools: PropertyRecommendationTools):
    """
    Create a LangChain agent for the real estate chatbot
    
    Args:
        property_tools: An instance of PropertyRecommendationTools
        
    Returns:
        AgentExecutor: The configured chatbot agent
    """
    # Define tools using StructuredTool which handles arguments better
    tools = [
        StructuredTool.from_function(
            func=lambda **kwargs: _handle_property_search(property_tools, **kwargs),
            name="search_properties",
            description="""
            Search for properties based on criteria like area, property_type, budget, configurations, etc.
            """,
            args_schema=SearchPropertiesInput
        ),
        StructuredTool.from_function(
            func=lambda: property_tools.get_unique_areas(),
            name="get_areas",
            description="Get a list of all available areas/locations in Hyderabad."
        ),
        StructuredTool.from_function(
            func=lambda: property_tools.get_property_types(),
            name="get_property_types",
            description="Get a list of all available property types."
        ),
        StructuredTool.from_function(
            func=lambda: property_tools.get_configurations(),
            name="get_configurations",
            description="Get a list of all available BHK configurations."
        ),
        StructuredTool.from_function(
            func=lambda: property_tools.get_price_range(),
            name="get_price_range",
            description="Get the minimum and maximum property prices available in the database."
        )
    ]
    
    # Enhanced system prompt with better fallback handling
    enhanced_prompt = SYSTEM_PROMPT + """

IMPORTANT GUIDELINES FOR PROPERTY RECOMMENDATIONS:

1. When exact property matches aren't found:
   - Always explain why certain preferences might be difficult to match
   - Suggest which preferences the user might consider adjusting
   - Present alternative properties that match SOME of their criteria
   - Focus on properties from the same area if location was specified

2. When showing properties:
   - Highlight which aspects match the user's preferences
   - Point out where properties differ from their ideal preferences
   - Suggest realistic alternatives if their budget doesn't match the area

3. For better recommendations:
   - Suggest nearby areas if their preferred location has limited options
   - Explain trade-offs between different areas (e.g., price vs. connectivity)
   - Offer helpful context about property trends in Hyderabad

4. When using tools:
   - Use the search_properties tool to find matching properties
   - Use the get_areas, get_property_types and get_configurations tools to find available options
   - Always pass parameters as named arguments, not positional arguments

When searching for properties, use ALL the information the user provides to make the most relevant recommendations.
"""
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", enhanced_prompt),
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

def _handle_property_search(property_tools, **kwargs):
    """
    Handle property search and provide enhanced feedback.
    
    Args:
        property_tools: PropertyRecommendationTools instance
        **kwargs: Search parameters
        
    Returns:
        Dict: Results with properties and feedback
    """
    try:
        # Extract search parameters
        area = kwargs.get('area')
        property_type = kwargs.get('property_type')
        min_budget = kwargs.get('min_budget')
        max_budget = kwargs.get('max_budget')
        configurations = kwargs.get('configurations')
        possession_date = kwargs.get('possession_date')
        min_size = kwargs.get('min_size')
        max_size = kwargs.get('max_size')
        
        # Log search parameters for debugging
        print(f"Searching for properties with: area={area}, type={property_type}, budget={min_budget}-{max_budget}, config={configurations}")
        
        # Perform the search
        properties, feedback, exact_match = property_tools.search_properties(
            area=area,
            property_type=property_type,
            min_budget=min_budget,
            max_budget=max_budget,
            configurations=configurations,
            possession_date=possession_date,
            min_size=min_size,
            max_size=max_size
        )
        
        # Create a response with the properties and feedback
        result = {
            "properties": properties,
            "exact_match": exact_match,
            "feedback": feedback,
            "count": len(properties)
        }
        
        # Add relevant advice based on feedback
        if not exact_match and "strategy" in feedback:
            strategy = feedback.get("strategy")
            
            if strategy == "area_only":
                result["advice"] = f"I found {len(properties)} properties in {area}, but I had to relax some of your other preferences to find matches."
                
                if "adjustment_needed" in feedback:
                    if feedback["adjustment_needed"] == "min_budget":
                        result["advice"] += f" You might need to increase your budget for this area."
                    elif feedback["adjustment_needed"] == "max_budget":
                        result["advice"] += f" Properties in this area may be below your budget range."
                    elif feedback["adjustment_needed"] == "configurations":
                        result["advice"] += f" Your requested configuration might be less common in this area."
            
            elif strategy == "relaxed_budget":
                result["advice"] = "I slightly adjusted your budget range to find these properties. They're close to your preferences but may be slightly outside your original budget."
                
            elif strategy == "relaxed_configuration":
                result["advice"] = "I found properties in your area and budget, but with different configurations than you requested."
                
            elif strategy == "diverse_sample":
                result["advice"] = "Your combination of preferences is quite specific and didn't match our database exactly. Here's a diverse selection that may interest you."
        
        return result
    
    except Exception as e:
        print(f"Error in property search: {e}")
        # Return a simple error response if something goes wrong
        return {
            "properties": [],
            "exact_match": False,
            "feedback": {"error": str(e)},
            "count": 0,
            "advice": "I encountered an error while searching for properties. Please try with different criteria."
        }

# Simple CLI for direct testing
if __name__ == "__main__":
    from utils.data_loader import load_property_data
    from config import DATA_PATH
    
    # Load data
    try:
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
    
    except Exception as e:
        print(f"Error initializing the agent: {e}")
        print("Please check your configuration and data files.")