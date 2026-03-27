"""
优化的双模型系统测试脚本

测试查询路由、上下文管理、提示词模板等组件
"""

import sys
import os
import time
import logging

# 添加服务目录到路径
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_query_router():
    """测试查询路由器"""
    logger.info("=" * 60)
    logger.info("测试1: 查询路由器")
    logger.info("=" * 60)

    from query_router import get_query_router, QueryType

    router = get_query_router(threshold=5.0)

    # 测试用例
    test_queries = [
        "59元套餐的分成是多少？",  # 简单查询
        "59元套餐和99元套餐的分成有什么区别？",  # 对比
        "如果我是社会渠道，59元套餐的分成是多少？",  # 条件
        "那如果我是校园渠道呢？",  # 追问
        "59元套餐新入网和存量用户的分成分别是多少，如何计算？",  # 复杂计算
    ]

    for query in test_queries:
        logger.info(f"\n测试查询: {query}")
        decision = router.route(query)

        logger.info(f"  → 模型: {decision.model_size.value}")
        logger.info(f"  → 类型: {decision.query_type.value}")
        logger.info(f"  → 复杂度: {decision.complexity_score:.1f}")
        logger.info(f"  → 模板: {decision.prompt_template}")
        logger.info(f"  → 追问: {decision.is_follow_up}")
        logger.info(f"  → 原因: {', '.join(decision.reasons)}")

    logger.info("\n✅ 查询路由器测试完成")


def test_context_manager():
    """测试上下文管理器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 上下文管理器")
    logger.info("=" * 60)

    from context_manager import get_context_manager

    ctx_manager = get_context_manager()

    # 测试数据
    query = "59元套餐的分成是多少？"
    chat_history = [
        {"role": "user", "content": "99元套餐的分成是多少？"},
        {"role": "assistant", "content": "99元套餐的分成是80元，分3期结算。"},
        {"role": "user", "content": "那59元呢？"}
    ]
    retrieval_results = [
        {"text": "59元套餐分成60元，分3期", "score": 0.9},
        {"text": "99元套餐分成80元，分3期", "score": 0.8},
        {"text": "129元套餐分成100元，分4期", "score": 0.7},
    ]

    logger.info(f"\n测试查询: {query}")
    logger.info(f"历史轮数: {len(chat_history)}")
    logger.info(f"检索文档数: {len(retrieval_results)}")

    processed_history, processed_docs = ctx_manager.prepare_context(
        query=query,
        chat_history=chat_history,
        retrieval_results=retrieval_results,
        is_follow_up=True
    )

    logger.info(f"\n处理后的历史: {len(processed_history)} 条")
    for msg in processed_history:
        logger.info(f"  - {msg['role']}: {msg['content'][:50]}...")

    logger.info(f"\n处理后的文档: {len(processed_docs)} 个")
    for i, doc in enumerate(processed_docs, 1):
        logger.info(f"  - 文档{i}: {doc[:50]}...")

    logger.info("\n✅ 上下文管理器测试完成")


def test_prompt_templates():
    """测试提示词模板"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 提示词模板")
    logger.info("=" * 60)

    from prompts import (
        SimpleQueryPrompt,
        ComplexQueryPrompt,
        FollowUpPrompt,
        CalculationPromptTemplate
    )

    # 测试数据
    query = "59元套餐新入网的分成如何计算？"
    context = [
        "59元套餐分成60元，分3期结算。新入网和存量用户相同。",
        "社会渠道和自营厅执行统一标准。"
    ]
    chat_history = [
        {"role": "user", "content": "99元套餐的分成是多少？"},
        {"role": "assistant", "content": "99元套餐分成80元，分3期。"}
    ]

    # 测试简单模板
    logger.info("\n测试简单查询模板:")
    simple_template = SimpleQueryPrompt()
    simple_prompt = simple_template.build_prompt(query, context)
    logger.info(f"提示词长度: {len(simple_prompt)} 字符")
    logger.info(f"提示词预览:\n{simple_prompt[:500]}...")

    # 测试复杂模板
    logger.info("\n测试复杂查询模板:")
    complex_template = CalculationPromptTemplate()
    complex_prompt = complex_template.build_prompt(
        query, context, chat_history, calculation_type="commission"
    )
    logger.info(f"提示词长度: {len(complex_prompt)} 字符")
    logger.info(f"提示词预览:\n{complex_prompt[:500]}...")

    # 测试追问模板
    logger.info("\n测试追问模板:")
    follow_up_template = FollowUpPrompt()
    follow_up_prompt = follow_up_template.build_prompt(
        "那如果是校园渠道呢？", context, chat_history
    )
    logger.info(f"提示词长度: {len(follow_up_prompt)} 字符")
    logger.info(f"提示词预览:\n{follow_up_prompt[:500]}...")

    logger.info("\n✅ 提示词模板测试完成")


def test_full_integration():
    """测试完整集成"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 完整集成（需要Ollama运行）")
    logger.info("=" * 60)

    try:
        from optimized_dual_model_service import get_optimized_service

        service = get_optimized_service(
            model_7b="qwen2.5:7b",
            model_14b="qwen2.5:14b",
            complexity_threshold=5.0
        )

        logger.info("\n注意: 此测试需要 Ollama 正在运行")
        logger.info("并已安装 qwen2.5:7b 和 qwen2.5:14b 模型")

        # 测试简单查询（应该使用7B）
        logger.info("\n测试简单查询:")
        response = service.chat(
            message="59元套餐的分成是多少？",
            context=["59元套餐分成60元，分3期结算。"]
        )
        logger.info(f"成功: {response.success}")
        logger.info(f"模型: {response.model_used}")
        logger.info(f"类型: {response.query_type}")
        logger.info(f"复杂度: {response.complexity_score}")
        logger.info(f"时间: {response.processing_time}s")

        # 测试复杂查询（应该使用14B）
        logger.info("\n测试复杂查询:")
        response = service.chat(
            message="59元套餐和99元套餐的分成有什么区别？",
            context=[
                "59元套餐分成60元，分3期结算。",
                "99元套餐分成80元，分3期结算。"
            ]
        )
        logger.info(f"成功: {response.success}")
        logger.info(f"模型: {response.model_used}")
        logger.info(f"类型: {response.query_type}")
        logger.info(f"复杂度: {response.complexity_score}")
        logger.info(f"时间: {response.processing_time}s")

        # 显示统计
        stats = service.get_statistics()
        logger.info(f"\n统计信息:")
        logger.info(f"  总请求数: {stats['total_requests']}")
        logger.info(f"  7B使用: {stats['7b_count']}")
        logger.info(f"  14B使用: {stats['14b_count']}")
        logger.info(f"  14B比例: {stats['14b_ratio']}%")
        logger.info(f"  平均复杂度: {stats['avg_complexity']:.2f}")

        logger.info("\n✅ 完整集成测试完成")

    except Exception as e:
        logger.warning(f"完整集成测试跳过: {e}")
        logger.info("（这是正常的，如果没有启动Ollama或安装模型）")


def main():
    """主函数"""
    logger.info("\n" + "=" * 60)
    logger.info("优化的双模型系统 - 测试套件")
    logger.info("=" * 60)

    # 运行测试
    test_query_router()
    test_context_manager()
    test_prompt_templates()
    test_full_integration()

    logger.info("\n" + "=" * 60)
    logger.info("所有测试完成！")
    logger.info("=" * 60)

    logger.info("\n下一步:")
    logger.info("1. 确保已安装 qwen2.5:7b 和 qwen2.5:14b 模型")
    logger.info("2. 启动 Ollama 服务")
    logger.info("3. 运行完整集成测试验证功能")
    logger.info("4. 集成到现有的 /api/chat 接口")


if __name__ == "__main__":
    main()
