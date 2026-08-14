#!/usr/bin/env python3
"""
Workflow Export Script
从 Dify 实例导出 Workflow DSL

用法：
    python export-workflow.py --app-id <app_id> --output <output_file>

环境变量：
    DIFY_API_URL: Dify API 地址（默认 http://localhost:80/v1）
    DIFY_API_KEY: Dify API 密钥

示例：
    export DIFY_API_URL=http://localhost:80/v1
    export DIFY_API_KEY=app-xxxxxxxxxxxx
    python export-workflow.py --app-id xxx-xxx-xxx --output ../dsl/base-export.yml
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


def export_workflow(api_url: str, api_key: str, app_id: str) -> dict:
    """导出 Workflow DSL"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 获取 App 信息
    app_url = f"{api_url}/apps/{app_id}"
    try:
        response = requests.get(app_url, headers=headers)
        response.raise_for_status()
        app_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"错误: 无法获取 App 信息 - {str(e)}")
        sys.exit(1)

    # 获取 Workflow 信息
    workflow_url = f"{api_url}/apps/{app_id}/workflows/publish"
    try:
        response = requests.get(workflow_url, headers=headers)
        response.raise_for_status()
        workflow_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"错误: 无法获取 Workflow 信息 - {str(e)}")
        sys.exit(1)

    # 构建 DSL 结构
    dsl_data = {
        "version": "0.1.5",
        "kind": "app",
        "app": {
            "name": app_data.get("name", ""),
            "mode": app_data.get("mode", ""),
            "icon": app_data.get("icon", ""),
            "icon_type": app_data.get("icon_type", "emoji"),
            "icon_background": app_data.get("icon_background", "#FFFFFF"),
            "description": app_data.get("description", ""),
            "use_icon_as_answer_icon": app_data.get("use_icon_as_answer_icon", False)
        },
        "workflow": workflow_data
    }

    return dsl_data


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="从 Dify 实例导出 Workflow DSL")
    parser.add_argument("--app-id", required=True, help="App ID")
    parser.add_argument("--output", required=True, help="输出文件路径")
    parser.add_argument("--include-secret", action="store_true", help="包含敏感信息")

    args = parser.parse_args()

    # 检查输出文件是否已存在
    output_path = Path(args.output)
    if output_path.exists():
        print(f"警告: 输出文件已存在 - {args.output}")
        response = input("是否覆盖? (y/N): ")
        if response.lower() != 'y':
            print("操作已取消")
            sys.exit(0)

    # 获取 API 配置
    api_url, api_key = get_api_config()

    # 导出 DSL
    print(f"正在从 {api_url} 导出 App {args.app_id}...")
    dsl_data = export_workflow(api_url, api_key, args.app_id)

    # 保存文件
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            yaml.dump(dsl_data, f, allow_unicode=True, default_flow_style=False)
        print(f"✅ 导出成功: {args.output}")
    except Exception as e:
        print(f"错误: 无法保存文件 - {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
