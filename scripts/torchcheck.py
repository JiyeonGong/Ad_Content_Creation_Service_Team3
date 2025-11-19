# python C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\scripts\torchcheck.py
import torch

# 0. 설치된 PyTorch 버전 확인
print(f"설치된 PyTorch 버전: {torch.__version__}")

# 0-1. 설치된 CUDA 버전 확인 (PyTorch가 컴파일된 버전)
print(f"PyTorch가 컴파일된 CUDA 버전: {torch.version.cuda}")

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
    
    # 4. 사용할 장치 자동 선택
    device = torch.device('cuda:0')
    print(f"선택된 장치: {device}")
else:
    # CPU만 사용
    device = torch.device('cpu')
    print(f"선택된 장치: {device}")