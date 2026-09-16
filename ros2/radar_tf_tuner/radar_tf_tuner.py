#!/usr/bin/env python3
"""Interactive TF tuner for aligning a radar frame to a lidar frame in RViz.

Publishes the parent_frame -> child_frame transform at 20 Hz from six ROS 2
parameters (x, y, z, roll, pitch, yaw). Adjust them live with rqt_reconfigure
sliders or `ros2 param set`, and copy the equivalent static_transform_publisher
command from the log once the point clouds line up.
"""
import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from tf2_ros import TransformBroadcaster

POSE_KEYS = ('x', 'y', 'z', 'roll', 'pitch', 'yaw')


def quat_from_euler(roll, pitch, yaw):
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return (
        sr * cp * cy - cr * sp * sy,  # x
        cr * sp * cy + sr * cp * sy,  # y
        cr * cp * sy - sr * sp * cy,  # z
        cr * cp * cy + sr * sp * sy,  # w
    )


class RadarTfTuner(Node):
    def __init__(self):
        super().__init__('radar_tf_tuner')
        self.declare_parameter('parent_frame', 'os_sensor')
        self.declare_parameter('child_frame', 'ti_radar')

        # Declaring a range makes rqt_reconfigure render a slider.
        ranges = {
            'x': (-2.0, 2.0), 'y': (-2.0, 2.0), 'z': (-2.0, 2.0),                # metres
            'roll': (-3.15, 3.15), 'pitch': (-3.15, 3.15), 'yaw': (-3.15, 3.15),  # radians
        }
        for name, (lo, hi) in ranges.items():
            desc = ParameterDescriptor(
                floating_point_range=[FloatingPointRange(from_value=lo, to_value=hi, step=0.001)])
            self.declare_parameter(name, 0.0, desc)

        self.br = TransformBroadcaster(self)
        self.add_on_set_parameters_callback(self.on_params)
        self.create_timer(0.05, self.publish)  # 20 Hz
        self.log_command({})

    def get(self, name):
        return self.get_parameter(name).value

    def publish(self):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = self.get('parent_frame')
        t.child_frame_id = self.get('child_frame')
        t.transform.translation.x = self.get('x')
        t.transform.translation.y = self.get('y')
        t.transform.translation.z = self.get('z')
        qx, qy, qz, qw = quat_from_euler(self.get('roll'), self.get('pitch'), self.get('yaw'))
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.br.sendTransform(t)

    def log_command(self, overrides):
        cur = {k: overrides.get(k, self.get(k)) for k in POSE_KEYS}
        parent = overrides.get('parent_frame', self.get('parent_frame'))
        child = overrides.get('child_frame', self.get('child_frame'))
        self.get_logger().info(
            'ros2 run tf2_ros static_transform_publisher '
            f"--x {cur['x']:.3f} --y {cur['y']:.3f} --z {cur['z']:.3f} "
            f"--roll {cur['roll']:.3f} --pitch {cur['pitch']:.3f} --yaw {cur['yaw']:.3f} "
            f'--frame-id {parent} --child-frame-id {child}')

    def on_params(self, params):
        # Called before the new values are stored, so pass them in explicitly.
        self.log_command({p.name: p.value for p in params})
        return SetParametersResult(successful=True)


def main():
    rclpy.init()
    node = RadarTfTuner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
