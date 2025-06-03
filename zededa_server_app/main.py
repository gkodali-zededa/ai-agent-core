import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import os
import logging

# Import ADKOrchestrator instead of MCPClient
from .adk_orchestrator import ADKOrchestrator
# MCPClient might still be needed if there are other non-websocket uses,
# but for the /ws endpoint, ADKOrchestrator is primary.
# from .agent import MCPClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint for Kubernetes liveness/readiness probes.
    """
    return {"status": "ok"}

# This path is relative to the CWD when the server is run.
# If running `uvicorn zededa_server_app.main:app` from the project root,
# "zededa.py" will correctly point to the zededa.py in the root.
# In Docker, this will be /app/zededa.py if WORKDIR is /app
container_server_script_path = "zededa.py"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set in environment.")
        await websocket.send_text("Error: Server configuration issue (ANTHROPIC_API_KEY missing).")
        await websocket.close(code=1008)
        return

    # Ensure the container_server_script_path is valid and exists
    # This check should ideally be done at startup if the path is static.
    current_dir = os.getcwd()
    absolute_script_path = os.path.abspath(os.path.join(current_dir, container_server_script_path))
    logger.info(f"Looking for MCP server script at: {absolute_script_path} (from CWD: {current_dir})")

    if not os.path.exists(absolute_script_path):
        logger.error(f"Invalid or non-existent server script path: {absolute_script_path}")
        await websocket.send_text(f"Error: Tool server script not found at {absolute_script_path}")
        await websocket.close(code=1008)
        return

    # Use ADKOrchestrator
    orchestrator = ADKOrchestrator(websocket=websocket, anthropic_api_key=anthropic_api_key)
    
    try:
        logger.info(f"Attempting to connect to MCP server with ADKOrchestrator: {absolute_script_path}")
        # Pass the absolute path to connect_to_mcp_server
        await orchestrator.connect_to_mcp_server(absolute_script_path)

        await orchestrator.chat_loop() # ADKOrchestrator's chat loop

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket (ADKOrchestrator for {absolute_script_path})")
    except Exception as e:
        logger.error(f"An error occurred with ADKOrchestrator for {absolute_script_path}: {e}", exc_info=True)
        try:
            await websocket.send_text(f"Server-side error. Please check server logs.")
        except Exception: # Websocket might already be closed
            pass
    finally:
        logger.info(f"Cleaning up ADKOrchestrator for {absolute_script_path}")
        await orchestrator.cleanup()
        try:
            if websocket.client_state != websocket.client_state.DISCONNECTED:
                 await websocket.close()
        except RuntimeError:
            pass
        logger.info(f"WebSocket connection closed (ADKOrchestrator for {absolute_script_path})")

if __name__ == "__main__":
    logger.info("FastAPI server starting directly (uvicorn zededa_server_app.main:app --reload --port 8000 for dev)")
    logger.info(f"Tool server script path: '{container_server_script_path}' (resolved to '{os.path.abspath(container_server_script_path)}')")

    # Check for ANTHROPIC_API_KEY at startup when running directly
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY environment variable not set. Please set it before running.")
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)
