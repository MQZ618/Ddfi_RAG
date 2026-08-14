#!/usr/bin/env python3
"""
DSL Diff Script
比较两个 DSL 文件的差异

用法：
    python diff-dsl.py <file1> <file2>

示例：
    python diff-dsl.py ../dsl/base-export.yml ../dsl/research-assistant.yml
"""

import argparse
import sys
import yaml
from pathlib import Path
from typing import Any


def load_dsl(file_path: str) -> dict:
    """加载 DSL 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"错误: 无法读取文件 {file_path} - {str(e)}")
        sys.exit(1)


def get_node_dict(nodes: list) -> dict:
    """将节点列表转换为字典"""
    result = {}
    for node in nodes:
        if isinstance(node, dict):
            node_id = node.get("id")
            if node_id:
                result[node_id] = node
    return result


def get_edge_key(edge: dict) -> str:
    """获取边的唯一标识"""
    source = edge.get("source", "")
    target = edge.get("target", "")
    source_handle = edge.get("sourceHandle", "")
    return f"{source}->{target}:{source_handle}"


def compare_values(path: str, val1: Any, val2: Any, differences: list):
    """递归比较两个值"""
    if type(val1) != type(val2):
        differences.append({
            "path": path,
            "type": "type_changed",
            "old": type(val1).__name__,
            "new": type(val2).__name__
        })
        return

    if isinstance(val1, dict):
        all_keys = set(val1.keys()) | set(val2.keys())
        for key in sorted(all_keys):
            new_path = f"{path}.{key}"
            if key not in val1:
                differences.append({
                    "path": new_path,
                    "type": "added",
                    "new": val2[key]
                })
            elif key not in val2:
                differences.append({
                    "path": new_path,
                    "type": "removed",
                    "old": val1[key]
                })
            else:
                compare_values(new_path, val1[key], val2[key], differences)
    elif isinstance(val1, list):
        if len(val1) != len(val2):
            differences.append({
                "path": path,
                "type": "length_changed",
                "old": len(val1),
                "new": len(val2)
            })
        for i in range(min(len(val1), len(val2))):
            compare_values(f"{path}[{i}]", val1[i], val2[i], differences)
    else:
        if val1 != val2:
            differences.append({
                "path": path,
                "type": "changed",
                "old": val1,
                "new": val2
            })


def compare_nodes(nodes1: list, nodes2: list) -> list:
    """比较节点差异"""
    differences = []
    dict1 = get_node_dict(nodes1)
    dict2 = get_node_dict(nodes2)

    all_ids = set(dict1.keys()) | set(dict2.keys())

    for node_id in sorted(all_ids):
        if node_id not in dict1:
            differences.append({
                "path": f"workflow.graph.nodes.{node_id}",
                "type": "added",
                "new": dict2[node_id]
            })
        elif node_id not in dict2:
            differences.append({
                "path": f"workflow.graph.nodes.{node_id}",
                "type": "removed",
                "old": dict1[node_id]
            })
        else:
            compare_values(
                f"workflow.graph.nodes.{node_id}",
                dict1[node_id],
                dict2[node_id],
                differences
            )

    return differences


def compare_edges(edges1: list, edges2: list) -> list:
    """比较边差异"""
    differences = []
    dict1 = {get_edge_key(e): e for e in edges1 if isinstance(e, dict)}
    dict2 = {get_edge_key(e): e for e in edges2 if isinstance(e, dict)}

    all_keys = set(dict1.keys()) | set(dict2.keys())

    for edge_key in sorted(all_keys):
        if edge_key not in dict1:
            differences.append({
                "path": f"workflow.graph.edges.{edge_key}",
                "type": "added",
                "new": dict2[edge_key]
            })
        elif edge_key not in dict2:
            differences.append({
                "path": f"workflow.graph.edges.{edge_key}",
                "type": "removed",
                "old": dict1[edge_key]
            })
        else:
            compare_values(
                f"workflow.graph.edges.{edge_key}",
                dict1[edge_key],
                dict2[edge_key],
                differences
            )

    return differences


def compare_dsl(file1: str, file2: str) -> list:
    """比较两个 DSL 文件"""
    dsl1 = load_dsl(file1)
    dsl2 = load_dsl(file2)

    differences = []

    # 比较顶层字段
    compare_values("app", dsl1.get("app", {}), dsl2.get("app", {}), differences)

    # 比较 workflow
    workflow1 = dsl1.get("workflow", {})
    workflow2 = dsl2.get("workflow", {})

    # 比较 features
    compare_values("workflow.features", workflow1.get("features", {}), workflow2.get("features", {}), differences)

    # 比较 graph
    graph1 = workflow1.get("graph", {})
    graph2 = workflow2.get("graph", {})

    # 比较 nodes
    nodes_diff = compare_nodes(graph1.get("nodes", []), graph2.get("nodes", []))
    differences.extend(nodes_diff)

    # 比较 edges
    edges_diff = compare_edges(graph1.get("edges", []), graph2.get("edges", []))
    differences.extend(edges_diff)

    return differences


def format_diff(diff: dict) -> str:
    """格式化差异"""
    path = diff["path"]
    diff_type = diff["type"]

    if diff_type == "added":
        return f"+ {path}: 新增"
    elif diff_type == "removed":
        return f"- {path}: 删除"
    elif diff_type == "changed":
        old = str(diff["old"])[:50]
        new = str(diff["new"])[:50]
        return f"~ {path}: {old} -> {new}"
    elif diff_type == "type_changed":
        return f"~ {path}: 类型从 {diff['old']} 变为 {diff['new']}"
    elif diff_type == "length_changed":
        return f"~ {path}: 长度从 {diff['old']} 变为 {diff['new']}"
    else:
        return f"? {path}: 未知变化"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="比较两个 DSL 文件的差异")
    parser.add_argument("file1", help="第一个 DSL 文件")
    parser.add_argument("file2", help="第二个 DSL 文件")

    args = parser.parse_args()

    # 检查文件是否存在
    if not Path(args.file1).exists():
        print(f"错误: 文件不存在 - {args.file1}")
        sys.exit(1)

    if not Path(args.file2).exists():
        print(f"错误: 文件不存在 - {args.file2}")
        sys.exit(1)

    print(f"比较: {args.file1} vs {args.file2}")
    print("-" * 50)

    differences = compare_dsl(args.file1, args.file2)

    if not differences:
        print("✅ 两个文件完全相同")
    else:
        print(f"发现 {len(differences)} 处差异:\n")
        for diff in differences:
            print(format_diff(diff))

    print("-" * 50)
    print(f"差异总数: {len(differences)}")

    # 统计不同类型的差异
    added = sum(1 for d in differences if d["type"] == "added")
    removed = sum(1 for d in differences if d["type"] == "removed")
    changed = sum(1 for d in differences if d["type"] in ("changed", "type_changed", "length_changed"))

    print(f"  新增: {added}")
    print(f"  删除: {removed}")
    print(f"  修改: {changed}")


if __name__ == "__main__":
    main()
