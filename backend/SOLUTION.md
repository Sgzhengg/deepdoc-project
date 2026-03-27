# DeepDoctection 权重不匹配问题 - 完整解决方案

## 问题总结
- Doctr 模型权重尺寸不匹配：期望 127 类但实际 124 类
- 需要保留表格检测和布局检测功能
- 优先考虑不重新构建镜像的方案

## 解决方案 1：热修复（推荐，无需重新构建）

### 1.1 立即执行的修复步骤
```bash
# 进入容器
docker exec -it <container_name> bash

# 清理有问题的模型缓存
rm -rf /root/.cache/deepdoctection/weights/doctr/db_resnet50/
rm -rf /root/.cache/huggingface/hub/models--doctr--*

# 安装 EasyOCR 替代 Doctr
pip install easyocr==1.7.1 opencv-python==4.8.1.78 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 重启服务
exit
docker restart <container_name>
```

### 1.2 配置文件修改
main.py 已更新为使用 EasyOCR：
```python
config_overwrite = [
    "USE_OCR=True",  # 启用 OCR 但使用 EasyOCR
    "USE_LAYOUT=True",
    "USE_TABLE_SEGMENTATION=True", 
    "DEVICE='cuda'",
    "OCR=EasyOcr",
    "EASYOCR_MODEL_LIST=['en','ch_sim']"
]
```

### 1.3 requirements.txt 更新
- 添加 `easyocr==1.7.1`
- 添加 `opencv-python==4.8.1.78`
- 移除或注释 `python-doctr==0.12.0`

## 解决方案 2：重新构建镜像（如果方案1失败）

### 2.1 更新的 Dockerfile
```dockerfile
# 使用Python 3.10（DeepDoctection推荐版本）
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（添加 EasyOCR 依赖）
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
    libglib2.0-0 \
    libcairo2 \
    libpango1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装API依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY *.py .
COPY agents/ agents/
COPY core/ core/
COPY processors/ processors/
COPY retriever/ retriever/
COPY storage/ storage/

# 清理可能损坏的模型缓存
RUN rm -rf /root/.cache/deepdoctection/weights/doctr/db_resnet50/ && \
    rm -rf /root/.cache/deepdoctection/weights/Aryn/deformable-detr-DocLayNet/ && \
    rm -rf /root/.cache/huggingface/hub/

# 设置环境变量
ENV CUDA_VISIBLE_DEVICES=0
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV HF_HUB_DISABLE_SYMLINKS_WARNING=1
ENV HF_HUB_OFFLINE=0

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 构建命令
```bash
cd Z:\deepdoc-project\backend
docker build -t deepdoc-backend:fixed .
```

## 验证修复效果

### 3.1 健康检查
```bash
curl http://localhost:8000/health
```

### 3.2 测试 OCR 功能
```bash
curl -X POST -F "file=@test.pdf" http://localhost:8000/analyze
```

### 3.3 检查日志
```bash
docker logs <container_name>
```

## 预期结果
- ✅ OCR 功能正常（使用 EasyOCR）
- ✅ 表格检测功能保留
- ✅ 布局检测功能保留
- ✅ 无权重不匹配错误
- ✅ 支持 GPU 加速

## 故障排除

### 如果 EasyOCR 加载失败
```python
# 在 main.py 中回退到无 OCR 配置
config_overwrite = [
    "USE_OCR=False",
    "USE_LAYOUT=True",
    "USE_TABLE_SEGMENTATION=True",
    "DEVICE='cuda'"
]
```

### 如果模型仍然不匹配
```bash
# 完全清理缓存
docker system prune -a
docker volume prune
```

## 性能对比
- **Doctr**: 更精确但权重复杂
- **EasyOCR**: 更稳定，支持多语言，模型较小
- **无 OCR**: 最快，但仅支持布局和表格检测