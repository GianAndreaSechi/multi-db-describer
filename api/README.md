# multi-db-core

# Docker build

This one allow you to create a docker image to test and execute /core project

docker build -t multi-db-connector-api -f core/Dockerfile .

docker run -d -p 8000:8000 multi-db-api