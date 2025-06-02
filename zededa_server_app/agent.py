import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

from .supervisor_prompt import validate_data_with_claude, conforms_to_guidelines

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self, websocket=None):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # Get Anthropic API key from environment variables or allow it to be passed
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.anthropic = Anthropic(api_key=self.anthropic_api_key)
        self.websocket = websocket
    # methods will go here

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
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
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_response(self, claude_response_obj, available_tools, messages_history, final_text_output_list):
        """
        Processes a single response object from Claude.
        Updates messages_history and final_text_output_list.
        Handles tool calls and recursively processes subsequent responses.
        """
        current_assistant_blocks = []  # Blocks for the current claude_response_obj

        for content_block in claude_response_obj.content:
            if content_block.type == 'text':
                final_text_output_list.append(content_block.text)
                current_assistant_blocks.append(content_block)
            elif content_block.type == 'tool_use':
                # Add any preceding text and this tool_use block to current_assistant_blocks
                current_assistant_blocks.append(content_block)
                
                # Append the assistant message (text + tool_use) to history
                if current_assistant_blocks: # Ensure there's something to append
                    messages_history.append({
                        "role": "assistant",
                        "content": list(current_assistant_blocks) # Make a copy
                    })
                # Clear current_assistant_blocks as it's now part of messages_history for this turn
                current_assistant_blocks = [] 
                
                tool_name = content_block.name
                tool_args = content_block.input
                
                print(f"Calling tool: {tool_name} with args: {tool_args}") # Added for debugging
                result = await self.session.call_tool(tool_name, tool_args)
                final_text_output_list.append(f"[Calling tool {tool_name} with args {tool_args}]")
                print(f"Tool {tool_name} result: {result.content}") # Added for debugging

                # Append tool result to messages history
                messages_history.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": result.content # Assuming result.content is a string or suitable structure
                        }
                    ]
                })

                # Get next response from Claude
                next_claude_response_obj = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20240620", 
                    max_tokens=1000,
                    messages=messages_history, # Pass the full history
                    tools=available_tools
                )
                
                # Recursively process the new response
                await self.process_response(next_claude_response_obj, available_tools, messages_history, final_text_output_list)
                
                return # After a tool cycle and recursion, this path of process_response is done.

        # If the loop finished and current_assistant_blocks has content, 
        # it means this claude_response_obj consisted of only text blocks (or was empty).
        # This assistant message needs to be added to history.
        if current_assistant_blocks:
            messages_history.append({
                "role": "assistant",
                "content": current_assistant_blocks
            })

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        claude_response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20240620", 
            max_tokens=1000,
            messages=messages, # This is the initial user message
            tools=available_tools
        )

        final_text = []
        # `messages` (the history) will be mutated by process_response
        await self.process_response(claude_response, available_tools, messages, final_text)
        
        # Final response processing
        print(f"Final message history: {messages}") # Added for debugging
        return "\\n".join(final_text)
    
    async def chat_loop(self):
        """Run an interactive chat loop using websocket for I/O"""
        if not self.websocket:
            print("Websocket not initialized. Cannot start chat loop.")
            return

        print("\nMCP Client Started! Waiting for queries via websocket.")
        await self.websocket.send_text("MCP Client Ready. Send your queries or 'quit' to exit.")

        try:
            while True:
                query = await self.websocket.receive_text()
                query = query.strip()
                llm_response = validate_data_with_claude(query, self.anthropic_api_key)
                if not conforms_to_guidelines(llm_response):
                    await self.websocket.send_text("I'm sorry, but my primary function is to support you with inquiries about Zededa Inc and its services. Can I help  with a Zededa related question?")
                    break

                if query.lower() == 'quit':
                    await self.websocket.send_text("Exiting chat loop.")
                    break

                response_text = await self.process_query(query)
                await self.websocket.send_text(response_text)

        except Exception as e: # Catch WebSocketDisconnect or other errors
            print(f"\nWebsocket Error or Disconnection: {str(e)}")
            # Optionally send a final message if the websocket is still partially open
            try:
                await self.websocket.send_text(f"Error: {str(e)}")
            except Exception:
                pass # Ignore if sending fails
        finally:
            print("Chat loop ended.")


    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    # This main function is for CLI usage of the client.
    # It requires sys module to be imported.
    import sys 
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        # The original main function didn't call chat_loop as it's websocket-based.
        # If CLI interaction is needed, it would require a different loop.
        print("Connected to server. CLI interaction mode not fully implemented in this version of main().")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys # Ensure sys is available for the script execution context
    asyncio.run(main())
