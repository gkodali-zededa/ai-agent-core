from typing import Any, Optional
import httpx
import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("zededa")

# Constants
raw_token = os.environ.get("ZEDEDA_BEARER_TOKEN")
if raw_token is None:
    raise ValueError("Error: ZEDEDA_BEARER_TOKEN environment variable not set.")
if not raw_token.startswith("Bearer "):
    BEARER_TOKEN = "Bearer " + raw_token
else:
    BEARER_TOKEN = raw_token

ZEDEDA_API_BASE = os.environ.get("ZEDEDA_API_BASE_URL", "https://zedcontrol.local.zededa.net")
USER_AGENT = "zededa-ai-bot/1.0"

# change the following function to take http verb as an argument
# and use the correct http verb for the request
async def make_zededa_request(url: str, http_verb: str) -> dict[str, Any] | None:
    """Make a request to the Zededa API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
        "Authorization": BEARER_TOKEN
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(http_verb, url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_app_instance(app_instance: dict[str, Any]) -> str:
    id = app_instance.get("id", "")
    name = app_instance.get("name", "")
    status = app_instance.get("runState", "")
    type = app_instance.get("appType", "")
    deployment_type = app_instance.get("deploymentType", "")
    device_id = app_instance.get("deviceId", "")
    device_name = app_instance.get("deviceName", "")
    project_name = app_instance.get("projectName", "")
    app_name = app_instance.get("appName", "")
    # check if there is an error
    if "errInfo" in app_instance:
        error_info = app_instance["errInfo"][0]
        error_description = error_info.get("description", "")
        error_severity = error_info.get("severity", "")
        error_timestamp = error_info.get("timestamp", "")
    else:
        error_description = "No error"
        error_severity = "No error"
        error_timestamp = "No error"
    return f"""
Device Id: {device_id}
Device Name: {device_name}
App Id: {id}
App Name: {name}
App Status: {status}
App Type: {type}
Deployment Type: {deployment_type}
Project Name: {project_name}
App Bundle Name: {app_name}
Error Description: {error_description}
Error Severity: {error_severity}
Error Timestamp: {error_timestamp}
"""

# --- Generated GET Endpoints from Swagger ---

@mcp.tool()
async def get_zededa_projects(page_size: Optional[int] = 100, page_num: Optional[int] = 1) -> dict[str, Any] | str:
    """Get all projects from Zededa."""
    url = f"{ZEDEDA_API_BASE}/api/v1/projects?next.pageSize={page_size}&next.pageNum={page_num}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return "Failed to retrieve projects."
    return response

@mcp.tool()
async def get_zededa_project_by_id(id: str) -> dict[str, Any] | str:
    """Get a specific project from Zededa by its ID."""
    url = f"{ZEDEDA_API_BASE}/api/v1/projects/id/{id}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve project with ID: {id}."
    return response

@mcp.tool()
async def get_zededa_project_by_name(name: str) -> dict[str, Any] | str:
    """Get a specific project from Zededa by its name."""
    url = f"{ZEDEDA_API_BASE}/api/v1/projects/name/{name}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve project with name: {name}."
    return response

@mcp.tool()
async def get_zededa_datastores(page_size: Optional[int] = 100, page_num: Optional[int] = 1) -> dict[str, Any] | str:
    """Get all datastores from Zededa."""
    url = f"{ZEDEDA_API_BASE}/api/v1/datastores?next.pageSize={page_size}&next.pageNum={page_num}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return "Failed to retrieve datastores."
    return response

@mcp.tool()
async def get_zededa_datastore_by_id(id: str) -> dict[str, Any] | str:
    """Get a specific datastore from Zededa by its ID."""
    url = f"{ZEDEDA_API_BASE}/api/v1/datastores/id/{id}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve datastore with ID: {id}."
    return response

@mcp.tool()
async def get_zededa_datastore_by_name(name: str) -> dict[str, Any] | str:
    """Get a specific datastore from Zededa by its name."""
    url = f"{ZEDEDA_API_BASE}/api/v1/datastores/name/{name}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve datastore with name: {name}."
    return response

@mcp.tool()
async def get_zededa_images(page_size: Optional[int] = 100, page_num: Optional[int] = 1) -> dict[str, Any] | str:
    """Get all images (app bundles) from Zededa."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps/images?next.pageSize={page_size}&next.pageNum={page_num}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return "Failed to retrieve images."
    return response

@mcp.tool()
async def get_zededa_image_by_id(id: str) -> dict[str, Any] | str:
    """Get a specific image (app bundle) from Zededa by its ID."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/id/{id}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve image with ID: {id}."
    return response

@mcp.tool()
async def get_zededa_image_by_name(name: str) -> dict[str, Any] | str:
    """Get a specific image (app bundle) from Zededa by its name."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps/images/name/{name}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve image with name: {name}."
    return response

@mcp.tool()
async def get_zededa_edge_apps(page_size: Optional[int] = 100, page_num: Optional[int] = 1) -> dict[str, Any] | str:
    """Get all edge applications from Zededa."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps?next.pageSize={page_size}&next.pageNum={page_num}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return "Failed to retrieve edge applications."
    return response

@mcp.tool()
async def get_zededa_edge_app_by_id(id: str) -> dict[str, Any] | str:
    """Get a specific edge application from Zededa by its ID."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps/id/{id}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve edge application with ID: {id}."
    return response

@mcp.tool()
async def get_zededa_edge_app_by_name(name: str) -> dict[str, Any] | str:
    """Get a specific edge application from Zededa by its name."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps/name/{name}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve edge application with name: {name}."
    return response

@mcp.tool()
async def get_zededa_nodes(page_size: Optional[int] = 100, page_num: Optional[int] = 1) -> dict[str, Any] | str:
    """Get all nodes (edge devices) from Zededa."""
    # Note: API might use different query params, adjust if needed based on spec details
    url = f"{ZEDEDA_API_BASE}/api/v1/devices/status-config?next.pageSize={page_size}&next.pageNum={page_num}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return "Failed to retrieve nodes."
    # Assuming the list is under 'list' key like app instances
    if "list" in response:
         return response # Or process the list if needed
    else:
         return response # Return raw response if 'list' key not found

@mcp.tool()
async def get_zededa_node_by_id(id: str) -> dict[str, Any] | str:
    """Get a specific node (edge device) from Zededa by its ID."""
    url = f"{ZEDEDA_API_BASE}/api/v1/devices/id/{id}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve node with ID: {id}."
    return response

@mcp.tool()
async def get_zededa_node_by_name(name: str) -> dict[str, Any] | str:
    """Get a specific node (edge device) from Zededa by its name."""
    url = f"{ZEDEDA_API_BASE}/api/v1/devices/name/{name}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve node with name: {name}."
    return response

@mcp.tool()
async def get_zededa_networks(page_size: Optional[int] = 100, page_num: Optional[int] = 1) -> dict[str, Any] | str:
    """Get all networks from Zededa."""
    url = f"{ZEDEDA_API_BASE}/api/v1/networks?next.pageSize={page_size}&next.pageNum={page_num}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return "Failed to retrieve networks."
    return response

@mcp.tool()
async def get_zededa_network_by_id(id: str) -> dict[str, Any] | str:
    """Get a specific network from Zededa by its ID."""
    url = f"{ZEDEDA_API_BASE}/api/v1/networks/id/{id}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve network with ID: {id}."
    return response

@mcp.tool()
async def get_zededa_network_by_name(name: str) -> dict[str, Any] | str:
    """Get a specific network from Zededa by its name."""
    url = f"{ZEDEDA_API_BASE}/api/v1/networks/name/{name}"
    response = await make_zededa_request(url, "get")
    if response is None:
        return f"Failed to retrieve network with name: {name}."
    return response

# --- End Generated GET Endpoints ---

@mcp.tool()
async def get_zededa_app_instances(page_size: Optional[int] = 500, page_num: Optional[int] = 1) -> str:
    """Get all app instances from Zededa."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/status-config?next.pageSize={page_size}&next.pageNum={page_num}"
    response = await make_zededa_request(url, "get")
    if response is None or "list" not in response:
        return "Failed to retrieve app instances or response format is unexpected."
    app_instances = response["list"]
    if not app_instances:
        return "No app instances found."
    formatted_app_instances = [format_app_instance(app_instance) for app_instance in app_instances]
    return "\n--\n".join(formatted_app_instances)

@mcp.tool()
async def get_zededa_app_instance_status_from_id(app_instance_id: str) -> dict[str, Any] | str:
    """Get the status of a specific app instance from Zededa by it's id."""
    url = f"{ZEDEDA_API_BASE}/api/v1/apps/instances/id/{app_instance_id}/status"
    response = await make_zededa_request(url, "get")
    # format_app_instance is not used here as the status endpoint response
    # might not be a full app instance object compatible with the formatter.
    # Returning raw JSON provides more flexibility.
    # return format_app_instance(response) 
    return response

@mcp.tool()
async def delete_zededa_app_instance_by_id(app_instance_id: str) -> str:
    """Delete a specific app instance from Zededa by it's id."""
    url = f"{ZEDEDA_API_BASE}/api/v2/apps/instances/id/{app_instance_id}"
    response = await make_zededa_request(url, "delete")
    return format_app_instance(response)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')