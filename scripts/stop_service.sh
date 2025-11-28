#!/bin/bash

echo "Stopping HA Microphone Listener Backend..."

# Check if systemd service exists and is active
if systemctl is-active --quiet ha_microphone_listener_backend.service 2>/dev/null; then
    echo "Stopping systemd service..."
    sudo systemctl stop ha_microphone_listener_backend.service
    echo "HA Microphone Listener Backend service stopped"
else
    # Fallback: Find and kill the process - check common FastAPI ports
    for port in 8000 8080 5000; do
        PID=$(lsof -ti:$port 2>/dev/null | grep -v "^$")
        if [ -n "$PID" ]; then
            echo "Found process on port $port (PID: $PID)"
            kill $PID
            echo "Process $PID killed successfully"
            
            # Wait a moment and check if it's still running
            sleep 2
            if lsof -i:$port > /dev/null 2>&1; then
                echo "Process still running, force killing..."
                kill -9 $PID
            fi
            echo "HA Microphone Listener Backend stopped"
            exit 0
        fi
    done
    echo "No HA Microphone Listener Backend process found running"
fi