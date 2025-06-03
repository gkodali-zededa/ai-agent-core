# Deployment Plan for AI Agent Core

This document outlines conceptual deployment strategies for the AI Agent Core application, focusing on Dockerization and deployment to Google Cloud Run.

## 1. Overview

The AI Agent Core consists of two main processes that need to run concurrently:
1.  **The ADK-based Agent (FastAPI/Uvicorn):** This is the main application server, currently running via `uvicorn zededa_server_app.main:app`. It handles incoming user requests (e.g., via WebSockets) and orchestrates the agent's logic using the `ADKOrchestrator`.
2.  **`zededa.py` (FastMCP stdio server):** This script acts as a local tool server, exposing Zededa API interaction capabilities. The `ADKOrchestrator` communicates with it using the `mcp` library over stdio pipes.

Running these two processes together, especially with the stdio communication requirement for `zededa.py`, presents challenges within a single Docker container.

## 2. Dockerfile Configuration for Co-execution

The primary challenge is managing the `zededa.py` process and enabling the `ADKOrchestrator` (running within the Uvicorn-served FastAPI app) to connect to its stdio.

Here are a few options:

### Option A: Process Manager (e.g., `supervisord`)

Using a process manager like `supervisord` is a common way to run multiple processes in a container.

*   **Configuration (`supervisord.conf`):**
    ```ini
    [supervisord]
    nodaemon=true

    [program:adk_agent]
    command=uvicorn zededa_server_app.main:app --host 0.0.0.0 --port 8080
    stdout_logfile=/dev/stdout
    stdout_logfile_maxbytes=0
    stderr_logfile=/dev/stderr
    stderr_logfile_maxbytes=0

    [program:zededa_tool_server]
    command=python zededa.py
    stdout_logfile=/var/log/zededa_tool_server.out.log
    stderr_logfile=/var/log/zededa_tool_server.err.log
    # The following is tricky for stdio_client:
    # redirect_stdin=true
    ```
*   **How `ADKOrchestrator` connects:** The `ADKOrchestrator` uses `mcp.client.stdio.stdio_client` which expects to start the `python zededa.py` command itself and directly control its stdin/stdout pipes.
*   **Challenge for stdio:**
    *   `supervisord` is designed to manage and monitor processes, including their stdio streams, primarily for logging or basic redirection.
    *   Allowing an external process (like the `stdio_client` invoked by `ADKOrchestrator`) to "take over" the stdio of a child process managed by `supervisord` is non-trivial and goes against `supervisord`'s typical operational model. `supervisord` expects to be the parent and manager of these streams.
    *   If `zededa.py` is started by `supervisord`, `ADKOrchestrator` cannot simply provide the command `python zededa.py` to `stdio_client` as that would attempt to start a *new* `zededa.py` process, not connect to the one managed by `supervisord`.
    *   Specialized configurations involving named pipes (FIFOs) might be a workaround but add significant complexity.

### Option B: Custom Entrypoint Script with Backgrounding

An `entrypoint.sh` script can be used to start one process in the background and then the main application in the foreground.

*   **`entrypoint.sh`:**
    ```bash
    #!/bin/sh
    # Start zededa.py in the background
    python /app/zededa.py &
    ZEDEDA_PID=$! # Get PID of backgrounded process

    # Start the main ADK agent application in the foreground
    exec uvicorn zededa_server_app.main:app --host 0.0.0.0 --port ${PORT:-8080}

    # Optional: wait for ZEDEDA_PID to ensure cleanup, though exec replaces the script
    # wait $ZEDEDA_PID
    ```
*   **Challenge for stdio:**
    *   Similar to Option A, when `python zededa.py &` is run, its stdio streams are managed by the shell, typically detaching them from direct programmatic access needed by `stdio_client`.
    *   The `ADKOrchestrator`'s `stdio_client` would still try to launch a *new* `zededa.py` process. It wouldn't automatically know how to find and connect to the stdio of the backgrounded `zededa.py`.
    *   Workarounds like creating explicit named pipes (FIFOs) before starting `zededa.py` and configuring `zededa.py` to use these FIFOs for its stdio, then having `ADKOrchestrator` connect to these FIFOs, could theoretically work but are complex to manage correctly, especially with process lifecycle and cleanup.

### Option C: Modify `zededa.py` for TCP Communication (Preferred)

This is the **strongly recommended approach** for robustness, simplicity, and scalability if modifications to `zededa.py` are permissible.

*   **Change `zededa.py`:**
    *   Modify the `FastMCP` server within `zededa.py` to listen on a local TCP port (e.g., `localhost:9000`) instead of using `transport='stdio'`. This usually involves changing how the `mcp.transport.Transport` and `mcp.server.Server` are configured.
*   **Change `ADKOrchestrator`:**
    *   Update `ADKOrchestrator.connect_to_mcp_server` to use an equivalent TCP client from the `mcp` library (e.g., `mcp.client.tcp.tcp_client` if it exists, or adapt to a standard TCP socket connection if `FastMCP` on `zededa.py` can support a simple socket protocol).
    *   The connection would be to `localhost:9000` (or the configured port).
*   **Benefits:**
    *   Decouples the two processes.
    *   Simplifies process management significantly. Standard inter-process communication over TCP is well-understood and robust.
    *   Avoids all the complexities of stdio redirection and management.
    *   Scales better if you were to ever separate these into different containers/services (though not the current goal).
*   **`entrypoint.sh` (with Option C):**
    ```bash
    #!/bin.sh
    # Start zededa.py (now listening on TCP) in the background
    python /app/zededa.py &

    # Start the main ADK agent application in the foreground
    exec uvicorn zededa_server_app.main:app --host 0.0.0.0 --port ${PORT:-8080}
    ```

### Sketch of Dockerfile (Assuming Option C or a working stdio solution)

```dockerfile
# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app/

# Install any needed packages specified in requirements.txt
# Ensure mcp, anthropic, fastapi, uvicorn, python-dotenv, etc., are listed
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container (if Uvicorn uses it)
EXPOSE 8080

# Define environment variables (can also be set at runtime)
ENV ANTHROPIC_API_KEY=""
# Add other ENV variables like ZEDEDA_BEARER_TOKEN, ZEDEDA_API_BASE_URL if needed by zededa.py directly

# Entrypoint script (if using Option B or C for multiple processes)
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Command to run the application
# If using entrypoint.sh (Options B or C):
CMD ["/app/entrypoint.sh"]

# If zededa.py is somehow launched by ADKOrchestrator itself (not recommended for stdio server):
# CMD ["uvicorn", "zededa_server_app.main:app", "--host", "0.0.0.0", "--port", "8080"]

# If using supervisord (Option A):
# COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
# CMD ["/usr/bin/supervisord"]
```
*(Note: `requirements.txt` would need to be created and list all dependencies.)*

## 3. Deployment to Google Cloud Run (Conceptual)

Google Cloud Run is a suitable platform for deploying containerized applications like this AI Agent. Assuming **Option C (TCP communication for `zededa.py`)** is implemented for simpler containerization, the steps are:

1.  **Prerequisites:**
    *   Google Cloud SDK installed and configured (`gcloud init`, `gcloud auth login`).
    *   A Google Cloud Project created with billing enabled.
    *   Required APIs enabled in your GCP project:
        *   Cloud Build API (for building Docker images)
        *   Cloud Run API
        *   Artifact Registry API (or Container Registry API)
        *   Secret Manager API (recommended for secrets)

2.  **Containerize the Application:**
    *   Ensure your `Dockerfile` is correctly set up (preferably using Option C from above).
    *   Build the Docker image locally and tag it for Artifact Registry:
        ```bash
        docker build -t YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/ai-agent-core:latest .
        ```
        (Replace `YOUR_REGION`, `YOUR_PROJECT_ID`, `YOUR_REPO_NAME` accordingly. E.g., `us-central1-docker.pkg.dev/my-gcp-project/ai-agents/ai-agent-core:latest`)

3.  **Push to Artifact Registry:**
    *   Authenticate Docker with Artifact Registry (if not already done):
        ```bash
        gcloud auth configure-docker YOUR_REGION-docker.pkg.dev
        ```
    *   Push the image:
        ```bash
        docker push YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/ai-agent-core:latest
        ```

4.  **Deploy to Cloud Run:**
    *   Use the `gcloud run deploy` command. Example:
        ```bash
        gcloud run deploy ai-agent-core-service \
          --image YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/YOUR_REPO_NAME/ai-agent-core:latest \
          --platform managed \
          --region YOUR_DEPLOY_REGION \ # e.g., us-central1
          --allow-unauthenticated \ # For public access; use --no-allow-unauthenticated and IAM for private services
          --port 8080 \ # The port your Uvicorn server listens on *inside* the container
          --set-env-vars ANTHROPIC_API_KEY="your-anthropic-api-key-value",ZEDEDA_BEARER_TOKEN="your-zededa-token-value",ZEDEDA_API_BASE_URL="your-zededa-api-url" \
          # For better security, use Secret Manager for API keys:
          # --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key-secret:latest,ZEDEDA_BEARER_TOKEN=zededa-bearer-token-secret:latest \
          --min-instances 0 \ # Can scale to zero for cost-effectiveness
          --max-instances 2 \ # Adjust based on expected load
          --cpu 1 \ # Adjust CPU
          --memory 512Mi \ # Adjust memory
          --concurrency 80 # Default, adjust based on application's ability to handle concurrent requests
        ```
    *   **Key Flags Explained:**
        *   `ai-agent-core-service`: Your chosen name for the Cloud Run service.
        *   `--image`: Points to the image in Artifact Registry.
        *   `--platform managed`: Uses Google-managed infrastructure.
        *   `--region`: The GCP region where the service will be deployed.
        *   `--allow-unauthenticated`: Makes the service publicly accessible. For internal services or those requiring authentication, use `--no-allow-unauthenticated` and configure IAM or IAP.
        *   `--port 8080`: Specifies the port your application (Uvicorn) listens on *inside* the container. Cloud Run handles external mapping to HTTPS on port 443.
        *   `--set-env-vars`: Directly sets environment variables. **Not recommended for secrets.**
        *   `--set-secrets`: Securely mounts secrets from Google Secret Manager as environment variables or files. This is the recommended way to handle API keys and other sensitive data. You'd need to create these secrets in Secret Manager first.
        *   `--min-instances`, `--max-instances`: Configure scaling behavior.
        *   `--cpu`, `--memory`: Allocate resources to your service instances.
        *   `--concurrency`: How many requests one instance can handle simultaneously.

5.  **Accessing the Service:**
    *   Once deployed, Cloud Run will provide a URL to access your service.
    *   WebSockets are supported by Cloud Run.

## 4. Other Platforms (Brief Mention)

*   **Google Kubernetes Engine (GKE):**
    *   For more complex scenarios requiring fine-grained control over networking, storage (persistent volumes), or specific hardware, GKE would be a more suitable choice.
    *   Deployment would involve creating Kubernetes Deployments, Services, and potentially Ingress resources.
    *   This adds operational overhead compared to Cloud Run.
*   **ADK Agent Engine (Hypothetical):**
    *   If a dedicated "ADK Agent Engine" platform existed, it would likely have its own specialized deployment mechanisms, potentially simplifying the process by understanding ADK agent structures intrinsically. This is purely conceptual based on the ADK's name.

## 5. Monitoring and Logging

*   Cloud Run automatically integrates with Cloud Logging and Cloud Monitoring for standard output/error streams and basic metrics.
*   Implement structured logging within the application for better observability.
