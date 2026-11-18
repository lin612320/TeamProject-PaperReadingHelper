# FastAPI 服务。
FROM python:3.11-slim
WORKDIR /app

# ---------------------------------------------------------------------------
# 国内网络下的两处调整（2026-11-06，P1）：
#   1. pip 走清华镜像。PyPI 官方源的 torch 包实测下载 9 分钟不动。
#   2. torch 单独装 CPU 版。默认装的是 CUDA 版，会连带拉 cuda-toolkit /
#      nvidia-cudnn / nccl / triton 等约 3GB 依赖，而本服务只用 CPU 推理。
#      CPU 版 wheel 约 180MB，镜像小 5GB 以上，构建时间从 40 分钟降到几分钟。
#   如需 GPU 或官方源，构建时覆盖 build-arg：
#      docker compose build --build-arg TORCH_CHANNEL=https://pypi.org/simple ai-service
# ---------------------------------------------------------------------------
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG TORCH_CHANNEL=https://download.pytorch.org/whl/cpu

COPY requirements.txt .

# ① 先装 CPU 版 torch（后续 pip 看到 torch 已满足，就不会再拉 CUDA 全套）
RUN pip install --no-cache-dir --retries 10 --timeout 120 \
        --index-url ${TORCH_CHANNEL} \
        torch

# ② 再装其余依赖；torch 已在，不会重复下载
RUN pip install --no-cache-dir --retries 10 --timeout 120 \
        --index-url ${PIP_INDEX_URL} \
        -r requirements.txt

COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
