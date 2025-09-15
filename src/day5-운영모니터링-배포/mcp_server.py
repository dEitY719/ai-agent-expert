# --- Imports ---
import os
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from langfuse import observe
from pydantic import BaseModel, Field
from server_resources import get_style_guide, get_template
from server_tools import arxiv_search, news_api_search, web_search
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# --- App & Limiter Setup ---
app = FastAPI(title="LLM Agent Resource Hub (MCP Server)", version="1.0.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Security Setup ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == os.environ.get("MASTER_API_KEY"):
        return api_key
    else:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")


# --- Pydantic Models ---
class ToolCallRequest(BaseModel):
    query: str = Field(..., description="Tool에 전달할 검색어 또는 입력값")


# --- Root Endpoint ---
@app.get("/", summary="서버 상태 확인", tags=["Status"])
async def read_root():
    return {"status": "ok", "message": "MCP Server is running successfully."}


# --- Production Endpoints with Langfuse Observability ---
@app.post("/api/v1/tools/web_search", summary="웹 검색 (보안/속도제한/추적)", tags=["Production Tools"])
@limiter.limit("20/minute")
@observe(name="mcp-tool-web-search")
async def prod_web_search(request: Request, data: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await web_search(data.query)
    return {"tool": "web_search", "query": data.query, "result": result}


@app.post("/api/v1/tools/news_api", summary="뉴스 검색 (보안/속도제한/추적)", tags=["Production Tools"])
@limiter.limit("20/minute")
@observe(name="mcp-tool-news-api")
async def prod_news_search(request: Request, data: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await news_api_search(data.query)
    return {"tool": "news_api", "query": data.query, "result": result}


@app.post("/api/v1/tools/arxiv_search", summary="논문 검색 (보안/속도제한/추적)", tags=["Production Tools"])
@limiter.limit("20/minute")
@observe(name="mcp-tool-arxiv-search")
async def prod_arxiv_search(request: Request, data: ToolCallRequest, api_key: str = Depends(get_api_key)):
    result = await arxiv_search(data.query)
    return {"tool": "arxiv_search", "query": data.query, "result": result}


@app.get(
    "/api/v1/resources/templates/{template_id}",
    summary="템플릿 조회 (보안/속도제한/추적)",
    tags=["Production Resources"],
)
@limiter.limit("60/minute")
@observe(name="mcp-resource-template")
async def prod_read_template(request: Request, template_id: str, api_key: str = Depends(get_api_key)):
    content = await get_template(template_id)
    if isinstance(content, dict) and "error" in content:
        raise HTTPException(status_code=404, detail=content["error"])
    return {"resource": "template", "id": template_id, "content": content}


print("mcp_server.py 파일이 Langfuse 추적 기능으로 업데이트되었습니다.")
