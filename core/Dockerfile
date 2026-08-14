# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Set the working directory in the container to the project root
WORKDIR /app

# Set PYTHONPATH to include the /app directory
ENV PYTHONPATH=/app

# Copy only the core component and its specific tests
COPY core /app/core
COPY tests/core /app/tests/core

# Copy the requirements file for the core component
COPY core/requirements.txt /app/core/requirements.txt

# Install any needed packages specified in core/requirements.txt
RUN pip install --no-cache-dir -r /app/core/requirements.txt

# Command to run core tests by default
# This can be overridden when running the container
CMD ["tail", "-f", "/dev/null"]
