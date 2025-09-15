import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

MCP_SERVER_URL = "http://localhost:8501"
A2A_SERVER_URL = "http://localhost:8502"

client = httpx.AsyncClient(timeout=300.0)


async def proxy_request(target_url: str, request: Request):
    """
    httpx를 스트리밍 모드로 사용하여 요청을 전달하고 응답을 스트리밍하는 함수.
    StreamConsumed 오류를 방지하기 위해 client.send(stream=True)를 사용합니다.
    """
    # 1. 클라이언트의 요청 정보를 기반으로 내부 서버로 보낼 요청을 재구성합니다.
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "cookie"]}

    req = client.build_request(
        method=request.method,
        url=target_url,
        headers=headers,
        params=request.query_params,
        content=await request.body(),
    )

    # 2. stream=True 옵션으로 요청을 보내 응답 본문을 미리 읽지 않도록 합니다.
    r = await client.send(req, stream=True)

    # 3. 내부 서버의 응답을 클라이언트에게 그대로 스트리밍합니다.
    return StreamingResponse(r.aiter_raw(), status_code=r.status_code, headers=r.headers)


@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_mcp(path: str, request: Request):
    """'/mcp'로 시작하는 모든 요청을 MCP 서버(8501)로 전달합니다."""
    target_url = f"{MCP_SERVER_URL}/{path}"
    return await proxy_request(target_url, request)


@app.api_route("/a2a/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_a2a(path: str, request: Request):
    """'/a2a'로 시작하는 모든 요청을 A2A Gateway 서버(8502)로 전달합니다."""
    target_url = f"{A2A_SERVER_URL}/{path}"
    return await proxy_request(target_url, request)


@app.get("/")
def read_root():
    return {"message": "Reverse Proxy is running. Use /mcp/ or /a2a/ prefixes."}
