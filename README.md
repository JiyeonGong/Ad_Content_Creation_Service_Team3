# Ad_Content_Creation_Service_Team3

## 🚀 헬스케어 AI 콘텐츠 제작 서비스

이 프로젝트는 **FastAPI** 백엔드와 **Streamlit** 프론트엔드를 결합하여 헬스케어 분야의 소상공인을 위한 인스타그램 홍보 콘텐츠(문구, 해시태그, 이미지)를 AI로 쉽고 빠르게 생성하는 서비스입니다.

### 🌟 주요 기능

| 기능 | 사용 모델/기술 | 설명 |
| :--- | :--- | :--- |
| **📝 홍보 문구 & 해시태그 생성** | `GPT-5 Mini` (OpenAI API) | 서비스 정보(이름, 특징, 지역, 톤)를 입력하면 인스타그램에 최적화된 3가지 문구와 해시태그를 생성합니다. |
| **🖼 문구 기반 이미지 생성 (T2I)** | `SDXL-Base-1.0` (Diffusers/PyTorch) | 생성된 문구를 기반으로 3가지 버전의 인스타그램 홍보 이미지를 생성합니다. |
| **🖼️ 이미지 편집 / 합성 (I2I)** | `SDXL-Base-1.0` (Diffusers/PyTorch) | 업로드하거나 생성된 이미지를 기반으로 문구와 추가 지시를 반영하여 새로운 스타일로 이미지를 편집/합성합니다. |

-----

### 🏛️ 아키텍처 및 기술 스택

이 서비스는 **클라이언트-서버 구조**로 분리되어 AI 추론의 부하를 백엔드 서버가 전담합니다.

| 영역 | 기술 스택 | 설명 |
| :--- | :--- | :--- |
| **백엔드 (AI 서버)** | **FastAPI**, `OpenAI` (GPT-5 Mini), `Diffusers` (SDXL), `Pydantic` | AI 모델 추론 로직을 담당하며, RESTful API를 통해 프론트엔드에 기능을 제공합니다. GPU를 사용하는 SDXL 모델을 효율적으로 로드하고 관리합니다. |
| **프론트엔드 (UI 앱)** | **Streamlit**, `requests` | 사용자 인터페이스(UI)를 구성하고, 사용자의 입력을 받아 백엔드 API를 호출하여 결과를 표시합니다. |
| **데이터 처리** | `Base64` 인코딩/디코딩, `io.BytesIO` | 이미지 데이터는 HTTP 통신을 위해 Base64로 인코딩되어 전송됩니다. |

-----

### 📦 종속성 관리 도구 설명

이 프로젝트는 Python 종속성 관리를 위해 `pip`와 차세대 패키지 관리 도구인 \*\*`uv`\*\*를 함께 사용할 수 있도록 준비되었습니다.

  * **pip (Python Package Installer):** Python 표준 패키지 설치 도구입니다. `requirements.txt`에 명시된 종속성을 설치하는 데 사용됩니다.
  * **uv (Next-generation Python package installer and resolver):** Rust로 작성된 빠르고 효율적인 패키지 설치 및 해소 도구입니다. `pyproject.toml` 기반의 현대적인 Python 프로젝트 관리에 유용하며, 특히 `pip`보다 빠른 설치 및 해소 속도를 제공합니다.

-----

### ⚙️ 실행 환경 설정 및 방법

#### 1\. 환경 설정

1.  **Python 버전 확인:** Python 3.10 이상이 설치되어 있어야 합니다.

2.  **종속성 설치:** `requirements.txt` 또는 `pyproject.toml`에 명시된 기본 패키지를 설치합니다.

      * **pip 사용 시:**
        ```bash
        pip install -r requirements.txt
        ```
      * **uv 사용 시 (권장):**
        ```bash
        uv sync
        ```

3.  **PyTorch 및 GPU 설정 (필수):** SDXL 모델 구동을 위해서는 **PyTorch**와 **CUDA Toolkit**이 필요합니다. 성능을 위해 GPU 환경을 권장합니다.

      * **GPU 환경 (CUDA 12.8 예시, `pyproject.toml`에 명시된 대로):**
        ```bash
        # uv 또는 pip을 사용하여 PyTorch 설치
        uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
        # 또는
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
        ```
      * **CPU 환경 (테스트용):**
        ```bash
        uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        # 또는
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        ```

4.  **OpenAI API Key 설정:**

      * 프로젝트 루트에 `.env` 파일을 생성하고 `OPENAI_API_KEY`를 설정합니다.
        ```ini
        # .env 파일 내용
        OPENAI_API_KEY="sk-..."
        ```

#### 2\. 서버 실행

Ad_Content_Creation_Service_Team3\src\healthcare>로 터미널 경로 이동 후

1.  **백엔드 서버 실행:**

    ```bash
    uvicorn backend:app --reload
    ```

      * 터미널에 "SDXL 모델 로딩 완료." 메시지가 뜨면 성공적으로 로드된 것입니다.

2.  **프론트엔드 앱 실행 (새 터미널):**

    ```bash
    streamlit run frontend.py
    ```

      * 웹 브라우저에서 Streamlit UI에 접속하여 서비스를 이용합니다.