import os

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

# --- FastAPI 앱 초기화 ---
app = FastAPI(
    title="LLM Agent Resource Hub (MCP Server)",
    description="다양한 Agent들이 공유할 수 있는 Tool과 리소스를 제공하는 중앙 MCP 서버입니다.",
    version="1.0.0",
)


# --- 기본 엔드포인트: 서버 상태 확인 ---
@app.get("/", summary="서버 상태 확인", tags=["Status"])
async def read_root():
    """서버가 정상적으로 실행 중인지 확인하는 기본 엔드포인트입니다."""
    return {"status": "ok", "message": "MCP Server is running successfully."}


print("✅ mcp_server.py 파일의 기본 뼈대가 생성되었습니다.")

from typing import Any, Dict

from fastapi import Body

# 방금 만든 Tool 함수들을 import
from server_tools import arxiv_search, news_api_search, web_search


# --- Pydantic 모델 정의: Tool 호출을 위한 입력 스키마 ---
class ToolCallRequest(BaseModel):
    query: str = Field(..., description="Tool에 전달할 검색어 또는 입력값")


# --- Tool 엔드포인트 구현 ---
@app.post("/tools/web_search", summary="일반 웹 검색 수행", tags=["Tools"])
async def run_web_search(request: ToolCallRequest):
    result = await web_search(request.query)
    return {"tool": "web_search", "query": request.query, "result": result}


@app.post("/tools/news_api", summary="최신 뉴스 기사 검색", tags=["Tools"])
async def run_news_search(request: ToolCallRequest):
    result = await news_api_search(request.query)
    return {"tool": "news_api", "query": request.query, "result": result}


@app.post("/tools/arxiv_search", summary="학술 논문 검색", tags=["Tools"])
async def run_arxiv_search(request: ToolCallRequest):
    result = await arxiv_search(request.query)
    return {"tool": "arxiv_search", "query": request.query, "result": result}


print("✅ 3개의 Tool 엔드포인트가 mcp_server.py에 추가되었습니다.")

from server_resources import get_style_guide, get_template


# --- 리소스 엔드포인트 구현 ---
@app.get("/resources/templates/{template_id}", summary="블로그 템플릿 조회", tags=["Resources"])
async def read_template(template_id: str):
    content = await get_template(template_id)
    if "error" in content:
        raise HTTPException(status_code=404, detail=content["error"])
    return {"resource": "template", "id": template_id, "content": content}


@app.get("/resources/style_guides/{guide_id}", summary="스타일 가이드 조회", tags=["Resources"])
async def read_style_guide(guide_id: str):
    content = await get_style_guide(guide_id)
    if "error" in content:
        raise HTTPException(status_code=404, detail=content["error"])
    return {"resource": "style_guide", "id": guide_id, "content": content}


print("✅ 2개의 리소스 엔드포인트가 mcp_server.py에 추가되었습니다.")

from fastapi import Request, Security
from fastapi.security import APIKeyHeader

# --- 보안: API 키 인증 ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def get_api_key(api_key: str = Security(api_key_header)):
    """요청 헤더에서 API 키를 가져와 마스터 키와 비교하는 의존성 함수"""
    if api_key == os.environ["MASTER_API_KEY"]:
        return api_key
    else:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key",
        )


# --- 기존 엔드포인트를 보안이 적용된 버전으로 교체 ---
# 새로운 경로로 보안 엔드포인트 생성


@app.post("/secure/tools/web_search", summary="일반 웹 검색 수행 (보안)", tags=["Protected Tools"])
async def secure_web_search(request: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await web_search(request.query)
    return {"tool": "web_search", "query": request.query, "result": result}


@app.post("/secure/tools/news_api", summary="최신 뉴스 기사 검색 (보안)", tags=["Protected Tools"])
async def secure_news_search(request: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await news_api_search(request.query)
    return {"tool": "news_api", "query": request.query, "result": result}


@app.post("/secure/tools/arxiv_search", summary="학술 논문 검색 (보안)", tags=["Protected Tools"])
async def secure_arxiv_search(request: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await arxiv_search(request.query)
    return {"tool": "arxiv_search", "query": request.query, "result": result}


@app.get("/secure/resources/templates/{template_id}", summary="블로그 템플릿 조회 (보안)", tags=["Protected Resources"])
async def secure_read_template(template_id: str, api_key: str = Depends(get_api_key)):
    content = await get_template(template_id)
    if isinstance(content, dict) and "error" in content:
        raise HTTPException(status_code=404, detail=content["error"])
    return {"resource": "template", "id": template_id, "content": content}


@app.get("/secure/resources/style_guides/{guide_id}", summary="스타일 가이드 조회 (보안)", tags=["Protected Resources"])
async def secure_read_style_guide(guide_id: str, api_key: str = Depends(get_api_key)):
    content = await get_style_guide(guide_id)
    if isinstance(content, dict) and "error" in content:
        raise HTTPException(status_code=404, detail=content["error"])
    return {"resource": "style_guide", "id": guide_id, "content": content}


print("✅ 보안 API 키 인증이 적용된 새로운 엔드포인트들이 추가되었습니다.")

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# --- 안정성: 요청 수 제한 ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Rate limiting이 적용된 최종 엔드포인트들
@app.post("/api/v1/tools/web_search", summary="웹 검색 (최종)", tags=["Production Tools"])
@limiter.limit("10/minute")
async def production_web_search(request: Request, data: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await web_search(data.query)
    return {"tool": "web_search", "query": data.query, "result": result}


@app.post("/api/v1/tools/news_api", summary="뉴스 검색 (최종)", tags=["Production Tools"])
@limiter.limit("10/minute")
async def production_news_search(request: Request, data: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await news_api_search(data.query)
    return {"tool": "news_api", "query": data.query, "result": result}


@app.post("/api/v1/tools/arxiv_search", summary="논문 검색 (최종)", tags=["Production Tools"])
@limiter.limit("10/minute")
async def production_arxiv_search(request: Request, data: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await arxiv_search(data.query)
    return {"tool": "arxiv_search", "query": data.query, "result": result}


print("✅ Rate limiting이 적용된 최종 프로덕션 엔드포인트들이 추가되었습니다.")
