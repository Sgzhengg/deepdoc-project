"""
llama.cpp 可行性测试脚本

测试 llama-cpp-python 是否能够：
1. 正确加载 qwen2.5:32b 模型
2. 在 GPU 上运行
3. 正常生成响应
"""

import sys
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖是否安装"""
    logger.info("=" * 60)
    logger.info("步骤 1: 检查依赖")
    logger.info("=" * 60)

    # 检查 llama-cpp-python
    try:
        import llama_cpp
        logger.info(f"✅ llama-cpp-python 已安装 (版本: {llama_cpp.__version__})")
    except ImportError:
        logger.error("❌ llama-cpp-python 未安装")
        logger.info("\n请运行以下命令安装:")
        logger.info("pip install llama-cpp-python")
        return False

    # 检查 CUDA
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA 可用 (版本: {torch.version.cuda})")
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"   显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            logger.warning("⚠️ CUDA 不可用，将使用 CPU（速度会很慢）")
    except ImportError:
        logger.warning("⚠️ PyTorch 未安装，无法验证 CUDA")

    return True


def get_model_path():
    """获取 qwen2.5:32b 模型路径"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2: 定位模型文件")
    logger.info("=" * 60)

    # Ollama 模型路径
    ollama_blobs = os.path.expanduser("~/.ollama/models/blobs")

    # qwen2.5:32b 的 blob hash（从 ollama list 获取）
    qwen32b_hash = "sha256-6150cb382311b69f09cc0f9a1b69fc029cbd742b66bb8ec531aa5ecf5c613e93"

    model_path = os.path.join(ollama_blobs, qwen32b_hash)

    if os.path.exists(model_path):
        size_gb = os.path.getsize(model_path) / (1024**3)
        logger.info(f"✅ 找到模型文件: {model_path}")
        logger.info(f"   文件大小: {size_gb:.1f} GB")

        # 验证 GGUF 格式
        with open(model_path, 'rb') as f:
            magic = f.read(4)
            if magic == b'GGUF':
                logger.info("✅ 模型格式: GGUF")
            else:
                logger.error(f"❌ 模型格式错误: {magic}")
                return None

        return model_path
    else:
        logger.error(f"❌ 模型文件不存在: {model_path}")
        logger.info("\n请确认 Ollama 已下载 qwen2.5:32b 模型")
        return None


def test_model_loading(model_path: str):
    """测试模型加载"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 3: 测试模型加载")
    logger.info("=" * 60)

    try:
        from llama_cpp import Llama

        logger.info("正在加载模型（这可能需要1-2分钟）...")

        start_time = time.time()

        # 创建 LLM 实例
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1,        # 全部加载到 GPU
            n_ctx=2048,             # 上下文长度（测试用短一点）
            verbose=False,           # 减少日志输出
            use_mmap=True,
        )

        load_time = time.time() - start_time
        logger.info(f"✅ 模型加载成功! 耗时: {load_time:.1f} 秒")

        # 检查显存使用
        try:
            import torch
            if torch.cuda.is_available():
                memory_used = torch.cuda.memory_allocated() / 1024**3
                logger.info(f"   GPU 显存使用: {memory_used:.1f} GB")
        except:
            pass

        return llm

    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        logger.error("\n可能的原因:")
        logger.error("  1. GPU 显存不足（需要 ~20GB）")
        logger.error("  2. CUDA 驱动版本不兼容")
        logger.error("  3. llama-cpp-python 编译时未启用 CUDA 支持")
        return None


def test_model_inference(llm):
    """测试模型推理"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 4: 测试模型推理")
    logger.info("=" * 60)

    try:
        # 简单的测试提示词
        prompt = """用户: 1+1等于几？

助手:"""

        logger.info(f"测试提示词: {prompt}")
        logger.info("\n正在生成回答...")

        start_time = time.time()

        response = llm(
            prompt,
            max_tokens=100,
            temperature=0.2,
            stop=["用户:", "User:", "\n"],
            echo=False
        )

        generation_time = time.time() - start_time

        answer = response['choices'][0]['text'].strip()
        tokens_per_second = response['usage']['total_tokens'] / generation_time if generation_time > 0 else 0

        logger.info(f"✅ 推理成功!")
        logger.info(f"   回答: {answer}")
        logger.info(f"   耗时: {generation_time:.2f} 秒")
        logger.info(f"   速度: {tokens_per_second:.1f} tokens/秒")
        logger.info(f"   使用的 tokens: {response['usage']['total_tokens']}")

        return True

    except Exception as e:
        logger.error(f"❌ 推理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("\n" + "=" * 60)
    logger.info("llama.cpp 可行性测试")
    logger.info("=" * 60)

    # 步骤 1: 检查依赖
    if not check_dependencies():
        logger.error("\n❌ 依赖检查失败，请先安装必要的依赖")
        return 1

    # 步骤 2: 定位模型
    model_path = get_model_path()
    if not model_path:
        logger.error("\n❌ 无法找到模型文件")
        return 1

    # 步骤 3: 测试加载
    llm = test_model_loading(model_path)
    if not llm:
        logger.error("\n❌ 模型加载失败")
        return 1

    # 步骤 4: 测试推理
    if not test_model_inference(llm):
        logger.error("\n❌ 模型推理失败")
        return 1

    # 成功
    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有测试通过！llama.cpp 方案可行")
    logger.info("=" * 60)
    logger.info("\n下一步:")
    logger.info("  1. 实现 llama_service.py 核心服务")
    logger.info("  2. 集成到现有的聊天 API")
    logger.info("  3. 编写完整的提示词模板")

    return 0


if __name__ == "__main__":
    sys.exit(main())
