"""
Ollama 模型调用包装器

由于 Ollama HTTP API 在 Windows 上对大模型支持有问题，
使用 CLI 方式调用模型（虽然较慢，但更稳定）
"""

import logging
import subprocess
import json
import re
import time
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)


class OllamaHTTPClient:
    """
    Ollama HTTP API 客户端

    通过HTTP API调用 Ollama 模型
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        timeout: int = 120,
        base_url: str = "http://localhost:11434"
    ):
        """
        初始化

        Args:
            model_name: 模型名称
            timeout: 超时时间（秒）
            base_url: Ollama服务地址
        """
        self.model_name = model_name
        self.timeout = timeout
        self.base_url = base_url

        logger.info(
            f"OllamaHTTPClient initialized: model={model_name}, "
            f"timeout={timeout}s, url={base_url}"
        )

    def generate(self, prompt: str) -> str:
        """
        生成响应

        Args:
            prompt: 输入提示词

        Returns:
            生成的文本
        """
        try:
            start_time = time.time()

            # 调用 HTTP API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"HTTP API error: {response.status_code} - {response.text}")
                raise Exception(f"HTTP API failed: {response.text}")

            result = response.json()
            output = result.get("response", "")

            duration = time.time() - start_time
            logger.info(f"Generation completed in {duration:.2f}s")

            return output

        except requests.Timeout:
            logger.error(f"HTTP API timeout after {self.timeout}s")
            raise Exception(f"HTTP API timeout")
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise


class OllamaCLIClient:

    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        timeout: int = 120,
        num_predict: int = 2000,
        temperature: float = 0.2
    ):
        """
        初始化

        Args:
            model_name: 模型名称
            timeout: 超时时间（秒）
            num_predict: 最大生成token数
            temperature: 温度参数
        """
        self.model_name = model_name
        self.timeout = timeout
        self.num_predict = num_predict
        self.temperature = temperature

        logger.info(
            f"OllamaCLIClient initialized: model={model_name}, "
            f"timeout={timeout}s, temperature={temperature}"
        )

    def generate(self, prompt: str) -> str:
        """
        生成响应

        Args:
            prompt: 输入提示词

        Returns:
            生成的文本
        """
        try:
            start_time = time.time()

            # 构建命令
            cmd = [
                "ollama", "run", self.model_name, prompt
            ]

            logger.debug(f"Executing: {' '.join(cmd[:3])}... (prompt length: {len(prompt)})")

            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                logger.error(f"Ollama CLI error: {result.stderr}")
                raise Exception(f"Ollama CLI failed: {result.stderr}")

            # 清理输出
            output = self._clean_output(result.stdout)

            duration = time.time() - start_time
            logger.info(f"Generation completed in {duration:.2f}s")

            return output

        except subprocess.TimeoutExpired:
            logger.error(f"Ollama CLI timeout after {self.timeout}s")
            raise Exception(f"Ollama CLI timeout")

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    def _clean_output(self, output: str) -> str:
        """清理模型输出"""
        output = output.strip()

        # 移除 ANSI 转义序列
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)

        # 移除进度字符（如果有）
        output = re.sub(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]', '', output)

        # 移除可能的思考过程标记（如果是推理模型）
        if "<|思考|>" in output:
            # 保留最终答案
            parts = output.split("<|思考|>")
            output = parts[-1] if parts else output

        # 移除结束标记
        output = output.replace("<|im_end|>", "").replace("<|end|>", "").strip()

        return output


class ModelInvoker:
    """
    模型调用器

    统一的模型调用接口
    """

    def __init__(self, use_http: bool = True):
        self.clients = {}
        self.use_http = use_http  # 默认使用HTTP API

    def get_client(self, model_name: str) -> "OllamaHTTPClient":
        """获取模型客户端（带缓存）"""
        if model_name not in self.clients:
            # 根据模型大小设置不同参数
            if "14b" in model_name.lower() or "32b" in model_name.lower():
                client = OllamaCLIClient(
                    model_name=model_name,
                    timeout=180,  # 大模型需要更长超时
                    num_predict=3000,  # 允许更长输出
                    temperature=0.1  # 降低温度以提高准确性
                )
            else:
                client = OllamaCLIClient(
                    model_name=model_name,
                    timeout=120,
                    num_predict=2000,
                    temperature=0.2
                )

            self.clients[model_name] = client

        return self.clients[model_name]

    def invoke(self, model_name: str, prompt: str) -> str:
        """
        调用模型

        Args:
            model_name: 模型名称
            prompt: 完整提示词

        Returns:
            模型响应
        """
        client = self.get_client(model_name)
        return client.generate(prompt)


# 全局单例
_model_invoker: Optional[ModelInvoker] = None


def get_model_invoker() -> ModelInvoker:
    """获取模型调用器实例"""
    global _model_invoker
    if _model_invoker is None:
        _model_invoker = ModelInvoker()
    return _model_invoker
