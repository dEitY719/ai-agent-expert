#!/usr/bin/env python3
"""
A2A 표준 준수 멀티 에이전트 시스템 데모
공식 a2a-sdk 클라이언트 사용
"""

import asyncio
import json
from typing import Any, Dict

import httpx


class A2AMultiAgentDemo:
    """A2A 표준 멀티 에이전트 시스템 데모"""

    def __init__(self):
        self.research_agent_url = "http://localhost:8000"
        self.writing_agent_url = "http://localhost:8001"

    async def get_agent_card(self, agent_url: str) -> Dict[str, Any]:
        """에이전트 카드를 가져옵니다."""

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{agent_url}/.well-known/agent-card.json")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {"error": f"Agent Card 가져오기 실패: {e}"}

    async def send_a2a_message(
        self, agent_url: str, message: str, skill: str = "", task_id: str = ""
    ) -> Dict[str, Any]:
        """A2A 표준 메시지를 보냅니다."""

        # A2A 표준 JSON-RPC 2.0 요청 구성
        request_data = {"jsonrpc": "2.0", "method": "message/send", "params": {"message": {"text": message}}, "id": 1}

        # 스킬 지정
        if skill:
            request_data["params"]["skill"] = skill

        # 태스크 ID 지정 (피드백용)
        if task_id:
            request_data["params"]["taskId"] = task_id
            request_data["params"]["contextId"] = task_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(agent_url, json=request_data)
                response.raise_for_status()
                result = response.json()
                return result.get("result", {})
            except Exception as e:
                return {"error": f"A2A 메시지 전송 실패: {e}"}

    async def verify_a2a_compliance(self):
        """A2A 표준 준수 여부를 검증합니다."""

        print("\n🔍 A2A 표준 준수 여부 검증")
        print("=" * 60)

        # 연구 에이전트 검증
        print("📚 연구 에이전트 검증:")
        research_card = await self.get_agent_card(self.research_agent_url)
        if "error" not in research_card:
            print(f"  ✅ Agent Card: {research_card.get('name')} v{research_card.get('version')}")
            print(f"  ✅ URL: {research_card.get('url')}")
            print(f"  ✅ Skills: {len(research_card.get('skills', []))}개")
            print(f"  ✅ Capabilities: {research_card.get('capabilities', {})}")
        else:
            print(f"  ❌ {research_card['error']}")

        # 글쓰기 에이전트 검증
        print("\n✍️ 글쓰기 에이전트 검증:")
        writing_card = await self.get_agent_card(self.writing_agent_url)
        if "error" not in writing_card:
            print(f"  ✅ Agent Card: {writing_card.get('name')} v{writing_card.get('version')}")
            print(f"  ✅ URL: {writing_card.get('url')}")
            print(f"  ✅ Skills: {len(writing_card.get('skills', []))}개")
            print(f"  ✅ Capabilities: {writing_card.get('capabilities', {})}")
        else:
            print(f"  ❌ {writing_card['error']}")

    async def interactive_research_session(self):
        """대화형 연구 세션을 시작합니다."""

        print(f"\n📚 A2A 연구 에이전트와의 대화 시작")
        print("=" * 60)
        print("연구하고 싶은 주제를 입력하세요. (종료: 'quit' 또는 'exit')")

        research_content = ""

        while True:
            try:
                user_input = input("\n연구 질문: ").strip()

                if user_input.lower() in ["quit", "exit", "종료"]:
                    print("연구 세션을 종료합니다.")
                    break

                if not user_input:
                    print("질문을 입력해주세요.")
                    continue

                print(f"🔍 연구 중: {user_input}")

                research_result = await self.send_a2a_message(self.research_agent_url, user_input, skill="research")

                if "error" in research_result:
                    print(f"❌ 연구 오류: {research_result['error']}")
                    continue

                task = research_result.get("task", {})
                artifacts = task.get("artifacts", [])
                if artifacts:
                    content = artifacts[0].get("content", "")
                    research_content = content  # 최신 연구 내용 저장
                    print(f"\n✅ 연구 결과:")
                    print("-" * 40)
                    print(content)
                    print("-" * 40)
                else:
                    print("❌ 연구 결과를 가져올 수 없습니다")
                    continue

                # 글쓰기 에이전트로 이동할지 묻기
                move_choice = input(
                    f"\n다음 중 선택하세요:\n1. 글쓰기 에이전트로 이동\n2. 연구를 더 계속하기\n선택 (1/2): "
                ).strip()

                if move_choice == "1":
                    await self.interactive_writing_session(research_content, user_input)
                    return
                elif move_choice == "2":
                    print("연구를 계속합니다.")
                else:
                    print("잘못된 선택입니다. 연구를 계속합니다.")

            except KeyboardInterrupt:
                print("\n\n연구 세션이 중단되었습니다.")
                break

    async def interactive_writing_session(self, research_content: str = "", original_topic: str = ""):
        """대화형 글쓰기 세션을 시작합니다."""

        print(f"\n✍️ A2A 글쓰기 에이전트와의 대화 시작")
        print("=" * 60)

        current_task_id = None

        # 연구 내용이 있으면 자동으로 글쓰기 시작
        if research_content:
            writing_prompt = f"주제: {original_topic}\n\n연구 자료:\n{research_content[:1000]}...\n\n위 연구 자료를 바탕으로 체계적인 글을 작성해주세요."

            print(f"📝 연구 내용을 바탕으로 글을 작성합니다...")

            writing_result = await self.send_a2a_message(self.writing_agent_url, writing_prompt, skill="writing")

            if "error" not in writing_result:
                task = writing_result.get("task", {})
                current_task_id = task.get("id")
                artifacts = task.get("artifacts", [])
                if artifacts:
                    content = artifacts[0].get("content", "")
                    print(f"\n📄 작성된 글:")
                    print("=" * 80)
                    print(content)
                    print("=" * 80)

        print("\n글쓰기 요청이나 피드백을 입력하세요. (종료: 'quit' 또는 'exit')")

        while True:
            try:
                user_input = input(f"\n글쓰기 요청/피드백: ").strip()

                if user_input.lower() in ["quit", "exit", "종료"]:
                    print("글쓰기 세션을 종료합니다.")
                    break

                if not user_input:
                    print("요청을 입력해주세요.")
                    continue

                # 피드백인지 새 글쓰기인지 판단
                if current_task_id and any(
                    word in user_input.lower() for word in ["수정", "피드백", "개선", "바꿔", "고쳐"]
                ):
                    print(f"🔄 피드백 반영 중: {user_input}")

                    result = await self.send_a2a_message(
                        self.writing_agent_url, f"피드백: {user_input}", skill="revision", task_id=current_task_id
                    )
                else:
                    print(f"📝 새 글 작성 중: {user_input}")

                    result = await self.send_a2a_message(self.writing_agent_url, user_input, skill="writing")

                    # 새 태스크 ID 업데이트
                    if "error" not in result:
                        current_task_id = result.get("task", {}).get("id")

                if "error" in result:
                    print(f"❌ 오류: {result['error']}")
                    continue

                task = result.get("task", {})
                artifacts = task.get("artifacts", [])
                if artifacts:
                    content = artifacts[0].get("content", "")
                    print(f"\n📄 결과:")
                    print("-" * 80)
                    print(content)
                    print("-" * 80)
                else:
                    print("❌ 결과를 가져올 수 없습니다")

            except KeyboardInterrupt:
                print("\n\n글쓰기 세션이 중단되었습니다.")
                break


async def main():
    """메인 데모 함수"""

    print("🌐 A2A 표준 준수 멀티 에이전트 시스템 데모")
    print("=" * 60)
    print("✅ A2A SDK 기반 연구 에이전트 (포트 8000)")
    print("✅ A2A SDK 기반 글쓰기 에이전트 (포트 8001)")
    print("✅ JSON-RPC 2.0 over HTTP 통신")
    print("✅ Agent Card 표준 준수")
    print("✅ 공식 AgentExecutor 사용")

    demo = A2AMultiAgentDemo()

    # A2A 표준 준수 검증
    await demo.verify_a2a_compliance()

    print(f"\n모드를 선택하세요:")
    print("1. 연구 에이전트와 대화")
    print("2. 글쓰기 에이전트와 대화")

    try:
        choice = input(f"\n선택 (1-2): ").strip()

        if choice == "1":
            await demo.interactive_research_session()
        elif choice == "2":
            await demo.interactive_writing_session()
        else:
            print("❌ 잘못된 선택입니다")

    except KeyboardInterrupt:
        print("\n⏹️ 데모 중단됨")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())
