import subprocess
import sys
import logging
import json
import os
import time
import hashlib
import hmac


try:
    import openai
    from openai import OpenAI
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    import openai  # Re-import after installation
    from openai import OpenAI    

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests  # Re-import after installation

try:
    from flask import Flask, request, jsonify, abort
except ImportError:
    # If not installed, install PyGithub
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask, request, jsonify  # Import again after installation


# Set up logging
#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)

BOT_USER_ID = "U0802HRH9NG"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")
slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
max_response_tokens = 200
temperature = 0.95

def verify_slack_request(req):
    timestamp = req.headers.get("X-Slack-Request-Timestamp")
    slack_signature = req.headers.get("X-Slack-Signature")

    # Check if headers are missing
    if not timestamp or not slack_signature:
        print("Missing Slack headers")
        return False

    # Reject if the timestamp is too old (to prevent replay attacks)
    if abs(time.time() - float(timestamp)) > 60 * 5:
        print("Timestamp too old")
        return False

    # Create the base string as per Slack's requirements
    sig_basestring = f"v0:{timestamp}:{req.get_data(as_text=True)}"
    my_signature = "v0=" + hmac.new(
        slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare signatures to verify request
    return hmac.compare_digest(my_signature, slack_signature)


def post_message_to_slack(channel, text, thread_ts=None):
    """Posts a message back to the Slack channel."""
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "channel": channel,
        "text": text,
        "thread_ts": thread_ts
    }
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200 or not response.json().get("ok"):
        logging.error("Failed to send message to Slack: %s", response.text)
    else:
        #logging.info("Message sent to Slack channel %s: %s", channel, text)
        logging.info("Message sent to Slack channel %s", channel)

@app.route('/webhook', methods=['POST'])

def process_slack_event():
    app.logger.info("Webhook endpoint hit")
    if not verify_slack_request(request):
        abort(403)  # Forbidden if verification fails

            # Ignore retries by Slack
    if request.headers.get("X-Slack-Retry-Num"):
        return jsonify({"status": "Ignored retry"}), 200

    if request.content_type != 'application/json':
        app.logger.info("Received non-JSON content type")
        return jsonify({"error": "Invalid content type"}), 400
    data = request.get_json()

    app.logger.info("Received POST data: %s", data)

    # Check if the necessary fields are in the request
    if data and 'challenge' in data and data.get("type") == "url_verification":
        # Return HTTP 200 with the 'challenge' field in the response
        return jsonify({"challenge": data['challenge']}), 200

# Process "event_callback" type which indicates a message event
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        
          # Check if the event is a message and not from the bot itself
        if event['type'] == 'message' and event.get('user') != BOT_USER_ID:
            message_text = event["text"]
            user_id = event["user"]
            channel_id = event["channel"]
            thread_ts = event.get("ts")

            # Log message details
            log_entry = {
                "user": user_id,
                "channel": channel_id,
                "message": message_text,
                "thread_ts": thread_ts
            }
            #logging.info("Received message event: %s", json.dumps(log_entry))
            #post_message_to_slack(channel_id, f"Echo: {message_text}")
            response = get_chatgpt_response(message_text, max_response_tokens, temperature)
            #return jsonify({"status": "Message received"}), 200
            
            formatted_response = f"```{response}```"  # Wrap in triple backticks
            #logging.info("choice of zero completion formatted: %s", formatted_response)
            post_message_to_slack(event["channel"], formatted_response, thread_ts)
            return jsonify({"status": "message processed"}), 200
            #return response, 200

        if event['type'] == 'message' and event.get('user') == BOT_USER_ID:
            #logging.info("Received message from this bot, skipping: %s")
            return jsonify({"status": "Message was from this bot"}), 200
    
    # If the request does not have the required fields, return a 400 Bad Request
    return jsonify({"error": "Bad Request"}), 400

# Return 400 for any other route
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Bad Request"}), 400

# Function to get response from ChatGPT
def get_chatgpt_response(message_text, max_response_tokens, temperature):
    try:
       client = OpenAI(
           # This is the default and can be omitted
           api_key=os.environ.get("OPENAI_API_KEY"),
       )

       completion = client.chat.completions.create(
           messages=[
               {
                   "role": "user",
                   "content": message_text,
                }
            ],
            model="gpt-4o",
            max_tokens=max_response_tokens,
            temperature=temperature
       )

       #chatgpt_response = completion.choices[0].message["content"]
       #logging.info("Received chatgpt repsonse: %s", completion)
       chatgpt_response = completion.choices[0].message.content
       #logging.info("content of chatgpt response: %s", chatgpt_response)
       return chatgpt_response
    except Exception as e:
        print("Error communicating with OpenAI:", e)  # Print detailed error
        return f"An error occurred while contacting ChatGPT: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

