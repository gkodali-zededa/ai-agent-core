# Use an official Python runtime as a parent image
FROM python:3.13.3-slim

# Set the working directory in the container
WORKDIR /app

# Install uv (a fast Python package installer and resolver)
# Using pip to install uv itself as it's convenient within a Dockerfile
RUN pip install uv --no-cache-dir

# copy the .env file to the container
COPY .env ./

# Copy the project definition and lock file
COPY pyproject.toml uv.lock ./

# Install project dependencies using uv
# --no-cache can be used if you want to minimize layer size, uv handles caching efficiently.
RUN uv pip sync --no-cache-dir --system ./pyproject.toml

# Copy the application code into the container
# Copy the main application package
COPY zededa_server_app/ ./zededa_server_app/
# Copy the zededa.py script, which is referenced by the server
COPY zededa.py ./

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable for Python to run in unbuffered mode (good for logs)
ENV PYTHONUNBUFFERED=1

# Run app.main:app when the container launches
# The command assumes zededa_server_app.main contains your FastAPI app instance
# and zededa.py is in the WORKDIR (/app)
CMD ["uvicorn", "--host", "0.0.0.0", "zededa_server_app.main:app", "--port", "8000"]
