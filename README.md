# 🛍️ 소상공인을 위한 광고 제작 서비스 (Fit - AD)

> **"딱 맞는, 알맞는 이미지를 제공합니다! Fit - AD."**
>
> 소상공인을 위한 AI 기반 마케팅 자동화 플랫폼 (Flux.1 & ComfyUI 기반)

![Python](https://img.shields.io/badge/Python-3.12-blue) 
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red)
![ComfyUI](https://img.shields.io/badge/ComfyUI-Latest-purple)

---

## 1. 프로젝트 개요
최근 소비 트렌드가 '경험'과 '비주얼' 중심으로 변화함에 따라 요식업, 뷰티, 헬스케어, 소매업 등 모든 업종에서 SNS 마케팅의 중요성이 그 어느 때보다 커졌습니다. 소상공인 창업은 활발히 이루어지고 있지만, 그만큼 동종 업계 간의 경쟁은 더욱 치열해졌습니다.
    
고객 유치를 위해 인스타그램 등 SNS 관리는 필수적인 생존 전략이 되었으나, 본업에 쫓기는 소상공인이 전문적인 콘텐츠를 직접 기획하고 제작하는 것은 엄청난 시간과 노력을 요구합니다. 단순히 스마트폰으로 찍은 투박한 제품 사진이나, "문의 환영"과 같은 익숙한 문구만으로는 더 이상 소비자의 눈길을 사로잡는 경쟁력을 갖기 어렵습니다.
    
본 프로젝트의 목표는 소상공인들이 겪는 이 '마케팅 격차'를 생성형 AI 기술로 메우는 것입니다. 전문 마케터나 디자이너가 아닌, 각 분야의 전문가인 사장님들이 **온라인 광고 콘텐츠 생성 과정에서 겪는 비용적, 심리적 부담과 어려움을 해소**할 수 있음을 기대합니다.

---
## 2. 프로젝트 소개
이 프로젝트는 **최신 생성형 AI 모델(Flux.1, GPT, SDXL)**을 활용하여, 비전문가도 **클릭 몇 번으로 '카피라이팅 - 고화질 이미지 - 3D 홍보 텍스트'를 원스톱으로 생성**할 수 있는 자동화 플랫폼입니다.

### 🎯 핵심 목표
- **Accessibility(기술 장벽 해소):** 전문 마케터나 디자이너가 아닌 소상공인도, 기술적 장벽과 심리적 부담 없이 손쉽게 온라인 광고 콘텐츠를 생성할 수 있도록 돕는다.
- **Ready-to-Post(즉시 게시 가능한 품질):** 생성형 AI를 활용해 별도의 추가 가공(Editing) 없이 바로 SNS에 업로드할 수 있는 전문가급의 맞춤형 광고 이미지를 제공한다.
- **Efficiency(본업 집중 지원):** 1인 사업자나 골목 상권의 소규모 매장도 대형 프랜차이즈와 동등하게 온라인 시장에서 경쟁할 수 있는 무기를 갖게 된다.

---

## 3. 실행 화면

```
여기에 넣는 이미지는 assets 폴더에 하위 폴더 만들고 화면 이미지 캡쳐해서 넣을 것
```
| 메인 페이지 (문구 생성) | 이미지 생성 결과 (T2I) |
| :---: | :---: |
| ![메인화면](./assets/main_page.png) | ![결과물](./assets/result_sample.png) |
| *업종과 분위기만 선택하면 카피 자동 생성* | *생성된 문구를 바탕으로 고화질 이미지 생성* |

| 이미지 스타일 편집 (I2I) | 3D 캘리그라피 생성 |
| :---: | :---: |
| ![편집화면](./assets/edit_mode.png) | ![3D텍스트](./assets/3d_text.png) |
| *기존 사진의 조명과 분위기 변경* | *홍보용 3D 텍스트 디자인 생성* |

---

## 4. 시스템 아키텍처 & 다이어그램
복잡한 AI 모델의 연산 처리를 효율적으로 관리하기 위해 **3-Tier Architecture**를 채택했습니다. 특히 무거운 GPU 연산을 담당하는 ComfyUI를 백엔드와 분리하여 확장성을 확보했습니다.



```mermaid
여기에 아키텍처 이미지 추가

```

## 5. 주요 기술 스택 
### Frontend
- Streamlit (1.28+): 직관적인 웹 UI 구성 및 상태 관리
- Pillow: 이미지 전처리 및 시각화

### Backend & API
- FastAPI (0.104+): 비동기 REST API 서버, Pydantic 데이터 검증
- OpenAI API: GPT-5 Mini 기반 마케팅 문구 생성

### AI Core (Generative Models)
- ComfyUI: 노드 기반 이미지 생성 파이프라인 오케스트레이션
- FLUX.1-dev (GGUF): 고품질 T2I/I2I 생성 (메모리 최적화 적용)
- FLUX.1-Fill & BEN2: 자연스러운 배경 제거 및 인페인팅
- SDXL ControlNet (Depth): 3D 텍스트 심도 제어

## 6. 프로젝트 폴더 구조
```
├── comfyui
├── configs
│   ├── experiment_t2i_01.yaml
│   ├── frontend_config.yaml
│   ├── image_editing_config.yaml
│   ├── model_config.yaml
│   └── test_flux_gcp.yaml
├── Dockerfile
├── docs
│   ├── env_example.md
│   └── 임시.md
├── outputs
│   └── flux_gcp
│       └── 20251122_082524
├── pyproject.toml
├── README.md
├── requirements.txt
├── scripts
│   ├── download_t5xxl.py
│   ├── install_comfyui.sh
│   ├── load_flux_fp8_for_lora.py
│   ├── monitor_backend.sh
│   ├── monitor.sh
│   ├── run_experiment.py
│   ├── start_all.sh
│   ├── start_comfyui.sh
│   ├── stop_all.sh
│   ├── stop_comfyui.sh
│   ├── test
│   │   ├── prompt_self_test.py
│   │   └── validate_model_config.py
│   ├── test_flux_gcp.py
│   └── torchcheck.py
├── src
│   ├── __init__.py
│   ├── backend
│   │   ├── __init__.py
│   │   ├── comfyui_client.py
│   │   ├── comfyui_workflows.py
│   │   ├── exceptions.py
│   │   ├── main.py
│   │   ├── model_loader.py
│   │   ├── model_registry.py
│   │   ├── post_processor.py
│   │   ├── services.py
│   │   └── text_overlay.py
│   └── frontend
│       ├── __init__.py
│       ├── app.py
│       ├── model_selector.py
│       └── utils.py
└── uv.lock
```

## 6. 개발 환경
```
여기에 개발환경 정보 추가
```

## 7. 환경설정 및 설치

## 8. 실행 방법

---
## 9. 협업 & 문서 자료
### 👤 협업일지
- 공지연 👉
- 배진석 👉
- 조계승 👉
- 조민수 👉

### 프로젝트 문서
- 프로젝트 Notion 페이지 👉 ![노션 링크](https://chlorinated-knife-ad5.notion.site/part4-3-29490068d16d80778fa3c473cba05d56?source=copy_link)
- 프로젝트 보고서(Notion) 👉 ![최종 보고서 링크](https://chlorinated-knife-ad5.notion.site/Part-4-3-2bd90068d16d803d8bd5f55fa5cf4f32?source=copy_link)
- 최종 발표 자료 및 보고서(pdf) 👉 ![PPT 다운로드]()
