# -*- coding: utf-8 -*-
"""
配置加载模块

用于加载和管理系统配置
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器"""

    # 默认配置
    DEFAULT_CONFIG = {
        'answer_format': {
            'max_direct_answer_length': 50,
            'min_detailed_explanation_length': 30,
            'required_sections': ['【直接回答】', '【详细说明】', '【数据来源】']
        },
        'content_validation': {
            'forbidden_phrases': ['不知道', '不清楚', '无法回答', '不能确定'],
            'require_data_source': True,
            'require_evidence': True
        },
        'validation_thresholds': {
            'min_acceptable_score': 60,
            'critical_penalty': 20,
            'warning_penalty': 10,
            'max_constraints_shown': 10,
            'max_tables_shown': 3
        },
        'constraint_extraction': {
            'patterns': [],
            'entity_patterns': {}
        },
        'table_parsing': {
            'table_types': {},
            'column_patterns': {},
            'delimiters': ['|', '\t', '：', ';']
        },
        'model_config': {
            'primary_model': {
                'name': 'qwen2.5:14b',
                'provider': 'ollama',
                'temperature': 0.3,
                'max_tokens': 2000
            },
            'light_model': {
                'name': 'qwen2.5:7b',
                'provider': 'ollama',
                'temperature': 0.1,
                'max_tokens': 500
            }
        },
        'retrieval_config': {
            'vector_db': {
                'provider': 'qdrant',
                'host': 'localhost',
                'port': 6333,
                'collection': 'deepdoc_vectors'
            },
            'embedding_model': {
                'name': 'bge-small-zh-v1.5',
                'dimensions': 512
            },
            'search': {
                'top_k': 5,
                'score_threshold': 0.5,
                'fusion_method': 'rrf'
            }
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path or self._find_config_file()
        self.config = self._load_config()

    def _find_config_file(self) -> Optional[str]:
        """查找配置文件"""
        # 可能的配置文件位置
        possible_paths = [
            # 当前目录下的config文件夹
            os.path.join(os.getcwd(), 'config', 'qa_config.yaml'),
            # backend/config目录
            os.path.join(os.path.dirname(__file__), '..', 'config', 'qa_config.yaml'),
            # 项目根目录的config文件夹
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'qa_config.yaml'),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"找到配置文件: {path}")
                return path

        logger.warning("未找到配置文件，使用默认配置")
        return None

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config = self.DEFAULT_CONFIG.copy()

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        config = self._merge_config(config, user_config)
                        logger.info(f"成功加载配置文件: {self.config_path}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}，使用默认配置")

        return config

    def _merge_config(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """递归合并配置"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'model_config.primary_model.name'
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段

        Args:
            section: 配置段名称

        Returns:
            配置段字典
        """
        return self.config.get(section, {})

    def reload(self) -> bool:
        """
        重新加载配置

        Returns:
            是否成功
        """
        try:
            self.config = self._load_config()
            logger.info("配置重新加载成功")
            return True
        except Exception as e:
            logger.error(f"配置重新加载失败: {e}")
            return False

    def update(self, key: str, value: Any) -> None:
        """
        更新配置项（运行时）

        Args:
            key: 配置键
            value: 新值
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
        logger.info(f"更新配置: {key} = {value}")

    def save(self, path: Optional[str] = None) -> bool:
        """
        保存配置到文件

        Args:
            path: 保存路径，默认使用原配置文件路径

        Returns:
            是否成功
        """
        save_path = path or self.config_path

        if not save_path:
            logger.error("没有指定保存路径")
            return False

        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"配置保存成功: {save_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False


# 全局实例
_config_loader = None


def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """获取配置加载器实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def get_config(key: str, default: Any = None) -> Any:
    """
    快捷方法：获取配置项

    Args:
        key: 配置键
        default: 默认值

    Returns:
        配置值
    """
    return get_config_loader().get(key, default)


def get_answer_format_config() -> Dict[str, Any]:
    """获取答案格式配置"""
    return get_config_loader().get_section('answer_format')


def get_validation_config() -> Dict[str, Any]:
    """获取验证配置"""
    return get_config_loader().get_section('validation_thresholds')


def get_constraint_config() -> Dict[str, Any]:
    """获取约束提取配置"""
    return get_config_loader().get_section('constraint_extraction')


def get_table_parsing_config() -> Dict[str, Any]:
    """获取表格解析配置"""
    return get_config_loader().get_section('table_parsing')


def get_model_config() -> Dict[str, Any]:
    """获取模型配置"""
    return get_config_loader().get_section('model_config')


if __name__ == "__main__":
    # 测试代码
    loader = ConfigLoader()

    print("=== 配置测试 ===")
    print(f"直接回答最大长度: {loader.get('answer_format.max_direct_answer_length')}")
    print(f"主模型名称: {loader.get('model_config.primary_model.name')}")
    print(f"向量数据库: {loader.get('retrieval_config.vector_db.provider')}")

    print("\n=== 答案格式配置 ===")
    import json
    print(json.dumps(get_answer_format_config(), ensure_ascii=False, indent=2))

    print("\n=== 约束提取配置 ===")
    print(json.dumps(get_constraint_config(), ensure_ascii=False, indent=2))
