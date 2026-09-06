# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Set the working directory in the container to the service folder
WORKDIR /app/mcp

# Set PYTHONPATH to include the current directory
ENV PYTHONPATH=/app/mcp

# Copy only the necessary components
# Copy mcp folder content to /app/mcp
COPY mcp /app/mcp

# Install remaining dependencies for the MCP
RUN pip install --no-cache-dir -r /app/mcp/requirements.txt

# Expose the port that FastAPI runs on
EXPOSE 8000

# Command to run the fastmcp application using the src package
CMD ["python", "-m", "src.server"]
