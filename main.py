import subprocess
import sys
try:
    from flask import Flask, request, jsonify
except ImportError:
    # If not installed, install PyGithub
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask, request, jsonify  # Import again after installation




app = Flask(__name__)

@app.route('/slack/webhook', methods=['POST'])
def url_verification():
    data = request.get_json()

    # Check if the necessary fields are in the request
    if data and 'challenge' in data and data.get("type") == "url_verification":
        # Return HTTP 200 with the 'challenge' field in the response
        return jsonify({"challenge": data['challenge']}), 200
    
    # If the request does not have the required fields, return a 400 Bad Request
    return jsonify({"error": "Bad Request"}), 400

# Return 400 for any other route
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Bad Request"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

