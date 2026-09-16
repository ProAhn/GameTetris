#!/usr/bin/env python3
"""Interactive TF tuner for aligning a radar frame to a lidar frame in RViz.

Publishes the parent_frame -> child_frame transform as a *static* transform
(/tf_static, latched) from six ROS 2 parameters (x, y, z, roll, pitch, yaw).
Using a static transform matches the behaviour of
`ros2 run tf2_ros static_transform_publisher`: tf2 treats it as valid for all
time, so it works even when the radar messages carry a timestamp of 0 or a
clock that differs from this machine. Every parameter change re-sends the
static transform, which overwrites the previous value in every tf2 buffer.

Adjust the parameters live with rqt_reconfigure sliders or `ros2 param set`,
and copy the equivalent static_transform_publisher command from the log once
the point clouds line up.
"""
import math

import rclpy
from geometry_msgs.msg import TransformStamped
from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from tf2_ros import StaticTransformBroadcaster

POSE_KEYS = ('x', 'y', 'z', 'roll', 'pitch', 'yaw')
FRAME_KEYS = ('parent_frame', 'child_frame')


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

        self.br = StaticTransformBroadcaster(self)
        self.add_on_set_parameters_callback(self.on_params)
        # Re-send once per second so a late-started RViz or a restarted tf2
        # buffer always picks the transform up.
        self.create_timer(1.0, lambda: self.publish({}))
        self.publish({})

    def current(self, overrides):
        """Current parameter values with `overrides` (not yet stored) applied."""
        return {k: overrides.get(k, self.get_parameter(k).value) for k in POSE_KEYS + FRAME_KEYS}

    def publish(self, overrides):
        v = self.current(overrides)
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = v['parent_frame']
        t.child_frame_id = v['child_frame']
        t.transform.translation.x = v['x']
        t.transform.translation.y = v['y']
        t.transform.translation.z = v['z']
        qx, qy, qz, qw = quat_from_euler(v['roll'], v['pitch'], v['yaw'])
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.br.sendTransform(t)

    def log_command(self, overrides):
        v = self.current(overrides)
        self.get_logger().info(
            'ros2 run tf2_ros static_transform_publisher '
            f"--x {v['x']:.3f} --y {v['y']:.3f} --z {v['z']:.3f} "
            f"--roll {v['roll']:.3f} --pitch {v['pitch']:.3f} --yaw {v['yaw']:.3f} "
            f"--frame-id {v['parent_frame']} --child-frame-id {v['child_frame']}")

    def on_params(self, params):
        # Called before the new values are stored, so pass them in explicitly
        # and push the updated static transform immediately.
        overrides = {p.name: p.value for p in params}
        self.publish(overrides)
        self.log_command(overrides)
        return SetParametersResult(successful=True)


def main():
    rclpy.init()
    node = RadarTfTuner()
    node.log_command({})
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
