# Real Estate Assistant - WhatsApp Integration

This project provides a Real Estate Assistant that helps users find properties in Hyderabad based on their preferences. The assistant can be accessed via two interfaces:

1. **Streamlit Web Application**: Interactive web interface
2. **WhatsApp Bot**: Conversational assistant via WhatsApp

## Prerequisites

- Python 3.8+
- A WhatsApp Business API account
- A publicly accessible server with HTTPS (for WhatsApp webhook)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

1. Copy the `.env.template` file to `.env`:
   ```bash
   cp .env.template .env
   ```

2. Edit the `.env` file and fill in your actual values:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `WHATSAPP_API_TOKEN`: Your WhatsApp Business API token
   - `WHATSAPP_PHONE_NUMBER_ID`: Your WhatsApp Phone Number ID
   - `WHATSAPP_VERIFY_TOKEN`: A custom token for webhook verification

### 3. Set Up WhatsApp Business API

1. Sign up for WhatsApp Business API access through Meta Business Suite
2. Set up your WhatsApp Business account and get your Phone Number ID
3. Generate an API token
4. Configure a webhook URL (you'll need a public HTTPS URL)

### 4. Expose Your Webhook

For WhatsApp integration, your webhook needs to be accessible via HTTPS. You can use:

- **ngrok**: For testing locally
  ```bash
  ngrok http 5000
  ```

- **Cloud hosting**: Deploy to a server with a public IP

- **Serverless service**: Deploy on AWS Lambda, Google Cloud Functions, etc.

### 5. Configure WhatsApp Business API

1. Go to Meta Developer Portal
2. Set up a webhook with the following configuration:
   - URL: `https://your-domain.com/webhook` (or your ngrok URL)
   - Verify token: Same as your `WHATSAPP_VERIFY_TOKEN`
   - Subscribe to the following fields:
     - `messages`
     - `message_deliveries`

## Running the Application

### Option 1: Run Both Interfaces

```bash
python main.py --mode both
```

### Option 2: Run Only the Streamlit Web App

```bash
python main.py --mode streamlit
```
Or directly:
```bash
streamlit run app.py
```

### Option 3: Run Only the WhatsApp Bot

```bash
python main.py --mode whatsapp
```

## How It Works

- **Web Interface**: Displays properties with detailed filtering and visualization
- **WhatsApp Interface**: Provides a conversational experience with simplified property displays

### Capabilities

Both interfaces support:
- Property search by location, type, budget, configuration, etc.
- Remembering user preferences
- Providing recommendations and alternatives
- Displaying property details and pricing

### WhatsApp Commands

- `more` or `next`: Show more properties from the current search
- Ask natural language questions about properties in Hyderabad

## Troubleshooting

### Common Issues

1. **WhatsApp messages not being received**:
   - Verify your webhook URL is publicly accessible
   - Check that your server is running and can receive POST requests
   - Confirm webhook verification was successful

2. **WhatsApp API errors**:
   - Check your API token is valid
   - Ensure your WhatsApp Business account is active
   - Verify rate limits haven't been exceeded

3. **Property data not loading**:
   - Verify database path is correct
   - Ensure database has been initialized properly

## Extending the Project

- Add media messages to send property images via WhatsApp
- Implement location-based search using WhatsApp location sharing
- Add interactive buttons for property filtering in WhatsApp
- Create a multi-user management system for real estate agents

## Security Considerations

- Store API keys and tokens securely
- Validate all incoming webhook requests
- Implement rate limiting for both interfaces
- Consider adding user authentication for the web interface

## Support

For any issues or questions, please open an issue in the GitHub repository or contact the project maintainer.
