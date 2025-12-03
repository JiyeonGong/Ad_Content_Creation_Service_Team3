# comfyui_client.py
"""
ComfyUI API 클라이언트
백그라운드에서 실행 중인 ComfyUI와 통신
"""
import os
import json
import time
import base64
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """ComfyUI API 클라이언트"""

    def __init__(self, base_url: str = "http://localhost:8188", timeout: int = 600):
        """
        Args:
            base_url: ComfyUI 서버 주소
            timeout: API 호출 타임아웃 (초)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def check_connection(self) -> bool:
        """ComfyUI 서버 연결 확인"""
        try:
            response = self.session.get(
                f"{self.base_url}/system_stats",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"⚠️ ComfyUI 연결 실패: {e}")
            return False

    def upload_image(self, image_bytes: bytes, filename: str = "input.png") -> str:
        """
        ComfyUI에 이미지 업로드

        Args:
            image_bytes: 이미지 바이트 데이터
            filename: 파일명

        Returns:
            업로드된 이미지 이름
        """
        try:
            logger.info(f"📤 이미지 업로드 중... (크기: {len(image_bytes)/1024:.1f}KB)")

            files = {
                "image": (filename, BytesIO(image_bytes), "image/png")
            }

            response = self.session.post(
                f"{self.base_url}/upload/image",
                files=files,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                uploaded_name = result.get("name", filename)
                logger.info(f"✅ 이미지 업로드 완료: {uploaded_name}")
                return uploaded_name
            else:
                raise Exception(f"업로드 실패: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"❌ 이미지 업로드 오류: {e}")
            raise

    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """
        워크플로우를 큐에 추가

        Args:
            workflow: ComfyUI 워크플로우 JSON

        Returns:
            prompt_id (작업 ID)
        """
        try:
            payload = {"prompt": workflow}

            response = self.session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id")
                logger.info(f"✅ 워크플로우 큐 등록: {prompt_id}")
                return prompt_id
            else:
                raise Exception(f"큐 등록 실패: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"❌ 워크플로우 큐 등록 오류: {e}")
            raise

    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        작업 히스토리 조회

        Args:
            prompt_id: 작업 ID

        Returns:
            히스토리 데이터 또는 None
        """
        try:
            response = self.session.get(
                f"{self.base_url}/history/{prompt_id}",
                timeout=30  # 10초 → 30초로 증가 (히스토리 생성 대기)
            )

            if response.status_code == 200:
                history = response.json()
                return history.get(prompt_id)
            else:
                return None

        except Exception as e:
            logger.warning(f"⚠️ 히스토리 조회 오류: {e}")
            return None

    def get_queue_status(self) -> Dict[str, Any]:
        """현재 큐 상태 및 진행 중인 작업 조회"""
        try:
            response = self.session.get(
                f"{self.base_url}/queue",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}

    def wait_for_completion(
        self,
        prompt_id: str,
        check_interval: int = 2,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        작업 완료 대기 (진행상황 추적)

        Args:
            prompt_id: 작업 ID
            check_interval: 확인 간격 (초)
            progress_callback: 진행상황 콜백 함수 (current_step, total_steps, step_name, node_id)

        Returns:
            완료된 작업 히스토리
        """
        logger.info(f"⏳ 작업 시작 (ID: {prompt_id})")

        start_time = time.time()
        last_progress = None
        was_in_queue = False  # 큐에 들어갔었는지 추적
        completed_nodes = set()  # 완료된 노드 추적

        while True:
            # 타임아웃 체크
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise TimeoutError(f"작업 타임아웃 ({self.timeout}초 초과)")

            # 큐 상태 조회 (진행 중인 작업의 progress 정보)
            queue_info = self.get_queue_status()
            queue_running = queue_info.get("queue_running", [])
            queue_pending = queue_info.get("queue_pending", [])

            # 현재 작업이 큐에 있는지 확인
            in_queue = False
            for item in queue_running:
                if item[1] == prompt_id:
                    in_queue = True
                    was_in_queue = True
                    break

            if not in_queue:
                for item in queue_pending:
                    if item[1] == prompt_id:
                        in_queue = True
                        was_in_queue = True
                        break

            # 히스토리 확인
            history = self.get_history(prompt_id)

            if history is not None:
                # 작업 완료 확인
                status = history.get("status", {})

                if status.get("completed", False):
                    logger.info(f"✅ 작업 완료! (소요 시간: {elapsed:.1f}초)")
                    return history

                # 에러 확인
                if "error" in status:
                    error_msg = status.get("error", "Unknown error")
                    raise Exception(f"ComfyUI 작업 실패: {error_msg}")

                # 진행상황 추적 (완료된 노드 확인)
                if progress_callback:
                    outputs = history.get("outputs", {})
                    for node_id in outputs.keys():
                        if node_id not in completed_nodes:
                            completed_nodes.add(node_id)
                            # 콜백 호출
                            try:
                                progress_callback(node_id=node_id, elapsed=elapsed)
                            except Exception as e:
                                logger.warning(f"⚠️ Progress callback 오류: {e}")
            else:
                # 큐에서 사라진 후 히스토리 생성까지 최대 10초 대기
                # 히스토리가 없는데 큐에도 없으면 → 히스토리 생성 대기 중일 수 있다
                if was_in_queue and not in_queue:
                    if elapsed > 15:  # 5초 → 15초로 증가
                        raise Exception(
                            f"워크플로우가 큐에서 사라졌지만 히스토리가 없습니다. "
                            f"워크플로우 validation 에러 가능성이 높습니다. "
                            f"ComfyUI 로그를 확인하세요."
                        )
                    # 아직 대기 시간이 남았으면 경고 로그만 출력
                    if elapsed > 5 and elapsed % 5 < check_interval:  # 5초마다 한 번씩 출력
                        logger.warning(f"⚠️ 큐에서 사라졌으나 히스토리 대기 중... ({elapsed:.1f}초 경과)")

            # 대기
            time.sleep(check_interval)

    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """
        ComfyUI에서 생성된 이미지 다운로드

        Args:
            filename: 파일명
            subfolder: 서브폴더
            folder_type: 폴더 타입 (output, input, temp)

        Returns:
            이미지 바이트 데이터
        """
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }

            response = self.session.get(
                f"{self.base_url}/view",
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"✅ 이미지 다운로드 완료: {filename}")
                return response.content
            else:
                raise Exception(f"다운로드 실패: {response.status_code}")

        except Exception as e:
            logger.error(f"❌ 이미지 다운로드 오류: {e}")
            raise

    def extract_output_images(self, history: Dict[str, Any]) -> list[bytes]:
        """
        히스토리에서 출력 이미지 추출

        Args:
            history: 작업 히스토리

        Returns:
            이미지 바이트 리스트
        """
        images = []

        try:
            outputs = history.get("outputs", {})
            logger.info(f"📥 출력 이미지 다운로드 중... ({len(outputs)}개 노드)")

            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        filename = img_info.get("filename")
                        subfolder = img_info.get("subfolder", "")
                        folder_type = img_info.get("type", "output")

                        if filename:
                            img_bytes = self.get_image(filename, subfolder, folder_type)
                            images.append(img_bytes)
                            logger.info(f"   ✓ {filename} ({len(img_bytes)/1024:.1f}KB)")

            logger.info(f"✅ 출력 이미지 {len(images)}개 추출 완료")
            return images

        except Exception as e:
            logger.error(f"❌ 이미지 추출 오류: {e}")
            raise

    def execute_workflow(
        self,
        workflow: Dict[str, Any],
        input_image: Optional[bytes] = None,
        input_image_node_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Tuple[list[bytes], Dict[str, Any]]:
        """
        워크플로우 실행 (전체 파이프라인)

        Args:
            workflow: ComfyUI 워크플로우 JSON
            input_image: 입력 이미지 (선택)
            input_image_node_id: 입력 이미지가 들어갈 노드 ID (선택)
            progress_callback: 진행상황 콜백 함수 (선택)

        Returns:
            (출력 이미지 리스트, 히스토리)
        """
        # 1. 연결 확인
        if not self.check_connection():
            raise ConnectionError("ComfyUI 서버에 연결할 수 없습니다. ComfyUI가 실행 중인지 확인하세요.")

        # 2. 입력 이미지 업로드 (필요 시)
        if input_image and input_image_node_id:
            uploaded_name = self.upload_image(input_image)

            # 워크플로우에 업로드된 이미지 이름 설정
            if input_image_node_id in workflow:
                workflow[input_image_node_id]["inputs"]["image"] = uploaded_name

        # 3. 워크플로우 큐 등록
        prompt_id = self.queue_prompt(workflow)

        # 4. 완료 대기 (진행상황 추적)
        history = self.wait_for_completion(prompt_id, progress_callback=progress_callback)

        # 5. 출력 이미지 추출
        output_images = self.extract_output_images(history)

        if not output_images:
            raise Exception("출력 이미지가 생성되지 않았습니다.")

        return output_images, history

    def get_queue_info(self) -> Dict[str, Any]:
        """큐 상태 조회"""
        try:
            response = self.session.get(
                f"{self.base_url}/queue",
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {}

        except Exception as e:
            print(f"⚠️ 큐 조회 오류: {e}")
            return {}

    def free_memory(self, unload_models: bool = True, free_memory: bool = True) -> bool:
        """
        ComfyUI 메모리 해제 (모델 언로드)
        
        Args:
            unload_models: 모델 언로드 여부
            free_memory: VRAM 해제 여부
            
        Returns:
            성공 여부
        """
        try:
            payload = {
                "unload_models": unload_models,
                "free_memory": free_memory
            }
            
            # 1. /free 시도 (ComfyUI 최신 버전)
            response = self.session.post(
                f"{self.base_url}/free",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ ComfyUI 메모리 해제 완료 (/free)")
                return True
                
            # 2. 실패 시 /internal/free 시도 (구버전)
            response = self.session.post(
                f"{self.base_url}/internal/free",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ ComfyUI 메모리 해제 완료 (/internal/free)")
                return True
                
            print(f"⚠️ 메모리 해제 실패: {response.status_code}")
            return False
            
        except Exception as e:
            print(f"❌ 메모리 해제 오류: {e}")
            return False
