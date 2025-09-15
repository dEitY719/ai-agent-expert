#!/usr/bin/env python3
"""
A2A SDK를 사용한 연구 에이전트
공식 A2A 표준 완전 준수
"""

import asyncio
import uuid
from typing import Any, Dict, Optional

import litellm
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps.jsonrpc import JSONRPCApplication
from a2a.types import AgentCard, AgentSkill
from dotenv import load_dotenv

load_dotenv()


class ResearchAgentExecutor(AgentExecutor):
    """연구 에이전트 실행기 - A2A 표준 준수"""

    async def execute(self, context: RequestContext) -> Dict[str, Any]:
        """에이전트 실행 메서드"""

        try:
            # 요청에서 메시지 추출
            message = context.request.get("message", {}).get("text", "")
            skill_id = context.request.get("skill", "")

            if not message:
                return {
                    "task": {
                        "id": str(uuid.uuid4()),
                        "status": {"state": "failed", "message": "메시지가 비어있습니다."},
                    }
                }

            # 연구 수행
            if skill_id == "research" or not skill_id:
                result = await self.conduct_research(message)

                task_id = str(uuid.uuid4())
                return {
                    "task": {
                        "id": task_id,
                        "status": {"state": "completed", "message": "연구 조사 완료"},
                        "artifacts": [{"type": "text/plain", "content": result}],
                    }
                }
            else:
                return {
                    "task": {
                        "id": str(uuid.uuid4()),
                        "status": {"state": "failed", "message": f"지원하지 않는 스킬: {skill_id}"},
                    }
                }

        except Exception as e:
            return {
                "task": {
                    "id": str(uuid.uuid4()),
                    "status": {"state": "failed", "message": f"연구 수행 중 오류: {str(e)}"},
                }
            }

    async def conduct_research(self, topic: str) -> str:
        """주제에 대한 연구를 수행합니다."""

        research_prompt = f"""
다음 주제에 대한 체계적인 연구 조사를 수행해주세요:

주제: {topic}

다음 관점들을 포함하여 연구해주세요:
1. 현재 기술 수준과 발전 현황
2. 주요 연구 동향 및 트렌드
3. 핵심 과제와 한계점
4. 미래 전망과 발전 방향
5. 사회적 영향과 시사점

각 항목당 2-3개의 구체적인 내용을 제시해주세요.
한국어로 답변하고, 전문적이면서도 이해하기 쉽게 설명해주세요.
"""

        try:
            response = await litellm.acompletion(
                model="gpt-4o-mini", messages=[{"role": "user", "content": research_prompt}], temperature=0.2
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"연구 수행 중 오류가 발생했습니다: {str(e)}"


class ResearchAgentApp(JSONRPCApplication):
    """연구 에이전트 애플리케이션 - A2A 표준 준수"""

    def build(self) -> AgentExecutor:
        """에이전트 실행기를 빌드합니다."""
        return ResearchAgentExecutor()


# A2A Agent Card 정의 (완전한 필수 필드 포함)
RESEARCH_AGENT_CARD = AgentCard(
    name="Research Agent",
    version="1.0.0",
    description="체계적인 연구 조사를 수행하는 A2A 표준 준수 에이전트입니다.",
    url="http://localhost:8000",
    capabilities={"streaming": False, "push_notifications": False},
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    security=[],
    skills=[
        AgentSkill(
            id="research",
            name="학술 연구",
            description="연구 주제에 대한 체계적 조사 및 분석을 수행합니다.",
            tags=["research", "academic", "analysis"],
            examples=[
                {
                    "request": {"message": {"text": "양자컴퓨팅 기술의 현재와 미래"}},
                    "response": "양자컴퓨팅에 대한 체계적 연구 결과를 제공합니다.",
                }
            ],
        )
    ],
)


async def main():
    """연구 에이전트 서버를 시작합니다."""

    print("🔬 A2A 표준 연구 에이전트 서버 시작")
    print(f"📍 URL: http://localhost:8000")
    print(f"📋 Agent Card: {RESEARCH_AGENT_CARD.name} v{RESEARCH_AGENT_CARD.version}")

    # A2A JSONRPCApplication 생성
    app = ResearchAgentApp(agent_card=RESEARCH_AGENT_CARD)

    # 서버 시작
    await app.start_server(host="localhost", port=8000)


if __name__ == "__main__":
    asyncio.run(main())
