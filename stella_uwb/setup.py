from setuptools import find_packages, setup

package_name = 'stella_uwb'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/uwb_config.yaml']),
        ('share/' + package_name + '/launch', ['launch/stella_uwb.launch.py']),
    ],
    install_requires=['setuptools', 'pyserial', 'pyyaml'],
    entry_points={
        'console_scripts': [
            'uwb_publisher = stella_uwb.uwb_publisher:main',
        ],
    },
)
