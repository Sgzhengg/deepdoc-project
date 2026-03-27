"""
重新加载表格数据，修复表头解析问题
"""

import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from agents.enhanced_table_analyzer import ChannelTableAnalyzer

def reload_tables():
    """重新加载所有表格"""
    print("=" * 80)
    print("重新加载表格数据")
    print("=" * 80)

    # 初始化表格分析器
    analyzer = ChannelTableAnalyzer()

    # 清空现有表格
    analyzer.tables = []
    print(f"\n已清空现有表格数据")

    # 重新加载文档
    doc_path = 'c:/Users/Administrator/Desktop/12月渠道政策/12月放号独立部分（政策-操作-ID）.docx'

    if os.path.exists(doc_path):
        print(f"\n正在加载文档: {doc_path}")
        new_tables = analyzer.load_from_docx(doc_path)
        print(f"[成功] 成功加载 {len(new_tables)} 个表格")
    else:
        print(f"[失败] 文档不存在: {doc_path}")
        return

    # 查找59元潮玩青春卡所在的表格
    print("\n" + "=" * 80)
    print("检查59元潮玩青春卡表格")
    print("=" * 80)

    for table in analyzer.tables:
        for row in table.data:
            if '59元潮玩青春卡' in str(row):
                print(f"\n表格索引: {table.index}")
                print(f"表头: {table.headers}")
                print(f"\n59元潮玩青春卡数据行:")
                print(row)
                break

    # 保存到缓存
    print("\n" + "=" * 80)
    print("保存表格缓存")
    print("=" * 80)

    success = analyzer.save_tables_to_cache()
    if success:
        print("[成功] 表格缓存已更新")
        print(f"缓存文件: {analyzer.TABLES_CACHE_FILE}")
    else:
        print("[失败] 保存缓存失败")

    # 显示表头对比
    print("\n" + "=" * 80)
    print("表头对比（修复前后）")
    print("=" * 80)

    print("\n修复前的表头（有重复）:")
    print("['套餐名称', '方案ID', '套内资费', '套内资费', '套内资费', ...]")

    print("\n修复后的表头:")
    for table in analyzer.tables:
        if table.index == 0:  # 第一个表格
            print(f"表格{table.index}: {table.headers[:6]}")
            break

if __name__ == "__main__":
    try:
        reload_tables()
        print("\n" + "=" * 80)
        print("[完成] 表格重新加载完成")
        print("=" * 80)
    except Exception as e:
        print(f"\n[错误] 重新加载失败：{e}")
        import traceback
        traceback.print_exc()
