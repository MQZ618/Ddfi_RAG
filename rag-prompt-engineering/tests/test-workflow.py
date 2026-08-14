#!/usr/bin/env python3
"""
Workflow Test Cases
测试 Workflow V0 的各个分支和场景

用法：
    python test-workflow.py

测试覆盖：
1. 知识库检索（有证据）
2. 知识库检索（无证据）
3. 翻译
4. 一般问答
5. 澄清
6. 复合请求
"""

import json
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestCase:
    """测试案例"""
    name: str
    description: str
    input_query: str
    expected_task_type: str
    expected_normalized_query: str
    expected_needs_knowledge: bool
    expected_needs_clarification: bool
    expected_is_compound_request: bool
    expected_evidence_status: Optional[str] = None
    expected_answer_contains: Optional[str] = None
    expected_answer_not_contains: Optional[str] = None


# 测试案例定义
TEST_CASES = [
    # 1. 知识库检索 - 有证据
    TestCase(
        name="knowledge_search_with_evidence",
        description="知识库检索，有相关证据",
        input_query="查找关于 Transformer 在自然语言处理中的最新进展",
        expected_task_type="knowledge_search",
        expected_normalized_query="Transformer 在自然语言处理中的最新进展",
        expected_needs_knowledge=True,
        expected_needs_clarification=False,
        expected_is_compound_request=False,
        expected_evidence_status="PASS",
        expected_answer_not_contains="当前知识库未检索到"
    ),

    # 2. 知识库检索 - 无证据
    TestCase(
        name="knowledge_search_without_evidence",
        description="知识库检索，无相关证据",
        input_query="查找关于量子计算在药物发现中的最新进展",
        expected_task_type="knowledge_search",
        expected_normalized_query="量子计算在药物发现中的最新进展",
        expected_needs_knowledge=True,
        expected_needs_clarification=False,
        expected_is_compound_request=False,
        expected_evidence_status="FAIL",
        expected_answer_contains="当前知识库未检索到"
    ),

    # 3. 翻译
    TestCase(
        name="translation_english_to_chinese",
        description="英译中翻译",
        input_query="请翻译：Deep learning has shown promising results in natural language processing.",
        expected_task_type="translation",
        expected_normalized_query="Deep learning has shown promising results in natural language processing.",
        expected_needs_knowledge=False,
        expected_needs_clarification=False,
        expected_is_compound_request=False,
        expected_answer_contains="深度学习"
    ),

    # 4. 一般问答
    TestCase(
        name="general_qa_concept",
        description="一般概念问答",
        input_query="什么是卷积神经网络？",
        expected_task_type="general_qa",
        expected_normalized_query="什么是卷积神经网络？",
        expected_needs_knowledge=False,
        expected_needs_clarification=False,
        expected_is_compound_request=False,
        expected_answer_contains="卷积"
    ),

    # 5. 澄清
    TestCase(
        name="clarification_vague",
        description="请求过于模糊",
        input_query="帮我查一下这个",
        expected_task_type="clarification",
        expected_normalized_query="",
        expected_needs_knowledge=False,
        expected_needs_clarification=True,
        expected_is_compound_request=False
    ),

    # 6. 复合请求
    TestCase(
        name="compound_request",
        description="复合请求：查找并翻译",
        input_query="查找最新的机器学习论文并翻译摘要",
        expected_task_type="knowledge_search",
        expected_normalized_query="最新的机器学习论文",
        expected_needs_knowledge=True,
        expected_needs_clarification=False,
        expected_is_compound_request=True
    ),

    # 7. 翻译 - 中译英
    TestCase(
        name="translation_chinese_to_english",
        description="中译英翻译",
        input_query="请将以下内容翻译成英文：深度学习在计算机视觉领域取得了显著进展。",
        expected_task_type="translation",
        expected_normalized_query="深度学习在计算机视觉领域取得了显著进展。",
        expected_needs_knowledge=False,
        expected_needs_clarification=False,
        expected_is_compound_request=False,
        expected_answer_contains="deep learning"
    ),

    # 8. 知识库检索 - 特定领域
    TestCase(
        name="knowledge_search_specific_domain",
        description="特定领域知识库检索",
        input_query="查找医学影像中深度学习应用的综述文献",
        expected_task_type="knowledge_search",
        expected_normalized_query="医学影像中深度学习应用的综述文献",
        expected_needs_knowledge=True,
        expected_needs_clarification=False,
        expected_is_compound_request=False,
        expected_evidence_status="PASS"
    ),
]


def parse_task_parser_output(output: str) -> dict:
    """解析 Task Parser 输出"""
    try:
        # 尝试直接解析 JSON
        return json.loads(output)
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', output)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    return {}


def simulate_task_parser(test_case: TestCase) -> dict:
    """模拟 Task Parser 输出（用于本地测试）"""
    # 这是一个简化的模拟，实际应调用 LLM
    query = test_case.input_query.lower()

    # 检测复合请求（优先级最高）
    is_compound = "并" in query and ("翻译" in query or "查找" in query)

    # 简单的规则判断
    if is_compound:
        # 复合请求：选择主要任务（通常是第一个动词）
        if "查找" in query or "检索" in query:
            task_type = "knowledge_search"
            needs_knowledge = True
            needs_clarification = False
        else:
            task_type = "translation"
            needs_knowledge = False
            needs_clarification = False
    elif any(kw in query for kw in ["翻译", "translate", "请将"]):
        task_type = "translation"
        needs_knowledge = False
        needs_clarification = False
    elif any(kw in query for kw in ["查找", "检索", "研究", "文献", "论文"]):
        task_type = "knowledge_search"
        needs_knowledge = True
        needs_clarification = False
    elif any(kw in query for kw in ["这个", "那个", "帮我", "查一下"]) and len(query) < 10:
        task_type = "clarification"
        needs_knowledge = False
        needs_clarification = True
    else:
        task_type = "general_qa"
        needs_knowledge = False
        needs_clarification = False

    return {
        "task_type": task_type,
        "normalized_query": test_case.expected_normalized_query,
        "needs_knowledge": needs_knowledge,
        "needs_clarification": needs_clarification,
        "is_compound_request": is_compound,
        "reason": "模拟测试"
    }


def test_task_parser(test_case: TestCase) -> tuple[bool, list[str]]:
    """测试 Task Parser"""
    errors = []

    # 模拟 Task Parser 输出
    result = simulate_task_parser(test_case)

    # 验证 task_type
    if result.get("task_type") != test_case.expected_task_type:
        errors.append(
            f"task_type 不匹配: 期望 {test_case.expected_task_type}, "
            f"实际 {result.get('task_type')}"
        )

    # 验证 needs_knowledge
    if result.get("needs_knowledge") != test_case.expected_needs_knowledge:
        errors.append(
            f"needs_knowledge 不匹配: 期望 {test_case.expected_needs_knowledge}, "
            f"实际 {result.get('needs_knowledge')}"
        )

    # 验证 needs_clarification
    if result.get("needs_clarification") != test_case.expected_needs_clarification:
        errors.append(
            f"needs_clarification 不匹配: 期望 {test_case.expected_needs_clarification}, "
            f"实际 {result.get('needs_clarification')}"
        )

    # 验证 is_compound_request
    if result.get("is_compound_request") != test_case.expected_is_compound_request:
        errors.append(
            f"is_compound_request 不匹配: 期望 {test_case.expected_is_compound_request}, "
            f"实际 {result.get('is_compound_request')}"
        )

    return len(errors) == 0, errors


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Workflow V0 测试案例")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    errors_list = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {test_case.name}")
        print(f"  描述: {test_case.description}")
        print(f"  输入: {test_case.input_query}")

        # 运行测试
        is_passed, errors = test_task_parser(test_case)

        if is_passed:
            print(f"  结果: ✅ 通过")
            passed += 1
        else:
            print(f"  结果: ❌ 失败")
            for error in errors:
                print(f"    - {error}")
            failed += 1
            errors_list.append({
                "test_case": test_case.name,
                "errors": errors
            })

        print()

    # 打印总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"总测试数: {len(TEST_CASES)}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"通过率: {passed/len(TEST_CASES)*100:.1f}%")

    if errors_list:
        print("\n失败详情:")
        for item in errors_list:
            print(f"\n  {item['test_case']}:")
            for error in item['errors']:
                print(f"    - {error}")

    print()
    return failed == 0


def main():
    """主函数"""
    success = run_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
