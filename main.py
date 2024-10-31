#!/usr/bin/env python3

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from github import Github
import base64
import os

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
            file_content = repo.get_contents(content_file.path, ref=branch)
            files_content[content_file.path] = file_content.content  # Already base64 encoded
            
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
            try:
                # Extract GitHub repo, branch, and folder from the POST request payload
                repo_name = args['repo']
                branch = args['branch']
                folder = args['folder']

                # Call the function to get files' base64 content
                files_base64_content = get_files_base64_encoded(GITHUB_TOKEN, repo_name, branch, folder)

                # Send the files' content as response
                self.reply({
                    "output": {
                        "files": files_base64_content
                    }
                })

            except KeyError as e:
                self.reply({"error": f"Missing parameter: {str(e)}"})
            except Exception as e:
                self.reply({"error": str(e)})
        else:
            self.unsupported()


if __name__ == '__main__':
    httpd = HTTPServer(('', 4355), Plugin)
    print("Server started at port 4355")
    httpd.serve_forever()
