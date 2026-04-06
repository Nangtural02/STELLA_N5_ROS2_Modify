#!/bin/bash
if [ -z "$1" ]; then
  echo "Usage: ./install_service.sh <service_file>"
  echo "Example: ./install_service.sh stella_bringup.service"
  exit 1
fi

SERVICE_FILE="$1"
SERVICE_NAME=$(basename "$SERVICE_FILE")

sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
echo "Installed and enabled: $SERVICE_NAME"
echo "  start:   sudo systemctl start $SERVICE_NAME"
echo "  stop:    sudo systemctl stop $SERVICE_NAME"
echo "  status:  sudo systemctl status $SERVICE_NAME"
echo "  log:     journalctl -u $SERVICE_NAME -f"
