#!/bin/bash
#
# Switch between unicast (Discovery Server) and multicast discovery.
# Usage: ./switch_discovery.sh unicast|multicast
#

set -e

if [ "$1" != "unicast" ] && [ "$1" != "multicast" ]; then
  echo "Usage: ./switch_discovery.sh <unicast|multicast>"
  exit 1
fi

MODE=$1

for SERVICE in stella_bringup.service stella_joy.service; do
  FILE="/etc/systemd/system/$SERVICE"
  if [ ! -f "$FILE" ]; then
    echo "[SKIP] $SERVICE not installed"
    continue
  fi

  if [ "$MODE" = "multicast" ]; then
    # Comment out the discovery server line
    sudo sed -i 's|^Environment="ROS_DISCOVERY_SERVER=.*"|#Environment="ROS_DISCOVERY_SERVER=disabled"|' "$FILE"
    echo "[OK] $SERVICE -> multicast"
  else
    # Restore from robot.env
    source "$(grep EnvironmentFile "$FILE" | cut -d= -f2-)"
    DISC="${DISCOVERY_SERVER_IP}:${DISCOVERY_SERVER_PORT}"
    sudo sed -i "s|^#Environment=\"ROS_DISCOVERY_SERVER=.*\"|Environment=\"ROS_DISCOVERY_SERVER=$DISC\"|" "$FILE"
    echo "[OK] $SERVICE -> unicast ($DISC)"
  fi
done

sudo systemctl daemon-reload
sudo systemctl restart stella_bringup.service
sleep 8
sudo systemctl restart stella_joy.service

echo ""
echo "=== Switched to $MODE ==="
