# business_rules_clarifier.py
"""
业务规则澄清和修正模块
解决常见的概念混淆问题
"""

# ============ 新入网相关优惠活动澄清 ============

NEW_CUSTOMER_PROMPT = """
# 重要：新入网优惠活动区分说明

## 活动一：新入网7折优惠
- **适用套餐**：99元及以上套餐（如129元全家享套餐等）
- **办理路径**：和商汇 → 【入网融合】→ 【一般套餐】→ 个人优惠
- **活动内容**：套餐费用享受7折优惠（如129元折后为89元/月）
- **优惠期限**：12个月或24个月
- **关键特征**：这是"套餐折扣"，不是"流量赠送"

## 活动二：新入网119元套餐10GB流量赠送
- **适用套餐**：119元以上套餐（需当月生效）
- **办理路径**：
  - 和商汇：【套餐】菜单搜索"2025年新入网119元以及上融合套餐叠加流量优惠"
  - 或NGBOSS：搜索特定方案ID（JYPT999.231007997502.0等）
- **活动内容**：每月赠送10GB国内通用流量
- **优惠期限**：6个月/12个月/24个月可选
- **关键条件**：必须在入网31天内办理

## 两者的主要区别：
1. **性质不同**：7折优惠是套餐费用折扣，10GB赠送是额外流量赠送
2. **适用范围不同**：7折优惠适用于99元以上套餐，10GB赠送适用于119元以上套餐
3. **办理路径不同**：7折优惠在【入网融合】菜单，10GB赠送在【套餐】菜单
4. **受益方式不同**：7折优惠直接降低月费，10GB赠送增加流量额度

## 回答问题时请注意：
- 当用户问"7折优惠"时，回答活动一的内容和路径
- 当用户问"流量赠送"或"10GB"时，回答活动二的内容和路径
- 不要将两个活动混淆或混合回答
- 明确说明这是两个不同的优惠活动
"""

# ============ 59元潮玩青春卡套餐完整信息 ============

PACKAGE_59_PROMPT = """
# 59元潮玩青春卡套餐完整信息

## 套餐包含内容（必须全部列出）：
1. **10GB通用流量**：国内通用流量（这是通用流量，不是定向流量！数值是10GB，不是30GB！）
2. **30GB定向流量**：定向应用流量（这是定向流量，不是通用流量！数值是30GB！）
3. **套内通话**：0分钟
4. **套外语音**：0.19元/分钟
5. **套外流量**：5元/GB（不是10元/GB，注意数值准确）
6. **全国亲情网**：统付版内3个移动号码互打免费
7. **40GB中国移动云盘服务**：20G个人云 + 20G家庭云
8. **万能副卡**：不能办理（59元套餐不支持万能副卡，只有59元及以上才能办理）

## ⚠️ 关键区分：通用流量 vs 定向流量
- **通用流量（10GB）**：可以在所有应用和网站使用，没有限制
- **定向流量（30GB）**：只能在特定应用（如咪咕视频、咪咕音乐等）使用
- **常见错误**：将30GB定向流量误认为是30GB通用流量
- **正确说法**：10GB通用流量 + 30GB定向流量

## 重要提醒：
- **10GB通用流量**是套餐的重要组成部分，回答时必须包含，数值是10GB不是30GB
- **30GB定向流量**是定向流量，不能说成通用流量
- 套外流量是**5元/GB**，不是10元/GB
- 59元套餐**不能办理万能副卡**，这点要明确说明

## 检查清单：
回答59元套餐相关问题时，确保包含：
✅ 10GB通用流量（重要！数值是10GB，不是30GB！）
✅ 30GB定向流量（数值是30GB，注意区分！）
✅ 套外语音0.19元/分钟
✅ 套外流量5元/GB
✅ 全国亲情网3个号码
✅ 40GB云盘服务
✅ 不能办理万能副卡

## 回答格式要求：
在【直接回答】中，必须明确区分：
- ✅ 正确：包含10GB通用流量、30GB定向流量
- ❌ 错误：包含30GB通用流量（混淆了通用和定向）
- ❌ 错误：包含10GB定向流量（数值错误）
"""

# ============ 费用计算详细说明 ============

PRICING_CALCULATION_PROMPT = """
# 费用计算详细说明要求

## 回答费用相关问题时必须包含：

### 1. 具体数字
- 所有金额必须精确到元（如：44.5元，不是"约45元"）
- 所有比例必须用百分比或倍数明确表示
- 所有时间必须用具体的月份表示

### 2. 计算过程
对于涉及计算的问题，必须展示：
- **计算公式**：明确列出计算方式
- **计算步骤**：逐步展示计算过程
- **最终结果**：给出明确的计算结果

### 示例：
问题：129元套餐7折后分成如何计算？

正确回答格式：
【直接回答】
办理129元全家享套餐并享受7折优惠后，渠道的套餐分成按实收套餐费89元的50%计算，即每月44.50元。

【详细说明】
根据文档规定，办理129元全家享套餐并享受7折优惠后的费用计算如下：

1. **套餐实收计算**：
   - 原价：129元/月
   - 7折优惠：129元 × 0.7 = 90.3元
   - 月减免：40元
   - 实收：129元 - 40元 = 89元

2. **套餐分成计算**：
   - 分成比例：50%
   - 计算公式：89元 × 50% = 44.5元
   - 发放方式：按实收套餐费的50%计算

3. **服务运营激励**（如有）：
   - 发放周期：T3至T12月（共10个月）
   - 发放比例：实收套餐费的15%
   - 月发放金额：89元 × 15% = 13.35元

【数据来源】
- 12月放号独立部分-酬金.docx
- 12月放号独立部分（政策-操作-ID）.docx

## 常见错误避免：
❌ 不要说"大约"或"大概"
❌ 不要省略计算步骤
❌ 不要遗漏具体数字
❌ 不要混淆时间周期（如T3-T12不要说成T+3至T+7）
"""

# ============ 辅助函数 ============

def detect_question_type(question: str) -> str:
    """
    检测问题类型，返回需要添加的澄清提示

    Args:
        question: 用户问题

    Returns:
        需要添加的提示类型，如"new_customer", "package_59", "pricing"等
    """
    question_lower = question.lower()

    # 检测新入网7折优惠相关问题
    if any(keyword in question for keyword in ["新入网", "7折", "七折", "优惠活动"]):
        if "流量" in question or "10gb" in question:
            return "new_customer_confusion"
        return "new_customer_discount"

    # 检测59元套餐相关问题
    if "59元" in question or "59元套餐" in question or "潮玩青春卡" in question:
        if "套餐" in question and ("包含" in question or "内容" in question or "有什么" in question):
            return "package_59_complete"

    # 检测费用计算相关问题
    if any(keyword in question for keyword in ["费用", "价格", "多少钱", "分成", "激励", "计算"]):
        return "pricing_calculation"

    return None


def get_clarification_prompt(question_type: str) -> str:
    """
    根据问题类型获取相应的澄清提示

    Args:
        question_type: 问题类型

    Returns:
        澄清提示文本
    """
    prompts = {
        "new_customer_confusion": NEW_CUSTOMER_PROMPT,
        "new_customer_discount": NEW_CUSTOMER_PROMPT,
        "package_59_complete": PACKAGE_59_PROMPT,
        "pricing_calculation": PRICING_CALCULATION_PROMPT,
    }

    return prompts.get(question_type, "")


def build_enhanced_prompt(question: str, base_prompt: str) -> str:
    """
    构建增强的提示词，添加业务规则澄清

    Args:
        question: 用户问题
        base_prompt: 基础提示词

    Returns:
        增强后的提示词
    """
    question_type = detect_question_type(question)

    if question_type:
        clarification = get_clarification_prompt(question_type)
        return f"""{base_prompt}

# 特别注意
{clarification}

请基于以上澄清信息和检索到的文档内容回答用户问题。
"""

    return base_prompt


# ============ 验证函数 ============

def validate_answer_59_package(answer: str) -> dict:
    """
    验证59元套餐答案的完整性

    Args:
        answer: 系统生成的答案

    Returns:
        验证结果，包含missing_items列表
    """
    missing_items = []

    # 检查必需的内容
    required_items = {
        "10GB通用流量": ["10gb通用", "10gb通用流量", "10 gb通用"],
        "万能副卡限制": ["不能办理万能副卡", "不支持万能副卡", "不可办理万能副卡"],
        "套外流量5元": ["5元/GB", "5元/gb", "5元gb"],
    }

    answer_lower = answer.lower()

    for item_name, keywords in required_items.items():
        if not any(keyword.lower() in answer_lower for keyword in keywords):
            missing_items.append(item_name)

    return {
        "is_complete": len(missing_items) == 0,
        "missing_items": missing_items,
        "completeness_rate": (3 - len(missing_items)) / 3 * 100
    }


def validate_answer_pricing(answer: str) -> dict:
    """
    验证费用计算答案的完整性

    Args:
        answer: 系统生成的答案

    Returns:
        验证结果
    """
    issues = []

    # 检查是否有具体数字
    if not any(char.isdigit() for char in answer):
        issues.append("缺少具体数字")

    # 检查是否有计算过程
    if "计算" not in answer and "公式" not in answer:
        issues.append("缺少计算过程")

    # 检查是否使用了模糊词汇
    vague_terms = ["大约", "大概", "左右", "约", "可能"]
    if any(term in answer for term in vague_terms):
        issues.append("使用了模糊词汇，应使用精确数字")

    return {
        "has_issues": len(issues) > 0,
        "issues": issues,
        "quality_score": (3 - len(issues)) / 3 * 100
    }


def validate_answer_new_customer(answer: str, question: str) -> dict:
    """
    验证新入网相关答案是否混淆了不同优惠

    Args:
        answer: 系统生成的答案
        question: 用户问题

    Returns:
        验证结果
    """
    issues = []

    # 检查7折优惠问题
    if "7折" in question or "七折" in question:
        # 答案中不应该出现10GB流量赠送的内容
        if "10GB" in answer or "10gb" in answer.lower():
            issues.append("7折优惠问题中错误地包含了10GB流量赠送信息")

        # 答案中应该包含【入网融合】路径
        if "入网融合" not in answer:
            issues.append("7折优惠问题中缺少【入网融合】办理路径")

    # 检查流量赠送问题
    if "流量赠送" in question or "10GB" in question:
        # 答案中不应该出现7折优惠的内容
        if "7折" in answer or "七折" in answer:
            issues.append("流量赠送问题中错误地包含了7折优惠信息")

        # 答案中应该包含【套餐】菜单或NGBOSS路径
        if "套餐" not in answer and "ngboss" not in answer.lower():
            issues.append("流量赠送问题中缺少【套餐】菜单或NGBOSS办理路径")

    return {
        "has_confusion": len(issues) > 0,
        "confusion_issues": issues,
        "clarity_score": (2 - len(issues)) / 2 * 100
    }
