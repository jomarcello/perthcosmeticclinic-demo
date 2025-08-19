#!/usr/bin/env python3
import asyncio
import json
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from urllib.parse import urlencode

async def call_railway_mcp(action, params=None):
    """Call Railway MCP via Python client"""
    base_url = "https://server.smithery.ai/@jason-tan-swe/railway-mcp/mcp"
    smithery_params = {
        "api_key": "2f9f056b-67dc-47e1-b6c4-79c41bf85d07", 
        "profile": "zesty-clam-4hb4aa"
    }
    url = f"{base_url}?{urlencode(smithery_params)}"
    
    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                if action == "list_projects":
                    result = await session.call_tool("project_list", {})
                elif action == "create_project":
                    result = await session.call_tool("project_create", params or {})
                elif action == "deploy_service":
                    result = await session.call_tool("service_create_from_repo", params or {})
                else:
                    return {"error": f"Unknown action: {action}"}
                
                return {"success": True, "data": result}
                
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: railway_mcp_python.py <action> [params]"}))
        sys.exit(1)
    
    action = sys.argv[1]
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    
    result = asyncio.run(call_railway_mcp(action, params))
    print(json.dumps(result))
