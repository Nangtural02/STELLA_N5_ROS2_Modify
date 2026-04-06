"""
Launch file for STELLA joystick teleop.

Launches joystick hardware nodes only:
  1. joy_node          - reads joystick hardware, publishes joy
  2. teleop_twist_joy  - converts joy -> cmd_vel

The safety gate (stella_safety_gate) runs as part of stella_bringup,
so all cmd_vel commands are automatically gated.
"""

import os
import yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def load_joy_params(filepath):
    """Load teleop params from YAML, extracting the ros__parameters dict."""
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    # Support both 'teleop_twist_joy_node: ros__parameters:' and flat format
    for key in data:
        if 'ros__parameters' in data[key]:
            return data[key]['ros__parameters']
    return data


def generate_launch_description():
    home = os.path.expanduser('~')
    repo_dir = os.path.join(home, 'colcon_ws', 'src', 'STELLA_N5_ROS2_Modify')
    default_config = os.path.join(repo_dir, 'stella_tools', 'joystick', 'stella_joy.yaml')

    joy_dev = LaunchConfiguration('joy_dev', default='0')
    config_filepath = LaunchConfiguration('config_filepath', default=default_config)
    robot_ns = LaunchConfiguration('robot_ns', default='')

    # Load teleop params as dict (namespace-safe)
    teleop_params = load_joy_params(default_config)

    namespaced_nodes = GroupAction([
        PushRosNamespace(robot_ns),

        # Joystick driver
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_id': joy_dev,
                'deadzone': 0.3,
                'autorepeat_rate': 20.0,
            }],
        ),

        # Twist conversion: joy -> cmd_vel
        Node(
            package='teleop_twist_joy',
            executable='teleop_node',
            name='teleop_twist_joy_node',
            parameters=[teleop_params],
        ),
    ])

    return LaunchDescription([
        DeclareLaunchArgument('joy_dev', default_value='0'),
        DeclareLaunchArgument('config_filepath', default_value=default_config,
                              description='Path to teleop joy config YAML'),
        DeclareLaunchArgument('robot_ns', default_value='',
                              description='Robot namespace (e.g. robot1, robot2)'),
        namespaced_nodes,
    ])
