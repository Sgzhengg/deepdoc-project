# DeepDoctection 权重不匹配问题修复方案

## 问题分析

**错误信息**：
```
size mismatch for model.linear.weight: copying a param with shape torch.Size([127, 256]) from checkpoint, the shape in current model is torch.Size([124, 256]).
size mismatch for model.linear.bias: copying a param with shape torch.Size([127]) from checkpoint, the shape in current model is torch.Size([124]).
```

**根本原因**：
- DocTR 0.12.0 词汇表从124字符（legacy_french）更新为127字符（french）
- DeepDoctection 1.0.5 仍使用旧词汇表配置，导致权重尺寸不匹配

## 解决方案

### 方案1：容器内快速修复（推荐，无需重建镜像）

**步骤1**：进入Docker容器
```bash
docker exec -it <container_name> bash
```

**步骤2**：运行修复脚本
```bash
cd /app
python fix_weights_mismatch.py
```

**步骤3**：手动降级（如果自动修复失败）
```bash
pip uninstall python-doctr -y
pip install python-doctr==0.10.0 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 清理缓存
rm -rf ~/.cache/deepdoctection/weights/doctr
rm -rf ~/.cache/deepdoctection/weights/Aryn
```

### 方案2：使用EasyOCR（已实现）

当前代码已配置为使用EasyOCR替代Doctr：
- ✅ 支持中英文识别
- ✅ 避免Doctr权重问题
- ✅ GPU加速支持

### 方案3：修改requirements.txt重建镜像

如果必须重新构建，修改requirements.txt：
```txt
# 降级到兼容版本
python-doctr==0.10.0
torch==2.2.0
torchvision==0.17.0
```

### 方案4：Doctr兼容配置

如果需要继续使用Doctr，使用以下配置：
```python
config_overwrite = [
    "USE_OCR=True",
    "USE_LAYOUT=True", 
    "USE_TABLE_SEGMENTATION=True",
    "DEVICE='cuda'",
    "OCR=Doctr",
    "DOCTR_TEXT_RECOGNIZER=crnn_vgg16_bn",
    "DOCTR_TEXT_DETECTOR=db_resnet50",
    "DOCTR_RECO_VOCAB=legacy_french",  # 关键：使用124字符词汇表
    "TENSORFLOW_ENABLED=False",
    "PYTORCH_ENABLED=True"
]
```

## 验证修复

创建测试脚本验证：
```python
import torch
from deepdoctection.analyzer import get_dd_analyzer

try:
    config = [
        "USE_OCR=True",
        "USE_LAYOUT=True",
        "DEVICE='cuda'",
        "OCR=EasyOcr"  # 或 "OCR=Doctr" + "DOCTR_RECO_VOCAB=legacy_french"
    ]
    analyzer = get_dd_analyzer(config_overwrite=config)
    print("✅ 修复成功")
except Exception as e:
    print(f"❌ 仍有问题: {e}")
```

## 推荐步骤

1. **立即可用**：使用当前EasyOCR配置（已实现）
2. **如需Doctr**：运行容器内修复脚本
3. **长期方案**：降级到python-doctr==0.10.0

## 注意事项

- ⚠️ 清理缓存后首次启动会重新下载模型
- ⚠️ EasyOCR对复杂布局的支持可能不如Doctr
- ✅ 建议保留EasyOCR作为主要OCR方案
- ✅ 保持表格检测和布局检测功能