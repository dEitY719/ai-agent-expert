# --- Imports ---
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional

from a2a_protocol import *
from content_creation_crew import MCPClient, handle_creation_logic
from dialogue_manager_langgraph import handle_dialogue_logic
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader

# Langfuse v3 SDK import
from langfuse import get_client
from quality_control_adk import handle_qc_logic

# Langfuse 클라이언트 전역 변수
langfuse_client = None


# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global langfuse_client
    # Startup: Langfuse 클라이언트 초기화
    try:
        langfuse_client = get_client()
        if langfuse_client:
            if langfuse_client.auth_check():
                print("Langfuse 클라이언트가 성공적으로 초기화되었습니다.")
            else:
                print("Langfuse 인증 실패")
    except Exception as e:
        print(f"Langfuse 초기화 실패: {e}")
        langfuse_client = None

    yield  # 서버 실행

    # Shutdown: Langfuse flush
    if langfuse_client:
        langfuse_client.flush()
        print("✅ Langfuse 이벤트가 모두 전송되었습니다.")


# --- App & Security Setup ---
app = FastAPI(title="A2A Integrated Research Blog System", version="1.0.0", lifespan=lifespan)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == os.environ.get("MASTER_API_KEY"):
        return api_key
    else:
        raise HTTPException(status_code=401, detail="Invalid API Key")


# --- MCP Client Setup ---
mcp_client: Optional[MCPClient] = None


@app.on_event("startup")
def startup_event():
    global mcp_client
    mcp_server_url = os.environ.get("MCP_SERVER_URL")
    master_key = os.environ.get("MASTER_API_KEY")
    if mcp_server_url and master_key:
        mcp_client = MCPClient(base_url=mcp_server_url, api_key=master_key)
        print(f"A2A Gateway: MCP 클라이언트가 '{mcp_server_url}'에 연결되었습니다.")
    else:
        print("A2A Gateway: MCP_SERVER_URL 또는 MASTER_API_KEY가 설정되지 않아 MCP 클라이언트를 초기화할 수 없습니다.")


# --- Endpoints ---
@app.get("/", tags=["Status"])
async def root():
    return {"status": "ok", "message": "A2A Gateway is alive"}


@app.post("/api/v1/dialogue", response_model=DialogueResponse, tags=["A2A Protocol"])
async def handle_dialogue(request: DialogueRequest, api_key: str = Depends(get_api_key)):

    if langfuse_client:
        with langfuse_client.start_as_current_span(
            name="dialogue-request", input={"user_input": request.user_input, "session_id": request.session_id}
        ) as span:
            # 트레이스 속성 설정
            span.update_trace(
                session_id=request.session_id, tags=["dialogue", "api"], metadata={"endpoint": "/api/v1/dialogue"}
            )

            try:
                result = await handle_dialogue_logic(request.user_input)

                # 결과 업데이트
                span.update(output=result)
                span.update_trace(output=result)

                return DialogueResponse(session_id=request.session_id, **result)

            except Exception as e:
                span.update(
                    output={"error": str(e)}, level="ERROR", status_message=f"Dialogue processing failed: {str(e)}"
                )
                raise
    else:
        # Langfuse 없이 실행
        result = await handle_dialogue_logic(request.user_input)
        return DialogueResponse(session_id=request.session_id, **result)


@app.post("/api/v1/create-content", response_model=ContentCreationResponse, tags=["A2A Protocol"])
async def handle_content_creation(request: ContentCreationRequest, api_key: str = Depends(get_api_key)):

    if langfuse_client:
        with langfuse_client.start_as_current_span(
            name="content-creation-request",
            input={"topic": request.topic, "user_preferences": request.user_preferences},
        ) as span:
            # 트레이스 속성 설정
            span.update_trace(
                tags=["content-creation", "api"],
                metadata={"endpoint": "/api/v1/create-content", "topic": request.topic},
            )

            try:
                draft = await asyncio.to_thread(
                    handle_creation_logic, request.topic, request.user_preferences, mcp_client
                )

                # 결과 업데이트
                response_data = {"draft_content": draft, "status": "COMPLETED"}
                span.update(output=response_data)
                span.update_trace(output=response_data)

                return ContentCreationResponse(draft_content=draft, status="COMPLETED")

            except Exception as e:
                error_data = {"error": str(e), "status": "FAILED"}
                span.update(output=error_data, level="ERROR", status_message=f"Content creation failed: {str(e)}")
                return ContentCreationResponse(draft_content="", status="FAILED", error_message=str(e))
    else:
        # Langfuse 없이 실행
        try:
            draft = await asyncio.to_thread(handle_creation_logic, request.topic, request.user_preferences, mcp_client)
            return ContentCreationResponse(draft_content=draft, status="COMPLETED")
        except Exception as e:
            return ContentCreationResponse(draft_content="", status="FAILED", error_message=str(e))


@app.post("/api/v1/quality-control", response_model=QualityControlResponse, tags=["A2A Protocol"])
async def handle_quality_control(request: QualityControlRequest, api_key: str = Depends(get_api_key)):

    if langfuse_client:
        with langfuse_client.start_as_current_span(
            name="quality-control-request",
            input={"topic": request.topic, "draft_content_length": len(request.draft_content)},
        ) as span:
            # 트레이스 속성 설정
            span.update_trace(
                tags=["quality-control", "api"],
                metadata={"endpoint": "/api/v1/quality-control", "topic": request.topic},
            )

            try:
                final_post, report = await handle_qc_logic(request.topic, request.draft_content)

                # 결과 업데이트
                response_data = {"final_post": final_post, "qa_report": report, "status": "COMPLETED"}
                span.update(output=response_data)
                span.update_trace(output=response_data)

                return QualityControlResponse(final_post=final_post, qa_report=report, status="COMPLETED")

            except Exception as e:
                span.update(
                    output={"error": str(e), "status": "FAILED"},
                    level="ERROR",
                    status_message=f"Quality control failed: {str(e)}",
                )
                raise
    else:
        # Langfuse 없이 실행
        final_post, report = await handle_qc_logic(request.topic, request.draft_content)
        return QualityControlResponse(final_post=final_post, qa_report=report, status="COMPLETED")


print("a2a_blog_system.py 파일이 Langfuse v3 SDK로 업데이트되었습니다.")
