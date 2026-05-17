#!/bin/bash
set -e

echo "=== VoxProof Deploy ==="

if [ ! -f .env ]; then
    echo "Creating .env from .env.example"
    cp .env.example .env
fi

if ! command -v docker &> /dev/null; then
    echo "Docker not found. Install Docker first."
    exit 1
fi

COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    COMPOSE="docker-compose"
fi

echo "1/3 Building and starting Docker service..."
$COMPOSE up -d --build

echo "2/3 Health check..."
sleep 2
curl -fsS http://127.0.0.1:8765/health || {
    echo "Health check failed. Recent logs:"
    $COMPOSE logs --tail=80 voxproof
    exit 1
}

echo "3/3 Done!"
echo "VoxProof running on http://127.0.0.1:8765"
echo "Remote demo URL: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP'):8765"
