import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import os
import logging  # Import the logging module

# MCPClient is now imported from the local client.py within this package
from .agent import MCPClient

# Configure basic logging
# You can customize the format and level further if needed
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint for Kubernetes liveness/readiness probes.
    """
    return {"status": "ok"}

# hardcode the container_server_script_path for now
# This path is relative to the CWD when the server is run.
# If running `uvicorn zededa_server_app.main:app` from the project root,
# "zededa.py" will correctly point to /Users/gkodali/Work/zededa-client/zededa.py
container_server_script_path = "zededa.py"  # In Docker, this will be /app/zededa.py

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Ensure the container_server_script_path is valid and exists
    # Inside Docker, paths should be absolute or relative to WORKDIR /app
    if not os.path.exists(container_server_script_path) or not (container_server_script_path.endswith('.py') or container_server_script_path.endswith('.js')):
        logger.error(f"Invalid or non-existent server script path: {container_server_script_path}")
        await websocket.send_text(f"Error: Invalid or non-existent server script path: {container_server_script_path}")
        await websocket.close(code=1008)  # Policy Violation
        return

    client = MCPClient(websocket=websocket)
    
    try:
        logger.info(f"Attempting to connect to MCP server: {container_server_script_path}")
        await client.connect_to_server(container_server_script_path)
        # chat_loop will now use the websocket passed during MCPClient initialization
        await client.chat_loop()
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from WebSocket for {container_server_script_path}")
    except Exception as e:
        logger.error(f"An error occurred with client for {container_server_script_path}: {e}", exc_info=True)
        # It's good practice to avoid sending detailed internal errors to the client.
        # Consider logging 'e' and sending a generic error message.
        await websocket.send_text(f"Server-side error. Please check server logs.")
    finally:
        logger.info(f"Cleaning up client for {container_server_script_path}")
        await client.cleanup()
        # Ensure websocket is closed if not already
        try:
            # Check state before attempting to close, or catch specific exception for already closed.
            if websocket.client_state != websocket.client_state.DISCONNECTED:
                 await websocket.close()
        except RuntimeError:  # Can happen if already closed or in an invalid state
            pass
        logger.info(f"WebSocket connection closed for {container_server_script_path}")

if __name__ == "__main__":
    # To run this FastAPI application:
    # 1. Navigate to the project root directory in your terminal:
    #    cd /Users/gkodali/Work/zededa-client
    # 2. Run uvicorn:
    #    uvicorn zededa_server_app.main:app --reload --port 8000
    #
    # The container_server_script_path is hardcoded above.
    # Clients connect to ws://<host>:<port>/ws
    logger.info("FastAPI server starting directly (not recommended for production). To run for development, use the command:")
    logger.info("uvicorn zededa_server_app.main:app --reload --port 8000")
    logger.info(f"Ensure '{container_server_script_path}' (resolved to '{os.path.abspath(container_server_script_path)}') is accessible.")
    # The following line allows direct execution `python zededa_server_app/main.py` from the root,
    # but `uvicorn zededa_server_app.main:app` is the standard for development/production.
    uvicorn.run(app, host="0.0.0.0", port=8000)
