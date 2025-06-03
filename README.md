# ai-agent-core

## Description
This project is a FastAPI-based AI agent that interacts with a Zededa control plane API. It uses an Anthropic language model to process queries and can execute predefined tools to fetch information or perform actions on Zededa entities.

## Setup

### Dependencies
Install dependencies using `uv pip install -r requirements.txt` (if a `requirements.txt` is generated from `pyproject.toml` and `uv.lock`) or `uv pip install .` based on `pyproject.toml`.

### Environment Variables
The application requires the following environment variables to be set:

*   `ANTHROPIC_API_KEY`: Your API key for the Anthropic (Claude) model.
*   `ZEDEDA_BEARER_TOKEN`: Bearer token for authenticating with the Zededa API. This should be the token value itself, without the "Bearer " prefix (the application will add it). When running the application using `make run` (which utilizes Docker), a default placeholder token (`dummy_token_for_dev_only`) is supplied from the `Makefile`. This allows the server to start without an explicit token for local development or testing. For actual API interactions, you should override this by setting the `ZEDEDA_BEARER_TOKEN` environment variable directly (e.g., in your shell or by modifying the `Makefile` for persistent changes) to a valid Bearer token.
*   `ZEDEDA_API_BASE_URL`: The base URL for the Zededa API. If not set, it defaults to `https://zedcontrol.local.zededa.net`.

These variables can be placed in a `.env` file in the project root directory, which will be loaded automatically by the application.

## Running the Application
Run the FastAPI server using Uvicorn:
```bash
uvicorn zededa_server_app.main:app --reload --port 8000
```

## Interacting with the Agent
Once running, the agent exposes a WebSocket endpoint at `ws://localhost:8000/ws` for communication. You can use a WebSocket client to connect and interact with the agent.
