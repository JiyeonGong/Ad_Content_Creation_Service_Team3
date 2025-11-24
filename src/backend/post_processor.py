# post_processor.py
"""
이미지 후처리 파이프라인
- ADetailer: 손/얼굴 자동 감지 후 Inpaint로 재생성
- YOLO: 손/물체 감지 + 마스킹
- Inpaint: 문제 영역 재생성
"""
import io
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

# YOLO (ultralytics)
from ultralytics import YOLO

# MediaPipe (손/얼굴 감지)
import mediapipe as mp


@dataclass
class DetectionBox:
    """감지된 영역 정보"""
    x1: int
    y1: int
    x2: int
    y2: int
    label: str
    confidence: float

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def expand(self, ratio: float = 1.2) -> 'DetectionBox':
        """박스 크기 확장 (마진 추가)"""
        w_expand = int(self.width * (ratio - 1) / 2)
        h_expand = int(self.height * (ratio - 1) / 2)
        return DetectionBox(
            x1=max(0, self.x1 - w_expand),
            y1=max(0, self.y1 - h_expand),
            x2=self.x2 + w_expand,
            y2=self.y2 + h_expand,
            label=self.label,
            confidence=self.confidence
        )


class PostProcessor:
    """이미지 후처리 파이프라인"""

    def __init__(self, device: str = "cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"

        # YOLO 모델 (사람/물체 감지)
        self.yolo_model: Optional[YOLO] = None

        # MediaPipe (손/얼굴/포즈 상세 감지)
        self.mp_hands = mp.solutions.hands
        self.mp_face = mp.solutions.face_detection
        self.mp_pose = mp.solutions.pose
        self.hands_detector = None
        self.face_detector = None
        self.pose_detector = None

        print(f"✅ PostProcessor 초기화 (device: {self.device})")

    def _load_yolo(self):
        """YOLO 모델 로드 (지연 로딩)"""
        if self.yolo_model is None:
            print("📥 YOLO 모델 로딩 중...")
            # YOLOv8n (nano) - 가벼움, 사람 감지용
            self.yolo_model = YOLO("yolov8n.pt")
            print("✅ YOLO 모델 로드 완료")

    def _load_mediapipe(self):
        """MediaPipe 감지기 로드"""
        if self.hands_detector is None:
            self.hands_detector = self.mp_hands.Hands(
                static_image_mode=True,
                max_num_hands=4,
                min_detection_confidence=0.5
            )
        if self.face_detector is None:
            self.face_detector = self.mp_face.FaceDetection(
                model_selection=1,  # 0: 2m 이내, 1: 5m 이내
                min_detection_confidence=0.5
            )
        if self.pose_detector is None:
            self.pose_detector = self.mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,  # 0: lite, 1: full, 2: heavy
                min_detection_confidence=0.5
            )

    def detect_with_yolo(self, image: Image.Image) -> List[DetectionBox]:
        """YOLO로 사람/물체 감지"""
        self._load_yolo()

        # PIL → numpy
        img_np = np.array(image)

        # YOLO 추론
        results = self.yolo_model(img_np, verbose=False)

        detections = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                detections.append(DetectionBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    label=cls_name,
                    confidence=conf
                ))

        return detections

    def detect_hands(self, image: Image.Image) -> List[DetectionBox]:
        """MediaPipe로 손 감지"""
        self._load_mediapipe()

        img_np = np.array(image)
        img_rgb = img_np if img_np.shape[2] == 3 else img_np[:, :, :3]

        results = self.hands_detector.process(img_rgb)

        detections = []
        h, w = img_rgb.shape[:2]

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # 모든 랜드마크에서 바운딩 박스 계산
                x_coords = [lm.x * w for lm in hand_landmarks.landmark]
                y_coords = [lm.y * h for lm in hand_landmarks.landmark]

                x1, x2 = int(min(x_coords)), int(max(x_coords))
                y1, y2 = int(min(y_coords)), int(max(y_coords))

                detections.append(DetectionBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    label="hand",
                    confidence=0.9
                ))

        return detections

    def _calculate_angle(self, p1, p2, p3) -> float:
        """
        세 점으로 각도 계산 (p2가 꼭지점)
        Returns: 각도 (degrees, 0-180)
        """
        import math
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])

        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)

        if mag1 * mag2 == 0:
            return 180.0

        cos_angle = max(-1, min(1, dot / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    def _check_finger_joint_angles(self, hand_landmarks, w: int, h: int) -> Dict[str, Any]:
        """
        손가락 관절 각도 검증
        - 비정상적으로 꺾인 관절 감지
        - 엄지 길이 비율 검증

        Returns: {"is_valid": bool, "issues": [...]}
        """
        import math
        issues = []

        # MediaPipe Hand Landmarks:
        # 0: WRIST
        # 1-4: THUMB (CMC, MCP, IP, TIP)
        # 5-8: INDEX (MCP, PIP, DIP, TIP)
        # 9-12: MIDDLE
        # 13-16: RING
        # 17-20: PINKY

        def get_point(idx):
            lm = hand_landmarks.landmark[idx]
            return (lm.x * w, lm.y * h)

        # 1. 손가락 관절 각도 검증 (PIP, DIP 관절)
        # 정상 범위: 0° (펴짐) ~ 120° (굽힘)
        # 역방향 굽힘 (과신전): > 180° 또는 음의 각도
        finger_joints = {
            "index": [(5, 6, 7), (6, 7, 8)],   # MCP-PIP-DIP, PIP-DIP-TIP
            "middle": [(9, 10, 11), (10, 11, 12)],
            "ring": [(13, 14, 15), (14, 15, 16)],
            "pinky": [(17, 18, 19), (18, 19, 20)]
        }

        for finger_name, joints in finger_joints.items():
            for joint_indices in joints:
                p1 = get_point(joint_indices[0])
                p2 = get_point(joint_indices[1])
                p3 = get_point(joint_indices[2])

                angle = self._calculate_angle(p1, p2, p3)

                # 관절이 역방향으로 꺾인 경우 (과신전, angle < 160도인데 손가락이 반대로)
                # 또는 너무 심하게 꺾인 경우 (angle < 30도)
                if angle < 30:
                    issues.append(f"{finger_name} 관절 과도하게 꺾임 ({angle:.0f}°)")

        # 2. 엄지 검증
        # 엄지 길이 비율: TIP-IP / IP-MCP 가 너무 크면 비정상
        thumb_tip = get_point(4)
        thumb_ip = get_point(3)
        thumb_mcp = get_point(2)

        tip_to_ip = math.sqrt((thumb_tip[0]-thumb_ip[0])**2 + (thumb_tip[1]-thumb_ip[1])**2)
        ip_to_mcp = math.sqrt((thumb_ip[0]-thumb_mcp[0])**2 + (thumb_ip[1]-thumb_mcp[1])**2)

        if ip_to_mcp > 0:
            thumb_ratio = tip_to_ip / ip_to_mcp
            # 정상 범위: 0.5 ~ 1.5
            if thumb_ratio > 2.0:
                issues.append(f"엄지 끝마디 비정상적으로 김 (비율: {thumb_ratio:.1f})")
            elif thumb_ratio < 0.3:
                issues.append(f"엄지 끝마디 비정상적으로 짧음 (비율: {thumb_ratio:.1f})")

        # 3. 엄지 관절 각도 (CMC-MCP-IP, MCP-IP-TIP)
        thumb_cmc = get_point(1)
        thumb_angle1 = self._calculate_angle(thumb_cmc, thumb_mcp, thumb_ip)
        thumb_angle2 = self._calculate_angle(thumb_mcp, thumb_ip, thumb_tip)

        if thumb_angle1 < 30:
            issues.append(f"엄지 MCP 관절 비정상 ({thumb_angle1:.0f}°)")
        if thumb_angle2 < 30:
            issues.append(f"엄지 IP 관절 비정상 ({thumb_angle2:.0f}°)")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues
        }

    def count_fingers(self, image: Image.Image) -> Dict[str, Any]:
        """
        MediaPipe로 손가락 개수 및 관절 이상 체크
        Returns: {"hands": [{"fingers": int, "box": DetectionBox, "joint_issues": [...]}, ...], ...}
        """
        self._load_mediapipe()

        img_np = np.array(image)
        img_rgb = img_np if img_np.shape[2] == 3 else img_np[:, :, :3]

        results = self.hands_detector.process(img_rgb)

        hands_info = []
        h, w = img_rgb.shape[:2]

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # 손가락 펴짐 감지 (간단한 방법)
                # 각 손가락 끝(tip)이 해당 손가락 PIP 관절보다 위에 있으면 펴진 것
                finger_tips = [4, 8, 12, 16, 20]  # 엄지, 검지, 중지, 약지, 소지 끝
                finger_pips = [3, 6, 10, 14, 18]  # 각 손가락 PIP 관절

                fingers_up = 0
                for tip, pip in zip(finger_tips, finger_pips):
                    tip_y = hand_landmarks.landmark[tip].y
                    pip_y = hand_landmarks.landmark[pip].y
                    # 엄지는 x좌표로 비교 (좌우 방향)
                    if tip == 4:
                        tip_x = hand_landmarks.landmark[tip].x
                        pip_x = hand_landmarks.landmark[pip].x
                        if abs(tip_x - pip_x) > 0.05:  # 엄지가 펴짐
                            fingers_up += 1
                    else:
                        if tip_y < pip_y:  # 손가락이 펴짐
                            fingers_up += 1

                # 관절 각도 검증
                joint_check = self._check_finger_joint_angles(hand_landmarks, w, h)

                # 바운딩 박스
                x_coords = [lm.x * w for lm in hand_landmarks.landmark]
                y_coords = [lm.y * h for lm in hand_landmarks.landmark]
                x1, x2 = int(min(x_coords)), int(max(x_coords))
                y1, y2 = int(min(y_coords)), int(max(y_coords))

                hands_info.append({
                    "fingers": fingers_up,
                    "box": DetectionBox(x1=x1, y1=y1, x2=x2, y2=y2, label="hand", confidence=0.9),
                    "joint_issues": joint_check["issues"],
                    "has_joint_anomaly": not joint_check["is_valid"]
                })

        return {
            "hands": hands_info,
            "hand_count": len(hands_info)
        }

    def detect_faces(self, image: Image.Image) -> List[DetectionBox]:
        """MediaPipe로 얼굴 감지"""
        self._load_mediapipe()

        img_np = np.array(image)
        img_rgb = img_np if img_np.shape[2] == 3 else img_np[:, :, :3]

        results = self.face_detector.process(img_rgb)

        detections = []
        h, w = img_rgb.shape[:2]

        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x1 = int(bbox.xmin * w)
                y1 = int(bbox.ymin * h)
                x2 = int((bbox.xmin + bbox.width) * w)
                y2 = int((bbox.ymin + bbox.height) * h)

                detections.append(DetectionBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    label="face",
                    confidence=detection.score[0]
                ))

        return detections

    def detect_body_object_penetration(
        self,
        image: Image.Image,
        target_objects: List[str] = ["sports ball", "baseball bat", "tennis racket"]
    ) -> Dict[str, Any]:
        """
        MediaPipe Pose + YOLO로 물체가 신체를 관통하는 이상 감지

        바벨/운동기구가 다리나 몸을 뚫고 지나가는 것처럼 보이는 경우 감지

        Args:
            image: 입력 이미지
            target_objects: 관통 체크할 물체 목록 (YOLO 클래스명)

        Returns:
            {"has_penetration": bool, "issues": [...], "affected_boxes": [...]}
        """
        self._load_mediapipe()
        self._load_yolo()

        img_np = np.array(image)
        img_rgb = img_np if img_np.shape[2] == 3 else img_np[:, :, :3]
        h, w = img_rgb.shape[:2]

        issues = []
        affected_boxes = []

        # 1. YOLO로 물체 감지 (바벨 바는 "sports ball" 또는 직접 감지 안 될 수 있음)
        yolo_boxes = self.detect_with_yolo(image)

        # 바벨/바 형태 물체 찾기 (가로로 긴 물체)
        bar_like_objects = []
        for box in yolo_boxes:
            aspect_ratio = box.width / max(box.height, 1)
            # 가로로 긴 물체 (aspect ratio > 3) 또는 특정 운동기구
            if aspect_ratio > 3 or box.label in target_objects:
                bar_like_objects.append(box)

        if not bar_like_objects:
            return {"has_penetration": False, "issues": [], "affected_boxes": []}

        # 2. MediaPipe Pose로 신체 키포인트 감지
        pose_results = self.pose_detector.process(img_rgb)

        if not pose_results.pose_landmarks:
            return {"has_penetration": False, "issues": [], "affected_boxes": []}

        landmarks = pose_results.pose_landmarks.landmark

        # 다리 영역 세그먼트 계산
        leg_segments = []

        # 왼쪽 다리
        if landmarks[23].visibility > 0.5 and landmarks[27].visibility > 0.5:
            left_hip = (int(landmarks[23].x * w), int(landmarks[23].y * h))
            left_knee = (int(landmarks[25].x * w), int(landmarks[25].y * h))
            left_ankle = (int(landmarks[27].x * w), int(landmarks[27].y * h))
            leg_segments.append(("left_thigh", left_hip, left_knee))
            leg_segments.append(("left_shin", left_knee, left_ankle))

        # 오른쪽 다리
        if landmarks[24].visibility > 0.5 and landmarks[28].visibility > 0.5:
            right_hip = (int(landmarks[24].x * w), int(landmarks[24].y * h))
            right_knee = (int(landmarks[26].x * w), int(landmarks[26].y * h))
            right_ankle = (int(landmarks[28].x * w), int(landmarks[28].y * h))
            leg_segments.append(("right_thigh", right_hip, right_knee))
            leg_segments.append(("right_shin", right_knee, right_ankle))

        # 3. 바 형태 물체가 다리 세그먼트를 관통하는지 체크
        for bar_box in bar_like_objects:
            bar_y_center = (bar_box.y1 + bar_box.y2) // 2
            bar_x_left = bar_box.x1
            bar_x_right = bar_box.x2

            for seg_name, seg_start, seg_end in leg_segments:
                # 세그먼트의 x 범위
                seg_x_min = min(seg_start[0], seg_end[0])
                seg_x_max = max(seg_start[0], seg_end[0])
                # 세그먼트의 y 범위
                seg_y_min = min(seg_start[1], seg_end[1])
                seg_y_max = max(seg_start[1], seg_end[1])

                # 바가 세그먼트의 x 범위를 가로지르는지
                if bar_x_left < seg_x_max and bar_x_right > seg_x_min:
                    # 바의 y 위치가 세그먼트 내에 있는지
                    if seg_y_min < bar_y_center < seg_y_max:
                        # 관통 비율 계산
                        penetration_ratio = (bar_y_center - seg_y_min) / max(seg_y_max - seg_y_min, 1)

                        # 10%~90% 위치에서 교차하면 관통으로 판단 (끝부분 제외)
                        if 0.1 < penetration_ratio < 0.9:
                            issues.append(f"물체가 {seg_name}을 관통 (교차율: {penetration_ratio:.1%})")
                            affected_boxes.append(bar_box)

        # 중복 제거
        unique_issues = list(set(issues))

        return {
            "has_penetration": len(unique_issues) > 0,
            "issues": unique_issues,
            "affected_boxes": affected_boxes
        }

    def create_mask_from_boxes(
        self,
        image_size: Tuple[int, int],
        boxes: List[DetectionBox],
        expand_ratio: float = 1.3,
        feather: int = 10
    ) -> Image.Image:
        """감지된 박스들로부터 마스크 생성"""
        w, h = image_size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)

        for box in boxes:
            expanded = box.expand(expand_ratio)
            # 이미지 범위 내로 클리핑
            x1 = max(0, expanded.x1)
            y1 = max(0, expanded.y1)
            x2 = min(w, expanded.x2)
            y2 = min(h, expanded.y2)
            draw.rectangle([x1, y1, x2, y2], fill=255)

        # 마스크 가장자리 부드럽게
        if feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(feather))

        return mask

    def adetailer_process(
        self,
        image: Image.Image,
        inpaint_pipeline,
        prompt: str,
        targets: List[str] = ["hand", "face"],
        strength: float = 0.4,
        steps: int = 20
    ) -> Image.Image:
        """
        ADetailer 스타일 후처리
        - 손/얼굴 감지 → 해당 영역 Inpaint로 재생성

        Args:
            image: 원본 이미지
            inpaint_pipeline: Flux/SD Inpaint 파이프라인
            prompt: 재생성용 프롬프트
            targets: 감지 대상 ["hand", "face"]
            strength: Inpaint 강도 (0.3-0.5 권장)
            steps: 추론 스텝
        """
        result_image = image.copy()

        all_boxes = []

        # 타겟별 감지
        if "hand" in targets:
            hand_boxes = self.detect_hands(image)
            all_boxes.extend(hand_boxes)
            print(f"  🖐️ 손 감지: {len(hand_boxes)}개")

        if "face" in targets:
            face_boxes = self.detect_faces(image)
            all_boxes.extend(face_boxes)
            print(f"  👤 얼굴 감지: {len(face_boxes)}개")

        if not all_boxes:
            print("  ℹ️ 감지된 영역 없음 - 원본 반환")
            return result_image

        # 마스크 생성
        mask = self.create_mask_from_boxes(
            image.size,
            all_boxes,
            expand_ratio=1.3,
            feather=15
        )

        # Inpaint 실행
        print(f"  🎨 Inpaint 실행 중 (strength={strength}, steps={steps})...")

        # Flux Inpaint 호출
        inpaint_result = inpaint_pipeline(
            prompt=prompt,
            image=result_image,
            mask_image=mask,
            strength=strength,
            num_inference_steps=steps,
            guidance_scale=3.5
        )

        result_image = inpaint_result.images[0]
        print("  ✅ ADetailer 처리 완료")

        return result_image

    def detect_anomalies(
        self,
        image: Image.Image,
        check_hands: bool = True,
        check_overlap: bool = True,
        check_penetration: bool = True,
        fingers_per_hand: int = 5,
        min_fingers_allowed: int = 4
    ) -> Dict[str, Any]:
        """
        이미지 이상 감지
        - 손가락 개수 이상
        - 물체 겹침
        - 물체-신체 관통 (바벨이 다리를 뚫는 등)

        Args:
            fingers_per_hand: 손당 손가락 개수 (기본 5)
            min_fingers_allowed: 최소 허용 손가락 (그립에서 엄지 가려짐 허용, 기본 4)
            check_penetration: 물체-신체 관통 체크 여부

        Returns:
            {"has_anomaly": bool, "anomalies": [...], "boxes": [...]}
        """
        anomalies = []
        boxes = []

        if check_hands:
            finger_info = self.count_fingers(image)

            if finger_info["hand_count"] > 0:
                for i, hand in enumerate(finger_info["hands"]):
                    boxes.append(hand["box"])
                    # 손가락 개수 이상 (min_fingers_allowed ~ fingers_per_hand 범위는 정상)
                    finger_count = hand["fingers"]
                    if finger_count < min_fingers_allowed or finger_count > fingers_per_hand:
                        anomalies.append(f"손 {i+1}: 손가락 {finger_count}개 ({min_fingers_allowed}~{fingers_per_hand}개 범위 벗어남)")
                    # 관절 이상 (엄지 길이, 역방향 꺾임 등)
                    if hand.get("has_joint_anomaly") and hand.get("joint_issues"):
                        for issue in hand["joint_issues"]:
                            anomalies.append(f"손 {i+1}: {issue}")

            # 손이 너무 많은 경우
            if finger_info["hand_count"] > 4:
                anomalies.append(f"손이 너무 많음: {finger_info['hand_count']}개")

        if check_overlap:
            # YOLO로 사람/물체 감지
            yolo_boxes = self.detect_with_yolo(image)
            person_boxes = [b for b in yolo_boxes if b.label == "person"]
            object_boxes = [b for b in yolo_boxes if b.label != "person"]

            # 사람-물체 겹침 체크 (간단한 IoU)
            for person in person_boxes:
                for obj in object_boxes:
                    iou = self._calculate_iou(person, obj)
                    if iou > 0.5:  # 50% 이상 겹침
                        anomalies.append(f"사람-{obj.label} 과도한 겹침 (IoU={iou:.2f})")

        # 물체-신체 관통 체크
        if check_penetration:
            penetration_result = self.detect_body_object_penetration(image)
            if penetration_result["has_penetration"]:
                anomalies.extend(penetration_result["issues"])
                boxes.extend(penetration_result["affected_boxes"])

        return {
            "has_anomaly": len(anomalies) > 0,
            "anomalies": anomalies,
            "boxes": boxes
        }

    def _calculate_iou(self, box1: DetectionBox, box2: DetectionBox) -> float:
        """두 박스의 IoU (Intersection over Union) 계산"""
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = box1.width * box1.height
        area2 = box2.width * box2.height
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def full_pipeline(
        self,
        image: Image.Image,
        inpaint_pipeline,
        prompt: str,
        auto_detect: bool = True,
        force_adetailer: bool = False,
        adetailer_targets: List[str] = ["hand"],
        adetailer_strength: float = 0.4,
        fingers_per_hand: int = 5,
        min_fingers_allowed: int = 4,
        check_penetration: bool = True
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        전체 후처리 파이프라인

        Args:
            image: 원본 이미지
            inpaint_pipeline: Inpaint 파이프라인
            prompt: 프롬프트
            auto_detect: True면 이상 감지 후 필요시만 처리
            force_adetailer: True면 무조건 ADetailer 실행
            adetailer_targets: ADetailer 타겟 ["hand", "face"]
            adetailer_strength: Inpaint 강도
            fingers_per_hand: 손당 손가락 개수 (기본 5)
            min_fingers_allowed: 최소 허용 손가락 (기본 4, 그립에서 엄지 가려짐 허용)
            check_penetration: 물체-신체 관통 체크 여부 (기본 True)

        Returns:
            (처리된 이미지, 처리 정보)
        """
        info = {
            "original_size": image.size,
            "processed": False,
            "anomalies_detected": [],
            "adetailer_applied": False
        }

        result = image

        # 1. 이상 감지 (auto_detect일 때)
        if auto_detect and not force_adetailer:
            print("🔍 이상 감지 중...")
            anomaly_result = self.detect_anomalies(
                image,
                fingers_per_hand=fingers_per_hand,
                min_fingers_allowed=min_fingers_allowed,
                check_penetration=check_penetration
            )
            info["anomalies_detected"] = anomaly_result["anomalies"]

            if anomaly_result["has_anomaly"]:
                print(f"  ⚠️ 이상 감지됨: {anomaly_result['anomalies']}")
                force_adetailer = True
            else:
                print("  ✅ 이상 없음")

        # 2. ADetailer 실행
        if force_adetailer:
            print("🖌️ ADetailer 처리 시작...")
            result = self.adetailer_process(
                image=result,
                inpaint_pipeline=inpaint_pipeline,
                prompt=prompt,
                targets=adetailer_targets,
                strength=adetailer_strength
            )
            info["adetailer_applied"] = True
            info["processed"] = True

        return result, info

    def cleanup(self):
        """리소스 정리"""
        if self.hands_detector:
            self.hands_detector.close()
            self.hands_detector = None
        if self.face_detector:
            self.face_detector.close()
            self.face_detector = None
        if self.pose_detector:
            self.pose_detector.close()
            self.pose_detector = None
        if self.yolo_model:
            del self.yolo_model
            self.yolo_model = None

        torch.cuda.empty_cache()
        print("🧹 PostProcessor 리소스 정리 완료")


# 싱글톤 인스턴스
_post_processor: Optional[PostProcessor] = None

def get_post_processor() -> PostProcessor:
    """PostProcessor 싱글톤 인스턴스"""
    global _post_processor
    if _post_processor is None:
        _post_processor = PostProcessor()
    return _post_processor
