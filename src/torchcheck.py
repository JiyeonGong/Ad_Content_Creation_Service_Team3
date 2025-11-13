# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\torchcheck.py
import torch

# 1. GPU(CUDA) 사용 가능 여부 확인
is_cuda_available = torch.cuda.is_available()
print(f"CUDA (GPU) 사용 가능: {is_cuda_available}")

if is_cuda_available:
    # 2. 사용 가능한 GPU 개수 확인
    device_count = torch.cuda.device_count()
    print(f"사용 가능한 GPU 개수: {device_count}")
    
    # 3. 첫 번째 GPU의 이름 확인
    gpu_name = torch.cuda.get_device_name(0)
    print(f"GPU 이름 (Device 0): {gpu_name}")
    
    # 4. 사용할 장치 자동 선택 (코드 작성 시 유용)
    device = torch.device('cuda:0' if is_cuda_available else 'cpu')
    print(f"선택된 장치: {device}")
else:
    # CPU만 사용
    device = torch.device('cpu')
    print(f"선택된 장치: {device}")