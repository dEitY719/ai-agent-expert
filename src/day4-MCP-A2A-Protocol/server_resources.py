BLOG_TEMPLATES = {
    "tech_analysis": "## 제목\n\n### 1. 기술 개요\n\n### 2. 핵심 작동 원리...",
    "product_review": "## 제목\n\n### 1. 첫인상 및 디자인\n\n### 2. 주요 기능...",
}

STYLE_GUIDES = {
    "default": "문체: 전문적이면서도 명확하게.\n대상 독자: 기술에 관심 있는 일반인.\n어조: 객관적이고 사실 기반.",
    "samsung_newsroom": "문체: 삼성전자 뉴스룸 공식 톤앤매너.\n대상 독자: 언론인 및 IT 업계 종사자.\n어조: 신뢰감을 주는 공식적인 어조.",
}


async def get_template(template_id: str):
    template = BLOG_TEMPLATES.get(template_id)
    if template:
        return template
    else:
        return {"error": "Template not found"}


async def get_style_guide(guide_id: str):
    guide = STYLE_GUIDES.get(guide_id)
    if guide:
        return guide
    else:
        return {"error": "Style guide not found"}
