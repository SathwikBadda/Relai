
# test_webhook.py - Updated test script for WhatsApp webhook

import requests
import json

# Configuration
WEBHOOK_URL = "http://localhost:5001"  # Change to your ngrok URL when testing with WhatsApp

def test_webhook_verification():
    """Test webhook verification"""
    print("=== Testing Webhook Verification ===")
    
    # IMPORTANT: Make sure this token matches the one set in your environment
    # or in the WHATSAPP_VERIFY_TOKEN variable in your bot
    verify_token = "1234567890"  # This MUST match exactly
    
    # Test parameters that WhatsApp sends
    params = {
        'hub.mode': 'subscribe',
        'hub.verify_token': verify_token,
        'hub.challenge': 'test_challenge_123'
    }
    
    print(f"Testing with verify_token: {verify_token}")
    
    response = requests.get(f"{WEBHOOK_URL}/webhook", params=params)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200 and response.text == 'test_challenge_123':
        print("✅ Webhook verification successful!")
        return True
    else:
        print("❌ Webhook verification failed!")
        print("Make sure the WHATSAPP_VERIFY_TOKEN in your bot matches the token used in this test")
        return False

def test_message_webhook():
    """Test incoming message webhook"""
    print("\n=== Testing Message Webhook ===")
    
    # Simulate WhatsApp message webhook payload
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550559999",
                                "phone_number_id": "596790770173493"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": "919100246849"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "919100246849",
                                    "id": "wamid.test123",
                                    "timestamp": "1684747665",
                                    "text": {
                                        "body": "Hello, I want to buy a home"
                                    },
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f"{WEBHOOK_URL}/webhook", 
        json=webhook_payload,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Message webhook successful!")
        return True
    else:
        print("❌ Message webhook failed!")
        return False

def test_manual_processing():
    """Test manual message processing endpoint"""
    print("\n=== Testing Manual Message Processing ===")
    
    test_payload = {
        "sender_id": "919100246849",
        "message": "HI"
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f"{WEBHOOK_URL}/process-message",
        json=test_payload,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Manual processing successful!")
        return True
    else:
        print("❌ Manual processing failed!")
        return False

def test_server_status():
    """Test if server is running"""
    print("=== Testing Server Status ===")
    
    try:
        response = requests.get(f"{WEBHOOK_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Server is running!")
            return True
        else:
            print("❌ Server returned error!")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running!")
        return False

def test_send_message():
    """Test sending a message"""
    print("\n=== Testing Send Message ===")
    
    params = {
        'phone': '919100246849',  # Replace with your test number
        'message': 'Test message from webhook test script'
    }
    
    response = requests.get(f"{WEBHOOK_URL}/test-send", params=params)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Message sent successfully!")
        return True
    else:
        print("❌ Failed to send message!")
        return False

def test_webhook_debug():
    """Test webhook configuration endpoint"""
    print("\n=== Testing Webhook Debug Info ===")
    
    response = requests.get(f"{WEBHOOK_URL}/webhook-test")
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        debug_info = response.json()
        print("Debug Information:")
        for key, value in debug_info.items():
            print(f"  {key}: {value}")
        print("✅ Webhook debug info retrieved!")
        return True
    else:
        print("❌ Failed to get webhook debug info!")
        return False

def run_all_tests():
    """Run all tests"""
    print("🧪 Starting WhatsApp Bot Tests\n")
    
    tests = [
        ("Server Status", test_server_status),
        ("Webhook Debug Info", test_webhook_debug),
        ("Send Message", test_send_message),
        ("Webhook Verification", test_webhook_verification),
        ("Message Webhook", test_message_webhook),
        ("Manual Processing", test_manual_processing)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<25}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your WhatsApp bot is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs for more details.")
        
        # Provide specific guidance for failed tests
        if not results.get("Webhook Verification", True):
            print("\n🔧 To fix webhook verification:")
            print("1. Set environment variable: export WHATSAPP_VERIFY_TOKEN='your_verify_token'")
            print("2. Or update the token in your bot code to match 'your_verify_token'")
            print("3. Make sure both the test script and bot use the EXACT same token")

if __name__ == "__main__":
    run_all_tests()