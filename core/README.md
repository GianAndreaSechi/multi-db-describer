# multi-db-core

# Docker build

This one allow you to create a docker image to test and execute /core project

docker build -t multi-db-core -f core/Dockerfile .

docker run -d multi-db-core

docker ps

docker exec -it <container_id> bash