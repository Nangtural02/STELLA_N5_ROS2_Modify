#!/bin/bash
#
# Switch between unicast (Static Peers) and multicast discovery.
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
    sudo sed -i 's|^Environment="FASTRTPS_DEFAULT_PROFILES_FILE=.*"|#Environment="FASTRTPS_DEFAULT_PROFILES_FILE=disabled"|' "$FILE"
    echo "[OK] $SERVICE -> multicast"
  else
    # Restore peers XML path from the commented line's repo dir
    REPO_DIR=$(grep EnvironmentFile "$FILE" | sed 's|EnvironmentFile=||;s|/stella_tools/config/robot.env||')
    PEERS="$REPO_DIR/stella_tools/config/fastdds_peers.xml"
    sudo sed -i "s|^#Environment=\"FASTRTPS_DEFAULT_PROFILES_FILE=.*\"|Environment=\"FASTRTPS_DEFAULT_PROFILES_FILE=$PEERS\"|" "$FILE"
    echo "[OK] $SERVICE -> unicast (static peers)"
  fi
done

sudo systemctl daemon-reload
sudo systemctl restart stella_bringup.service
sleep 8
sudo systemctl restart stella_joy.service

echo ""
echo "=== Switched to $MODE ==="
