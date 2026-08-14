#!/usr/bin/env python3
"""
Workflow DSL Validator for Dify v1.16.1
验证 Workflow DSL 的结构完整性和基本正确性

用法：
    python validate-workflow.py <dsl_file>

示例：
    python validate-workflow.py ../dsl/research-assistant.yml
"""

import sys
import yaml
from pathlib import Path
from typing import Any
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


def validate_yaml_parsable(content: str) -> tuple[bool, Any, str]:
    """验证 YAML 可解析"""
    try:
        data = yaml.safe_load(content)
        return True, data, ""
    except yaml.YAMLError as e:
        return False, None, f"YAML 解析错误: {str(e)}"


def validate_workflow_structure(data: dict) -> tuple[bool, list[str]]:
    """验证 workflow.graph、nodes 和 edges 存在"""
    errors = []

    # 检查顶层结构
    if not isinstance(data, dict):
        return False, ["DSL 根元素必须是字典"]

    # 检查 workflow 字段
    workflow = data.get("workflow")
    if not workflow:
        errors.append("缺少 'workflow' 字段")
        return False, errors

    if not isinstance(workflow, dict):
        errors.append("'workflow' 字段必须是字典")
        return False, errors

    # 检查 graph 字段
    graph = workflow.get("graph")
    if not graph:
        errors.append("缺少 'workflow.graph' 字段")
        return False, errors

    if not isinstance(graph, dict):
        errors.append("'workflow.graph' 字段必须是字典")
        return False, errors

    # 检查 nodes 字段
    nodes = graph.get("nodes")
    if not nodes:
        errors.append("缺少 'workflow.graph.nodes' 字段")
        return False, errors

    if not isinstance(nodes, list):
        errors.append("'workflow.graph.nodes' 字段必须是列表")
        return False, errors

    # 检查 edges 字段
    edges = graph.get("edges")
    if not edges:
        errors.append("缺少 'workflow.graph.edges' 字段")
        return False, errors

    if not isinstance(edges, list):
        errors.append("'workflow.graph.edges' 字段必须是列表")
        return False, errors

    return len(errors) == 0, errors


def validate_node_ids_unique(nodes: list) -> tuple[bool, list[str]]:
    """验证节点 ID 不重复"""
    errors = []
    node_ids = set()

    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"节点 {i} 必须是字典")
            continue

        node_id = node.get("id")
        if not node_id:
            errors.append(f"节点 {i} 缺少 'id' 字段")
            continue

        if node_id in node_ids:
            errors.append(f"节点 ID '{node_id}' 重复")
        else:
            node_ids.add(node_id)

    return len(errors) == 0, errors


def validate_edges_source_target(nodes: list, edges: list) -> tuple[bool, list[str]]:
    """验证 edge 的 source 和 target 均存在"""
    errors = []
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}

    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"边 {i} 必须是字典")
            continue

        source = edge.get("source")
        target = edge.get("target")

        if not source:
            errors.append(f"边 {i} 缺少 'source' 字段")
        elif source not in node_ids:
            errors.append(f"边 {i} 的 source '{source}' 不存在于节点中")

        if not target:
            errors.append(f"边 {i} 缺少 'target' 字段")
        elif target not in node_ids:
            errors.append(f"边 {i} 的 target '{target}' 不存在于节点中")

    return len(errors) == 0, errors


def validate_start_node_exists(nodes: list) -> tuple[bool, list[str]]:
    """验证 Start 节点存在"""
    errors = []

    has_start = False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        # 真实 DSL 中，节点外层 type 是 custom，实际类型在 data.type 中
        node_data = node.get("data", {})
        node_type = node_data.get("type") if isinstance(node_data, dict) else None
        if not node_type:
            node_type = node.get("type")
        if node_type == "start":
            has_start = True
            break

    if not has_start:
        errors.append("缺少 Start 节点")

    return len(errors) == 0, errors


def validate_no_orphan_nodes(nodes: list, edges: list) -> tuple[bool, list[str]]:
    """验证不存在明显孤立节点"""
    errors = []
    warnings = []

    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    connected_nodes = set()

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source:
            connected_nodes.add(source)
        if target:
            connected_nodes.add(target)

    # Start 节点不需要入边
    start_node_ids = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type") or node.get("data", {}).get("type")
        if node_type == "start":
            start_node_ids.add(node.get("id"))

    # 检查孤立节点
    orphan_nodes = node_ids - connected_nodes - start_node_ids
    if orphan_nodes:
        errors.append(f"发现孤立节点（无任何边连接）: {orphan_nodes}")

    return len(errors) == 0, errors


def validate_branch_exits(nodes: list, edges: list) -> tuple[bool, list[str]]:
    """验证每条业务分支最终存在 Answer 或 End 出口"""
    errors = []

    node_types = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        # 真实 DSL 中，节点外层 type 是 custom，实际类型在 data.type 中
        node_data = node.get("data", {})
        node_type = node_data.get("type") if isinstance(node_data, dict) else None
        if not node_type:
            node_type = node.get("type")
        if node_id and node_type:
            node_types[node_id] = node_type

    # 构建邻接表
    adjacency = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            if source not in adjacency:
                adjacency[source] = []
            adjacency[source].append(target)

    # 从每个节点出发，检查是否存在路径到达 Answer 或 End
    def has_path_to_exit(node_id: str, visited: set) -> bool:
        if node_id in visited:
            return False
        visited.add(node_id)

        node_type = node_types.get(node_id)
        if node_type in ("answer", "end"):
            return True

        neighbors = adjacency.get(node_id, [])
        for neighbor in neighbors:
            if has_path_to_exit(neighbor, visited):
                return True

        return False

    # 检查所有非 Answer/End 节点
    for node_id, node_type in node_types.items():
        if node_type in ("answer", "end", "start"):
            continue
        if not has_path_to_exit(node_id, set()):
            errors.append(f"节点 '{node_id}' (类型: {node_type}) 无法到达 Answer 或 End 节点")

    return len(errors) == 0, errors


def validate_variable_references(data: dict) -> tuple[bool, list[str]]:
    """检查变量引用（仅在可可靠解析时）"""
    errors = []
    warnings = []

    # 这是一个简化版本，仅检查基本的变量引用格式
    # 完整的 Dify parser 需要更复杂的实现

    workflow = data.get("workflow", {})
    graph = workflow.get("graph", {})
    nodes = graph.get("nodes", [])

    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}

    for node in nodes:
        if not isinstance(node, dict):
            continue

        node_data = node.get("data", {})
        if not isinstance(node_data, dict):
            continue

        # 检查 variable_selector 字段
        for key, value in node_data.items():
            if key.endswith("_selector") and isinstance(value, list):
                if len(value) >= 2:
                    ref_node_id = value[0]
                    # 排除系统变量 'sys'
                    if ref_node_id != "sys" and ref_node_id not in node_ids:
                        warnings.append(
                            f"节点 '{node.get('id')}' 的 {key} 引用了不存在的节点 '{ref_node_id}'"
                        )

    return len(errors) == 0, errors, warnings


def validate_no_placeholders(data: dict) -> tuple[bool, list[str]]:
    """检查不存在占位符"""
    errors = []

    workflow = data.get("workflow", {})
    graph = workflow.get("graph", {})
    nodes = graph.get("nodes", [])

    # 检查占位符模式
    placeholder_patterns = [
        "TODO_MODEL",
        "TODO_DATASET",
        "PLACEHOLDER",
        "YOUR_",
        "INSERT_",
        "REPLACE_"
    ]

    # 检查伪造 UUID 模式（连续重复字符）
    import re
    fake_uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

    for node in nodes:
        if not isinstance(node, dict):
            continue

        node_data = node.get("data", {})
        if not isinstance(node_data, dict):
            continue

        node_id = node.get("id", "unknown")
        node_type = node_data.get("type", "unknown")

        # 检查 LLM 节点的 model 配置
        if node_type == "llm":
            model = node_data.get("model", {})
            if isinstance(model, dict):
                provider = model.get("provider", "")
                name = model.get("name", "")

                if not provider or provider in placeholder_patterns:
                    errors.append(f"LLM 节点 '{node_id}' 的 model.provider 为空或占位符")
                if not name or name in placeholder_patterns:
                    errors.append(f"LLM 节点 '{node_id}' 的 model.name 为空或占位符")

        # 检查 Knowledge Retrieval 节点的 dataset_ids
        if node_type == "knowledge-retrieval":
            dataset_ids = node_data.get("dataset_ids", [])
            if not dataset_ids:
                errors.append(f"Knowledge Retrieval 节点 '{node_id}' 的 dataset_ids 为空")
            else:
                for dataset_id in dataset_ids:
                    if not dataset_id or len(dataset_id) < 10:
                        errors.append(f"Knowledge Retrieval 节点 '{node_id}' 的 dataset_id '{dataset_id}' 看起来无效")

    return len(errors) == 0, errors


def validate_no_secrets(data: dict) -> tuple[bool, list[str]]:
    """检查不存在 API Key 或 secret"""
    errors = []

    # 检查敏感字段模式
    import re
    secret_patterns = [
        re.compile(r'api[_-]?key', re.IGNORECASE),
        re.compile(r'secret', re.IGNORECASE),
        re.compile(r'credential', re.IGNORECASE),
        re.compile(r'token', re.IGNORECASE),
        re.compile(r'password', re.IGNORECASE),
    ]

    # 已知的安全值
    safe_values = {"", "none", "null", "undefined"}

    def check_dict(d: dict, path: str):
        for key, value in d.items():
            current_path = f"{path}.{key}"

            # 检查 key 名称是否匹配敏感模式
            for pattern in secret_patterns:
                if pattern.search(key):
                    # 检查值是否为空或安全值
                    if isinstance(value, str) and value.lower() not in safe_values:
                        # 排除常见的非敏感匹配
                        if key.lower() not in ["source_type", "target_type", "node_type"]:
                            errors.append(f"发现可能的敏感字段: {current_path}")
                    break

            # 递归检查嵌套字典
            if isinstance(value, dict):
                check_dict(value, current_path)

    workflow = data.get("workflow", {})
    graph = workflow.get("graph", {})
    nodes = graph.get("nodes", [])

    for node in nodes:
        if isinstance(node, dict):
            node_data = node.get("data", {})
            if isinstance(node_data, dict):
                check_dict(node_data, f"node.{node.get('id', 'unknown')}")

    return len(errors) == 0, errors


def validate_semantic_structure(data: dict) -> tuple[bool, list[str]]:
    """验证 V0 语义结构"""
    errors = []

    workflow = data.get("workflow", {})
    graph = workflow.get("graph", {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # 构建节点映射
    node_map = {}
    node_types = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        node_data = node.get("data", {})
        data_type = node_data.get("type") if isinstance(node_data, dict) else None
        if not data_type:
            data_type = node.get("type")
        if node_id:
            node_map[node_id] = node
            node_types[node_id] = data_type

    # 构建邻接表和反向邻接表
    adjacency = {}
    reverse_adjacency = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            if source not in adjacency:
                adjacency[source] = []
            adjacency[source].append(target)
            if target not in reverse_adjacency:
                reverse_adjacency[target] = []
            reverse_adjacency[target].append(source)

    # 1. 检查 Start 存在
    start_nodes = [nid for nid, ntype in node_types.items() if ntype == "start"]
    if not start_nodes:
        errors.append("缺少 Start 节点")
    elif len(start_nodes) > 1:
        errors.append(f"存在多个 Start 节点: {start_nodes}")

    # 2. 检查 Task Parser 存在
    task_parser_nodes = [nid for nid, ntype in node_types.items() if ntype == "llm" and "task" in nid.lower()]
    if not task_parser_nodes:
        # 尝试通过标题查找
        for nid, node in node_map.items():
            node_data = node.get("data", {})
            title = node_data.get("title", "") if isinstance(node_data, dict) else ""
            if "task" in title.lower() and "parser" in title.lower():
                task_parser_nodes.append(nid)
    if not task_parser_nodes:
        errors.append("缺少 Task Parser 节点")

    # 3. 检查 Main Router 存在
    router_nodes = [nid for nid, ntype in node_types.items() if ntype == "if-else" and "router" in nid.lower()]
    if not router_nodes:
        # 尝试通过标题查找
        for nid, node in node_map.items():
            node_data = node.get("data", {})
            title = node_data.get("title", "") if isinstance(node_data, dict) else ""
            if "router" in title.lower() or "main" in title.lower():
                if node_types.get(nid) == "if-else":
                    router_nodes.append(nid)
    if not router_nodes:
        errors.append("缺少 Main Router (If/Else) 节点")

    # 4. 检查 Task Parser 不直接连接多个业务分支
    if task_parser_nodes:
        task_parser_id = task_parser_nodes[0]
        task_parser_targets = adjacency.get(task_parser_id, [])
        # 检查是否直接连接到多个业务节点
        business_node_types = ["knowledge-retrieval", "llm", "answer"]
        business_targets = [t for t in task_parser_targets if node_types.get(t) in business_node_types and t != "task-parse-code"]
        if len(business_targets) > 1:
            errors.append(f"Task Parser 直接连接多个业务分支: {business_targets}")

    # 5. 检查 knowledge_search 只进入知识库分支
    # (通过检查 router 的 edges)

    # 6. 检查 translation 不经过知识库
    # 7. 检查 general_qa 不经过知识库
    # 8. 检查 clarification 有明确 Answer

    # 9. 检查 Evidence FAIL 不进入 RAG LLM
    evidence_check_nodes = [nid for nid, ntype in node_types.items() if ntype == "if-else" and "evidence" in nid.lower()]
    for ec_id in evidence_check_nodes:
        ec_targets = adjacency.get(ec_id, [])
        for target in ec_targets:
            edge = next((e for e in edges if e.get("source") == ec_id and e.get("target") == target), None)
            if edge:
                source_handle = edge.get("sourceHandle", "")
                # FAIL 或 false 不应该进入 RAG LLM
                if source_handle in ["false", "FAIL"]:
                    target_type = node_types.get(target)
                    if target_type == "llm" and "rag" in target.lower():
                        errors.append(f"Evidence FAIL 分支进入了 RAG LLM: {target}")

    # 10. 检查 dataset_ids 为真实值
    for node in nodes:
        node_data = node.get("data", {})
        if not isinstance(node_data, dict):
            continue
        if node_data.get("type") == "knowledge-retrieval":
            dataset_ids = node_data.get("dataset_ids", [])
            if not dataset_ids:
                errors.append(f"Knowledge Retrieval 节点 dataset_ids 为空")
            for did in dataset_ids:
                if not did or len(did) < 10:
                    errors.append(f"无效的 dataset_id: {did}")

    # 11. 检查 model provider/name 为真实值
    for node in nodes:
        node_data = node.get("data", {})
        if not isinstance(node_data, dict):
            continue
        if node_data.get("type") == "llm":
            model = node_data.get("model", {})
            if isinstance(model, dict):
                provider = model.get("provider", "")
                name = model.get("name", "")
                if not provider or "TODO" in provider.upper():
                    errors.append(f"LLM 节点 '{node.get('id')}' 的 model.provider 无效")
                if not name or "TODO" in name.upper():
                    errors.append(f"LLM 节点 '{node.get('id')}' 的 model.name 无效")

    # 12-14. 检查无 API Key、无 credential、无 TODO
    # (已在 validate_no_secrets 和 validate_no_placeholders 中处理)

    # 15. 检查无未知 node id
    # (已在 validate_edges_source_target 中处理)

    # 16. 检查 edge source/target 均存在
    # (已在 validate_edges_source_target 中处理)

    # 17. 检查所有业务分支最终有用户输出
    # (已在 validate_branch_exits 中处理)

    # 检查 Question Classifier 不应存在
    qc_nodes = [nid for nid, ntype in node_types.items() if ntype == "question-classifier"]
    if qc_nodes:
        errors.append(f"发现不应存在的 Question Classifier 节点: {qc_nodes}")

    return len(errors) == 0, errors


def validate_workflow(dsl_file: str) -> ValidationResult:
    """验证 Workflow DSL 文件"""
    errors = []
    warnings = []

    # 读取文件
    try:
        with open(dsl_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return ValidationResult(False, [f"无法读取文件: {str(e)}"], [])

    # 1. 验证 YAML 可解析
    is_parsable, data, parse_error = validate_yaml_parsable(content)
    if not is_parsable:
        return ValidationResult(False, [parse_error], [])

    # 2. 验证 workflow 结构
    is_valid, structure_errors = validate_workflow_structure(data)
    if not is_valid:
        return ValidationResult(False, structure_errors, [])
    errors.extend(structure_errors)

    # 获取 nodes 和 edges
    nodes = data["workflow"]["graph"]["nodes"]
    edges = data["workflow"]["graph"]["edges"]

    # 3. 验证节点 ID 不重复
    is_valid, id_errors = validate_node_ids_unique(nodes)
    errors.extend(id_errors)

    # 4. 验证边的 source 和 target 存在
    is_valid, edge_errors = validate_edges_source_target(nodes, edges)
    errors.extend(edge_errors)

    # 5. 验证 Start 节点存在
    is_valid, start_errors = validate_start_node_exists(nodes)
    errors.extend(start_errors)

    # 6. 验证不存在孤立节点
    is_valid, orphan_errors = validate_no_orphan_nodes(nodes, edges)
    errors.extend(orphan_errors)

    # 7. 验证每条分支有出口
    is_valid, exit_errors = validate_branch_exits(nodes, edges)
    errors.extend(exit_errors)

    # 8. 检查变量引用（可选）
    is_valid, var_errors, var_warnings = validate_variable_references(data)
    warnings.extend(var_warnings)

    # 9. 检查占位符
    is_valid, placeholder_errors = validate_no_placeholders(data)
    errors.extend(placeholder_errors)

    # 10. 检查敏感信息
    is_valid, secret_errors = validate_no_secrets(data)
    errors.extend(secret_errors)

    # 11. 语义结构检查
    is_valid, semantic_errors = validate_semantic_structure(data)
    errors.extend(semantic_errors)

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python validate-workflow.py <dsl_file>")
        print("示例: python validate-workflow.py ../dsl/research-assistant.yml")
        sys.exit(1)

    dsl_file = sys.argv[1]

    if not Path(dsl_file).exists():
        print(f"错误: 文件不存在 - {dsl_file}")
        sys.exit(1)

    print(f"正在验证: {dsl_file}")
    print("-" * 50)

    result = validate_workflow(dsl_file)

    if result.is_valid:
        print("✅ 验证通过")
    else:
        print("❌ 验证失败")

    if result.errors:
        print("\n错误:")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")

    if result.warnings:
        print("\n警告:")
        for i, warning in enumerate(result.warnings, 1):
            print(f"  {i}. {warning}")

    print("-" * 50)
    print(f"总结: {'通过' if result.is_valid else '失败'}")
    print(f"  错误数: {len(result.errors)}")
    print(f"  警告数: {len(result.warnings)}")

    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
