import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse import observe
from langfuse.langchain import CallbackHandler


async def handle_dialogue_logic(user_input: str):
    """LangGraph Agent의 역할을 시뮬레이션하는 대화 관리 로직 (Langfuse 추적 기능 추가)"""
    print("[LangGraph Service] 🧠 대화 관리자 실행됨...")

    # 각 서비스 호출을 위한 고유한 Langfuse 핸들러 생성
    handler = CallbackHandler()

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
        prompt = f"다음 사용자 요청의 핵심 주제를 20단어 이내의 간결한 한 문장으로 요약하고, 사용자의 숨겨진 요구사항(스타일, 톤앤매너 등)을 추론해줘. 결과는 '주제: [요약된 주제]\n요구사항: [추론된 요구사항]' 형식으로만 답변해줘. 다른 말은 절대 추가하지 마.\n\n사용자 요청: '{user_input}'"

        # LLM 호출 시 config에 콜백 핸들러 전달
        response_text = llm.invoke(prompt, config={"callbacks": [handler]}).content

        topic = response_text.split("주제:")[1].split("요구사항:")[0].strip()
        preferences = response_text.split("요구사항:")[1].strip()
    except Exception as e:
        print(f"[LangGraph Service] 🔴 LLM 호출 오류, Fallback 로직 사용: {e}")
        topic = user_input
        preferences = "전문적이면서도 쉬운 어조로 작성해주세요."

    response = {
        "agent_response": f"알겠습니다. '{topic}'에 대한 블로그 글 생성을 시작하겠습니다. '{preferences}' 요구사항을 반영하겠습니다.",
        "next_action": {"action": "CREATE_CONTENT", "topic": topic, "user_preferences": preferences},
    }
    print(f"[LangGraph Service] ✅ 다음 행동 결정: {response['next_action']}")
    return response


print("✅ dialogue_manager_langgraph.py 파일이 Langfuse 추적 기능으로 업데이트되었습니다.")
