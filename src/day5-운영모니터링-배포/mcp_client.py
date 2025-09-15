import json

import requests


class MCPClient:
    def __init__(self, base_url: str, api_key: str):
        if not base_url:
            raise ValueError("MCP 서버의 base_url이 필요합니다.")
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    def call_tool(self, tool_name: str, query: str) -> dict:
        endpoint = f"{self.base_url}/api/v1/tools/{tool_name}"
        payload = {"query": query}
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            return {"error": f"HTTP 오류: {e.response.status_code}", "detail": e.response.text}
        except Exception as e:
            return {"error": f"Tool 호출 중 오류 발생: {e}"}

    def get_resource(self, resource_type: str, resource_id: str) -> dict:
        endpoint = f"{self.base_url}/api/v1/resources/{resource_type}/{resource_id}"
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            return {"error": f"HTTP 오류: {e.response.status_code}", "detail": e.response.text}
        except Exception as e:
            return {"error": f"리소스 조회 중 오류 발생: {e}"}
