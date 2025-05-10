# prompts/__init__.py - Package initialization file

try:
    from prompts.system_prompts import (
        SYSTEM_PROMPT,
        INVESTMENT_FOCUSED_PROMPT,
        FIRST_TIME_BUYER_PROMPT,
        LUXURY_PROPERTY_PROMPT,
        NRI_CUSTOMER_PROMPT
    )

    __all__ = [
        'SYSTEM_PROMPT',
        'INVESTMENT_FOCUSED_PROMPT',
        'FIRST_TIME_BUYER_PROMPT',
        'LUXURY_PROPERTY_PROMPT',
        'NRI_CUSTOMER_PROMPT'
    ]
except ImportError as e:
    # In case the system_prompts.py file isn't complete
    # or not all prompts are defined
    print(f"Warning: Could not import all prompts: {e}")
    # Define a fallback SYSTEM_PROMPT
    SYSTEM_PROMPT = """
    You are a smart, conversational real estate chatbot agent designed to assist users looking to either buy a home 
    or invest in property in Hyderabad, India. Your task is to naturally chat with the user, help them define their 
    goals and preferences, and recommend properties from a property database.
    """
    __all__ = ['SYSTEM_PROMPT']