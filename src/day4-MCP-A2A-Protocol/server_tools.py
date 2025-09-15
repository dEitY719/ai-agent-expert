import os

import arxiv
from newsapi import NewsApiClient
from tavily import TavilyClient


# --- 1. 웹 검색 (Tavily) ---
async def web_search(query: str) -> str:
    try:
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        response = client.search(query=query, max_results=3, search_depth="advanced")
        return str(
            [{"title": obj["title"], "url": obj["url"], "content": obj["content"]} for obj in response["results"]]
        )
    except Exception as e:
        return f"Tavily API 오류: {e}"


# --- 2. 뉴스 기사 검색 (NewsAPI) ---
async def news_api_search(query: str) -> str:
    try:
        client = NewsApiClient(api_key=os.environ["NEWS_API_KEY"])
        response = client.get_everything(q=query, language="ko", sort_by="relevancy", page_size=3)
        if response["status"] == "ok":
            return str(
                [
                    {"title": article["title"], "url": article["url"], "description": article["description"]}
                    for article in response["articles"]
                ]
            )
        else:
            return f"News API 오류: {response.get('message', 'Unknown error')}"
    except Exception as e:
        return f"News API 클라이언트 오류: {e}"


# --- 3. 학술 논문 검색 (Arxiv) ---
async def arxiv_search(query: str) -> str:
    try:
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=2, sort_by=arxiv.SortCriterion.Relevance)
        results = list(client.results(search))
        return str(
            [
                {
                    "title": result.title,
                    "authors": [str(a) for a in result.authors],
                    "summary": result.summary,
                    "pdf_url": result.pdf_url,
                }
                for result in results
            ]
        )
    except Exception as e:
        return f"Arxiv 검색 오류: {e}"
