"""
CLI Ollama Client - 通过命令行调用 Ollama 模型
用于解决 Windows 版本 Ollama API 无法识别某些模型的问题
"""

import logging
import asyncio
import json
import subprocess
import os
from typing import List, Dict, Any, Optional, AsyncIterator
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)


class CLIChatOllama(BaseChatModel):
    """
    通过 CLI 调用 Ollama 的聊天模型

    当 Ollama API 在 Windows 上无法识别某些模型时，使用此客户端
    """

    model_name: str = "deepseek-r1:32b"
    temperature: float = 0.2
    num_predict: int = 1000
    top_k: int = 20
    top_p: float = 0.9
    timeout: int = 600  # 增加到10分钟，应对 32B 模型的长推理时间

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(f"初始化 CLI Ollama 客户端，模型: {self.model_name}")

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """将消息格式化为 Ollama CLI 输入格式"""
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                formatted.append(f"Assistant: {msg.content}")
            elif isinstance(msg, SystemMessage):
                formatted.append(f"System: {msg.content}")
        return "\n".join(formatted)

    def _run_ollama(self, prompt: str) -> str:
        """通过 CLI 运行 Ollama"""
        process = None
        try:
            # 注意：ollama run 命令不支持参数传递
            # 参数需要在 Modelfile 中设置或使用环境变量
            cmd = [
                "ollama", "run", self.model_name, prompt
            ]

            logger.debug(f"执行命令: {' '.join(cmd)}")

            # 设置GPU环境变量
            env = {
                **os.environ,
                "OLLAMA_NUM_GPU": "1",  # 强制使用GPU
                "CUDA_VISIBLE_DEVICES": "0"  # 使用第一块GPU
            }

            # 使用 Popen 代替 run，以便更好地控制进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env
            )

            try:
                # 等待进程完成，带超时
                stdout, stderr = process.communicate(timeout=self.timeout)

                if process.returncode != 0:
                    logger.error(f"Ollama CLI 错误: {stderr}")
                    raise Exception(f"Ollama CLI 失败: {stderr}")

                # 清理输出（移除进度字符）
                output = stdout
                # 移除 ANSI 转义序列
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                output = ansi_escape.sub('', output)

                return output.strip()

            except subprocess.TimeoutExpired:
                # 超时时强制杀死进程
                logger.error(f"Ollama CLI 超时 (>{self.timeout}秒)，正在终止进程...")
                process.kill()
                # 等待进程结束，避免僵尸进程
                process.wait(timeout=5)
                raise Exception(f"Ollama CLI 超时 (>{self.timeout}秒)")

        except Exception as e:
            logger.error(f"Ollama CLI 调用失败: {e}")
            raise
        finally:
            # 确保进程被清理
            if process and process.poll() is None:
                logger.warning("⚠️  进程仍在运行，强制终止...")
                process.kill()
                try:
                    process.wait(timeout=5)
                except:
                    pass

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成"""
        prompt = self._format_messages(messages)
        response_text = self._run_ollama(prompt)

        # 提取实际响应（移除 thinking 等前缀）
        lines = response_text.split('\n')
        actual_response = []
        in_thinking = False
        for line in lines:
            line = line.strip()
            if line.lower().startswith('thinking'):
                in_thinking = True
                continue
            if in_thinking and not line:
                in_thinking = False
                continue
            if line and not in_thinking:
                actual_response.append(line)

        response_text = '\n'.join(actual_response)

        generation = ChatGeneration(message=AIMessage(content=response_text))
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成（在线程池中运行）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._generate, messages, stop, run_manager, **kwargs
        )

    @property
    def _llm_type(self) -> str:
        return "cli_ollama"

    def _convert_prompt_to_messages(self, prompt: str) -> List[BaseMessage]:
        """如果直接传入字符串，转换为消息列表"""
        return [HumanMessage(content=prompt)]


def create_cli_ollama(
    model_name: str = "deepseek-r1:32b",
    temperature: float = 0.2,
    num_predict: int = 1000,
    timeout: int = 300  # 增加到5分钟，应对长提示词,
) -> CLIChatOllama:
    """
    创建 CLI Ollama 客户端

    Args:
        model_name: 模型名称（通过 ollama list 查看）
        temperature: 温度参数
        num_predict: 最大生成长度
        timeout: 超时时间（秒）

    Returns:
        CLIChatOllama 实例
    """
    return CLIChatOllama(
        model_name=model_name,
        temperature=temperature,
        num_predict=num_predict,
        timeout=timeout
    )
