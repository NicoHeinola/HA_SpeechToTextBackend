#!/bin/bash

# Auto-start HA Microphone Listener Backend
echo "Starting HA Microphone Listener Backend..."

# Check if systemd service exists
if systemctl list-unit-files ha_microphone_listener_backend.service &>/dev/null; then
    # Use systemd service
    if systemctl is-active --quiet ha_microphone_listener_backend.service; then
        echo "HA Microphone Listener Backend service is already running"
        sudo systemctl status ha_microphone_listener_backend.service --no-pager
    else
        echo "Starting systemd service..."
        sudo systemctl start ha_microphone_listener_backend.service
        sleep 2
        if systemctl is-active --quiet ha_microphone_listener_backend.service; then
            echo "HA Microphone Listener Backend service started successfully"
            sudo systemctl status ha_microphone_listener_backend.service --no-pager
        else
            echo "Failed to start service. Check logs with: sudo journalctl -u ha_microphone_listener_backend -n 50"
        fi
    fi
else
    echo "Systemd service not found. Run ./scripts/setup_service.sh first."
fi