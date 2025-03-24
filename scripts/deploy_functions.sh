#!/bin/bash

# EINO Streaming Service Startup Script
# For Windows, run this script using Git Bash or WSL

# Color codes for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   EINO Streaming Microservice - Startup Script    ${NC}"
echo -e "${BLUE}====================================================${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker and try again.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose and try again.${NC}"
    exit 1
fi

# Check environment argument
ENV=${1:-dev}
if [[ "$ENV" != "dev" && "$ENV" != "test" && "$ENV" != "prod" ]]; then
    echo -e "${RED}Invalid environment. Please use: dev, test, or prod${NC}"
    exit 1
fi

echo -e "${GREEN}Starting EINO Streaming Service in ${ENV} environment...${NC}"

# For local development without Docker, uncomment these lines:
# echo -e "${GREEN}Installing Python dependencies...${NC}"
# pip install -r requirements.txt
# echo -e "${GREEN}Starting FastAPI service...${NC}"
# cd app && python main.py

# Use Docker Compose for consistent environment
echo -e "${GREEN}Building Docker containers...${NC}"
docker-compose build

echo -e "${GREEN}Starting Docker containers...${NC}"
docker-compose up -d

echo -e "${GREEN}Service started successfully!${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}The API is available at: http://localhost:8000${NC}"
echo -e "${BLUE}API Documentation: http://localhost:8000/docs${NC}"
echo -e "${BLUE}Frontend Test Client: http://localhost:4200${NC}"
echo -e "${BLUE}To view logs: docker-compose logs -f${NC}"
echo -e "${BLUE}To stop the service: docker-compose down${NC}"
echo -e "${BLUE}====================================================${NC}"