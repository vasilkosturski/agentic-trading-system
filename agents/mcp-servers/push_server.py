#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

load_dotenv(override=True)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

mcp = FastMCP("push_server")

class PushModelArgs(BaseModel):
    message: str = Field(description="A brief message to push")

@mcp.tool()
def push(args: PushModelArgs):
    """Send a push notification with this brief message"""
    print(f"Push: {args.message}")
    
    # If Pushover credentials are available, send actual notification
    if pushover_user and pushover_token:
        payload = {"user": pushover_user, "token": pushover_token, "message": args.message}
        try:
            response = requests.post(pushover_url, data=payload)
            if response.status_code == 200:
                return "Push notification sent successfully"
            else:
                return f"Push notification failed: {response.status_code}"
        except Exception as e:
            return f"Push notification error: {str(e)}"
    else:
        # Fallback: just log the message
        return f"Push notification logged: {args.message}"

if __name__ == "__main__":
    mcp.run(transport="stdio")