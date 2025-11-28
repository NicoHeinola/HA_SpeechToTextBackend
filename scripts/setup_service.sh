#!/bin/bash

# Default values
DEFAULT_SERVICE_USER="user"
DEFAULT_USER_HOME="/home/user"

# Get user input or use defaults
SERVICE_USER="${1:-$DEFAULT_SERVICE_USER}"
USER_HOME="${2:-$DEFAULT_USER_HOME}"

echo "Setting up HA_MicrophoneListenerBackend service with:"
echo "  Service User: $SERVICE_USER"
echo "  User Home: $USER_HOME"

# Clean up any existing service files or symlinks
echo "Cleaning up existing service files..."
sudo systemctl stop ha_microphone_listener_backend.service 2>/dev/null || true
sudo systemctl disable ha_microphone_listener_backend.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/ha_microphone_listener_backend.service
sudo systemctl daemon-reload

# Create the service file with substituted values
cat > /tmp/ha_microphone_listener_backend.service << EOF
[Unit]
Description=Home Assistant Microphone Listener Backend API
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$USER_HOME/prod_codes/HomeAssistant/HA_MicrophoneListenerBackend
Environment="ENVIRONMENT=production"
Environment="PYTHONPATH=$USER_HOME/prod_codes/HomeAssistant/HA_MicrophoneListenerBackend"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin"
Environment="DISPLAY=:0"
Environment="WAYLAND_DISPLAY=wayland-0"
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_RUNTIME_PATH=/run/user/1000/pulse"
ExecStart=/bin/bash -c 'source $USER_HOME/prod_codes/HomeAssistant/HA_MicrophoneListenerBackend/.venv/bin/activate && python3 main.py'
Restart=always
RestartSec=10
StandardOutput=append:$USER_HOME/prod_codes/HomeAssistant/HA_MicrophoneListenerBackend/microphone_listener.log
StandardError=append:$USER_HOME/prod_codes/HomeAssistant/HA_MicrophoneListenerBackend/microphone_listener.log

[Install]
WantedBy=multi-user.target
EOF

# Copy directly to systemd directory
sudo cp /tmp/ha_microphone_listener_backend.service /etc/systemd/system/ha_microphone_listener_backend.service
rm /tmp/ha_microphone_listener_backend.service

echo "Service file created successfully!"

# Start the service
echo "Enabling and starting the HA Microphone Listener Backend service..."

sudo systemctl daemon-reload
sudo systemctl enable ha_microphone_listener_backend.service
sudo systemctl start ha_microphone_listener_backend.service
sudo systemctl status ha_microphone_listener_backend.service