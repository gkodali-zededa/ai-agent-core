import asyncio
import os
from typing import Optional, List, Dict, Any, Tuple # Keep Tuple if other functions might use it
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

# supervisor_prompt functions are used by ADKOrchestrator directly
# from .supervisor_prompt import validate_data_with_claude, conforms_to_guidelines

load_dotenv()  # load environment variables from .env


# ADK_LLM_REFACTOR: The following functions `_process_claude_response` and
# `process_query_logic` are now conceptually integrated into
# `ADKOrchestrator.handle_user_query`. They are commented out here.

# async def _process_claude_response(
#     claude_response_obj: Any,
#     anthropic_client: Anthropic,
#     mcp_session: ClientSession,
#     available_tools: List[Dict[str, Any]],
#     messages_history: List[Dict[str, Any]],
#     final_text_output_list: List[str]
# ):
#     # ... (logic moved to ADKOrchestrator.handle_user_query inner loop) ...
#     pass

# async def process_query_logic(
#     query: str,
#     anthropic_client: Anthropic,
#     mcp_session: ClientSession,
#     available_tools: List[Dict[str, Any]],
#     incoming_messages_history: List[Dict[str, Any]]
# ) -> Tuple[str, List[Dict[str, Any]]]:
#     # ... (logic moved to ADKOrchestrator.handle_user_query) ...
#     pass

# ADK_LLM_REFACTOR: `get_available_tools` has been moved to adk_orchestrator.py
# as `get_available_tools_for_adk`.
# async def get_available_tools(mcp_session: ClientSession) -> List[Dict[str, Any]]:
#     # ... (logic moved) ...
#     pass


# The MCPClient class is now significantly reduced. Its primary role in WebSocket
# handling has been taken over by ADKOrchestrator.
# It might still be useful for direct CLI testing or other non-ADK orchestrated scenarios,
# but its core methods (chat_loop, process_query) are no longer central to the main app.

class MCPClient:
    def __init__(self, websocket=None):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.websocket = websocket

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server."""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio_reader, stdio_writer = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(stdio_reader, stdio_writer))

        await self.session.initialize()
        if self.session:
            response = await self.session.list_tools()
            tools = response.tools
            print("MCPClient: Connected to server with tools:", [tool.name for tool in tools])
        else:
            print("MCPClient: Session not initialized after connect_to_server.")
    
    async def cleanup(self):
        """Clean up resources"""
        print("MCPClient: Cleaning up resources...")
        await self.exit_stack.aclose()
        print("MCPClient: Resources cleaned up.")

async def main_cli_usage():
    # ADK_LLM_REFACTOR: This CLI mode is now largely non-functional without
    # `process_query_logic` and `get_available_tools` being available here.
    # To make it work, it would need to instantiate ADKOrchestrator or
    # replicate its logic, which is beyond the current scope.
    print("CLI Usage Note: This mode is currently non-functional due to LLM logic refactoring.")
    print("The core LLM interaction logic has been moved into ADKOrchestrator.")
    import sys 
    if len(sys.argv) < 2:
        print("Usage: python zededa_server_app/agent.py <path_to_server_script>")
        sys.exit(1)

    print(f"Attempting to connect to server: {sys.argv[1]} for basic MCPClient test.")
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        if client.session:
            print("MCPClient connected. Further CLI interaction for LLM calls is disabled in this refactored version.")
        else:
            print("Failed to connect MCPClient session for CLI.")
    except Exception as e:
        print(f"CLI Error with MCPClient: {e}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main_cli_usage())
