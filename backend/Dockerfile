# 使用Python 3.10（DeepDoctection推荐版本）
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（添加EasyOCR所需的系统库）
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    libgthread-2.0-0 \
    libgomp1 \
    libgcc-s1 \
    libstdc++6 \
    libc6 \
    libglvnd0 \
    libglx0 \
    libegl1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装API依赖
COPY requirements.txt .
# 添加PyTorch索引源以支持+cu118版本
RUN pip install --no-cache-dir --prefer-binary \
    -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --extra-index-url https://download.pytorch.org/whl/cu118

# 复制应用代码
COPY *.py .
COPY agents/ agents/
COPY core/ core/
COPY processors/ processors/
COPY retriever/ retriever/
COPY storage/ storage/
COPY services/ services/
COPY routes/ routes/

# 清理可能损坏的模型缓存（包括Doctr和EasyOCR）
RUN rm -rf /home/developer/.cache/deepdoctection/weights/Aryn/deformable-detr-DocLayNet && \
    rm -rf /home/developer/.cache/huggingface/hub && \
    rm -rf /home/developer/.cache/deepdoctection/weights/doctr && \
    rm -rf /root/.cache/easyocr && \
    rm -rf /tmp/* && \
    # 创建缓存目录
    mkdir -p /root/.cache/easyocr && \
    mkdir -p /root/.cache/deepdoctection/weights

# 设置环境变量以优化GPU性能和兼容性
ENV CUDA_VISIBLE_DEVICES=0
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1
ENV HF_HUB_OFFLINE=0
# EasyOCR 优化设置
ENV EASYOCR_ENABLE_GPU=1
ENV EASYOCR_MODEL_STORAGE_DIRECTORY=/root/.cache/easyocr
# EasyOCR 环境变量
ENV EASYOCR_CACHE_DIR=/root/.cache/easyocr
# 跳过不兼容的模型权重
ENV DEEPDOCTECTION_SKIP_INCOMPATIBLE_WEIGHTS=1
# 优先使用EasyOCR
ENV DEEPDOCTECTION_OCR_ENGINE=easyocr

# 暴露端口
EXPOSE 8000

# 启动命令 - 修复：使用 "main:app" 而不是 "main.py:app"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]