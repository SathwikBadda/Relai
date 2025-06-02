# config.py - Updated to include WhatsApp configuration
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")  # Default to GPT-4 Turbo

# Data Configuration - Use SQLite database by default
DEFAULT_CSV_PATH = "/Users/sathwik/Relai_agent/data/properties.csv"
DEFAULT_DB_PATH = "/Users/sathwik/Relai_agent/data/properties.db"

# Check if database exists, if not, fallback to CSV
if os.path.exists(DEFAULT_DB_PATH):
    DATA_PATH = os.getenv("DATA_PATH", DEFAULT_DB_PATH)
    print(f"Using SQLite database at: {DATA_PATH}")
else:
    DATA_PATH = os.getenv("DATA_PATH", DEFAULT_CSV_PATH)
    print(f"SQLite database not found, using CSV at: {DATA_PATH}")

# Agent Configuration
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))

# App Configuration
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# Streamlit Configuration
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

# WhatsApp Configuration
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "your_whatsapp_api_token")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "your_phone_number_id")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "your_verify_token")
WHATSAPP_PORT = int(os.getenv("WHATSAPP_PORT", "5000"))

# Application Mode - "streamlit" or "whatsapp" or "both"
APP_MODE = os.getenv("APP_MODE", "both")