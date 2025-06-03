IMAGE_NAME := zededa-ai-agent
CONTAINER_NAME := zededa-ai-agent-container

ZEDEDA_BEARER_TOKEN ?= "dummy_token_for_dev_only"

.PHONY: build run clean

# Target to build the Docker image
build:
	@echo "Building Docker image $(IMAGE_NAME)..."
	docker build -t $(IMAGE_NAME) .
	@echo "Docker image $(IMAGE_NAME) built successfully."

# Target to run the Docker container
run:
	@echo "Running Docker container $(CONTAINER_NAME) from image $(IMAGE_NAME)..."
	@echo "Access the application at http://localhost:8000"
	@# Stop and remove container if it already exists to prevent conflicts
	-docker stop $(CONTAINER_NAME) > /dev/null 2>&1 || true
	-docker rm $(CONTAINER_NAME) > /dev/null 2>&1 || true
	docker run -d -p 8000:8000 -e ZEDEDA_BEARER_TOKEN=$(ZEDEDA_BEARER_TOKEN) --name $(CONTAINER_NAME) $(IMAGE_NAME)
	@echo "Container $(CONTAINER_NAME) started. To see logs, run: docker logs $(CONTAINER_NAME)"

logs:
	@echo "Fetching logs from container $(CONTAINER_NAME)..."
	docker logs -f $(CONTAINER_NAME)

# Optional: Target to stop and remove the container
clean:
	@echo "Stopping and removing container $(CONTAINER_NAME)..."
	-docker stop $(CONTAINER_NAME) > /dev/null 2>&1 || true
	-docker rm $(CONTAINER_NAME) > /dev/null 2>&1 || true
	-docker rmi $(IMAGE_NAME) > /dev/null 2>&1 || true
	@echo "Container $(CONTAINER_NAME) stopped and removed."

# Optional: Target to clean the Docker image (use with caution)
clean-image:
	@echo "Removing Docker image $(IMAGE_NAME)..."
	-docker rmi $(IMAGE_NAME) > /dev/null 2>&1 || true
	@echo "Docker image $(IMAGE_NAME) removed."
