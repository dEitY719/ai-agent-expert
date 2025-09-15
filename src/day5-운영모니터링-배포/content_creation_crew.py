import json

from crewai import Agent, Crew, Process, Task
from langchain.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse import observe
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from mcp_client import MCPClient


class MCPTool(BaseTool):
    name: str
    description: str
    client: MCPClient

    @observe(name="mcp-tool-call")
    def _run(self, query: str) -> str:
        print(f"  [MCP Bridge] CrewAI -> MCP Server: Calling tool '{self.name}' with query '{query}'")
        response = self.client.call_tool(self.name, query)
        return json.dumps(response, ensure_ascii=False)


def handle_creation_logic(topic: str, user_preferences: str, mcp_client: MCPClient):
    print(f"[CrewAI Service] 👥 콘텐츠 제작팀 가동됨 (주제: {topic[:30]}...)")
    try:
        handler = LangfuseCallbackHandler()

        crew_web_search = MCPTool(name="web_search", description="웹에서 최신 정보를 검색합니다.", client=mcp_client)
        crew_arxiv_search = MCPTool(name="arxiv_search", description="학술 논문을 검색합니다.", client=mcp_client)

        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", callbacks=[handler])
        researcher = Agent(
            role="선임 리서처",
            goal=f"{topic}에 대한 심층 분석",
            backstory="당신은 20년 경력의 기술 분석 전문가입니다.",
            tools=[crew_web_search, crew_arxiv_search],
            llm=llm,
            verbose=True,
        )
        writer = Agent(
            role="전문 작가",
            goal="리서치 결과를 바탕으로 매력적인 블로그 글 작성",
            backstory="당신은 기술 분야의 베스트셀러 작가입니다.",
            llm=llm,
            verbose=True,
        )

        research_task = Task(
            description=f"'{topic}'에 대해 웹과 학술 자료를 종합하여 심층 분석 보고서를 작성하세요.",
            expected_output="구조화된 분석 보고서",
            agent=researcher,
        )
        write_task = Task(
            description=f"리서치 보고서를 바탕으로, '{user_preferences}' 스타일을 반영하여 블로그 초안을 작성하세요.",
            expected_output="완성된 블로그 초안",
            agent=writer,
            context=[research_task],
        )

        crew = Crew(agents=[researcher, writer], tasks=[research_task, write_task], process=Process.sequential)
        result = crew.kickoff()
        print("[CrewAI Service] ✅ 초안 작성 완료.")
        return result
    except Exception as e:
        error_message = f"CrewAI 실행 중 오류 발생: {e}"
        print(f"[CrewAI Service] 🔴 {error_message}")
        return error_message


print("✅ content_creation_crew.py 파일이 Langfuse 추적 기능으로 업데이트되었습니다.")
