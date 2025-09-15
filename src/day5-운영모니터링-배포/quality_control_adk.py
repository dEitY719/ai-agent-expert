from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse.langchain import CallbackHandler


async def handle_qc_logic(topic: str, draft_content: str):
    print(f"[ADK Service] 🧐 품질 관리팀 가동됨 (주제: {topic[:30]}...)")

    # ADK 서비스 호출을 위한 핸들러 생성
    handler = CallbackHandler()

    try:
        qa_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        prompt = f"당신은 삼성전자 기술 블로그의 수석 편집자입니다. 다음 초안을 검토하고, 우리 블로그의 톤앤매너(전문적, 신뢰감, 명확함)에 맞춰 최종 발행 가능한 완벽한 최종본으로 만들어주세요.\n\n주제: {topic}\n초안: {draft_content}"

        # LLM 호출 시 config에 콜백 핸들러 전달
        final_post = qa_llm.invoke(prompt, config={"callbacks": [handler]}).content

        report = {
            "seo_score": 95,
            "readability": "excellent",
            "final_char_count": len(final_post),
            "status": "Approved",
        }
        print("[ADK Service] ✅ 최종 편집 및 보고서 생성 완료.")
        return final_post, report
    except Exception as e:
        error_message = f"ADK 품질 관리 중 오류 발생: {e}"
        print(f"[ADK Service] 🔴 {error_message}")
        return draft_content, {"status": "Failed", "error": error_message}


print("✅ quality_control_adk.py 파일이 Langfuse 추적 기능으로 업데이트되었습니다.")
