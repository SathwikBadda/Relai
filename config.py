# config.py - Configuration file for the Real Estate Chatbot

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")  # Default to GPT-4 Turbo

# Data Configuration - Use your specific path
DEFAULT_DATA_PATH = "/Users/sathwik/Relai_agent/data/properties.csv"
DATA_PATH = os.getenv("DATA_PATH", DEFAULT_DATA_PATH)

# Agent Configuration
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))

# App Configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# Streamlit Configuration
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

# Example .env file content - save this as .env
ENV_FILE_TEMPLATE = """
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
MODEL_NAME=gpt-4-turbo-preview

# Data Configuration
DATA_PATH=/Users/sathwik/Relai_agent/data/properties.csv

# Agent Configuration
TEMPERATURE=0.7
MAX_TOKENS=4000

# App Configuration
DEBUG_MODE=False

# Streamlit Configuration
STREAMLIT_PORT=8501
"""

# Function to create .env file if it doesn't exist
def create_env_file():
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write(ENV_FILE_TEMPLATE)
        print("Created .env file template. Please edit it with your API keys.")
        return False
    return True

# Function to check if configuration is valid
def validate_config():
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        print("Error: OPENAI_API_KEY not set. Please update your .env file.")
        return False
    
    if not os.path.exists(DATA_PATH):
        print(f"Error: Data file not found at {DATA_PATH}")
        print(f"Please make sure your CSV file exists at this location.")
        return False
    
    return True

if __name__ == "__main__":
    # This allows running this file directly to check configuration
    if create_env_file():
        if validate_config():
            print("Configuration is valid!")
        else:
            print("Configuration is invalid. Please fix the issues above.")
    else:
        print("Please update the .env file with your settings and run again.")