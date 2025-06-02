# whatsapp_bot.py - Enhanced WhatsApp Bot with Better Error Handling and Response Logic

import os
import sys
import json
import requests
from flask import Flask, request, jsonify
import logging
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional
import socket
import sqlite3
import time
import streamlit as st
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import LangChain components for memory management
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage

# Import your existing components
from config import DATA_PATH, WHATSAPP_API_TOKEN, WHATSAPP_PHONE_NUMBER_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("whatsapp_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Store user memories with LangChain ConversationBufferWindowMemory
user_memories = {}

# Get verify token from environment or use a default that matches what WhatsApp expects
WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'your_verify_token')

# WhatsApp API URL - Construct using the phone number ID
WHATSAPP_API_URL = f"https://graph.facebook.com/v22.0/585333798006829/messages"

# Log the API URL for debugging
logger.info(f"Using WhatsApp API URL: {WHATSAPP_API_URL}")
logger.info(f"Using WhatsApp Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
logger.info(f"Verify token: {WHATSAPP_VERIFY_TOKEN}")
logger.info(f"API Token (first 5 chars): {WHATSAPP_API_TOKEN[:5] if WHATSAPP_API_TOKEN else 'None'}")

# Test the configuration on startup
def test_whatsapp_configuration():
    """Test WhatsApp API configuration on startup"""
    logger.info("Testing WhatsApp API configuration...")
    
    if not WHATSAPP_API_TOKEN:
        logger.error("WHATSAPP_API_TOKEN not set!")
        return False
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("WHATSAPP_PHONE_NUMBER_ID not set!")
        return False
    
    # Test API connectivity with a simple request
    headers = {
        'Authorization': f'Bearer {WHATSAPP_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test with a simple API call to check if credentials work
        test_url = f"https://graph.facebook.com/v22.0/585333798006829"
        response = requests.get(test_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ WhatsApp API configuration test successful!")
            logger.info(f"Response: {response.json()}")
            return True
        else:
            logger.error(f"❌ WhatsApp API test failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ WhatsApp API test error: {e}")
        return False

# Database helper functions
def get_db_connection(db_path='data/properties.db'):
    """Get a database connection with row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def verify_database(db_path):
    """Check if database exists and has properties table"""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if properties table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties'")
        if not cursor.fetchone():
            conn.close()
            raise Exception("Database does not have a properties table")
        
        # Check if there are properties
        cursor.execute("SELECT COUNT(*) FROM properties")
        count = cursor.fetchone()[0]
        
        if count == 0:
            conn.close()
            raise Exception("Database has no properties")
        
        logger.info(f"Database verified: {count} properties found")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        raise e

# Initialize database
try:
    verify_database(DATA_PATH)
    logger.info(f"Database initialized successfully with data path: {DATA_PATH}")
except Exception as e:
    logger.error(f"Error initializing database: {e}")
    DATA_PATH = None

def find_free_port(start_port=5000, max_port=9000):
    """Find a free port to use"""
    port = start_port
    while port <= max_port:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    
    # If no ports are available in range, return a default and hope for the best
    return 8080

def get_or_create_memory(sender_id: str) -> ConversationBufferWindowMemory:
    """
    Get or create a LangChain memory for the user
    
    Args:
        sender_id: WhatsApp ID of the sender
        
    Returns:
        ConversationBufferWindowMemory: Memory object for the user
    """
    if sender_id not in user_memories:
        # Create a new memory with a window of 20 messages (10 human + 10 AI)
        user_memories[sender_id] = {
            "memory": ConversationBufferWindowMemory(
                k=20,  # Keep last 20 messages
                return_messages=True,
                memory_key="chat_history"
            ),
            "last_activity": datetime.now(),
            "remaining_properties": [],
            "user_preferences": {}
        }
        logger.info(f"Created new memory for user {sender_id}")
    
    # Update last activity
    user_memories[sender_id]["last_activity"] = datetime.now()
    
    return user_memories[sender_id]["memory"]

def get_chat_history(sender_id: str) -> List[Dict]:
    """
    Get formatted chat history for the agent
    
    Args:
        sender_id: WhatsApp ID of the sender
        
    Returns:
        List[Dict]: Formatted chat history for the agent
    """
    memory = get_or_create_memory(sender_id)
    messages = memory.chat_memory.messages
    
    # Convert LangChain messages to the format expected by the agent
    formatted_history = []
    for message in messages:
        if isinstance(message, HumanMessage):
            formatted_history.append({"role": "human", "content": message.content})
        elif isinstance(message, AIMessage):
            formatted_history.append({"role": "ai", "content": message.content})
    
    return formatted_history

def save_to_memory(sender_id: str, human_message: str, ai_message: str):
    """
    Save a human-AI message pair to memory
    
    Args:
        sender_id: WhatsApp ID of the sender
        human_message: The human's message
        ai_message: The AI's response
    """
    memory = get_or_create_memory(sender_id)
    memory.save_context(
        {"input": human_message},
        {"output": ai_message}
    )
    logger.info(f"Saved conversation to memory for user {sender_id}")

def send_whatsapp_message(recipient_id: str, message: str, max_retries: int = 3) -> Dict:
    """
    Send a message to a WhatsApp user with enhanced error handling and retries
    
    Args:
        recipient_id: WhatsApp ID of the recipient
        message: Text message to send
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dict: Response from the WhatsApp API
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {WHATSAPP_API_TOKEN}'
    }
    
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': recipient_id,
        'type': 'text',
        'text': {
            'body': message
        }
    }
    
    for attempt in range(max_retries):
        try:
            # Log request details (without full token for security)
            logger.info(f"📤 Sending message to {recipient_id} (attempt {attempt + 1}/{max_retries})")
            logger.info(f"🔹 Message preview: {message[:100]}...")
            logger.info(f"🔹 Using URL: {WHATSAPP_API_URL}")
            
            response = requests.post(
                WHATSAPP_API_URL,
                headers=headers,
                json=payload,
                timeout=30  # Add timeout
            )
            
            # Log response details
            logger.info(f"📥 WhatsApp API response:")
            logger.info(f"🔹 Status Code: {response.status_code}")
            logger.info(f"🔹 Response Headers: {dict(response.headers)}")
            logger.info(f"🔹 Response Body: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Message sent successfully!")
                logger.info(f"🆔 Message ID: {result.get('messages', [{}])[0].get('id', 'N/A')}")
                return result
            else:
                logger.error(f"❌ WhatsApp API error: {response.status_code}")
                logger.error(f"🔹 Error details: {response.text}")
                
                # Parse error response
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    error_code = error_data.get('error', {}).get('code', 'Unknown code')
                    logger.error(f"🔹 Error Code: {error_code}")
                    logger.error(f"🔹 Error Message: {error_message}")
                    
                    # Don't retry for certain errors
                    if response.status_code in [400, 401, 403]:
                        logger.error("❌ Permanent error, not retrying")
                        return {"error": error_message, "status_code": response.status_code}
                except:
                    pass
                
                # If this was the last attempt, return error
                if attempt == max_retries - 1:
                    return {"error": response.text, "status_code": response.status_code}
                
                # Wait before retrying
                wait_time = (attempt + 1) * 2  # Exponential backoff
                logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Request timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                return {"error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 Connection error on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                return {"error": "Connection error"}
        except Exception as e:
            logger.error(f"💥 Unexpected error on attempt {attempt + 1}: {e}", exc_info=True)
            if attempt == max_retries - 1:
                return {"error": str(e)}
    
    return {"error": "All retry attempts failed"}

def format_property_for_whatsapp(property_data: Dict) -> str:
    """
    Format a property object for WhatsApp display
    
    Args:
        property_data: Property data dictionary
        
    Returns:
        str: Formatted message for WhatsApp
    """
    return (
        f"🏢 *{property_data['name']}*\n\n"
        f"📍 *Location*: {property_data['area']}\n"
        f"🏠 *Type*: {property_data['type']}\n"
        f"🛏 *Configuration*: {property_data['configuration']}\n"
        f"📏 *Size*: {property_data['size']}\n"
        f"💰 *Price*: {property_data['approx_total_price']}\n"
        f"🗓 *Possession*: {property_data['possession_date']}"
    )

def handle_properties_response(sender_id: str, properties: List[Dict], advice: str) -> None:
    """
    Handle sending property results via WhatsApp with enhanced error handling
    
    Args:
        sender_id: WhatsApp ID of the recipient
        properties: List of property dictionaries
        advice: Advice text to send before properties
    """
    try:
        # Send advice message first if available
        if advice:
            result = send_whatsapp_message(sender_id, f"💡 {advice}")
            if "error" in result:
                logger.error(f"Failed to send advice: {result}")
                return
        
        # Send summary message
        if len(properties) > 0:
            summary = f"I found {len(properties)} properties matching your criteria."
            result = send_whatsapp_message(sender_id, summary)
            if "error" in result:
                logger.error(f"Failed to send summary: {result}")
                return
        
            # Send up to 3 properties in detail
            properties_to_show = min(3, len(properties))
            
            result = send_whatsapp_message(
                sender_id, 
                f"Here are the top {properties_to_show} properties:"
            )
            if "error" in result:
                logger.error(f"Failed to send property header: {result}")
                return
            
            for i, prop in enumerate(properties[:properties_to_show], 1):
                property_message = format_property_for_whatsapp(prop)
                result = send_whatsapp_message(sender_id, property_message)
                if "error" in result:
                    logger.error(f"Failed to send property {i}: {result}")
                    # Continue with next property instead of stopping
                
                # Add small delay between messages
                time.sleep(1)
            
            # If there are more properties, let the user know
            if len(properties) > properties_to_show:
                remaining = len(properties) - properties_to_show
                result = send_whatsapp_message(
                    sender_id,
                    f"There are {remaining} more properties available. Type 'more' to see the next 3 properties."
                )
                if "error" not in result:
                    # Store the remaining properties in the user session
                    if sender_id in user_memories:
                        user_memories[sender_id]["remaining_properties"] = properties[properties_to_show:]
            else:
                # No more properties to show
                if sender_id in user_memories and "remaining_properties" in user_memories[sender_id]:
                    user_memories[sender_id]["remaining_properties"] = []
        else:
            result = send_whatsapp_message(
                sender_id, 
                "I couldn't find any properties matching your exact criteria. Let me suggest some alternatives or try adjusting your preferences."
            )
            if "error" in result:
                logger.error(f"Failed to send no results message: {result}")
    
    except Exception as e:
        logger.error(f"Error in handle_properties_response: {e}", exc_info=True)

# Import the fixed agent functions - Updated to work with new fix_agent.py
try:
    # Import core functionality from fix_agent
    from fix_agent import direct_property_search, get_user_preferences
    
    # Define adapter functions to maintain compatibility
    def search_properties_directly(sender_id, **kwargs):
        """Adapter function to call direct_property_search with session_id"""
        # Add session_id to kwargs
        kwargs['session_id'] = sender_id
        return direct_property_search(**kwargs)
    
    def get_user_preferences_from_memory(sender_id):
        """Adapter function to get user preferences"""
        # Configure session ID in streamlit state
        st.session_state = {'session_id': sender_id}
        return get_user_preferences()
    
    def extract_search_params_from_message(message, chat_history=None, user_prefs=None):
        """
        Extract search parameters from user message
        Uses the process_natural_language function from fix_agent if available
        """
        try:
            from fix_agent import process_natural_language
            preferences = {}
            process_natural_language(message, preferences)
            return preferences
        except ImportError:
            # Fallback to basic extraction if process_natural_language is not available
            preferences = {}
            
            # Extract area (basic implementation)
            area_match = re.search(r'in\s+([A-Za-z\s]+)', message, re.IGNORECASE)
            if area_match:
                preferences['area'] = area_match.group(1).strip()
            
            # Extract property type
            if 'apartment' in message.lower():
                preferences['property_type'] = 'Apartment'
            elif 'villa' in message.lower():
                preferences['property_type'] = 'Villa'
            
            # Extract BHK
            bhk_match = re.search(r'(\d+)\s*bhk', message, re.IGNORECASE)
            if bhk_match:
                preferences['configurations'] = f"{bhk_match.group(1)}BHK"
            
            return preferences
    
    def create_response_with_context(message, chat_history=None, search_results=None):
        """Generate a response based on context"""
        if search_results and search_results.get('properties'):
            property_count = len(search_results['properties'])
            
            if property_count > 0:
                area = search_results['properties'][0]['area']
                return f"I've found {property_count} properties in {area} that might interest you. Let me show you some details."
            else:
                return "I couldn't find any properties matching your exact criteria. Would you like to adjust your search?"
        else:
            # Default responses based on message content
            if 'hello' in message.lower() or 'hi' in message.lower():
                return "Hello! I'm your Hyderabad Real Estate Assistant. What kind of property are you looking for?"
            elif 'property' in message.lower() or 'home' in message.lower() or 'house' in message.lower():
                return "I can help you find properties in Hyderabad. Could you tell me which area you're interested in?"
            elif 'thank' in message.lower():
                return "You're welcome! Is there anything else you'd like to know about properties in Hyderabad?"
            else:
                return "I'm your Hyderabad Real Estate Assistant. I can help you find properties based on your preferences. What are you looking for today?"
    
    logger.info("✅ Successfully imported and adapted functions from fix_agent")
except ImportError as e:
    logger.error(f"❌ Failed to import from fix_agent: {e}")
    # Provide fallback functions
    def search_properties_directly(*args, **kwargs):
        return {"properties": [], "count": 0, "advice": "Property search not available"}
    
    def get_user_preferences_from_memory(*args, **kwargs):
        return {"has_preferences": False, "message": "Preferences not available"}
    
    def extract_search_params_from_message(*args, **kwargs):
        return {}
    
    def create_response_with_context(*args, **kwargs):
        return "I'm sorry, the system is not fully available right now."

# Add a root route for basic testing
@app.route('/', methods=['GET'])
def home():
    """Home route for basic server testing"""
    return jsonify({
        "status": "ok",
        "message": "WhatsApp Real Estate Assistant webhook server is running",
        "active_users": len(user_memories),
        "whatsapp_api_test": test_whatsapp_configuration(),
        "endpoints": {
            "/webhook": "WhatsApp webhook endpoint",
            "/webhook-test": "Test endpoint for webhook configuration",
            "/test-send": "Test endpoint to send a WhatsApp message",
            "/process-message": "Manual message processing endpoint",
            "/memory-stats": "View memory statistics"
        }
    })

# Add memory statistics endpoint
@app.route('/memory-stats', methods=['GET'])
def memory_stats():
    """View memory statistics for debugging"""
    stats = {}
    for user_id, user_data in user_memories.items():
        memory = user_data["memory"]
        stats[user_id] = {
            "message_count": len(memory.chat_memory.messages),
            "last_activity": user_data["last_activity"].isoformat(),
            "has_remaining_properties": len(user_data.get("remaining_properties", [])) > 0,
            "has_preferences": len(user_data.get("user_preferences", {})) > 0
        }
    
    return jsonify({
        "total_users": len(user_memories),
        "user_stats": stats,
        "database_status": "connected" if DATA_PATH else "not connected",
        "whatsapp_api_status": "configured" if WHATSAPP_API_TOKEN else "not configured"
    })

# Add a test endpoint to send a message directly
@app.route('/test-send', methods=['GET', 'POST'])
def test_send():
    """Test endpoint to send a WhatsApp message"""
    try:
        if request.method == 'POST':
            data = request.json or {}
            recipient = data.get('phone', request.args.get('phone', '919100246849'))
            message = data.get('message', request.args.get('message', 'Test message from Hyderabad Real Estate Assistant'))
        else:
            # GET request
            recipient = request.args.get('phone', '919100246849')
            message = request.args.get('message', 'Test message from Hyderabad Real Estate Assistant')
        
        logger.info(f"🧪 Testing message send to {recipient}")
        
        # Check if configuration is valid
        if not test_whatsapp_configuration():
            return jsonify({
                "status": "error",
                "message": "WhatsApp API configuration test failed. Check your tokens and phone number ID."
            }), 500
        
        # Send the message
        result = send_whatsapp_message(recipient, message)
        
        return jsonify({
            "status": "success" if "error" not in result else "error", 
            "recipient": recipient, 
            "message": message, 
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error sending test message: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# Webhook verification route
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Verify the webhook for WhatsApp API
    """
    # Log all request parameters for debugging
    logger.info(f"🔍 Webhook verification request received")
    logger.info(f"🔹 Query params: {dict(request.args)}")
    logger.info(f"🔹 Headers: {dict(request.headers)}")
    
    # WhatsApp sends a verification token
    verify_token = request.args.get('hub.verify_token')
    mode = request.args.get('hub.mode')
    challenge = request.args.get('hub.challenge')
    
    logger.info(f"🔑 Verifying webhook:")
    logger.info(f"🔹 Mode: {mode}")
    logger.info(f"🔹 Received token: {verify_token}")
    logger.info(f"🔹 Expected token: {WHATSAPP_VERIFY_TOKEN}")
    logger.info(f"🔹 Challenge: {challenge}")
    logger.info(f"🔹 Token match: {verify_token == WHATSAPP_VERIFY_TOKEN}")
    
    # Check if the verification token matches your token
    if mode == 'subscribe' and verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info(f"✅ Webhook verified successfully, returning challenge: {challenge}")
        return challenge, 200
    
    logger.error(f"❌ Webhook verification failed.")
    logger.error(f"🔹 Expected mode: 'subscribe', received: '{mode}'")
    logger.error(f"🔹 Expected token: '{WHATSAPP_VERIFY_TOKEN}', received: '{verify_token}'")
    return jsonify({"error": "Verification failed", "expected_token": WHATSAPP_VERIFY_TOKEN}), 403

# Webhook message handling route
@app.route('/webhook', methods=['POST'])
def webhook_post():
    """Enhanced webhook handler for WhatsApp API with better message parsing"""
    try:
        # Log request details
        request_data = request.get_data(as_text=True)
        logger.info(f"📬 WEBHOOK POST - Received data: {request_data}")
        
        # Get client IP for security
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        logger.info(f"🌐 Request from IP: {client_ip}")
        
        try:
            data = request.json
            if not data:
                logger.warning("⚠️ No JSON data received")
                return jsonify({"status": "error", "message": "No JSON data"}), 400
            
            logger.info(f"📋 Parsed JSON data: {json.dumps(data, indent=2)}")
            
            # Enhanced message parsing
            processed_messages = 0
            
            # Check if it's a WhatsApp webhook format
            if 'entry' in data:
                for entry in data.get('entry', []):
                    logger.info(f"🔍 Processing entry: {entry}")
                    
                    # Handle messages
                    for change in entry.get('changes', []):
                        if change.get('field') == 'messages':
                            value = change.get('value', {})
                            
                            # Get metadata
                            metadata = value.get('metadata', {})
                            phone_number_id = metadata.get('phone_number_id')
                            logger.info(f"📞 Message for phone number ID: {phone_number_id}")
                            
                            # Process each message
                            messages = value.get('messages', [])
                            for message in messages:
                                sender_id = message.get('from')
                                message_id = message.get('id')
                                timestamp = message.get('timestamp')
                                
                                logger.info(f"📨 Processing message:")
                                logger.info(f"🔹 From: {sender_id}")
                                logger.info(f"🔹 ID: {message_id}")
                                logger.info(f"🔹 Timestamp: {timestamp}")
                                logger.info(f"🔹 Type: {message.get('type')}")
                                
                                # Extract message text based on type
                                message_text = None
                                
                                if message.get('type') == 'text':
                                    message_text = message.get('text', {}).get('body')
                                elif message.get('type') == 'interactive':
                                    # Handle interactive messages (buttons, lists, etc.)
                                    interactive = message.get('interactive', {})
                                    if interactive.get('type') == 'button_reply':
                                        message_text = interactive.get('button_reply', {}).get('title')
                                    elif interactive.get('type') == 'list_reply':
                                        message_text = interactive.get('list_reply', {}).get('title')
                                
                                if message_text and sender_id:
                                    logger.info(f"✅ Found valid message: '{message_text}' from {sender_id}")
                                    
                                    # Process the message asynchronously to avoid timeout
                                    try:
                                        process_whatsapp_message(sender_id, message_text)
                                        processed_messages += 1
                                    except Exception as process_error:
                                        logger.error(f"❌ Error processing message: {process_error}", exc_info=True)
                                        # Send an error message to the user
                                        try:
                                            send_whatsapp_message(
                                                sender_id, 
                                                "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
                                            )
                                        except:
                                            pass
                                else:
                                    logger.warning(f"⚠️ Could not extract message text or sender ID")
                                    logger.warning(f"🔹 Message: {message}")
                            
                            # Handle message status updates
                            statuses = value.get('statuses', [])
                            for status in statuses:
                                logger.info(f"📊 Message status update: {status}")
            else:
                logger.warning(f"⚠️ Unexpected webhook format: {data}")
            
            # Log summary
            logger.info(f"📈 Processed {processed_messages} messages")
            
            return jsonify({
                "status": "success", 
                "processed_messages": processed_messages,
                "timestamp": datetime.now().isoformat()
            }), 200
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            logger.error(f"🔹 Raw data: {request_data}")
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400
        except Exception as e:
            logger.error(f"❌ Error processing webhook data: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500
    
    except Exception as e:
        logger.error(f"❌ WEBHOOK POST - Critical error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/webhook-test', methods=['GET'])
def test_webhook():
    """Test endpoint to verify webhook configuration"""
    config_status = test_whatsapp_configuration()
    
    return jsonify({
        "status": "webhook test endpoint",
        "environment_verify_token": WHATSAPP_VERIFY_TOKEN[:3] + "..." if WHATSAPP_VERIFY_TOKEN and len(WHATSAPP_VERIFY_TOKEN) > 3 else "not set",
        "whatsapp_phone_id": WHATSAPP_PHONE_NUMBER_ID,
        "whatsapp_api_url": WHATSAPP_API_URL,
        "data_path": DATA_PATH,
        "database_connected": DATA_PATH is not None,
        "whatsapp_config_valid": config_status,
        "active_users": len(user_memories),
        "timestamp": datetime.now().isoformat()
    })

# Manual message processing endpoint
@app.route('/process-message', methods=['POST'])
def process_message():
    """Manual message processing endpoint for testing"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400
        
        sender_id = data.get('sender_id')
        message = data.get('message')
        
        if not sender_id or not message:
            return jsonify({
                "status": "error", 
                "message": "Both 'sender_id' and 'message' are required"
            }), 400
        
        logger.info(f"🔧 Manual processing: sender={sender_id}, message={message}")
        
        # Process the message
        process_whatsapp_message(sender_id, message)
        
        return jsonify({
            "status": "success",
            "message": "Message processed successfully",
            "sender_id": sender_id,
            "processed_message": message,
            "memory_messages": len(user_memories.get(sender_id, {}).get("memory", ConversationBufferWindowMemory()).chat_memory.messages),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in manual processing: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.before_request
def log_request_info():
    """Log every request for debugging"""
    if request.path not in ['/favicon.ico', '/']:  # Skip favicon and home requests
        logger.info(f"📥 Request: {request.method} {request.path}")

def process_whatsapp_message(sender_id: str, message_text: str) -> None:
    """
    Enhanced process a message from a WhatsApp user with better error handling
    
    Args:
        sender_id: WhatsApp ID of the sender
        message_text: Message text from the user
    """
    logger.info(f"🔄 Processing message from {sender_id}: {message_text}")
    
    # Check if database is available
    if DATA_PATH is None:
        logger.error("❌ Cannot process message: Database not available")
        send_whatsapp_message(
            sender_id,
            "I'm sorry, but I'm currently unable to access the property database. Please try again later."
        )
        return
    
    # Check WhatsApp API configuration
    if not WHATSAPP_API_TOKEN:
        logger.error("❌ Cannot send response: WhatsApp API token not configured")
        return
    
    try:
        # Get or create memory for this user
        memory = get_or_create_memory(sender_id)
        
        # Get chat history and user preferences
        chat_history = get_chat_history(sender_id)
        user_prefs = user_memories[sender_id].get("user_preferences", {})
        
        # Check if user is asking for more properties
        if message_text.lower() in ['more', 'next', 'show more']:
            if sender_id in user_memories and user_memories[sender_id]["remaining_properties"]:
                remaining = user_memories[sender_id]["remaining_properties"]
                properties_to_show = min(3, len(remaining))
                
                result = send_whatsapp_message(sender_id, f"Here are the next {properties_to_show} properties:")
                if "error" in result:
                    logger.error(f"Failed to send 'more properties' header: {result}")
                    return
                
                for i, prop in enumerate(remaining[:properties_to_show], 1):
                    property_message = format_property_for_whatsapp(prop)
                    result = send_whatsapp_message(sender_id, property_message)
                    if "error" in result:
                        logger.error(f"Failed to send property {i}: {result}")
                        continue
                    time.sleep(1)  # Add delay between messages
                
                # Update remaining properties
                user_memories[sender_id]["remaining_properties"] = remaining[properties_to_show:]
                
                # If there are still more properties, let the user know
                if len(remaining) > properties_to_show:
                    still_remaining = len(remaining) - properties_to_show
                    result = send_whatsapp_message(
                        sender_id,
                        f"There are {still_remaining} more properties available. Type 'more' to see the next 3 properties."
                    )
                    if "error" in result:
                        logger.error(f"Failed to send remaining count: {result}")
                else:
                    result = send_whatsapp_message(
                        sender_id,
                        "That's all the properties I have for you. Ask me anything else about real estate in Hyderabad!"
                    )
                    if "error" in result:
                        logger.error(f"Failed to send completion message: {result}")
                    user_memories[sender_id]["remaining_properties"] = []
                
                # Save to memory
                save_to_memory(sender_id, message_text, f"Showed {properties_to_show} more properties")
                return
            else:
                result = send_whatsapp_message(
                    sender_id,
                    "I don't have any more properties to show you from your last search. Please let me know what kind of property you're looking for."
                )
                if "error" in result:
                    logger.error(f"Failed to send no more properties message: {result}")
                return
        
        # Check if user is asking for preferences
        if any(phrase in message_text.lower() for phrase in ['my preferences', 'current preferences', 'saved preferences']):
            prefs_result = get_user_preferences_from_memory(sender_id)
            
            if prefs_result["has_preferences"]:
                prefs_list = []
                for key, value in prefs_result["preferences"].items():
                    prefs_list.append(f"• {key.replace('_', ' ').title()}: {value}")
                
                response_text = f"📋 Your Current Preferences:\n\n" + "\n".join(prefs_list)
                response_text += "\n\nYou can update any of these by telling me your new preferences!"
            else:
                response_text = prefs_result["message"]
            
            result = send_whatsapp_message(sender_id, response_text)
            if "error" in result:
                logger.error(f"Failed to send preferences: {result}")
            else:
                save_to_memory(sender_id, message_text, response_text)
            return
        
        # Extract search parameters from the message
        search_params = extract_search_params_from_message(message_text, chat_history, user_prefs)
        
        # Generate initial response based on context
        initial_response = create_response_with_context(message_text, chat_history)
        
        # If we have search parameters, perform the search
        if search_params:
            logger.info(f"🔍 Extracted search params: {search_params}")
            
            # Set up session ID in st.session_state for direct_property_search to use
            import streamlit as st
            st.session_state = {'session_id': sender_id}
            
            # Perform property search directly with the extracted parameters
            try:
                # Try using direct_property_search from fix_agent
                from fix_agent import direct_property_search
                search_results = direct_property_search(**search_params)
            except (ImportError, AttributeError):
                # Fallback to our adapter function
                search_results = search_properties_directly(sender_id, **search_params)
            
            # Update response based on search results
            final_response = create_response_with_context(message_text, chat_history, search_results)
            
            # Send the response
            result = send_whatsapp_message(sender_id, final_response)
            if "error" in result:
                logger.error(f"Failed to send search response: {result}")
                # Try sending a simplified error message
                send_whatsapp_message(sender_id, "I found some properties but had trouble sending the details. Please try again.")
                return
            
            # Save to memory
            save_to_memory(sender_id, message_text, final_response)
            
            # If we have properties, send them formatted
            if search_results and search_results.get('properties'):
                properties = search_results['properties']
                advice = search_results.get('advice', '')
                handle_properties_response(sender_id, properties, advice)
        else:
            # No search parameters found, just send conversational response
            result = send_whatsapp_message(sender_id, initial_response)
            if "error" in result:
                logger.error(f"Failed to send conversational response: {result}")
                # Try sending a simplified message
                send_whatsapp_message(sender_id, "I'm here to help you with real estate in Hyderabad. What can I assist you with?")
            else:
                save_to_memory(sender_id, message_text, initial_response)
        
        logger.info(f"✅ Successfully processed message. Memory now has {len(memory.chat_memory.messages)} messages")
        
    except Exception as e:
        logger.error(f"💥 Error processing message: {e}", exc_info=True)
        # Send error message to user
        try:
            error_response = "I apologize, but I encountered an error while processing your message. Please try rephrasing your request or try again later."
            result = send_whatsapp_message(sender_id, error_response)
            if "error" not in result:
                save_to_memory(sender_id, message_text, error_response)
        except Exception as send_error:
            logger.error(f"❌ Failed to send error message: {send_error}")

def run_whatsapp_bot(host='0.0.0.0', port=None):
    """
    Run the WhatsApp bot server with enhanced startup checks
    
    Args:
        host: Host to run the server on
        port: Port to run the server on (will find a free port if None)
    """
    # Test configuration before starting
    logger.info("🚀 Starting WhatsApp Real Estate Assistant Bot...")
    
    # Check database
    if DATA_PATH:
        logger.info("✅ Database connection available")
    else:
        logger.warning("⚠️ Database not available - limited functionality")
    
    # Test WhatsApp API
    if test_whatsapp_configuration():
        logger.info("✅ WhatsApp API configuration valid")
    else:
        logger.error("❌ WhatsApp API configuration invalid!")
        logger.error("Please check your WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID in config.py")
    
    # Find a free port if none is specified
    if port is None:
        port = find_free_port()
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    print(f"\n{'='*60}")
    print(f"🏡 WhatsApp Real Estate Assistant Bot Starting...")
    print(f"{'='*60}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📞 WhatsApp Phone ID: {WHATSAPP_PHONE_NUMBER_ID}")
    print(f"🔑 API Token: {'✅ Configured' if WHATSAPP_API_TOKEN else '❌ Missing'}")
    print(f"💾 Database: {'✅ Connected' if DATA_PATH else '❌ Not Available'}")
    print(f"{'='*60}")
    print(f"📋 Available Endpoints:")
    print(f"  • Status: http://localhost:{port}/")
    print(f"  • Webhook: http://localhost:{port}/webhook")
    print(f"  • Test Send: http://localhost:{port}/test-send")
    print(f"  • Memory Stats: http://localhost:{port}/memory-stats")
    print(f"  • Manual Process: POST http://localhost:{port}/process-message")
    print(f"{'='*60}")
    print(f"🔧 Testing Commands:")
    print(f"  • Test send: curl -X GET 'http://localhost:{port}/test-send?phone=YOUR_PHONE&message=Hello'")
    print(f"  • Manual process: curl -X POST http://localhost:{port}/process-message -H 'Content-Type: application/json' -d '{{\"sender_id\":\"test\",\"message\":\"hello\"}}'")
    print(f"{'='*60}\n")
    
    # Run the Flask app
    try:
        app.run(host=host, port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        print(f"❌ Failed to start server: {e}")

if __name__ == "__main__":
    # Try to run on port 5001, but find a free port if it's in use
    run_whatsapp_bot(port=None)