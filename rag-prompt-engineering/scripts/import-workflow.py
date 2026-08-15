#!/usr/bin/env python3
"""
Workflow Import Script
将 Workflow DSL 导入到 Dify 实例

用法：
    python import-workflow.py --dsl-file <dsl_file> [--app-id <app_id>]

环境变量：
    DIFY_API_URL: Dify API 地址（默认 http://localhost:80/v1）
    DIFY_API_KEY: Dify API 密钥

示例：
    # 创建新 App
    export DIFY_API_URL=http://localhost:80/v1
    export DIFY_API_KEY=app-xxxxxxxxxxxx
    python import-workflow.py --dsl-file ../dsl/research-assistant.yml

    # 更新现有 App
    python import-workflow.py --dsl-file ../dsl/research-assistant.yml --app-id xxx-xxx-xxx
"""

import argparse
import os
import sys
import requests
import yaml
from pathlib import Path


def get_api_config() -> tuple[str, str]:
    """获取 API 配置"""
    api_url = os.environ.get("DIFY_API_URL", "http://localhost:80/v1")
    api_key = os.environ.get("DIFY_API_KEY", "")

    if not api_key:
        print("错误: 请设置 DIFY_API_KEY 环境变量")
        sys.exit(1)

    return api_url, api_key


def import_workflow(api_url: str, api_key: str, dsl_file: str, app_id: str = None) -> dict:
    """导入 Workflow DSL"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 读取 DSL 文件
    try:
        with open(dsl_file, 'r', encoding='utf-8') as f:
            dsl_data = yaml.safe_load(f)
    except Exception as e:
        print(f"错误: 无法读取 DSL 文件 - {str(e)}")
        sys.exit(1)

    # 准备导入数据
    import_data = {
        "mode": "yaml-content",
        "yaml_content": yaml.dump(dsl_data, allow_unicode=True)
    }

    if app_id:
        import_data["app_id"] = app_id

    # 导入 DSL
    import_url = f"{api_url}/apps/imports"
    try:
        response = requests.post(import_url, headers=headers, json=import_data)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"错误: 导入失败 - {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应内容: {e.response.text}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="将 Workflow DSL 导入到 Dify 实例")
    parser.add_argument("--dsl-file", required=True, help="DSL 文件路径")
    parser.add_argument("--app-id", help="App ID（更新现有 App）")
    parser.add_argument("--dry-run", action="store_true", help="仅验证，不实际导入")

    args = parser.parse_args()

    # 检查 DSL 文件是否存在
    if not Path(args.dsl_file).exists():
        print(f"错误: DSL 文件不存在 - {args.dsl_file}")
        sys.exit(1)

    # 获取 API 配置
    api_url, api_key = get_api_config()

    # 验证 DSL 文件
    print(f"正在验证: {args.dsl_file}")
    try:
        with open(args.dsl_file, 'r', encoding='utf-8') as f:
            dsl_data = yaml.safe_load(f)

        # 基本验证
        if "workflow" not in dsl_data:
            print("错误: DSL 文件缺少 workflow 字段")
            sys.exit(1)

        graph = dsl_data["workflow"].get("graph", {})
        if "nodes" not in graph:
            print("错误: DSL 文件缺少 nodes 字段")
            sys.exit(1)

        if "edges" not in graph:
            print("错误: DSL 文件缺少 edges 字段")
            sys.exit(1)

        print("✅ DSL 文件格式验证通过")
    except yaml.YAMLError as e:
        print(f"错误: YAML 解析失败 - {str(e)}")
        sys.exit(1)

    if args.dry_run:
        print("✅ 干运行完成，DSL 文件有效")
        sys.exit(0)

    # 导入 DSL
    if args.app_id:
        print(f"正在更新 App {args.app_id}...")
    else:
        print("正在创建新 App...")

    result = import_workflow(api_url, api_key, args.dsl_file, args.app_id)

    # 显示结果
    if result.get("status") == "completed":
        print("✅ 导入成功")
        print(f"  App ID: {result.get('app_id')}")
        print(f"  App 模式: {result.get('app_mode')}")
    elif result.get("status") == "completed_with_warnings":
        print("⚠️ 导入成功（有警告）")
        print(f"  App ID: {result.get('app_id')}")
        print(f"  App 模式: {result.get('app_mode')}")
        print("  警告:")
        for warning in result.get("warnings", []):
            print(f"    - {warning.get('message')}")
    else:
        print("❌ 导入失败")
        print(f"  错误: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
