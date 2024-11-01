#!/usr/bin/env python3

import json
import sys
import subprocess
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import base64
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

try:
    from github import Github
except ImportError:
    # If not installed, install PyGithub
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub"])
    from github import Github  # Import again after installation

# Read the token for authentication (modify the path if necessary)
with open("/var/run/argo/token") as f:
    token = f.read().strip()

# Define GitHub token for accessing the GitHub API
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_files_base64_encoded(token, repo_name, branch, folder_path):
    # Initialize the GitHub client
    g = Github(token)
    
    # Get the repository
    repo = g.get_repo(repo_name)
    
    # Get the contents of the specified folder in the specified branch
    contents = repo.get_contents(folder_path, ref=branch)
    
    # Collect the base64-encoded contents of each file
    files_content = {}
    for content_file in contents:
        if content_file.type == "file":  # Ensure it's a file, not a subfolder
            file_content = base64.b64encode(content_file.decoded_content).decode('utf-8')
            files_content[content_file.name] = file_content
            
    return files_content

class Plugin(BaseHTTPRequestHandler):

    def args(self):
        return json.loads(self.rfile.read(int(self.headers.get('Content-Length'))))

    def reply(self, reply):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(reply).encode("UTF-8"))

    def forbidden(self):
        self.send_response(403)
        self.end_headers()

    def unsupported(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.headers.get("Authorization") != "Bearer " + token:
            self.forbidden()
            return

        if self.path == '/api/v1/getparams.execute':
            args = self.args()
            logging.info("Received input: %s", json.dumps(args))  # Log the full input for debugging

            try:
                # Access nested parameters
                parameters = args.get('input', {}).get('parameters', {})
                repo_name = parameters.get('repo')
                branch = parameters.get('branch')
                folder = parameters.get('folder')

                # Check for missing parameters
                missing_params = [param for param in ['repo', 'branch', 'folder'] if parameters.get(param) is None]
                if missing_params:
                    raise KeyError(f"Missing parameter(s): {', '.join(missing_params)}")

                # Call the function to get files' base64 content
                files_base64_content = get_files_base64_encoded(GITHUB_TOKEN, repo_name, branch, folder)
                configmap_name = os.path.basename(folder)

                # Send the files' content as response
                logging.info("Providing output: %s", json.dumps(files_base64_content))  # Log output contents
                self.reply({
                    "output": {
                       "parameters": [
                           {
                              "name": configmap_name,
                              "contents": files_base64_content
                           }
                       ]
                    }
                })

            except KeyError as e:
                logging.error("Missing parameter(s): %s", str(e))
                self.reply({"error": f"Missing parameter(s): {str(e)}"})
            except Exception as e:
                logging.error("Error occurred: %s", str(e), exc_info=True)
                self.reply({"error": str(e)})
        else:
            self.unsupported()


if __name__ == '__main__':
    httpd = HTTPServer(('', 4355), Plugin)
    logging.info("Server started at port 4355")
    httpd.serve_forever()
