import os
import sys

import rclpy
from rclpy.node import Node
import yaml

from stella_uwb_msgs.msg import UwbData
from stella_uwb_qm.tcp_reader import TcpReader
from stella_uwb_qm.nrf_reader import NrfReader
from stella_uwb_qm.parser import parse_json_line
from stella_uwb_qm.nrf_parser import parse_ranging_block


class UwbPublisher(Node):
    def __init__(self, config_path: str):
        super().__init__('uwb_qm_publisher')

        with open(config_path) as f:
            config = yaml.safe_load(f)

        self._pub = self.create_publisher(UwbData, 'uwb/qm_data', 10)

        ns = self.get_namespace().strip('/')
        base_frame_id = config.get('frame_id', 'uwb_link')
        self._frame_id = f'{ns}/{base_frame_id}' if ns else base_frame_id

        qm_type = (
            os.environ.get('UWB_QM_TYPE') or config.get('type', 'tcp')
        ).lower()

        if qm_type == 'nrf':
            nrf_cfg = config.get('nrf', {})
            port = (
                os.environ.get('UWB_QM_NRF_PORT')
                or nrf_cfg.get('port', 'ftdi://FT4222')
            )
            role = (
                os.environ.get('UWB_QM_NRF_ROLE')
                or nrf_cfg.get('role', 'controlee')
            )
            self._reader = NrfReader(
                port, role, self._on_nrf_block, self.get_logger()
            )
            self._reader.start()
            self.get_logger().info(
                f'UWB QM publisher started — nrf {port} ({role})'
            )
        else:
            tcp_cfg = config.get('tcp', {})
            host = (
                os.environ.get('UWB_QM_HOST')
                or tcp_cfg.get('host', '192.168.5.2')
            )
            port = int(
                os.environ.get('UWB_QM_PORT', 0) or tcp_cfg.get('port', 5000)
            )
            self._reader = TcpReader(
                host, port, self._on_tcp_line, self.get_logger()
            )
            self._reader.start()
            self.get_logger().info(
                f'UWB QM publisher started — tcp {host}:{port}'
            )

    def _publish_record(self, parsed: dict) -> None:
        msg = UwbData()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        msg.anchor_id = parsed['anchor_id']
        msg.distance = parsed['distance_m']
        msg.rssi = parsed['rssi']
        msg.cir = parsed['cir']
        msg.pdr = parsed['pdr']
        msg.status = parsed['status']
        msg.aoa_azimuth = parsed['aoa_azimuth']
        msg.aoa_elevation = parsed['aoa_elevation']
        msg.aoa_azimuth_fom = parsed['aoa_azimuth_fom']
        msg.aoa_elevation_fom = parsed['aoa_elevation_fom']
        self._pub.publish(msg)

    def _on_tcp_line(self, line: str):
        parsed = parse_json_line(line)
        if parsed is None:
            return
        self._publish_record(parsed)

    def _on_nrf_block(self, block: str):
        for parsed in parse_ranging_block(block):
            self._publish_record(parsed)

    def destroy_node(self):
        self.get_logger().info('Shutting down UWB QM publisher...')
        self._reader.stop()
        self._reader.join(timeout=2.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    config_path = None
    for i, arg in enumerate(sys.argv):
        if arg == '--config' and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]

    if config_path is None:
        print('Usage: ros2 run stella_uwb_qm uwb_publisher --config <path>')
        sys.exit(1)

    node = UwbPublisher(config_path)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
