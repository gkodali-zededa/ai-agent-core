import asyncio
import os
import uuid # For generating unique session IDs
from typing import Optional, Dict, List, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters # Assuming mcp is installed
from mcp.client.stdio import stdio_client # Assuming mcp is installed
# import adk # Hypothetical ADK library
# import adk.llm # Hypothetical ADK LLM client
# import adk.exceptions # Hypothetical ADK exceptions

from anthropic import Anthropic

from .supervisor_prompt import validate_data_with_claude, conforms_to_guidelines

async def get_available_tools_for_adk(mcp_session: ClientSession) -> List[Dict[str, Any]]:
    if not mcp_session:
        return []
    response = await mcp_session.list_tools()
    return [{
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.inputSchema
    } for tool in response.tools]

class ADKOrchestrator:
    def __init__(self, websocket=None, anthropic_api_key: Optional[str] = None):
        self.websocket = websocket
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            raise ValueError("Anthropic API key must be provided or set in ANTHROPIC_API_KEY environment variable.")

        self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)

        # self.adk_llm_client = adk.llm.Client(...) # Placeholder
        self.adk_llm_client = None

        self.mcp_session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        self._simulated_sessions: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self.current_adk_session: Optional[Dict[str, List[Dict[str, Any]]]] = None

        # ADK_VALIDATION_HOOK: Conceptual registration of the hook.
        # In a real ADK, you might have:
        # self.hypothetical_adk_core_agent = adk.AgentCore() # Or similar
        # self.hypothetical_adk_core_agent.register_pre_execution_hook(self._adk_input_validation_hook)
        # print("ADKOrchestrator: Input validation hook conceptually registered.")

    async def connect_to_mcp_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write_to_mcp = stdio_transport
        self.mcp_session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write_to_mcp))

        await self.mcp_session.initialize()
        print("ADKOrchestrator: Connected to MCP server.")

    def _get_or_create_simulated_session(self, session_id: str) -> Dict[str, List[Dict[str, Any]]]:
        if session_id not in self._simulated_sessions:
            print(f"ADKOrchestrator: Creating new simulated session for session_id: {session_id}")
            self._simulated_sessions[session_id] = {'history': []}
        return self._simulated_sessions[session_id]

    async def _adk_input_validation_hook(self, query: str, session_context: Any) -> bool:
        """
        # ADK_VALIDATION_HOOK: This method would be registered with the ADK execution engine.
        # It's called conceptually by the ADK before the main query handling logic.
        # session_context is a placeholder for any context ADK might pass to hooks.
        """
        print(f"ADK_VALIDATION_HOOK: Validating query: '{query}' for session: {session_context}")
        # Use self.anthropic_client for validation as per original logic
        validation_llm_response = validate_data_with_claude(query, self.anthropic_api_key)
        is_compliant = conforms_to_guidelines(validation_llm_response)

        if not is_compliant:
            # ADK_VALIDATION_HOOK: Here, the hook could raise a specific ADK exception or return a signal/status.
            # For example:
            # raise adk.exceptions.InputValidationFailedError(
            #     "I'm sorry, but my primary function is to support you with inquiries about Zededa Inc and its services. Can I help with a Zededa related question?"
            # )
            # Or, it could update the session with an error state:
            # session_context['validation_error'] = "Validation failed message..."
            print("ADK_VALIDATION_HOOK: Input does not conform to guidelines.")
            return False # Signalling failure

        print("ADK_VALIDATION_HOOK: Input conforms to guidelines.")
        return True # Signalling success

    async def handle_user_query(self, query: str) -> str:
        # ADK_VALIDATION_HOOK: At this point, input validation is assumed to have been performed
        # by the ADK via a registered hook (e.g., _adk_input_validation_hook).
        # ADK_VALIDATION_HOOK: If validation failed, the ADK core might have already sent a response,
        # raised an exception handled by the ADK, or this method might not even be called.
        # For this simulation, chat_loop will call the hook directly before this method.

        if not self.mcp_session:
            return "Error: MCP session not established."
        if not self.current_adk_session:
            return "Error: ADK session not initialized for this interaction."

        current_messages_history = list(self.current_adk_session['history'])
        current_messages_history.append({"role": "user", "content": query})

        available_tools_for_claude = await get_available_tools_for_adk(self.mcp_session)

        final_text_output_list = []
        loop_needed = True

        while loop_needed:
            if not current_messages_history:
                 print("ADKOrchestrator: Message history is empty, cannot call LLM.")
                 break

            print(f"ADK_LLM_REFACTOR: Calling Anthropic with history: {current_messages_history}")
            claude_response_obj = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                messages=current_messages_history,
                tools=available_tools_for_claude
            )

            loop_needed = False
            assistant_content_for_history = []

            for content_block in claude_response_obj.content:
                if content_block.type == 'text':
                    final_text_output_list.append(content_block.text)
                    assistant_content_for_history.append({"type": "text", "text": content_block.text})
                elif content_block.type == 'tool_use':
                    assistant_content_for_history.append({
                        "type": "tool_use",
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input
                    })

                    tool_name = content_block.name
                    tool_input = content_block.input

                    print(f"ADK_LLM_REFACTOR: Orchestrator calling tool: {tool_name} with args: {tool_input}")
                    mcp_tool_result = await self.mcp_session.call_tool(tool_name, tool_input)
                    final_text_output_list.append(f"[Calling tool {tool_name} with args {tool_input}]")
                    print(f"ADK_LLM_REFACTOR: Tool {tool_name} result: {mcp_tool_result.content}")

                    if assistant_content_for_history:
                         current_messages_history.append({"role": "assistant", "content": list(assistant_content_for_history)})
                    assistant_content_for_history = []

                    current_messages_history.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": mcp_tool_result.content
                        }]
                    })
                    loop_needed = True
                    break

            if assistant_content_for_history:
                current_messages_history.append({"role": "assistant", "content": assistant_content_for_history})

        self.current_adk_session['history'] = current_messages_history
        session_id_for_log = self.websocket_session_id if hasattr(self, 'websocket_session_id') else 'N/A'
        print(f"ADKOrchestrator: Updated history for session {session_id_for_log}: {len(self.current_adk_session['history'])} messages")

        return "\n".join(final_text_output_list)

    async def chat_loop(self):
        if not self.websocket:
            print("ADKOrchestrator: Websocket not initialized. Cannot start chat loop.")
            return

        self.websocket_session_id = str(uuid.uuid4())
        self.current_adk_session = self._get_or_create_simulated_session(self.websocket_session_id)
        print(f"ADKOrchestrator: Chat loop started for session_id: {self.websocket_session_id}. Waiting for queries.")

        await self.websocket.send_text(f"ADK Orchestrator Ready (Session: {self.websocket_session_id}). Send your queries or 'quit' to exit.")

        try:
            while True:
                query = await self.websocket.receive_text()
                query = query.strip()

                if query.lower() == 'quit':
                    await self.websocket.send_text("Exiting chat loop.")
                    break

                response_text = await self.handle_user_query(query)
                await self.websocket.send_text(response_text)

        except Exception as e:
            print(f"ADKOrchestrator: Websocket Error or Disconnection in session {self.websocket_session_id}: {str(e)}")
            try:
                await self.websocket.send_text(f"Error: {str(e)}")
            except Exception:
                pass
        finally:
            print(f"ADKOrchestrator: Chat loop ended for session {self.websocket_session_id}.")


    async def cleanup(self):
        print("ADKOrchestrator: Cleaning up resources...")
        await self.exit_stack.aclose()
        print("ADKOrchestrator: Resources cleaned up.")
