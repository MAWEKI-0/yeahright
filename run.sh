#!/bin/bash
# run.sh - Standardized script to run The Foundry application

echo "Stopping any existing Flask processes on port 5000..."
# Find and kill processes on port 5000 (macOS/Linux compatible)
# Use lsof to find PID, then kill -9
lsof -i :5000 | awk 'NR!=1 {print $2}' | xargs -r kill -9 2>/dev/null

# Give it a moment to clear
sleep 1

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting The Foundry application..."
python app.py
