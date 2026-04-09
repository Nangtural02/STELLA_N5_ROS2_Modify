# stella_uwb_qm

Qorvo QM UWB 장비에서 TCP(이더넷)로 레인징 데이터를 수신하여 ROS2 토픽으로 퍼블리시하는 노드.

## 배경

- QM 장비가 2대 존재: 하나는 **라즈베리파이 기반**(이더넷/TCP), 하나는 **nRF 기반**(다른 transport)
- 이 패키지는 라즈베리파이 QM의 TCP 수신을 담당
- 기존 `stella_uwb`(DWM3001CDK, UART)와는 독립적으로 동작
- 두 UWB 장비를 동시에 돌려 데이터를 비교·저장하는 것이 목표
- transport 확장을 고려하여 `tcp_reader`를 별도 모듈로 분리

## 데이터 소스

- **TCP 서버**: 192.168.5.2:5000 (QM 라즈베리파이)
- **포맷**: 줄바꿈 구분 JSON, ~5Hz (200ms 간격)
- **샘플**:
```json
{"timestamp": 1775725916.29, "sequence": 1053, "status": "Ok", "distance_cm": 172.0, "aoa_azimuth": -52.88, "aoa_elevation": 4.28, "aoa_azimuth_fom": 0.0, "aoa_elevation_fom": 0.0, "mac": "00:01"}
```

## 토픽

| 토픽 | 메시지 타입 | 설명 |
|------|------------|------|
| `uwb/qm_data` | `stella_uwb_msgs/UwbData` | QM UWB 레인징 데이터 |

네임스페이스 적용 시 `/{ns}/uwb/qm_data`로 퍼블리시됨.

## 실행

```bash
# 단독 실행
ros2 run stella_uwb_qm uwb_publisher --config <config_path>

# launch 파일
ros2 launch stella_uwb_qm stella_uwb_qm.launch.py

# robot.launch.py에서 launch_uwb_qm: true 로 활성화
```

## 설정

`config/uwb_config.yaml`:
```yaml
frame_id: "uwb_link"
tcp:
  host: "192.168.5.2"
  port: 5000
```

## UwbData.msg 필드 매핑

| JSON 필드 | UwbData 필드 | 변환 |
|-----------|-------------|------|
| `mac` | `anchor_id` | "00:01" → "0x0001" |
| `distance_cm` | `distance` | cm → m |
| `status` | `status` | "Ok" → 0, 그 외 → 255 |
| `aoa_azimuth` | `aoa_azimuth` | 그대로 (deg) |
| `aoa_elevation` | `aoa_elevation` | 그대로 (deg) |
| `aoa_azimuth_fom` | `aoa_azimuth_fom` | 그대로 (%) |
| `aoa_elevation_fom` | `aoa_elevation_fom` | 그대로 (%) |
| — | `rssi`, `pdr`, `cir` | 기본값 (TCP 소스에 없음) |
