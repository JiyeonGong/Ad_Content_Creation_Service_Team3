# FLUX.1-dev FP8 + LoRA 학습 가이드

## 메모리 사용량
- 원본: 22GB → FP8: 12GB → FP8+LoRA 학습: 14-16GB

## 사용법

### 1. 환경 준비
```bash
cd ~/Ad_Content_Creation_Service_Team3
source .venv/bin/activate
uv pip install peft>=0.7.0
```

### 2. FLUX FP8 로드
```bash
python scripts/load_flux_fp8_for_lora.py
```

### 3. LoRA 학습 코드

```python
from scripts.load_flux_fp8_for_lora import load_flux_fp8_for_lora
from peft import LoraConfig, get_peft_model

# 모델 로드
pipe = load_flux_fp8_for_lora()
base_model = pipe.transformer

# LoRA 설정
lora_config = LoraConfig(
    r=8,                    # rank (메모리 부족 시 4로)
    lora_alpha=16,
    target_modules=["to_q", "to_k", "to_v", "to_out"],
    lora_dropout=0.1,
    bias="none"
)

lora_model = get_peft_model(base_model, lora_config)

# 학습 (예시)
optimizer = torch.optim.AdamW(lora_model.parameters(), lr=1e-4)

for epoch in range(10):
    for batch in dataloader:
        loss = model(batch)  # 학습 로직 구현 필요
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

# 저장
lora_model.save_pretrained("./lora_weights")

# 로드
from peft import PeftModel
lora_model = PeftModel.from_pretrained(base_model, "./lora_weights")
```

## 메모리 최적화

```python
# Gradient checkpointing (자동 적용됨)
lora_model.enable_gradient_checkpointing()

# Mixed precision
from torch.cuda.amp import autocast, GradScaler
scaler = GradScaler()

with autocast():
    loss = model(batch)
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()

# Gradient accumulation
accumulation_steps = 4
loss = model(batch) / accumulation_steps
loss.backward()
if (i + 1) % accumulation_steps == 0:
    optimizer.step()
    optimizer.zero_grad()
```

## OOM 해결
1. LoRA rank: 8 → 4
2. Batch size: 줄이기
3. Gradient accumulation 사용
