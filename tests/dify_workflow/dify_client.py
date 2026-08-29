"""Dify API client for Workflow testing."""
import json
import os
import time
from typing import Any, Optional



class DifyClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        file_registry: Any | None = None,
        http_client: Any | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        if http_client is None:
            import requests

            http_client = requests
        self.http_client = http_client
        self.file_registry = file_registry
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
        if files is None and conversation_id and self.file_registry is not None:
            files = self.file_payloads(conversation_id)
        if files:
            payload["files"] = files

        resp = self.http_client.post(
            f"{self.base_url}/v1/chat-messages",
            headers=self.headers,
            json=payload,
            timeout=180,
        )
        return resp.json()

    def remember_file(
        self,
        conversation_id: str,
        *,
        file_id: str,
        sha256: str,
        size: int,
        name: str,
        mime_type: str,
        file_type: str = "document",
        transfer_method: str = "local_file",
        url: str | None = None,
    ):
        if self.file_registry is None:
            raise RuntimeError("file_registry is required to remember files")
        metadata = {"type": file_type, "transfer_method": transfer_method}
        if url is not None:
            metadata["url"] = url
        record = self.file_registry.register(
            conversation_id,
            file_id,
            sha256,
            size,
            name,
            mime_type,
            f"dify-file-ref:{file_id}",
            metadata=metadata,
        )
        self.file_registry.save()
        return record

    def file_payloads(self, conversation_id: str) -> list[dict[str, str]]:
        if self.file_registry is None:
            return []
        payloads = []
        for record in self.file_registry.list(conversation_id):
            transfer_method = record.metadata.get("transfer_method", "local_file")
            file_type = record.metadata.get("type", "document")
            if not isinstance(transfer_method, str) or not isinstance(file_type, str):
                raise ValueError("session file metadata has invalid Dify payload fields")
            payload: dict[str, str] = {"type": file_type, "transfer_method": transfer_method}
            if transfer_method == "remote_url":
                url = record.metadata.get("url")
                if not isinstance(url, str) or not url:
                    raise ValueError("remote_url session file is missing url")
                payload["url"] = url
            else:
                payload["upload_file_id"] = record.file_id
            payloads.append(payload)
        return payloads

    def get_conversations(self, user: str = "test-user") -> dict:
        resp = self.http_client.get(
            f"{self.base_url}/v1/conversations",
            headers=self.headers,
            params={"user": user, "limit": 20},
            timeout=30,
        )
        return resp.json()

    def get_messages(self, conversation_id: str, user: str = "test-user") -> dict:
        resp = self.http_client.get(
            f"{self.base_url}/v1/messages",
            headers=self.headers,
            params={"conversation_id": conversation_id, "user": user, "limit": 50},
            timeout=30,
        )
        return resp.json()

    def stop_generation(self, task_id: str, user: str = "test-user") -> dict:
        resp = self.http_client.post(
            f"{self.base_url}/v1/chat-messages/{task_id}/stop",
            headers=self.headers,
            json={"user": user},
            timeout=30,
        )
        return resp.json()

    def get_app_info(self) -> dict:
        resp = self.http_client.get(
            f"{self.base_url}/v1/info",
            headers=self.headers,
            timeout=30,
        )
        return resp.json()

    def get_app_parameters(self) -> dict:
        resp = self.http_client.get(
            f"{self.base_url}/v1/parameters",
            headers=self.headers,
            timeout=30,
        )
        return resp.json()
