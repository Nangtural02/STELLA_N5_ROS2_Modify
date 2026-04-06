#!/usr/bin/env python3
"""
stella_safety_gate - Universal velocity safety gate for STELLA robot.

ALL cmd_vel commands (Nav2, FMGT, teleop, etc.) pass through this gate
before reaching the motor driver.

  Subscriptions:
    cmd_vel      - velocity commands from any source
    joy          - joystick state for lock/unlock and speed control

  Publications:
    cmd_vel_safe - gated velocity commands → stella_md (via remapping)

Features:
  - Park/lock: Hold X button (1s) to toggle. When locked, all cmd_vel is blocked.
  - Speed multiplier: D-pad UP/DOWN to adjust (0.25x ~ 2.0x).
  - Rumble feedback for lock/unlock/blocked commands.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy, JoyFeedback


class StellaSafetyGate(Node):

    LOCK_BUTTON = 2          # Xbox X button
    DPAD_Y_AXIS = 7          # D-pad up=+1, down=-1
    HOLD_DURATION = 1.0      # seconds to hold for lock toggle
    MULTIPLIER_STEP = 0.25
    MULTIPLIER_MIN = 0.25
    MULTIPLIER_MAX = 2.0
    MULTIPLIER_DEFAULT = 1.0

    def __init__(self):
        super().__init__('stella_safety_gate')

        # State
        self.locked = False
        self.multiplier = self.MULTIPLIER_DEFAULT
        self.lock_btn_press_time = None
        self.lock_btn_was_pressed = False
        self.lock_toggled_this_press = False
        self.dpad_y_prev = 0.0
        self.last_warn_rumble = self.get_clock().now()

        # Publishers / Subscribers
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel_safe', 10)
        self.feedback_pub = self.create_publisher(JoyFeedback, 'joy/set_feedback', 10)
        self.cmd_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.joy_sub = self.create_subscription(
            Joy, 'joy', self.joy_callback, 10)

        # Timer to check lock hold duration & publish stop when locked (20 Hz)
        self.timer = self.create_timer(0.05, self.timer_callback)

        self.get_logger().info(
            f'Safety gate started - multiplier: {self.multiplier:.2f}x, locked: {self.locked}')

    def joy_callback(self, msg: Joy):
        self._handle_lock_button(msg)
        self._handle_dpad(msg)

    def _handle_lock_button(self, msg: Joy):
        if len(msg.buttons) <= self.LOCK_BUTTON:
            return

        pressed = bool(msg.buttons[self.LOCK_BUTTON])

        if pressed and not self.lock_btn_was_pressed:
            self.lock_btn_press_time = self.get_clock().now()
            self.lock_toggled_this_press = False

        if not pressed and self.lock_btn_was_pressed:
            self.lock_btn_press_time = None
            self.lock_toggled_this_press = False

        self.lock_btn_was_pressed = pressed

    def _handle_dpad(self, msg: Joy):
        if len(msg.axes) <= self.DPAD_Y_AXIS:
            return

        dpad_y = msg.axes[self.DPAD_Y_AXIS]

        if dpad_y != 0.0 and self.dpad_y_prev == 0.0:
            if dpad_y > 0:
                self.multiplier = min(
                    self.multiplier + self.MULTIPLIER_STEP, self.MULTIPLIER_MAX)
            else:
                self.multiplier = max(
                    self.multiplier - self.MULTIPLIER_STEP, self.MULTIPLIER_MIN)
            self.get_logger().info(f'Speed multiplier: {self.multiplier:.2f}x')

        self.dpad_y_prev = dpad_y

    def timer_callback(self):
        """Check lock button hold & continuously publish stop when locked."""
        if self.lock_btn_press_time is not None and not self.lock_toggled_this_press:
            elapsed = (self.get_clock().now() - self.lock_btn_press_time).nanoseconds / 1e9
            if elapsed >= self.HOLD_DURATION:
                self.locked = not self.locked
                self.lock_toggled_this_press = True
                state = 'LOCKED' if self.locked else 'UNLOCKED'
                self.get_logger().info(f'Robot {state}')
                self._rumble(1.0, 0.6 if self.locked else 0.3)

        if self.locked:
            self.cmd_pub.publish(Twist())

    def _rumble_pattern(self, intensity: float, pattern: list):
        """Play a rumble pattern: list of (on, off, on, off, ...) durations."""
        sequence = pattern[0]
        self._pattern_queue = []
        for i, dur in enumerate(sequence):
            is_on = (i % 2 == 0)
            self._pattern_queue.append((intensity if is_on else 0.0, dur))
        self._play_next_pattern()

    def _play_next_pattern(self):
        if not self._pattern_queue:
            msg = JoyFeedback()
            msg.type = JoyFeedback.TYPE_RUMBLE
            msg.id = 0
            msg.intensity = 0.0
            self.feedback_pub.publish(msg)
            return
        intensity, duration = self._pattern_queue.pop(0)
        msg = JoyFeedback()
        msg.type = JoyFeedback.TYPE_RUMBLE
        msg.id = 0
        msg.intensity = intensity
        self.feedback_pub.publish(msg)
        if hasattr(self, '_pattern_timer') and self._pattern_timer is not None:
            self._pattern_timer.cancel()
        self._pattern_timer = self.create_timer(duration, self._pattern_timer_cb)

    def _pattern_timer_cb(self):
        self._pattern_timer.cancel()
        self._play_next_pattern()

    def _rumble(self, intensity: float, duration: float = 0.3):
        """Send rumble feedback to the joystick for a given duration (seconds)."""
        msg = JoyFeedback()
        msg.type = JoyFeedback.TYPE_RUMBLE
        msg.id = 0
        msg.intensity = intensity
        self.feedback_pub.publish(msg)
        if hasattr(self, '_rumble_timer') and self._rumble_timer is not None:
            self._rumble_timer.cancel()
        self._rumble_timer = self.create_timer(duration, self._rumble_stop)

    def _rumble_stop(self):
        """Stop rumble (one-shot)."""
        msg = JoyFeedback()
        msg.type = JoyFeedback.TYPE_RUMBLE
        msg.id = 0
        msg.intensity = 0.0
        self.feedback_pub.publish(msg)
        self._rumble_timer.cancel()

    def cmd_vel_callback(self, msg: Twist):
        if self.locked:
            if (msg.linear.x != 0.0 or msg.linear.y != 0.0 or
                    msg.angular.z != 0.0):
                now = self.get_clock().now()
                if (now - self.last_warn_rumble).nanoseconds / 1e9 >= 0.5:
                    self._rumble_pattern(0.7, [(0.15, 0.05, 0.15)])
                    self.last_warn_rumble = now
            return

        out = Twist()
        out.linear.x = msg.linear.x * self.multiplier
        out.linear.y = msg.linear.y * self.multiplier
        out.linear.z = msg.linear.z * self.multiplier
        out.angular.x = msg.angular.x * self.multiplier
        out.angular.y = msg.angular.y * self.multiplier
        out.angular.z = msg.angular.z * self.multiplier
        self.cmd_pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = StellaSafetyGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
