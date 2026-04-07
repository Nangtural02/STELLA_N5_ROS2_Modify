#!/bin/bash
#
# Start ROS2 FastDDS Discovery Server on the control PC.
# Usage: bash start_discovery_server.sh [port]
# Default port: 11811
#

PORT=${1:-11811}

echo "Starting FastDDS Discovery Server on port $PORT..."
echo "Robots should set DISCOVERY_SERVER_IP to this machine's IP."
echo "Press Ctrl+C to stop."
echo ""

source /opt/ros/jazzy/setup.bash
fastdds discovery -i 0 -l 0.0.0.0 -p $PORT
