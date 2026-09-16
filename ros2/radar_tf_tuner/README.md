# radar_tf_tuner

RViz에서 레이더 포인트(`ti_radar`)와 라이다 포인트(`os_sensor`)를 겹쳐 보면서
두 프레임 사이의 TF를 실시간으로 조정하는 ROS 2 노드입니다.

`static_transform_publisher`는 값을 바꿀 때마다 재실행해야 하지만, 이 노드는
x, y, z, roll, pitch, yaw를 ROS 파라미터로 받아 20 Hz로 TF를 내보내므로
`rqt_reconfigure` 슬라이더로 움직이면서 RViz에서 바로 결과를 볼 수 있습니다.

## 배경: RViz에서 "Could not transform from [ti_radar] to [os_sensor]"

RadarPoints 디스플레이가 `Status: Error`이고 위 메시지가 나오면 TF 트리에
`ti_radar`와 `os_sensor`를 잇는 변환이 없는 것입니다. 진단은 다음과 같이 합니다.

```bash
ros2 topic echo <레이더 토픽> --field header.frame_id   # 실제 frame_id 확인
ros2 run tf2_tools view_frames                        # frames.pdf 로 TF 트리 확인
ros2 run tf2_ros tf2_echo os_sensor ti_radar          # 두 프레임 사이 변환 가능 여부
```

`tf2_echo`에서 "frame does not exist" 또는 "not connected"가 나오면 TF 연결이
없는 것이고, "extrapolation"이 나오면 타임스탬프(`use_sim_time`, 시간 동기화) 문제입니다.

## 요구 사항

- ROS 2 (Humble 이상 권장)
- `rqt_reconfigure` (`sudo apt install ros-$ROS_DISTRO-rqt-reconfigure`)

## 실행 방법

1. 기존에 띄워 둔 `static_transform_publisher`(os_sensor → ti_radar)는 종료합니다.
   같은 프레임을 두 곳에서 publish하면 충돌합니다.

2. 튜닝 노드를 실행합니다.

   ```bash
   python3 radar_tf_tuner.py
   ```

   프레임 이름이 다르면 파라미터로 넘깁니다.

   ```bash
   python3 radar_tf_tuner.py --ros-args -p parent_frame:=os_sensor -p child_frame:=ti_radar
   ```

3. 다른 터미널에서 슬라이더 UI를 띄웁니다.

   ```bash
   ros2 run rqt_reconfigure rqt_reconfigure
   ```

   왼쪽 목록에서 `radar_tf_tuner`를 선택하면 x, y, z, roll, pitch, yaw 슬라이더가
   나옵니다. `os_sensor` 기준으로 x는 앞뒤, y는 좌우, z는 위아래(m), yaw는 수평 회전(rad)입니다.
   슬라이더를 움직이면 RViz의 레이더 포인트가 바로 따라 움직입니다.

   GUI 없이 터미널에서 바꾸려면:

   ```bash
   ros2 param set /radar_tf_tuner y 0.15
   ros2 param set /radar_tf_tuner yaw 0.05
   ```

4. 값이 맞으면 저장합니다. 파라미터가 바뀔 때마다 노드 로그에 완성된
   `static_transform_publisher` 명령이 출력되므로 마지막 줄을 launch 파일이나
   URDF에 옮기면 됩니다. YAML로 남기려면:

   ```bash
   ros2 param dump /radar_tf_tuner > radar_tf.yaml
   ```

## 매칭 팁

- RViz에서 레이더 포인트는 Size를 0.1 정도로 키우고 라이다와 다른 색으로 두면 겹침이 잘 보입니다.
- 벽 모서리, 코너 리플렉터, 기둥처럼 두 센서 모두에서 뚜렷한 물체를 기준으로 맞춥니다.
- 순서는 yaw → x, y → z, pitch 순이 빠릅니다. 레이더는 z 정밀도가 낮으므로 수평면 위주로 맞춰도 충분한 경우가 많습니다.
- ROS 1이라면 같은 구조를 `dynamic_reconfigure` + `rqt_reconfigure`로 만들면 됩니다.
