#!/usr/bin/env python3
"""
연구 자료 저장 MCP 서버
FastMCP를 사용하여 연구 자료를 저장하고 관리하는 MCP 서버를 구현합니다.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field


# 데이터 모델 정의
class ResearchMaterial(BaseModel):
    """연구 자료 모델"""

    id: str = Field(..., description="연구 자료 고유 ID")
    title: str = Field(..., description="연구 자료 제목")
    content: str = Field(..., description="연구 자료 내용")
    category: str = Field(..., description="연구 자료 카테고리")
    tags: List[str] = Field(default_factory=list, description="연구 자료 태그")
    source_url: Optional[str] = Field(None, description="원본 출처 URL")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 일시")
    updated_at: datetime = Field(default_factory=datetime.now, description="수정 일시")
    author: Optional[str] = Field(None, description="저자")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


# MCP 서버 생성
research_server = FastMCP(
    name="Research Storage MCP Server",
    instructions="연구 자료를 저장하고 관리하는 MCP 서버입니다. 연구 자료의 저장, 검색, 수정, 삭제 기능을 제공합니다.",
)

# 데이터 저장 경로
DATA_DIR = Path(__file__).parent / "research_data"
DATA_DIR.mkdir(exist_ok=True)
MATERIALS_FILE = DATA_DIR / "materials.json"


def load_materials() -> Dict[str, ResearchMaterial]:
    """저장된 연구 자료들을 로드합니다."""
    if not MATERIALS_FILE.exists():
        return {}

    try:
        with open(MATERIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {material_id: ResearchMaterial(**material_data) for material_id, material_data in data.items()}
    except Exception as e:
        print(f"자료 로드 오류: {e}")
        return {}


def save_materials(materials: Dict[str, ResearchMaterial]):
    """연구 자료들을 저장합니다."""
    try:
        data = {material_id: material.dict() for material_id, material in materials.items()}
        with open(MATERIALS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"자료 저장 오류: {e}")


# 전역 자료 저장소
materials_store = load_materials()


@research_server.resource("research://materials", description="저장된 모든 연구 자료 목록")
async def list_all_materials():
    """저장된 모든 연구 자료의 목록을 반환합니다."""
    materials_list = []
    for material in materials_store.values():
        materials_list.append(
            {
                "id": material.id,
                "title": material.title,
                "category": material.category,
                "tags": material.tags,
                "created_at": material.created_at.isoformat(),
                "author": material.author,
            }
        )

    return {
        "total_count": len(materials_list),
        "materials": sorted(materials_list, key=lambda x: x["created_at"], reverse=True),
    }


@research_server.resource("research://materials/{material_id}", description="특정 연구 자료의 상세 정보")
async def get_material(material_id: str):
    """특정 연구 자료의 상세 정보를 반환합니다."""
    if material_id not in materials_store:
        return {"error": f"연구 자료를 찾을 수 없습니다: {material_id}"}

    material = materials_store[material_id]
    return {
        "material": material.dict(),
        "word_count": len(material.content.split()),
        "character_count": len(material.content),
    }


@research_server.resource("research://materials/category/{category}", description="특정 카테고리의 연구 자료 목록")
async def get_materials_by_category(category: str):
    """특정 카테고리의 연구 자료들을 반환합니다."""
    category_materials = [
        material for material in materials_store.values() if material.category.lower() == category.lower()
    ]

    return {
        "category": category,
        "count": len(category_materials),
        "materials": [
            {
                "id": material.id,
                "title": material.title,
                "tags": material.tags,
                "created_at": material.created_at.isoformat(),
                "author": material.author,
            }
            for material in category_materials
        ],
    }


@research_server.resource("research://materials/tag/{tag}", description="특정 태그가 포함된 연구 자료 목록")
async def get_materials_by_tag(tag: str):
    """특정 태그가 포함된 연구 자료들을 반환합니다."""
    tag_materials = [
        material for material in materials_store.values() if tag.lower() in [t.lower() for t in material.tags]
    ]

    return {
        "tag": tag,
        "count": len(tag_materials),
        "materials": [
            {
                "id": material.id,
                "title": material.title,
                "category": material.category,
                "created_at": material.created_at.isoformat(),
                "author": material.author,
            }
            for material in tag_materials
        ],
    }


@research_server.resource("research://materials/search/{query}", description="키워드 검색 결과")
async def search_materials(query: str):
    """제목, 내용, 태그에서 키워드를 검색합니다."""
    query_lower = query.lower()
    search_results = []

    for material in materials_store.values():
        relevance_score = 0

        # 제목 검색
        if query_lower in material.title.lower():
            relevance_score += 10

        # 내용 검색
        if query_lower in material.content.lower():
            relevance_score += 5

        # 태그 검색
        if any(query_lower in tag.lower() for tag in material.tags):
            relevance_score += 8

        # 카테고리 검색
        if query_lower in material.category.lower():
            relevance_score += 6

        if relevance_score > 0:
            search_results.append(
                {
                    "material": {
                        "id": material.id,
                        "title": material.title,
                        "category": material.category,
                        "tags": material.tags,
                        "created_at": material.created_at.isoformat(),
                        "author": material.author,
                    },
                    "relevance_score": relevance_score,
                    "preview": material.content[:200] + "..." if len(material.content) > 200 else material.content,
                }
            )

    # 관련도 순으로 정렬
    search_results.sort(key=lambda x: x["relevance_score"], reverse=True)

    return {"query": query, "total_results": len(search_results), "results": search_results}


# 도구(Tools) 정의
@research_server.tool(name="create_research_material", description="새로운 연구 자료를 생성합니다.")
async def create_research_material(
    title: str, content: str, category: str, tags: List[str] = None, source_url: str = None, author: str = None
) -> str:
    """새로운 연구 자료를 생성합니다."""
    if tags is None:
        tags = []

    material_id = str(uuid.uuid4())
    material = ResearchMaterial(
        id=material_id, title=title, content=content, category=category, tags=tags, source_url=source_url, author=author
    )

    materials_store[material_id] = material
    save_materials(materials_store)

    return f"연구 자료가 성공적으로 생성되었습니다. ID: {material_id}"


@research_server.tool(name="update_research_material", description="기존 연구 자료를 수정합니다.")
async def update_research_material(
    material_id: str,
    title: str = None,
    content: str = None,
    category: str = None,
    tags: List[str] = None,
    source_url: str = None,
    author: str = None,
) -> str:
    """기존 연구 자료를 수정합니다."""
    if material_id not in materials_store:
        return f"오류: 연구 자료를 찾을 수 없습니다. ID: {material_id}"

    material = materials_store[material_id]

    # 제공된 값들만 업데이트
    if title is not None:
        material.title = title
    if content is not None:
        material.content = content
    if category is not None:
        material.category = category
    if tags is not None:
        material.tags = tags
    if source_url is not None:
        material.source_url = source_url
    if author is not None:
        material.author = author

    material.updated_at = datetime.now()

    save_materials(materials_store)

    return f"연구 자료가 성공적으로 수정되었습니다. ID: {material_id}"


@research_server.tool(name="delete_research_material", description="연구 자료를 삭제합니다.")
async def delete_research_material(material_id: str) -> str:
    """연구 자료를 삭제합니다."""
    if material_id not in materials_store:
        return f"오류: 연구 자료를 찾을 수 없습니다. ID: {material_id}"

    deleted_material = materials_store.pop(material_id)
    save_materials(materials_store)

    return f"연구 자료가 성공적으로 삭제되었습니다. 제목: {deleted_material.title}"


@research_server.tool(name="get_research_statistics", description="연구 자료에 대한 통계를 제공합니다.")
async def get_research_statistics() -> Dict[str, Any]:
    """연구 자료에 대한 통계를 계산하여 반환합니다."""
    if not materials_store:
        return {"message": "저장된 연구 자료가 없습니다."}

    total_materials = len(materials_store)
    categories = {}
    tags = {}
    authors = {}
    total_words = 0

    for material in materials_store.values():
        # 카테고리별 통계
        categories[material.category] = categories.get(material.category, 0) + 1

        # 태그별 통계
        for tag in material.tags:
            tags[tag] = tags.get(tag, 0) + 1

        # 저자별 통계
        if material.author:
            authors[material.author] = authors.get(material.author, 0) + 1

        # 총 단어 수
        total_words += len(material.content.split())

    return {
        "total_materials": total_materials,
        "total_words": total_words,
        "categories": categories,
        "top_tags": sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10],
        "authors": authors,
        "average_words_per_material": total_words / total_materials if total_materials > 0 else 0,
    }


@research_server.tool(name="export_research_materials", description="연구 자료를 JSON 형식으로 내보냅니다.")
async def export_research_materials(category: str = None, format: str = "json") -> str:
    """연구 자료를 지정된 형식으로 내보냅니다."""
    if format.lower() != "json":
        return "오류: 현재 JSON 형식만 지원합니다."

    export_data = {}

    if category:
        # 특정 카테고리만 내보내기
        export_data = {
            material_id: material.dict()
            for material_id, material in materials_store.items()
            if material.category.lower() == category.lower()
        }
    else:
        # 모든 자료 내보내기
        export_data = {material_id: material.dict() for material_id, material in materials_store.items()}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_export_{timestamp}.json"

    export_path = DATA_DIR / filename
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    return f"연구 자료가 성공적으로 내보내졌습니다. 파일: {filename}, 자료 수: {len(export_data)}"


if __name__ == "__main__":
    # 서버 시작 시 데이터 로드 확인
    print(f"📚 연구 자료 저장 MCP 서버 시작")
    print(f"📁 데이터 저장 경로: {DATA_DIR}")
    print(f"📊 현재 저장된 자료 수: {len(materials_store)}")

    # 서버 실행
    research_server.run()
