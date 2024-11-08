import subprocess
import sys
import logging
import json

try:
    from flask import Flask, request, jsonify
except ImportError:
    # If not installed, install PyGithub
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask, request, jsonify  # Import again after installation


# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])

def url_verification():
    app.logger.info("Webhook endpoint hit")
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
        
        # Log the event to event.txt if it's a message
        if event.get("type") == "message" and "text" in event:
            message_text = event["text"]
            user_id = event["user"]
            channel_id = event["channel"]

            # Log message details
            log_entry = {
                "user": user_id,
                "channel": channel_id,
                "message": message_text
            }
            logging.info("Received message event: %s", json.dumps(log_entry))
            return jsonify({"status": "Message received"}), 200
    
    # If the request does not have the required fields, return a 400 Bad Request
    return jsonify({"error": "Bad Request"}), 400

# Return 400 for any other route
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Bad Request"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

