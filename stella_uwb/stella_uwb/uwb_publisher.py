"""UWB Publisher node: reads serial UWB devices, publishes UwbData."""
import yaml
import rclpy
from rclpy.node import Node
from stella_uwb_msgs.msg import UwbData

from stella_uwb.parser import parse_ntf_line
from stella_uwb.serial_reader import SerialReader


class UwbPublisher(Node):
    def __init__(self, config_path: str):
        super().__init__('uwb_publisher')

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Relative topic — namespace applied by PushRosNamespace in launch
        self._pub = self.create_publisher(UwbData, 'uwb/data', 10)

        # Apply namespace prefix to frame_id (e.g. robot2/uwb_link)
        ns = self.get_namespace().strip('/')
        base_frame_id = config.get('frame_id', 'uwb_link')
        self._frame_id = f'{ns}/{base_frame_id}' if ns else base_frame_id

        devices = config.get('uwb_devices', [])
        if not devices:
            self.get_logger().error('No uwb_devices in config!')
            return

        self._readers = []
        for dev in devices:
            port = dev['port']
            baud = dev.get('baud_rate', 115200)
            reader = SerialReader(port, baud, self._on_serial_line, self.get_logger())
            reader.start()
            self._readers.append(reader)
            self.get_logger().info(f'Started reader: {port} @ {baud}')

    def _on_serial_line(self, line: str):
        parsed = parse_ntf_line(line)
        if parsed is None:
            return

        msg = UwbData()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        msg.anchor_id = parsed['anchor_id']
        msg.distance = parsed['distance_m']
        msg.rssi = parsed['rssi']
        msg.cir = parsed['cir']
        msg.pdr = parsed['pdr']
        msg.status = parsed['status']
        self._pub.publish(msg)

    def destroy_node(self):
        self.get_logger().info('Shutting down UWB publisher...')
        for r in self._readers:
            r.stop()
        for r in self._readers:
            r.join(timeout=2.0)
        super().destroy_node()


def main(args=None):
    import sys
    rclpy.init(args=args)

    config_path = None
    for i, arg in enumerate(sys.argv):
        if arg == '--config' and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]

    if config_path is None:
        print('Usage: ros2 run stella_uwb uwb_publisher --config <path>')
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
