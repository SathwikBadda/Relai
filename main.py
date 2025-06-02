# whatsapp_bot.py - WhatsApp Bot Integration for Real Estate Assistant - FIXED VERSION

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

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your existing components
from fix_agent import create_fixed_agent
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

# Store user sessions with enhanced data
user_sessions = {}

# Get your verify token from env vars or use a default 
WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'your_verify_token')

# WhatsApp API URL - Construct using the phone number ID
WHATSAPP_API_URL = f"https://graph.facebook.com/v22.0/596790770173493/messages"

# Log the API URL for debugging
logger.info(f"Using WhatsApp API URL: {WHATSAPP_API_URL}")
logger.info(f"Using WhatsApp Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
logger.info(f"API Token (first 5 chars): {WHATSAPP_API_TOKEN[:5] if WHATSAPP_API_TOKEN else 'None'}")

# Initialize your agent - ENHANCED INITIALIZATION LIKE APP.PY
if "agent" not in globals():
    try:
        from utils.data_loader import detect_data_source
        
        # Detect data source type (CSV or SQLite)
        data_source_type = detect_data_source(DATA_PATH)
        
        if data_source_type == 'sqlite':
            # Check if database is valid
            def verify_database(db_path):
                """Check if database exists and has data"""
                try:
                    if not os.path.exists(db_path):
                        logger.error(f"Database file not found: {db_path}")
                        return False
                    
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties'")
                    if not cursor.fetchone():
                        logger.error("Database does not have a properties table")
                        conn.close()
                        return False
                    
                    cursor.execute("SELECT COUNT(*) FROM properties")
                    count = cursor.fetchone()[0]
                    conn.close()
                    
                    if count == 0:
                        logger.error("Database has no properties")
                        return False
                    
                    return True
                except Exception as e:
                    logger.error(f"Database verification error: {str(e)}")
                    return False
            
            if not verify_database(DATA_PATH):
                # Try to create database from CSV
                csv_path = DATA_PATH.replace('.db', '.csv')
                from utils.db_setup import import_csv_to_db
                if os.path.exists(csv_path):
                    logger.info(f"Creating database from CSV: {csv_path}")
                    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
                    import_csv_to_db(csv_path, DATA_PATH)
                else:
                    logger.error(f"CSV file not found: {csv_path}")
                    raise FileNotFoundError("Could not initialize database")
            
            # Create SQL-based agent
            logger.info(f"Using SQLite database: {DATA_PATH}")
            agent = create_fixed_agent(DATA_PATH)
            data_source = "SQLite"
            
        else:
            # CSV-based approach - convert to SQLite first
            db_path = DATA_PATH.replace('.csv', '.db')
            from utils.db_setup import import_csv_to_db
            
            if os.path.exists(DATA_PATH):
                logger.info(f"Converting CSV to SQLite: {DATA_PATH} -> {db_path}")
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                import_csv_to_db(DATA_PATH, db_path)
                
                # Use SQL-based agent
                agent = create_fixed_agent(db_path)
                data_source = "SQLite (converted from CSV)"
            else:
                raise FileNotFoundError(f"Data file not found: {DATA_PATH}")
        
        logger.info(f"Agent initialized successfully with {data_source}")
        
    except Exception as e:
        logger.error(f"Error initializing agent: {e}")
        agent = None

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

def send_whatsapp_message(recipient_id: str, message: str) -> Dict:
    """
    Send a message to a WhatsApp user
    
    Args:
        recipient_id: WhatsApp ID of the recipient
        message: Text message to send
        
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
    
    try:
        # Log request details (without full token for security)
        logger.info(f"Sending message to {recipient_id}: {message[:100]}...")
        
        response = requests.post(
            WHATSAPP_API_URL,
            headers=headers,
            json=payload
        )
        
        # Log response
        logger.info(f"WhatsApp API response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
        
        return response.json() if response.status_code == 200 else {"error": response.text, "status_code": response.status_code}
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
        return {"error": str(e)}

def format_property_for_whatsapp(property_data: Dict) -> str:
    """
    Format a property object for WhatsApp display - ENHANCED VERSION
    
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
        f"💰 *Price/sqft*: {property_data['price_per_sqft']}\n"
        f"💵 *Total Price*: {property_data['approx_total_price']}\n"
        f"🗓 *Possession*: {property_data['possession_date']}\n"
        f"───────────────────"
    )

def get_or_create_session(sender_id: str) -> str:
    """
    Get an existing session ID or create a new one
    
    Args:
        sender_id: WhatsApp ID of the sender
        
    Returns:
        str: Session ID
    """
    if sender_id not in user_sessions:
        user_sessions[sender_id] = {
            "session_id": str(uuid.uuid4()),
            "last_activity": datetime.now(),
            "conversation_history": []
        }
        logger.info(f"Created new session for {sender_id}: {user_sessions[sender_id]['session_id']}")
    
    # Update last activity
    user_sessions[sender_id]["last_activity"] = datetime.now()
    return user_sessions[sender_id]["session_id"]

# ENHANCED FUNCTION FROM APP.PY - Extract property data from response
def extract_property_data(response):
    """Extract property data from agent response with better error handling"""
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
        
        return None
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        return None

def handle_properties_response(sender_id: str, property_data: Dict) -> None:
    """
    Handle sending property results via WhatsApp - ENHANCED VERSION FROM APP.PY
    
    Args:
        sender_id: WhatsApp ID of the recipient
        property_data: Property data dictionary with properties, advice, feedback
    """
    try:
        # Extract data like in app.py
        properties = property_data.get("properties", [])
        exact_match = property_data.get("exact_match", False)
        feedback = property_data.get("feedback", {})
        advice = property_data.get("advice", "")
        
        if not properties:
            send_whatsapp_message(sender_id, "❌ No properties found matching your criteria. Try adjusting your search parameters.")
            return
        
        # Send match type info
        if exact_match:
            send_whatsapp_message(sender_id, f"✅ *Found {len(properties)} exact matches!*")
        else:
            send_whatsapp_message(sender_id, f"🔍 *Found {len(properties)} alternative suggestions*")
        
        # Send advice if available
        if advice:
            send_whatsapp_message(sender_id, f"💡 *Advice*: {advice}")
        
        # Send summary statistics like in app.py
        area_counts = {}
        type_counts = {}
        config_counts = {}
        
        for prop in properties:
            # Count by area
            area = prop["area"]
            area_counts[area] = area_counts.get(area, 0) + 1
            
            # Count by type
            p_type = prop["type"]
            type_counts[p_type] = type_counts.get(p_type, 0) + 1
            
            # Count by configuration
            configs = prop["configuration"].split(", ")
            for config in configs:
                if config != "Not specified":
                    config_counts[config] = config_counts.get(config, 0) + 1
        
        # Send summary message
        summary_parts = []
        if len(area_counts) > 1:
            top_areas = sorted(area_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            summary_parts.append(f"📍 *Top Areas*: {', '.join([f'{a} ({c})' for a, c in top_areas])}")
        
        if len(type_counts) > 1:
            summary_parts.append(f"🏠 *Types*: {', '.join([f'{t} ({c})' for t, c in type_counts.items()])}")
        
        if len(config_counts) > 1:
            top_configs = sorted(config_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            summary_parts.append(f"🛏 *Configs*: {', '.join([f'{c} ({count})' for c, count in top_configs])}")
        
        if summary_parts:
            summary_message = "📊 *Summary*:\n" + "\n".join(summary_parts)
            send_whatsapp_message(sender_id, summary_message)
        
        # Send first 3 properties in detail
        properties_to_show = min(3, len(properties))
        
        if properties_to_show > 0:
            send_whatsapp_message(
                sender_id, 
                f"🏡 *Here are the top {properties_to_show} properties:*"
            )
            
            for i, prop in enumerate(properties[:properties_to_show], 1):
                property_message = f"*Property {i}*:\n" + format_property_for_whatsapp(prop)
                send_whatsapp_message(sender_id, property_message)
        
        # If there are more properties, let the user know
        if len(properties) > properties_to_show:
            remaining = len(properties) - properties_to_show
            send_whatsapp_message(
                sender_id,
                f"📋 *{remaining} more properties available.*\nType 'more' to see the next 3 properties."
            )
            
            # Store the remaining properties in the user session
            user_sessions[sender_id]["remaining_properties"] = properties[properties_to_show:]
        else:
            # No more properties to show
            if "remaining_properties" in user_sessions[sender_id]:
                del user_sessions[sender_id]["remaining_properties"]
                
    except Exception as e:
        logger.error(f"Error in handle_properties_response: {e}")
        send_whatsapp_message(sender_id, "❌ Error displaying properties. Please try again.")

def handle_preferences_response(sender_id: str, preferences_data: Dict) -> None:
    """
    Handle sending user preferences via WhatsApp - NEW FUNCTION FROM APP.PY LOGIC
    
    Args:
        sender_id: WhatsApp ID of the recipient
        preferences_data: Preferences data dictionary
    """
    try:
        if preferences_data.get("has_preferences", False):
            prefs = preferences_data.get("preferences", {})
            message = preferences_data.get("message", "")
            
            if prefs:
                prefs_message = "🎯 *Your Stored Preferences*:\n\n"
                
                for key, value in prefs.items():
                    prefs_message += f"• *{key.replace('_', ' ').title()}*: {value}\n"
                
                if message:
                    prefs_message += f"\n💬 {message}"
                
                send_whatsapp_message(sender_id, prefs_message)
        elif preferences_data.get("message"):
            # Display message for no preferences
            send_whatsapp_message(sender_id, f"📝 {preferences_data.get('message')}")
            
    except Exception as e:
        logger.error(f"Error in handle_preferences_response: {e}")
        send_whatsapp_message(sender_id, "❌ Error displaying preferences.")

# Add a root route for basic testing
@app.route('/', methods=['GET'])
def home():
    """Home route for basic server testing"""
    return jsonify({
        "status": "ok",
        "message": "WhatsApp Real Estate Assistant webhook server is running",
        "agent_status": "initialized" if agent else "failed to initialize",
        "data_source": data_source if 'data_source' in globals() else "unknown",
        "endpoints": {
            "/webhook": "WhatsApp webhook endpoint",
            "/webhook-test": "Test endpoint for webhook configuration",
            "/test-send": "Test endpoint to send a WhatsApp message"
        }
    })

# Add a test endpoint to send a message directly
@app.route('/test-send', methods=['GET'])
def test_send():
    """Test endpoint to send a WhatsApp message"""
    try:
        # Get test phone number from query param or use a default
        recipient = request.args.get('phone', '919100246849')  # Add country code
        message = request.args.get('message', 'Test message from Hyderabad Real Estate Assistant!')
        
        logger.info(f"Sending test message to {recipient}: {message}")
        
        # Send the message
        result = send_whatsapp_message(recipient, message)
        
        return jsonify({
            "status": "success" if "error" not in result else "error", 
            "recipient": recipient, 
            "message": message, 
            "result": result
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
    logger.info(f"Webhook verification request received with args: {request.args}")
    
    # WhatsApp sends a verification token
    verify_token = request.args.get('hub.verify_token')
    mode = request.args.get('hub.mode')
    challenge = request.args.get('hub.challenge')
    
    logger.info(f"Verifying webhook: mode={mode}, token_match={verify_token==WHATSAPP_VERIFY_TOKEN}")
    
    # Check if the verification token matches your token
    if mode == 'subscribe' and verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info(f"Webhook verified successfully, returning challenge: {challenge}")
        return challenge
    
    logger.error(f"Webhook verification failed. Expected: {WHATSAPP_VERIFY_TOKEN}, Received: {verify_token}")
    return 'Verification failed', 403

# Webhook message handling route - COMPLETELY REWRITTEN WITH APP.PY LOGIC
@app.route('/webhook', methods=['POST'])
def webhook_post():
    """Webhook handler for WhatsApp API - ENHANCED VERSION"""
    try:
        # Log everything
        request_data = request.get_data(as_text=True)
        logger.info(f"WEBHOOK POST - Raw request data: {request_data}")
        
        try:
            data = request.json
            logger.info(f"WEBHOOK POST - JSON data: {json.dumps(data)}")
            
            # Process all messages in the webhook data
            processed_messages = 0
            
            # Check standard format
            if 'entry' in data and data['entry']:
                for entry in data['entry']:
                    for change in entry.get('changes', []):
                        if 'value' in change and 'messages' in change['value']:
                            for message in change['value']['messages']:
                                if 'from' in message and 'text' in message:
                                    sender_id = message['from']
                                    message_text = message['text'].get('body', '')
                                    
                                    if message_text:  # Only process non-empty messages
                                        logger.info(f"Processing message from {sender_id}: {message_text}")
                                        process_whatsapp_message(sender_id, message_text)
                                        processed_messages += 1
            
            logger.info(f"Processed {processed_messages} messages")
            
        except Exception as e:
            logger.error(f"Error processing webhook data: {e}", exc_info=True)
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"WEBHOOK POST - Error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/webhook-test', methods=['GET'])
def test_webhook():
    """Test endpoint to verify webhook configuration"""
    return jsonify({
        "status": "webhook test endpoint",
        "environment_verify_token": WHATSAPP_VERIFY_TOKEN[:3] + "..." if WHATSAPP_VERIFY_TOKEN and len(WHATSAPP_VERIFY_TOKEN) > 3 else "not set",
        "whatsapp_phone_id": WHATSAPP_PHONE_NUMBER_ID,
        "whatsapp_api_url": WHATSAPP_API_URL,
        "data_path": DATA_PATH,
        "agent_initialized": agent is not None,
        "data_source": data_source if 'data_source' in globals() else "unknown"
    })

# Add a catch-all route to log undefined paths
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    """Log and catch any undefined routes"""
    logger.info(f"Catch-all handler triggered: {request.method} /{path}")
    return jsonify({"status": "error", "message": f"Undefined route: /{path}"}), 404

@app.before_request
def log_request_info():
    """Log every request for debugging"""
    if request.path != '/favicon.ico':  # Skip favicon requests
        logger.info(f"Request: {request.method} {request.path}")
        if request.args:
            logger.info(f"Request args: {request.args}")

@app.after_request
def log_response_info(response):
    """Log details about the response"""
    logger.info(f"Response status: {response.status}")
    return response

def process_whatsapp_message(sender_id: str, message_text: str) -> None:
    """
    Process a message from a WhatsApp user - COMPLETELY REWRITTEN WITH APP.PY LOGIC
    
    Args:
        sender_id: WhatsApp ID of the sender
        message_text: Message text from the user
    """
    try:
        # Send typing indicator (acknowledgment)
        send_whatsapp_message(sender_id, "⏳ Processing your request...")
        logger.info(f"Sent acknowledgment to {sender_id}")
        
        # Check if agent is initialized
        if agent is None:
            logger.error("Cannot process message: Agent not initialized")
            send_whatsapp_message(
                sender_id,
                "❌ I'm sorry, but I'm currently unavailable. Please try again later."
            )
            return
        
        # Get or create session for this user
        session_id = get_or_create_session(sender_id)
        
        # Add message to conversation history
        user_sessions[sender_id]["conversation_history"].append({
            "role": "user",
            "content": message_text,
            "timestamp": datetime.now()
        })
        
        # Check if user is asking for more properties
        if message_text.lower().strip() in ['more', 'next', 'show more', 'next 3', 'more properties']:
            if "remaining_properties" in user_sessions[sender_id] and user_sessions[sender_id]["remaining_properties"]:
                remaining = user_sessions[sender_id]["remaining_properties"]
                properties_to_show = min(3, len(remaining))
                
                send_whatsapp_message(sender_id, f"🏡 *Here are the next {properties_to_show} properties:*")
                
                for i, prop in enumerate(remaining[:properties_to_show], 1):
                    property_message = f"*Property {i}*:\n" + format_property_for_whatsapp(prop)
                    send_whatsapp_message(sender_id, property_message)
                
                # Update remaining properties
                user_sessions[sender_id]["remaining_properties"] = remaining[properties_to_show:]
                
                # If there are still more properties, let the user know
                if len(remaining) > properties_to_show:
                    still_remaining = len(remaining) - properties_to_show
                    send_whatsapp_message(
                        sender_id,
                        f"📋 *{still_remaining} more properties available.*\nType 'more' to see the next 3 properties."
                    )
                else:
                    send_whatsapp_message(
                        sender_id,
                        "✅ That's all the properties I have for you. Ask me anything else about real estate in Hyderabad!"
                    )
                    del user_sessions[sender_id]["remaining_properties"]
                
                return
            else:
                send_whatsapp_message(
                    sender_id,
                    "🔍 I don't have any more properties to show from your last search. Please let me know what kind of property you're looking for."
                )
                return
        
        # Create a mock streamlit session state for the agent
        class MockStreamlitSession:
            def __init__(self, session_id):
                self.session_id = session_id
        
        # Store session in sys.modules to make it available to the agent
        import sys
        sys.modules['streamlit'] = type('MockStreamlit', (), {
            'session_state': MockStreamlitSession(session_id)
        })()
        
        # Process with the agent - SAME AS APP.PY
        try:
            # Get response from agent with the same structure as app.py
            agent_input = {
                "input": message_text,
                "chat_history": []
            }
            
            logger.info(f"Sending to agent: {agent_input}")
            
            # Get response from agent
            response = agent.invoke(agent_input)
            response_text = response.get("output", "I apologize, but I couldn't process your request properly.")
            
            logger.info(f"Agent response: {response_text[:200]}...")
            
            # Extract property data and user preferences - SAME AS APP.PY
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
                            logger.info(f"Found property data with {len(tool_result.get('properties', []))} properties")
                        elif action.tool == "get_user_preferences" and isinstance(tool_result, dict) and "has_preferences" in tool_result:
                            preferences_data = tool_result
                            logger.info(f"Found preferences data")
            
            # Send the agent's response text first
            send_whatsapp_message(sender_id, response_text)
            
            # Add to conversation history
            user_sessions[sender_id]["conversation_history"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now()
            })
            
            # Handle property data if available - SAME AS APP.PY
            if property_data:
                handle_properties_response(sender_id, property_data)
            
            # Handle user preferences if available - SAME AS APP.PY
            if preferences_data and preferences_data.get("has_preferences", False):
                handle_preferences_response(sender_id, preferences_data)
                
        except Exception as e:
            logger.error(f"Error processing message with agent: {e}", exc_info=True)
            send_whatsapp_message(
                sender_id,
                "❌ I apologize, but I encountered an error while processing your request. Please try again with a different query."
            )
            
    except Exception as e:
        logger.error(f"Error in process_whatsapp_message: {e}", exc_info=True)
        send_whatsapp_message(
            sender_id,
            "❌ Sorry, something went wrong. Please try again later."
        )

def run_whatsapp_bot(host='0.0.0.0', port=None):
    """
    Run the WhatsApp bot server
    
    Args:
        host: Host to run the server on
        port: Port to run the server on (will find a free port if None)
    """
    # Find a free port if none is specified
    if port is None:
        port = find_free_port()
    
    logger.info(f"Starting WhatsApp bot server on {host}:{port}")
    logger.info(f"Agent status: {'Initialized' if agent else 'Not initialized'}")
    print(f"Starting WhatsApp bot server on {host}:{port}")
    print(f"Visit http://localhost:{port}/ to check the server status")
    print(f"Test endpoint: http://localhost:{port}/test-send?phone=YOUR_PHONE&message=Hello")
    print(f"Webhook test: http://localhost:{port}/webhook-test")
    app.run(host=host, port=port, debug=False)  # Set debug to False for production

if __name__ == "__main__":
    # Try to run on port 5001, but find a free port if it's in use
    run_whatsapp_bot(port=5001)