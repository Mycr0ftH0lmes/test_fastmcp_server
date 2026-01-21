import os
import json
import requests
from typing import List
from fastmcp import FastMCP
from fastmcp.server.auth.providers.auth0 import Auth0Provider

DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"

def log_debug(message):
    if DEBUG_LOGGING:
        print(f"[DEBUG] {message}", flush=True)

def log_info(message):
    print(f"[INFO] {message}", flush=True)

def log_error(message):
    print(f"[ERROR] {message}", flush=True)

# Auth0 OAuth Configuration
# Get Auth0 configuration from environment variables
AUTH0_CONFIG_URL = os.getenv("AUTH0_CONFIG_URL")  # e.g., https://your-domain.auth0.com/.well-known/openid-configuration
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
AUTH0_BASE_URL = os.getenv("AUTH0_BASE_URL", "http://localhost:8000")  # Your server URL
AUTH0_REDIRECT_PATH = os.getenv("AUTH0_REDIRECT_PATH", "/auth/callback")

# Initialize Auth0 provider if all required config is present
auth_provider = None
if AUTH0_CONFIG_URL and AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET and AUTH0_AUDIENCE:
    try:
        auth_config = {
            "config_url": AUTH0_CONFIG_URL,
            "client_id": AUTH0_CLIENT_ID,
            "client_secret": AUTH0_CLIENT_SECRET,
            "audience": AUTH0_AUDIENCE,
            "base_url": AUTH0_BASE_URL,
            "redirect_path": AUTH0_REDIRECT_PATH,
        }
        
        auth_provider = Auth0Provider(**auth_config)
        log_info("Auth0 OAuth provider initialized successfully")
    except Exception as e:
        log_error(f"Failed to initialize Auth0 provider: {e}")
        auth_provider = None
else:
    log_info("Auth0 configuration not found. Server will run without authentication.")
    log_info("To enable Auth0, set: AUTH0_CONFIG_URL, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_AUDIENCE")

# Initialize FastMCP with optional Auth0 authentication
mcp = FastMCP("test_mcp", auth=auth_provider)

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
    """Fetches every page and subpage in the hierarchy using v3. max_page_depth=-1 ensures it iterates through all levels automatically."""
    url = f"{BASE_URL}/workspaces/{workspace_id}/docs/{doc_id}/pages"
    params = {"max_page_depth": -1, "content_format": "text/md"}
    response = requests.get(url, headers=headers, params=params)
    log_info(f"Extract Entire Doc API Call: {url}, Params: {params}, Status: {response.status_code}")
    if response.status_code == 200:
        # v3 returns a flat list of page objects with 'parent_page_id' to preserve the hierarchy structure.
        data = response.json()
        return data if data else {"message": "No pages found", "pages": []}
    else:
        log_error(f"Extraction Error: {response.status_code} - {response.text}")
        return {"error": f"API Error: {response.status_code}", "message": response.text}

# Auth0 authentication test tool (only works when Auth0 is configured)
@mcp.tool()
async def get_token_info() -> dict:
    """Returns information about the Auth0 token. Only available when Auth0 is configured."""
    if not auth_provider:
        return {"error": "Auth0 is not configured"}
    
    try:
        from fastmcp.server.dependencies import get_access_token
        token = get_access_token()
        return {
            "issuer": token.claims.get("iss"),
            "audience": token.claims.get("aud"),
            "scope": token.claims.get("scope"),
            "sub": token.claims.get("sub")
        }
    except Exception as e:
        log_error(f"Error getting token info: {e}")
        return {"error": str(e)}