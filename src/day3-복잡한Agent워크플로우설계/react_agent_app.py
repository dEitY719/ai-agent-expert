# streamlit run react_agent_app.py

import collections.abc
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Literal, Type

import instructor
import streamlit as st
import wolframalpha
from dotenv import load_dotenv
from langchain.tools import BaseTool, tool
from langchain.tools.render import render_text_description
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, PrivateAttr

st.set_page_config(page_title="ReAct Agent", page_icon="🤖", layout="wide")

# --- 초기 설정 ---

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
wolfram_app_id = os.getenv("WOLFRAM_ALPHA_APP_ID")

if not all([google_api_key, tavily_api_key, wolfram_app_id]):
    st.sidebar.title("🔑 API 키 설정")
    google_api_key = st.sidebar.text_input("Google API Key", type="password", key="google_api_key") or google_api_key
    tavily_api_key = st.sidebar.text_input("Tavily API Key", type="password", key="tavily_api_key") or tavily_api_key
    wolfram_app_id = (
        st.sidebar.text_input("WolframAlpha App ID", type="password", key="wolfram_app_id") or wolfram_app_id
    )

# --- 세션 상태 초기화 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --- 2. Agent 구성 요소 (Tool, LLM) 정의 ---
@st.cache_resource
def get_tools():
    # --- Tool 1: 웹 검색 ---
    search_tool = TavilySearchResults(max_results=3, name="tavily_search_results_json")

    # --- Tool 2: 간단한 계산기 ---
    class CalculatorInput(BaseModel):
        expression: str = Field(description="평가할 수학적 표현식")

    @tool(args_schema=CalculatorInput)
    def calculator_tool(expression: str) -> str:
        """간단한 사칙연산이나 숫자 계산에만 사용하세요."""
        try:
            return str(eval(expression))
        except Exception as e:
            return f"계산 오류: {e}"

    # --- Tool 3: 복합 과학/수학 엔진 (WolframAlpha LLM API) ---
    class WolframAlphaInput(BaseModel):
        query: str = Field(description="WolframAlpha에 보낼 복잡한 질문이나 수학/과학 수식")

    @tool(args_schema=WolframAlphaInput)
    def wolfram_alpha_tool(query: str) -> str:
        """복잡한 수학 문제, 방정식, 미적분, 화학식, 물리 공식, 단위 변환 등에 사용합니다."""
        try:
            import urllib.parse
            import urllib.request

            api_key = os.environ.get("WOLFRAM_ALPHA_APP_ID")
            if not api_key:
                return "API 키가 설정되지 않았습니다."

            # LLM API 사용 (텍스트 결과 반환)
            base_url = "https://www.wolframalpha.com/api/v1/llm-api"

            # URL 파라미터 구성
            params = {"input": query, "appid": api_key, "maxchars": 2000}  # 응답 길이 제한

            # URL 인코딩
            encoded_params = urllib.parse.urlencode(params)
            full_url = f"{base_url}?{encoded_params}"

            print(f"디버깅: 요청 URL: {full_url}")

            # 요청 실행
            with urllib.request.urlopen(full_url) as response:
                result = response.read().decode("utf-8")
                print(f"디버깅: LLM API 응답 성공")

                # 결과에서 핵심 정보만 추출
                if "Result:" in result:
                    # "Result:" 다음 부분만 추출
                    result_section = result.split("Result:")[1].split("\n")[0:3]
                    clean_result = "Result: " + "\n".join(result_section)
                    return clean_result.strip()

                return result[:500] + "..." if len(result) > 500 else result

        except urllib.error.HTTPError as e:
            error_code = e.code
            error_msg = e.read().decode("utf-8") if hasattr(e, "read") else str(e)

            if error_code == 501:
                return f"WolframAlpha가 쿼리를 이해하지 못했습니다: '{query}'. 다른 표현으로 시도해보세요."
            elif error_code == 403:
                return "API 키가 유효하지 않거나 권한이 없습니다."
            else:
                return f"HTTP 오류 {error_code}: {error_msg}"

        except Exception as e:
            return f"WolframAlpha 오류: {str(e)}"

    # --- Tool 4: 블로그 템플릿 ---
    class BlogTemplateInput(BaseModel):
        style: str = Field(
            description="블로그 글의 기본 구조(템플릿)를 생성할 때 사용합니다. '기술 분석' 또는 '제품 리뷰' 스타일 중 하나를 선택하세요."
        )

    @tool(args_schema=BlogTemplateInput)
    def blog_template_tool(style: str) -> str:
        """블로그 글의 기본 구조를 생성합니다."""
        if style == "기술 분석":
            return "## 제목\\n\\n### 1. 기술 개요\\n\\n### 2. 핵심 작동 원리\\n\\n### 3. 장단점 분석\\n\\n### 4. 실무 적용 사례\\n\\n### 5. 결론 및 향후 전망"
        elif style == "제품 리뷰":
            return "## 제목\\n\\n### 1. 첫인상 및 디자인\\n\\n### 2. 주요 기능 및 성능 테스트\\n\\n### 3. 실사용 후기\\n\\n### 4. 총평 및 추천 대상"
        else:
            return "오류: '기술 분석' 또는 '제품 리뷰' 스타일만 지원합니다."

    # --- Tool 5: 사용자에게 질문하기 ---
    class QuestionInput(BaseModel):
        question: str = Field(description="사용자에게 물어볼 질문")

    @tool(args_schema=QuestionInput)
    def ask_user_tool(question: str) -> str:
        """사용자에게 추가 정보를 질문할 때 사용합니다. 계획 수립이나 맞춤 조언을 위해 필요한 정보를 얻습니다."""
        return f"사용자에게 질문: {question}"

    # --- Tool 6: 맞춤형 계획 생성 ---
    class PlanningInput(BaseModel):
        user_info: str = Field(description="사용자 정보나 상황, 달성하고자 하는 목표")

    @tool(args_schema=PlanningInput)
    def create_study_plan_tool(user_info: str) -> str:
        """사용자 정보를 바탕으로 맞춤형 학습 계획을 생성합니다."""

        # 간단한 계획 생성 로직
        if "수능" in user_info.lower() or "수학" in user_info.lower():
            return f"""
    ## 📚 맞춤형 수능 수학 학습 계획

    **사용자 현황:** {user_info}

    ### 1단계: 현재 실력 점검 (1주차)
    - 기출문제 3개년 풀어보기
    - 약점 영역 파악

    ### 2단계: 개념 정리 (2-4주차)
    - 부족한 단원 집중 학습
    - 공식 암기 및 이해

    ### 3단계: 문제 유형별 연습 (5-8주차)
    - 킬러 문제 유형 분석
    - 시간 단축 연습

    ### 4단계: 실전 모의고사 (9-12주차)
    - 주 2회 모의고사
    - 오답 노트 작성
            """
        elif "블로그" in user_info.lower():
            return f"""
    ## ✍️ 맞춤형 블로그 시작 계획

    **사용자 현황:** {user_info}

    ### 1단계: 주제 및 타겟 독자 설정
    - 관심 분야와 전문성 연결
    - 독자층 명확화

    ### 2단계: 콘텐츠 전략 수립
    - 포스팅 주기 결정
    - 콘텐츠 캘린더 작성

    ### 3단계: 첫 포스팅 발행
    - 자기소개 글 작성
    - SEO 최적화 적용
            """

    tools = [
        search_tool,
        calculator_tool,
        wolfram_alpha_tool,
        blog_template_tool,
        ask_user_tool,
        create_study_plan_tool,
    ]
    return tools


@st.cache_resource
def get_llm_and_template(_google_api_key, _tools):
    os.environ["GOOGLE_API_KEY"] = _google_api_key
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    structured_llm = instructor.from_provider("google/gemini-2.5-flash")
    rendered_tools = render_text_description(_tools)
    action_schema = json.dumps(Action.model_json_schema(), indent=2).replace("{", "{{").replace("}", "}}")
    template = f"""
    # MISSION
    당신은 사용자의 복잡한 요구사항을 해결하는 최상위 AI 어시스턴트입니다.
    당신은 'Thought'와 'Action'을 반복하는 ReAct 패턴을 사용하여 문제를 단계적으로 해결해야 합니다.

    # TOOLS
    다음은 당신이 사용할 수 있는 도구 목록입니다:
    --- TOOLS ---
    {rendered_tools}
    --- END TOOLS ---

    # OUTPUT FORMAT
    당신의 응답은 반드시 다음 세 가지 키를 포함한 JSON 객체여야 합니다:
    1. 'thought': 현재 상황 분석과 다음 행동 계획을 서술하는 문자열
    2. 'tool': 사용할 도구의 이름 또는 'Final Answer'
    3. 'tool_input': 선택된 도구에 전달할 입력값

    --- ACTION SCHEMA ---
    {action_schema}
    --- END ACTION SCHEMA ---

    # WORKFLOW
    1. 사용자의 질문과 이전 대화 기록을 분석하여 현재 상황을 파악합니다.
    2. 'thought'에 다음 행동 계획을 상세히 서술합니다.
    3. 계획에 가장 적합한 도구와 입력값을 결정합니다.
    4. 만약 모든 정보가 수집되어 최종 답변을 할 수 있다면, 'tool'로 'Final Answer'를 사용합니다.

    --- CONTEXT ---
    이전 대화 기록:
    {{chat_history}}

    이전 행동 및 관찰 기록:
    {{intermediate_steps}}

    사용자 질문: {{user_query}}
    """
    prompt_template = ChatPromptTemplate.from_template(template)
    return llm, structured_llm, prompt_template


class Action(BaseModel):
    thought: str = Field(description="현재 상황 분석과 다음 행동 계획")

    tool: Literal[
        "tavily_search_results_json",
        "calculator_tool",
        "wolfram_alpha_tool",
        "blog_template_tool",
        "ask_user_tool",
        "create_study_plan_tool",
        "Final Answer",
    ] = Field(description="사용할 Tool의 이름 또는 최종 답변을 위한 'Final Answer'")

    tool_input: Any = Field(description="선택된 Tool에 전달할 입력값. 문자열 또는 JSON 객체 형태가 될 수 있습니다.")


# --- 3. ReAct 엔진 함수 ---
def run_structured_react_engine(user_query: str, chat_history: list, _tools, _structured_llm, _prompt_template):
    tool_map = {tool.name: tool for tool in _tools}

    history_str = "\n".join([f"Human: {h[0]}\nAssistant: {h[1]}" for h in chat_history])
    intermediate_steps_str = ""

    # 자율적 루프 시작
    for i in range(10):  # 최대 10번의 반복으로 안전장치 설정
        # 사이드바에 진행 상황 표시
        with st.sidebar:
            st.write(f"🔄 ReAct Loop: Iteration {i+1}")

        # 1. 프롬프트 생성
        prompt = _prompt_template.format(
            user_query=user_query, chat_history=history_str, intermediate_steps=intermediate_steps_str
        )

        # 2. instructor를 사용하여 구조화된 응답 생성
        try:
            response_object = _structured_llm.chat.completions.create(
                model="gemini-2.5-flash", response_model=Action, messages=[{"role": "user", "content": prompt}]
            )

            thought = response_object.thought
            action_obj = response_object

            # 사이드바에 Thought 표시
            with st.sidebar:
                st.write(f"🤔 **Thought:** {thought[:1000]}...")
                st.write(f"🎬 **Action:** {action_obj.tool}")

            # 3. 최종 답변인지 확인
            if action_obj.tool == "Final Answer":
                return action_obj.tool_input

            # 4. ask_user_tool 특별 처리
            if action_obj.tool == "ask_user_tool":
                question = action_obj.tool_input
                # 질문을 사용자에게 보여주고 ReAct 루프 중단
                return f"💬 **질문**: {question}\n\n위 질문에 답변해 주시면, 그 정보를 바탕으로 맞춤형 계획을 세워드리겠습니다!"

            # 5. Tool 실행
            if action_obj.tool in tool_map:
                tool_to_use = tool_map[action_obj.tool]
                tool_input = action_obj.tool_input

                with st.sidebar.expander(f"🎬 **Action:** {action_obj.tool}", expanded=False):
                    st.text(f"입력: {tool_input}")

                try:
                    observation = tool_to_use.invoke(tool_input)
                    # 사이드바에 관찰 결과 표시
                    with st.sidebar:
                        st.write(f"👀 **관찰:** {str(observation)[:1000]}...")
                except Exception as e:
                    observation = f"Tool 실행 중 오류 발생: {str(e)}"
            else:
                observation = f"오류: '{action_obj.tool}' Tool을 찾을 수 없습니다."

            # 5. 다음 루프를 위한 기록 업데이트
            intermediate_steps_str += (
                f"\nThought: {thought}\nAction: {action_obj.model_dump_json()}\nObservation: {observation}"
            )

        except Exception as e:
            return f"ReAct 엔진 실행 중 오류가 발생했습니다: {str(e)}"

    return "최대 반복 횟수에 도달하여 작업을 종료합니다."


# --- 4. Streamlit UI 메인 로직 ---
st.title("🤖 지능형 ReAct 문제 해결사")
st.write("수능 문제 풀이, 블로그 초안 작성 등 복잡한 질문을 해보세요!")

if not all([google_api_key, tavily_api_key, wolfram_app_id]):
    st.info("사이드바에 모든 API 키를 입력해주세요.")
else:
    os.environ["TAVILY_API_KEY"] = tavily_api_key
    os.environ["WOLFRAM_ALPHA_APP_ID"] = wolfram_app_id

    # 도구와 LLM/템플릿 초기화 (캐시 사용)
    tools = get_tools()
    llm, structured_llm, prompt_template = get_llm_and_template(google_api_key, tools)

    # 대화 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력
    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Agent가 생각하고 행동하는 중..."):
                # 사이드바 초기화
                with st.sidebar:
                    st.header("Agent의 생각 과정 엿보기")
                    st.empty()

                response = run_structured_react_engine(
                    prompt, st.session_state.chat_history, tools, structured_llm, prompt_template
                )
                st.markdown(response)

                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.chat_history.append((prompt, response))
