# 프롬프트 최적화 가이드

> 2025-11-22 작성
> AI 이미지 생성 품질 향상을 위한 자동 프롬프트 최적화

---

## 개요

사용자가 입력한 프롬프트를 GPT가 자동으로 최적화하여 AI 이미지 생성 아티팩트를 방지합니다.

**작동 흐름:**
```
사용자 프롬프트 → GPT 최적화 → 품질 키워드 추가 → FLUX 이미지 생성
```

---

## 설정 파일 위치

```
src/backend/services.py
```

`optimize_prompt()` 함수 내 `system_prompt` 변수에서 GPT에게 주는 지시를 수정합니다.

---

## 현재 설정된 품질 키워드

### 1. 사람 관련

```
- Hands: "detailed hands, five fingers, natural hand pose, anatomically correct hands, correct thumb direction, thumbs pointing outward"
- Faces: "detailed face, clear facial features, symmetric face"
- Body: "correct human anatomy, natural body proportions"
```

### 2. 물체 상호작용

```
- "proper object interaction, object not clipping through body"
- "realistic grip, natural holding pose"
- "physically accurate, no overlapping body parts with objects"
```

### 3. 운동 장비

```
- "equipment not penetrating body, proper form"
- "hands gripping equipment correctly, realistic weight interaction"
```

---

## 키워드 추가/수정 방법

### 1. 파일 열기

```bash
# 로컬
code src/backend/services.py

# GCP
nano src/backend/services.py
```

### 2. system_prompt 찾기

`optimize_prompt` 함수 내에서 `IMPORTANT - Quality keywords to prevent AI artifacts:` 부분을 찾습니다.

### 3. 키워드 추가 예시

**문제:** 엄지가 뒤집어져서 나옴
**해결:** 손 관련 키워드에 추가
```python
- Hands: "..., correct thumb direction, thumbs pointing outward"
```

**문제:** 눈이 비대칭
**해결:** 얼굴 관련 키워드에 추가
```python
- Faces: "..., symmetric eyes, equal eye size"
```

**문제:** 팔이 너무 길게 나옴
**해결:** 신체 관련 키워드에 추가
```python
- Body: "..., correct arm length, proportional limbs"
```

### 4. 새로운 카테고리 추가 예시

```python
4. If the scene involves food/drinks:
   - "realistic food texture, appetizing presentation"
   - "proper glass/cup holding, liquid not spilling"
```

---

## 자주 발생하는 문제와 키워드

| 문제 | 추가할 키워드 |
|------|--------------|
| 손가락 6개 | `five fingers, no extra fingers` |
| 엄지 뒤집힘 | `correct thumb direction, thumbs pointing outward` |
| 손이 물체 관통 | `object not clipping through body, proper grip` |
| 얼굴 비대칭 | `symmetric face, balanced facial features` |
| 눈 이상 | `symmetric eyes, natural eye shape` |
| 팔다리 길이 이상 | `proportional limbs, correct arm length` |
| 바벨 관통 | `equipment not penetrating body, realistic weight interaction` |
| 옷이 몸에 맞지 않음 | `well-fitted clothing, natural fabric drape` |

---

## 적용 및 테스트

### 1. 변경 후 커밋

```bash
git add src/backend/services.py
git commit -m "feat: 프롬프트 최적화 키워드 추가 - [문제 설명]"
git push origin mscho
```

### 2. GCP에서 적용

```bash
git pull origin mscho
# 서버 재시작 필요
```

### 3. 테스트

웹 UI 또는 터미널에서 이미지 생성 후 로그 확인:
```
🔄 프롬프트 최적화:
  원본: [사용자 입력]
  최적화: [GPT가 변환한 결과]
```

---

## 주의사항

1. **키워드가 너무 많으면** 프롬프트가 길어져서 다른 중요한 내용이 잘릴 수 있음
2. **영어로 작성** - GPT가 영어로 최적화하므로 키워드도 영어로
3. **테스트 필수** - 키워드 추가 후 실제 이미지 생성해서 효과 확인
4. **모델 한계** - 키워드만으로 100% 해결 안 될 수 있음 (AI 모델 자체 한계)
