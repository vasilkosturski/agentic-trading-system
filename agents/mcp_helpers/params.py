import os

from dotenv import load_dotenv

from mcp_helpers.types import MCPName

load_dotenv(override=True)

brave_api_key = os.getenv("BRAVE_API_KEY")
brave_env = {"BRAVE_API_KEY": brave_api_key} if brave_api_key else {}


def get_mcp_server_params() -> dict[MCPName, dict]:
    return {
        MCPName.FETCH: {"command": "mcp-server-fetch", "args": []},
        MCPName.BRAVE_SEARCH: {
            "command": "mcp-server-brave-search",
            "args": [],
            "env": brave_env,
        },
    }
