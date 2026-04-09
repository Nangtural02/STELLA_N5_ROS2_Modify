import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('stella_uwb_qm')
    default_config = os.path.join(pkg_dir, 'config', 'uwb_config.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'config',
            default_value=default_config,
            description='Path to UWB QM config YAML',
        ),
        Node(
            package='stella_uwb_qm',
            executable='uwb_publisher',
            name='uwb_qm_publisher',
            arguments=['--config', LaunchConfiguration('config')],
            output='screen',
        ),
    ])
