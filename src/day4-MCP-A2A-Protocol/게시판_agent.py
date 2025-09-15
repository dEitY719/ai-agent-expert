"""한국어 학술 연구 에이전트: 연구 조언, 관련 문헌 찾기, 연구 영역 제안, 웹 지식 접근. MCP 통합."""

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

from . import adk_config, prompt
from .sub_agents.academic_newresearch import academic_newresearch_agent
from .sub_agents.academic_websearch import academic_websearch_agent

# LiteLLM을 통한 OpenAI GPT-4o-mini 모델 설정
MODEL = LiteLlm(model="openai/gpt-4o-mini")

# MCP 연구 자료 저장 서버 통합
research_mcp_config = adk_config.get_research_mcp_config()
research_mcp_toolset = MCPToolset(
    connection_params=StdioServerParameters(command=research_mcp_config["command"], args=research_mcp_config["args"])
)

academic_coordinator = LlmAgent(
    name="academic_coordinator",
    model=MODEL,
    description=(
        "한국어 학술 연구 에이전트: "
        "사용자의 연구 주제나 논문에 대한 질문을 받아서, "
        "ArXiv와 웹 검색을 통해 관련 논문을 찾고, "
        "새로운 연구 방향을 제안하는 에이전트입니다. "
        "PDF 업로드가 아닌 검색 기반으로 작동하며, "
        "연구 자료를 MCP 서버에 저장하고 관리할 수 있습니다."
    ),
    instruction=prompt.ACADEMIC_COORDINATOR_PROMPT,
    output_key="research_topic",
    tools=[
        AgentTool(agent=academic_websearch_agent),
        AgentTool(agent=academic_newresearch_agent),
        research_mcp_toolset,  # MCP 연구 자료 저장 도구 추가
    ],
)

root_agent = academic_coordinator
