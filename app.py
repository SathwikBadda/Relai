# app.py - Streamlit frontend for the Real Estate Chatbot

import streamlit as st
import pandas as pd
import os
import sys
import time

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.property_tools import PropertyRecommendationTools
from utils.data_loader import load_property_data
from realestate_agent import create_real_estate_agent
from config import DATA_PATH

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
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .property-title {
        font-weight: bold;
        color: #1e88e5;
    }
    .property-detail {
        display: flex;
        flex-direction: row;
        margin-top: 0.3rem;
    }
    .property-label {
        font-weight: bold;
        min-width: 120px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    try:
        # Load data
        print(f"Loading property data from: {DATA_PATH}")
        property_df = load_property_data(DATA_PATH)
        print(f"Successfully loaded {len(property_df)} properties")
        
        # Create property tools
        property_tools = PropertyRecommendationTools(property_df)
        
        # Create agent
        st.session_state.agent = create_real_estate_agent(property_tools)
        
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

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# Function to format property recommendations
def format_property_results(properties):
    result_html = ""
    for prop in properties:
        result_html += f"""
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
    return result_html

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
                # Get response from agent
                response = st.session_state.agent.invoke({"input": user_message})
                response_text = response["output"]
                
                # Display response
                st.write(response_text)
                
                # Add to chat history
                st.session_state.messages.append({"role": "assistant", "content": response_text})
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
    
    # Add debug section
    if st.checkbox("Show debugging information"):
        st.subheader("Debug Info")
        st.write(f"Number of messages: {len(st.session_state.messages)}")
        for i, msg in enumerate(st.session_state.messages):
            st.write(f"Message {i}: {msg['role']} - {msg['content'][:50]}...")