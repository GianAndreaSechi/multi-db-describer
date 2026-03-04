# multi-db-connector

# Docker

docker build -t multi-db-connector -f core/Dockerfile .

docker run -d multi-db-connector

docker ps

docker exec -it <container_id> bash