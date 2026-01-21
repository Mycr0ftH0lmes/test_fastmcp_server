import os
import json
import requests
from typing import List
from fastmcp import FastMCP

DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"

def log_debug(message):
    if DEBUG_LOGGING:
        print(f"[DEBUG] {message}", flush=True)

def log_info(message):
    print(f"[INFO] {message}", flush=True)

def log_error(message):
    print(f"[ERROR] {message}", flush=True)

mcp = FastMCP("test_mcp")

# Secrets must come from env vars (NOT hardcoded)
CLICKUP_TOKEN = os.getenv("CLICKUP_TOKEN")
if not CLICKUP_TOKEN:
    log_error("Missing CLICKUP_TOKEN env var. Set it in FastMCP Cloud project settings.")

BASE_URL = os.getenv("CLICKUP_BASE_URL", "https://api.clickup.com/api/v3")

headers = { "Authorization": CLICKUP_TOKEN, 
            "Content-Type": "application/json"
        }

@mcp.tool()
def get_workspace_id(): 
    """Fetches the first available Workspace ID for the user.""" 
    # Note: The /team endpoint is still v2 but provides the necessary ID for v3 
    url = "https://api.clickup.com/api/v2/team" 
    response = requests.get(url, headers=headers) 
    log_info(f"Get Workspace ID API Call: {url}, Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        teams = data.get('teams', [])
        workspace_id = teams[0]['id'] if teams else None
        log_info(f"Workspace ID Response: Found {len(teams)} teams, returning: {workspace_id}")
        return workspace_id
    else:
        log_error(f"Auth Error: {response.status_code} - {response.text}")
        return {"error": f"API Error: {response.status_code}", "message": response.text}

    @mcp.tool()
    def extract_entire_doc_v3(workspace_id, doc_id): 
        """ Fetches every page and subpage in the hierarchy using v3. max_page_depth=-1 ensures it iterates through all levels automatically. """ 
        url = f"{BASE_URL}/workspaces/{workspace_id}/docs/{doc_id}/pages" 
        params = { "max_page_depth": -1, "content_format": "text/md" } 
        response = requests.get(url, headers=headers, params=params) 
        log_info(f"Extract Entire Doc API Call: {url}, Params: {params}, Status: {response.status_code}") 
        if response.status_code == 200: # v3 returns a flat list of page objects with 'parent_page_id' # to preserve the hierarchy/hira structure. 
            data = response.json() 
            return data if data else {"message": "No pages found", "pages": []} 
        else: 
            log_error(f"Extraction Error: {response.status_code} - {response.text}") 
            return {"error": f"API Error: {response.status_code}", "message": response.text}