#!/usr/bin/python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode

def generate_launch_description():

    odom_frame_id = LaunchConfiguration('odom_frame_id', default='odom')
    base_frame_id = LaunchConfiguration('base_frame_id', default='base_footprint')

    driver_node = LifecycleNode(package='stella_md',
                                executable='stella_md_node',
                                name='stella_md_node',
                                namespace='',
                                output='screen',
                                emulate_tty=True,
                                parameters=[{
                                    'odom_frame_id': odom_frame_id,
                                    'base_frame_id': base_frame_id,
                                }],
                                remappings=[
                                    ('cmd_vel', 'cmd_vel_safe'),
                                ],
                                )

    return LaunchDescription([
        DeclareLaunchArgument('odom_frame_id', default_value='odom',
                              description='TF frame id for odometry'),
        DeclareLaunchArgument('base_frame_id', default_value='base_footprint',
                              description='TF frame id for robot base'),
        driver_node,
    ])
