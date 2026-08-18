"""Dify API client for Workflow testing."""
import json
import os
import time
import requests
from typing import Optional


class DifyClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        query: str,
        user: str = "test-user",
        conversation_id: Optional[str] = None,
        files: Optional[list] = None,
        response_mode: str = "blocking",
    ) -> dict:
        payload = {
            "inputs": {},
            "query": query,
            "response_mode": response_mode,
            "user": user,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if files:
            payload["files"] = files

        resp = requests.post(
            f"{self.base_url}/v1/chat-messages",
            headers=self.headers,
            json=payload,
            timeout=180,
        )
        return resp.json()

    def get_conversations(self, user: str = "test-user") -> dict:
        resp = requests.get(
            f"{self.base_url}/v1/conversations",
            headers=self.headers,
            params={"user": user, "limit": 20},
            timeout=30,
        )
        return resp.json()

    def get_messages(self, conversation_id: str, user: str = "test-user") -> dict:
        resp = requests.get(
            f"{self.base_url}/v1/messages",
            headers=self.headers,
            params={"conversation_id": conversation_id, "user": user, "limit": 50},
            timeout=30,
        )
        return resp.json()

    def stop_generation(self, task_id: str, user: str = "test-user") -> dict:
        resp = requests.post(
            f"{self.base_url}/v1/chat-messages/{task_id}/stop",
            headers=self.headers,
            json={"user": user},
            timeout=30,
        )
        return resp.json()

    def get_app_info(self) -> dict:
        resp = requests.get(
            f"{self.base_url}/v1/info",
            headers=self.headers,
            timeout=30,
        )
        return resp.json()

    def get_app_parameters(self) -> dict:
        resp = requests.get(
            f"{self.base_url}/v1/parameters",
            headers=self.headers,
            timeout=30,
        )
        return resp.json()
