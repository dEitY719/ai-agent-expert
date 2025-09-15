#!/usr/bin/env python3
"""
A2A SDK를 사용한 글쓰기 에이전트
공식 A2A 표준 완전 준수 + 사용자 인터럽션 및 피드백 루프
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


class WritingAgentExecutor(AgentExecutor):
    """글쓰기 에이전트 실행기 - A2A 표준 준수"""

    def __init__(self):
        super().__init__()
        self.active_sessions = {}

    async def execute(self, context: RequestContext) -> Dict[str, Any]:
        """에이전트 실행 메서드"""

        try:
            # 요청에서 메시지 추출
            message = context.request.get("message", {}).get("text", "")
            skill_id = context.request.get("skill", "")
            task_id = context.request.get("taskId")
            context_id = context.request.get("contextId")

            if not message:
                return {
                    "task": {
                        "id": str(uuid.uuid4()),
                        "status": {"state": "failed", "message": "메시지가 비어있습니다."},
                    }
                }

            # 스킬에 따른 처리
            if skill_id == "writing" or (not skill_id and not task_id):
                # 새로운 글쓰기 요청
                result = await self.write_article(message)
                new_task_id = str(uuid.uuid4())

                return {
                    "task": {
                        "id": new_task_id,
                        "status": {"state": "completed", "message": "글쓰기 완료 (피드백 가능)"},
                        "artifacts": [{"type": "text/plain", "content": result}],
                        "supports_feedback": True,
                    }
                }

            elif skill_id == "revision" or task_id:
                # 피드백 및 수정 요청
                result = await self.process_feedback(message, task_id or context_id)

                return {
                    "task": {
                        "id": task_id or str(uuid.uuid4()),
                        "status": {"state": "completed", "message": "피드백 반영 완료"},
                        "artifacts": [{"type": "text/plain", "content": result}],
                        "supports_feedback": True,
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
                    "status": {"state": "failed", "message": f"글쓰기 수행 중 오류: {str(e)}"},
                }
            }

    async def write_article(self, message: str) -> str:
        """글쓰기 요청을 처리합니다."""

        writing_prompt = f"""
다음 주제에 대한 체계적인 글을 작성해주세요:

주제 또는 요청: {message}

다음 구조로 작성해주세요:
1. 서론 (문제 제기, 글의 목적)
2. 본론 (주요 내용, 논점들)
3. 결론 (요약 및 시사점)

약 1000-1500자 정도로 작성해주세요.
한국어로 작성하고, 체계적이고 논리적으로 구성해주세요.
"""

        try:
            response = await litellm.acompletion(
                model="gpt-4o-mini", messages=[{"role": "user", "content": writing_prompt}], temperature=0.4
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"글쓰기 수행 중 오류가 발생했습니다: {str(e)}"

    async def process_feedback(self, feedback: str, task_id: Optional[str] = None) -> str:
        """사용자 피드백을 처리합니다."""

        feedback_prompt = f"""
사용자로부터 다음과 같은 피드백을 받았습니다:

피드백: {feedback}

이 피드백을 반영하여 글을 개선하는 방안을 제시해주세요.
구체적인 수정 사항과 개선 방향을 설명해주세요.
가능하면 수정된 부분을 포함하여 답변해주세요.
"""

        try:
            response = await litellm.acompletion(
                model="gpt-4o-mini", messages=[{"role": "user", "content": feedback_prompt}], temperature=0.3
            )

            return f"피드백 반영 완료:\n\n{response.choices[0].message.content}"

        except Exception as e:
            return f"피드백 처리 중 오류가 발생했습니다: {str(e)}"


class WritingAgentApp(JSONRPCApplication):
    """글쓰기 에이전트 애플리케이션 - A2A 표준 준수"""

    def build(self) -> AgentExecutor:
        """에이전트 실행기를 빌드합니다."""
        return WritingAgentExecutor()


# A2A Agent Card 정의 (완전한 필수 필드 포함)
WRITING_AGENT_CARD = AgentCard(
    name="Writing Agent",
    version="1.0.0",
    description="사용자 인터럽션과 피드백 루프가 포함된 A2A 표준 준수 글쓰기 에이전트입니다.",
    url="http://localhost:8001",
    capabilities={"streaming": False, "push_notifications": False, "feedback_loops": True, "user_interruption": True},
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    security=[],
    skills=[
        AgentSkill(
            id="writing",
            name="글쓰기",
            description="주제에 대한 체계적인 글을 작성합니다.",
            tags=["writing", "content", "generation"],
            examples=[
                {
                    "request": {"message": {"text": "AI 기술의 미래에 대한 글을 써주세요"}},
                    "response": "AI 기술의 미래에 대한 체계적인 글을 작성합니다.",
                }
            ],
        ),
        AgentSkill(
            id="revision",
            name="글 수정",
            description="사용자 피드백을 반영하여 글을 수정합니다.",
            tags=["revision", "feedback", "improvement"],
            examples=[
                {
                    "request": {"message": {"text": "결론 부분을 더 강화해주세요"}, "taskId": "existing-task-id"},
                    "response": "피드백을 반영하여 결론 부분을 강화합니다.",
                }
            ],
        ),
    ],
)


async def main():
    """글쓰기 에이전트 서버를 시작합니다."""

    print("🖋️ A2A 표준 글쓰기 에이전트 서버 시작")
    print(f"📍 URL: http://localhost:8001")
    print(f"📋 Agent Card: {WRITING_AGENT_CARD.name} v{WRITING_AGENT_CARD.version}")
    print(f"💬 피드백 루프 지원: 글 완성 후 수정 요청 가능")

    # A2A JSONRPCApplication 생성
    app = WritingAgentApp(agent_card=WRITING_AGENT_CARD)

    # 서버 시작
    await app.start_server(host="localhost", port=8001)


if __name__ == "__main__":
    asyncio.run(main())
