# app.py - Enhanced Streamlit frontend for the Real Estate Chatbot

import streamlit as st
import pandas as pd
import os
import sys
import time
import json
import uuid
from typing import List, Dict, Any
import sqlite3

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_PATH
from utils.data_loader import detect_data_source

# Page configuration
st.set_page_config(
    page_title="Hyderabad Real Estate Assistant",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply basic styles directly in the app
st.markdown("""
<style>
    .stTextInput>div>div>input {
        border-radius: 20px;
        padding: 10px 15px;
        border: 1px solid #ddd;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.8rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
    }
    .chat-message.user {
        background-color: #f0f2f6;
    }
    .chat-message.assistant {
        background-color: #e6f7ff;
    }
    .property-card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1.2rem;
        margin: 0.75rem 0;
        border: 1px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease-in-out;
    }
    .property-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .property-title {
        font-weight: bold;
        color: #1e88e5;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .property-detail {
        display: flex;
        flex-direction: row;
        margin-top: 0.3rem;
    }
    .property-label {
        font-weight: bold;
        min-width: 120px;
        color: #555;
    }
    .feedback-box {
        background-color: #fffde7;
        border-left: 4px solid #ffd600;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    .highlight {
        background-color: #f1f8e9;
        padding: 0.2rem 0.4rem;
        border-radius: 0.2rem;
        font-weight: bold;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
        color: white;
    }
    .badge-exact {
        background-color: #4caf50;
    }
    .badge-relaxed {
        background-color: #ff9800;
    }
    .advice-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    .preferences-box {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
        font-size: 0.9rem;
    }
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .property-detail {
            flex-direction: column;
        }
        .property-label {
            min-width: auto;
            margin-bottom: 0.2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    # Generate a unique session ID for the user
    st.session_state.session_id = str(uuid.uuid4())

# Helper function to check if the database file exists and has data
def verify_database(db_path):
    """Check if database exists and has data"""
    try:
        if not os.path.exists(db_path):
            st.error(f"Database file not found: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties'")
        if not cursor.fetchone():
            st.error("Database does not have a properties table")
            conn.close()
            return False
        
        cursor.execute("SELECT COUNT(*) FROM properties")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            st.error("Database has no properties")
            return False
        
        return True
    except Exception as e:
        st.error(f"Database verification error: {str(e)}")
        return False

# Helper function to create the database from CSV if needed
def ensure_database_exists(csv_path, db_path):
    """Create database from CSV if it doesn't exist"""
    from utils.db_setup import create_db_schema, import_csv_to_db
    
    if not os.path.exists(db_path) or not verify_database(db_path):
        if os.path.exists(csv_path):
            st.info(f"Creating database from CSV: {csv_path}")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            import_csv_to_db(csv_path, db_path)
            return True
        else:
            st.error(f"CSV file not found: {csv_path}")
            return False
    
    return True

if "agent" not in st.session_state:
    try:
        # Detect data source type (CSV or SQLite)
        data_source_type = detect_data_source(DATA_PATH)
        
        if data_source_type == 'sqlite':
            # Check if database is valid
            if not verify_database(DATA_PATH):
                # Try to create database from CSV
                csv_path = DATA_PATH.replace('.db', '.csv')
                if not ensure_database_exists(csv_path, DATA_PATH):
                    st.error("Could not initialize database. Please check configuration.")
                    st.stop()
            
            # Create SQL-based agent
            from fix_agent import create_fixed_agent
            
            # Create agent
            print(f"Using SQLite database: {DATA_PATH}")
            st.session_state.agent = create_fixed_agent(DATA_PATH)
            
            # Set data source type for display
            st.session_state.data_source = "SQLite"
        else:
            # CSV-based approach
            from utils.property_tools import PropertyRecommendationTools
            from utils.data_loader import load_property_data
            from realestate_agent import create_real_estate_agent
            
            # Convert CSV to SQLite first
            db_path = DATA_PATH.replace('.csv', '.db')
            if ensure_database_exists(DATA_PATH, db_path):
                # Database created, use SQL-based agent
                from fix_agent import create_fixed_agent
                
                print(f"Created and using SQLite database: {db_path}")
                st.session_state.agent = create_fixed_agent(db_path)
                st.session_state.data_source = "SQLite (converted from CSV)"
            else:
                # Fallback to CSV if database creation fails
                print(f"Loading property data from CSV: {DATA_PATH}")
                property_df = load_property_data(DATA_PATH)
                print(f"Successfully loaded {len(property_df)} properties")
                
                # Create property tools
                property_tools = PropertyRecommendationTools(property_df)
                
                # Create agent
                st.session_state.agent = create_real_estate_agent(property_tools)
                
                # Set data source type for display
                st.session_state.data_source = "CSV"
        
        # Add initial welcome message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "👋 Hello! I'm your Hyderabad Real Estate Assistant. Are you looking to buy a home or invest in a property?"
        })
    except Exception as e:
        st.error(f"Error initializing the assistant: {str(e)}")
        st.stop()

# App title
st.title("🏡 Hyderabad Real Estate Assistant")
st.subheader("Your AI guide to finding the perfect property in Hyderabad")

# Display database type info
st.info(f"Using {st.session_state.data_source} database for property data")

# Function to display properties with improved formatting
def display_properties(property_data):
    try:
        # Extract data
        properties = property_data.get("properties", [])
        exact_match = property_data.get("exact_match", False)
        feedback = property_data.get("feedback", {})
        advice = property_data.get("advice", "")
        
        if not properties:
            st.warning("No properties found matching your criteria.")
            return
        
        # Display match type badge
        if exact_match:
            st.markdown('<span class="badge badge-exact">Exact Matches</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge badge-relaxed">Alternative Suggestions</span>', unsafe_allow_html=True)
        
        # Display advice if available
        if advice:
            st.markdown(f'<div class="advice-box">💡 {advice}</div>', unsafe_allow_html=True)
        
        # Count properties by area
        area_counts = {}
        for prop in properties:
            area = prop["area"]
            if area in area_counts:
                area_counts[area] += 1
            else:
                area_counts[area] = 1
        
        # Display summary by area
        if len(area_counts) > 1:
            st.markdown("<h4>Properties by Location</h4>", unsafe_allow_html=True)
            for area, count in area_counts.items():
                st.markdown(f"• {area}: {count} properties", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Display properties
        for i, prop in enumerate(properties):
            property_html = f"""
            <div class="property-card">
                <div class="property-title">{prop["name"]}</div>
                <div class="property-detail">
                    <div class="property-label">Location:</div>
                    <div>{prop["area"]}</div>
                </div>
                <div class="property-detail">
                    <div class="property-label">Type:</div>
                    <div>{prop["type"]}</div>
                </div>
                <div class="property-detail">
                    <div class="property-label">Configuration:</div>
                    <div>{prop["configuration"]}</div>
                </div>
                <div class="property-detail">
                    <div class="property-label">Size:</div>
                    <div>{prop["size"]}</div>
                </div>
                <div class="property-detail">
                    <div class="property-label">Price/sqft:</div>
                    <div>{prop["price_per_sqft"]}</div>
                </div>
                <div class="property-detail">
                    <div class="property-label">Total Price:</div>
                    <div>{prop["approx_total_price"]}</div>
                </div>
                <div class="property-detail">
                    <div class="property-label">Possession:</div>
                    <div>{prop["possession_date"]}</div>
                </div>
            </div>
            """
            st.markdown(property_html, unsafe_allow_html=True)
            
            # After every 5 properties (except the last batch), show a suggestion to refine search
            if (i + 1) % 5 == 0 and i + 1 < len(properties) and i + 1 < 15:
                st.markdown(f"""
                <div class="feedback-box">
                    To narrow down these options, consider:
                    • Specifying your budget range
                    • Adding your preferred configuration (1BHK, 2BHK, etc.)
                    • Mentioning property type (Apartment, Villa, etc.)
                </div>
                """, unsafe_allow_html=True)
        
        # If we have more than 10 properties, show a message at the end
        if len(properties) > 10:
            st.markdown(f"""
            <div class="feedback-box">
                <strong>Looking for something more specific?</strong><br>
                I've shown you {len(properties)} properties that match your criteria. To find your ideal home,
                please provide more details about your preferences such as budget range, property size, or specific configurations.
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying properties: {str(e)}")

# Function to display user preferences
def display_preferences(preferences_data):
    try:
        if preferences_data.get("has_preferences", False):
            prefs = preferences_data.get("preferences", {})
            message = preferences_data.get("message", "")
            
            if prefs:
                # Create HTML for preferences
                prefs_html = '<div class="preferences-box"><h4>Your Stored Preferences</h4>'
                
                for key, value in prefs.items():
                    prefs_html += f'<div><strong>{key.replace("_", " ").title()}:</strong> {value}</div>'
                
                # Add message
                if message:
                    prefs_html += f'<div class="mt-2"><em>{message}</em></div>'
                
                # Add suggestion to update preferences
                missing_prefs = []
                if "area" not in prefs:
                    missing_prefs.append("location")
                if "budget" not in prefs:
                    missing_prefs.append("budget range")
                if "configuration" not in prefs:
                    missing_prefs.append("BHK configuration")
                if "property_type" not in prefs:
                    missing_prefs.append("property type")
                
                if missing_prefs:
                    prefs_html += '<div class="mt-2"><strong>Suggested Updates:</strong> Consider adding your ' + ', '.join(missing_prefs) + ' to get better recommendations.</div>'
                
                prefs_html += '</div>'
                
                st.markdown(prefs_html, unsafe_allow_html=True)
        elif preferences_data.get("message"):
            # Display message for no preferences
            st.markdown(f'<div class="preferences-box">{preferences_data.get("message")}</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying preferences: {str(e)}")

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Check if we have property data to display
            if message["role"] == "assistant" and "property_data" in message:
                display_properties(message["property_data"])
            
            # Check if we have preference data to display
            if message["role"] == "assistant" and "preferences_data" in message:
                display_preferences(message["preferences_data"])

# Function to extract property data from response
def extract_property_data(response):
    try:
        # Look for property data in the intermediates or tool results
        if "intermediate_steps" in response:
            intermediate_steps = response.get("intermediate_steps", [])
            
            # Look for property data in the tool results
            for step in intermediate_steps:
                if isinstance(step, tuple) and len(step) >= 2:
                    action = step[0]
                    tool_result = step[1]
                    
                    # Check tool type
                    if hasattr(action, 'tool'):
                        if action.tool == "search_properties" and isinstance(tool_result, dict) and "properties" in tool_result:
                            return tool_result
                        elif action.tool == "get_user_preferences" and isinstance(tool_result, dict) and "has_preferences" in tool_result:
                            return tool_result
        
        # If no property data found in intermediates, try to detect it in the response text
        if "properties" in str(response) or "found properties" in str(response).lower():
            # Just set a flag that properties were mentioned
            return {"detected": True}
        
        return None
    except Exception as e:
        print(f"Error extracting data: {e}")
        return None

# User input
prompt = st.chat_input("Type your message here...")
if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Force a rerun to show user message before processing
    st.rerun()

# Check if the last message is from the user and needs a response
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_message = st.session_state.messages[-1]["content"]
    
    # Display thinking spinner
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Get response from agent - fixed version that doesn't need session_id in input
                response = st.session_state.agent.invoke({"input": user_message})
                response_text = response["output"]
                
                # Extract property data and user preferences
                property_data = None
                preferences_data = None
                
                # Look for tool results in the response
                intermediate_steps = response.get("intermediate_steps", [])
                for step in intermediate_steps:
                    if isinstance(step, tuple) and len(step) >= 2:
                        action = step[0]
                        tool_result = step[1]
                        
                        # Check tool type
                        if hasattr(action, 'tool'):
                            if action.tool == "search_properties" and isinstance(tool_result, dict) and "properties" in tool_result:
                                property_data = tool_result
                            elif action.tool == "get_user_preferences" and isinstance(tool_result, dict) and "has_preferences" in tool_result:
                                preferences_data = tool_result
                
                # Display response
                st.write(response_text)
                
                # Display property data if available
                if property_data:
                    display_properties(property_data)
                
                # Display user preferences if available
                if preferences_data and preferences_data.get("has_preferences", False):
                    display_preferences(preferences_data)
                
                # Add to chat history
                assistant_message = {"role": "assistant", "content": response_text}
                if property_data:
                    assistant_message["property_data"] = property_data
                if preferences_data:
                    assistant_message["preferences_data"] = preferences_data
                
                st.session_state.messages.append(assistant_message)
                
            except Exception as e:
                error_message = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# Sidebar with information
with st.sidebar:
    st.header("About This Assistant")
    st.write("""
    This AI real estate assistant helps you find properties in Hyderabad based on your preferences.
    
    Whether you're looking to:
    - Buy a home for your family
    - Invest in property for returns
    
    The assistant will guide you through the process and recommend suitable properties from our database.
    
    Your preferences are remembered during the conversation, so you can refine your search gradually.
    """)
    
    st.header("Popular Areas in Hyderabad")
    st.write("""
    - **Gachibowli & Hitech City**: IT hub, premium properties
    - **Kondapur & Miyapur**: Good connectivity, balanced prices
    - **Bachupally & Nizampet**: Family-friendly, upcoming areas
    - **Kukatpally**: Commercial center with various housing options
    - **Manikonda**: Near IT corridor, affordable options
    """)
    
    st.header("Tips for Home Buyers")
    st.write("""
    - ✅ Consider your commute times
    - ✅ Check builder reputation
    - ✅ Look for RERA approved projects
    - ✅ Evaluate amenities and community features
    - ✅ Account for additional costs (registration, GST)
    """)
    
    # Add conversion tool
    st.header("Budget Converter")
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Amount", min_value=0, value=10000000)
    with col2:
        unit = st.selectbox("Unit", ["Rupees", "Lakhs", "Crores"])
    
    # Calculate and display conversions
    if unit == "Rupees":
        st.write(f"₹{amount:,.2f}")
        st.write(f"₹{amount/100000:.2f} Lakhs")
        st.write(f"₹{amount/10000000:.2f} Crores")
    elif unit == "Lakhs":
        st.write(f"₹{amount*100000:,.2f}")
        st.write(f"₹{amount:.2f} Lakhs")
        st.write(f"₹{amount/100:.2f} Crores")
    else:  # Crores
        st.write(f"₹{amount*10000000:,.2f}")
        st.write(f"₹{amount*100:.2f} Lakhs")
        st.write(f"₹{amount:.2f} Crores")
    
    # Add session information
    if st.checkbox("Show session information"):
        st.subheader("Session Info")
        st.write(f"Session ID: {st.session_state.session_id}")
        st.write(f"Data Source: {st.session_state.data_source}")
        st.write(f"Number of messages: {len(st.session_state.messages)}")

        # Add database info if using SQLite
        if "SQLite" in st.session_state.data_source:
            try:
                db_path = DATA_PATH
                if not db_path.endswith('.db'):
                    db_path = db_path.replace('.csv', '.db')
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM properties")
                property_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT area) FROM properties")
                area_count = cursor.fetchone()[0]
                
                st.write(f"Database Properties: {property_count}")
                st.write(f"Unique Locations: {area_count}")
                
                conn.close()
            except Exception as e:
                st.error(f"Error getting database info: {str(e)}")