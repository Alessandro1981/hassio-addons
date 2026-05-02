#!/usr/bin/env bash
set -e

echo "Starting Strava Fitness MCP Add-on..."

exec uvicorn src.app:app --host 0.0.0.0 --port 8099
