#!/bin/bash
#
# STELLA robot service installer
# Interactive setup for robot namespace and ROS domain ID
#

set -e

USER_NAME="$(whoami)"
USER_HOME="$(eval echo ~$USER_NAME)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "=== STELLA Service Installer ==="
echo ""
echo "  User:  $USER_NAME"
echo "  Home:  $USER_HOME"
echo "  Repo:  $REPO_DIR"
echo ""

# Interactive input
read -p "Robot namespace (e.g. robot1, robot2): " ROBOT_NS
read -p "ROS Domain ID (e.g. 52): " DOMAIN_ID

if [ -z "$ROBOT_NS" ] || [ -z "$DOMAIN_ID" ]; then
  echo "Error: Both values are required."
  exit 1
fi

# 1. Generate robot.env
CONFIG_DIR="$REPO_DIR/config"
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_DIR/robot.env" <<EOF
ROBOT_NS=$ROBOT_NS
ROS_DOMAIN_ID=$DOMAIN_ID
EOF
echo "[OK] Created $CONFIG_DIR/robot.env"

# 2. Generate service files from templates
for SERVICE in stella_bringup.service stella_joy.service; do
  sed -e "s|__USER__|$USER_NAME|g" \
      -e "s|__HOME__|$USER_HOME|g" \
      -e "s|__REPO_DIR__|$REPO_DIR|g" \
      "$SCRIPT_DIR/$SERVICE" | sudo tee /etc/systemd/system/$SERVICE > /dev/null
  echo "[OK] Installed $SERVICE"
done

# 3. Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable stella_bringup.service stella_joy.service

echo ""
echo "=== Done ==="
echo "  start all:  sudo systemctl start stella_bringup stella_joy"
echo "  stop all:   sudo systemctl stop stella_joy stella_bringup"
echo "  status:     sudo systemctl status stella_bringup stella_joy"
echo "  log:        journalctl -u stella_bringup -u stella_joy -f"
echo ""
echo "  Robot config: $CONFIG_DIR/robot.env"
echo "  To change settings, edit robot.env and restart services."
