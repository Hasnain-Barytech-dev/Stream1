#!/bin/bash

# EINO Streaming Service Setup Script
# This script creates the empty project structure for later implementation
# For Windows, run this script using Git Bash or WSL

# Color codes for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   EINO Streaming Microservice - Setup Script      ${NC}"
echo -e "${BLUE}====================================================${NC}"

# Create base project directory
PROJECT_NAME="eino-streaming-service"
echo -e "${GREEN}Creating project directory: ${PROJECT_NAME}${NC}"
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

# Create directory structure
echo -e "${GREEN}Creating directory structure...${NC}"

# GitHub workflows directory
mkdir -p .github/workflows
touch .github/workflows/dev.yml
touch .github/workflows/testing.yml
touch .github/workflows/staging.yml
touch .github/workflows/prod.yml

# VS Code settings
mkdir -p .vscode
touch .vscode/settings.json
touch .vscode/extensions.json

# Main API application structure
mkdir -p app/api/endpoints
mkdir -p app/core
mkdir -p app/services/streaming
mkdir -p app/services/storage
mkdir -p app/services/processing
mkdir -p app/services/metrics
mkdir -p app/integrations
mkdir -p app/utils

# Create basic Python files
touch app/__init__.py
touch app/config.py
touch app/main.py

touch app/api/__init__.py
touch app/api/dependencies.py
touch app/api/routes.py
touch app/api/schemas.py

touch app/api/endpoints/__init__.py
touch app/api/endpoints/auth.py
touch app/api/endpoints/streams.py
touch app/api/endpoints/upload.py
touch app/api/endpoints/health.py

touch app/core/__init__.py
touch app/core/security.py
touch app/core/logging.py
touch app/core/exceptions.py

# Service directories with empty files
for dir in app/services/*/; do
    touch ${dir}__init__.py
done

touch app/services/streaming/hls_service.py
touch app/services/streaming/dash_service.py
touch app/services/streaming/manifest_generator.py
touch app/services/streaming/adaptive_streaming.py

touch app/services/storage/storage_service.py
touch app/services/storage/gcs_service.py
touch app/services/storage/local_service.py

touch app/services/processing/video_processor.py
touch app/services/processing/transcoder.py
touch app/services/processing/thumbnail_generator.py
touch app/services/processing/quality_analyzer.py

touch app/services/metrics/metrics_service.py

# Integration files
touch app/integrations/__init__.py
touch app/integrations/django_client.py
touch app/integrations/cloud_functions.py
touch app/integrations/pubsub_client.py

# Utility files
touch app/utils/__init__.py
touch app/utils/validators.py
touch app/utils/time_utils.py
touch app/utils/format_utils.py

# Cloud Functions
mkdir -p cloud_functions/process_video/utils
mkdir -p cloud_functions/generate_thumbnails/utils

touch cloud_functions/__init__.py
touch cloud_functions/process_video/main.py
touch cloud_functions/process_video/requirements.txt
touch cloud_functions/process_video/utils/__init__.py
touch cloud_functions/process_video/utils/ffmpeg_utils.py
touch cloud_functions/process_video/utils/gcs_utils.py

touch cloud_functions/generate_thumbnails/main.py
touch cloud_functions/generate_thumbnails/requirements.txt
touch cloud_functions/generate_thumbnails/utils/__init__.py
touch cloud_functions/generate_thumbnails/utils/image_utils.py

# Workers for background processing
mkdir -p workers
touch workers/__init__.py
touch workers/chunk_worker.py
touch workers/transcoding_worker.py
touch workers/manifest_worker.py
touch workers/cleanup_worker.py

# Test suite
mkdir -p tests/test_api
mkdir -p tests/test_services
mkdir -p tests/test_integration

touch tests/__init__.py
touch tests/conftest.py
touch tests/test_api/__init__.py
touch tests/test_api/test_streams.py
touch tests/test_api/test_upload.py
touch tests/test_services/__init__.py
touch tests/test_services/test_streaming.py
touch tests/test_services/test_storage.py
touch tests/test_integration/__init__.py
touch tests/test_integration/test_django_integration.py

# Utility scripts
mkdir -p scripts
touch scripts/setup_dev_env.sh
touch scripts/deploy_functions.sh
touch scripts/performance_test.py

# Terraform infrastructure as code
mkdir -p terraform
touch terraform/main.tf
touch terraform/variables.tf
touch terraform/outputs.tf
touch terraform/storage.tf
touch terraform/functions.tf
touch terraform/networking.tf
touch terraform/iam.tf

# Django integration
mkdir -p django_integration
touch django_integration/__init__.py
touch django_integration/models.py
touch django_integration/serializers.py
touch django_integration/views.py
touch django_integration/urls.py
touch django_integration/services.py

# Documentation
mkdir -p docs
touch docs/architecture.md
touch docs/integration.md
touch docs/api.md
touch docs/development.md

# Angular test client setup
mkdir -p frontend-test-client/src/app/components/upload
mkdir -p frontend-test-client/src/app/components/video-player
mkdir -p frontend-test-client/src/app/components/video-list
mkdir -p frontend-test-client/src/app/services
mkdir -p frontend-test-client/src/app/models
mkdir -p frontend-test-client/src/assets
mkdir -p frontend-test-client/src/environments

touch frontend-test-client/src/app/services/upload.service.ts
touch frontend-test-client/src/app/services/video.service.ts
touch frontend-test-client/src/app/models/video.model.ts
touch frontend-test-client/angular.json
touch frontend-test-client/package.json

# Root files
touch .gitignore
touch Dockerfile
touch docker-compose.yml
touch requirements.txt
touch requirements-dev.txt
touch README.md
touch kubernetes-dev.yaml
touch kubernetes-test.yaml
touch kubernetes-prod.yaml

# Make scripts executable
chmod +x scripts/*.sh

echo -e "${GREEN}Project structure created successfully!${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo -e "${BLUE}1. Navigate to the project directory: cd ${PROJECT_NAME}${NC}"
echo -e "${BLUE}2. Implement the required functionality${NC}"
echo -e "${BLUE}3. Run the service using Docker: docker-compose up${NC}"
echo -e "${BLUE}====================================================${NC}"