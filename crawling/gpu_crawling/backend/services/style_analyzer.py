"""
Style Analyzer - Extract style and color hints from product title.
Keyword-based for fast, dependency-free inference during crawling.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from services.color_analyzer import analyze_rgb_color, determine_color_temperature, hex_to_rgb


# Ordered style tags (priority matters for primary style)
STYLE_KEYWORDS: List[tuple[str, List[str]]] = [
    ("미니멀", ["미니멀", "심플", "베이직", "클린", "무지", "솔리드", "simple", "basic", "minimal"]),
    ("캐주얼", ["캐주얼", "데일리", "캠퍼스", "스쿨", "casual", "daily"]),
    ("스트릿", ["스트릿", "스트리트", "힙합", "힙", "street", "hiphop"]),
    ("스포티", ["스포츠", "스포티", "애슬레저", "트레이닝", "러닝", "sport", "athleisure"]),
    ("포멀", ["포멀", "클래식", "정장", "수트", "오피스", "댄디", "formal", "classic"]),
    ("빈티지", ["빈티지", "레트로", "구제", "vintage", "retro"]),
    ("러블리", ["러블리", "로맨틱", "페미닌", "프릴", "레이스", "romantic", "lovely"]),
    ("테크웨어", ["테크웨어", "고프코어", "gorp", "techwear"]),
    ("워크웨어", ["워크웨어", "유틸리티", "workwear", "utility"]),
    ("프레피", ["프레피", "아이비", "스쿨룩", "ivy", "preppy"]),
    ("Y2K", ["Y2K", "와이투케이", "2000", "00s"]),
    ("보헤미안", ["보헤미안", "보호", "boho", "bohemian"]),
]


COLOR_KEYWORDS: List[tuple[str, List[str]]] = [
    ("black", ["블랙", "검정", "흑색", "BLACK"]),
    ("white", ["화이트", "하양", "하얀", "WHITE", "아이보리"]),
    ("gray", ["그레이", "회색", "차콜", "그레", "GRAY", "GREY"]),
    ("navy", ["네이비", "남색", "NAVY"]),
    ("blue", ["블루", "파랑", "청색", "BLUE", "DENIM", "데님"]),
    ("red", ["레드", "빨강", "와인", "버건디", "RED"]),
    ("pink", ["핑크", "로즈", "PINK", "ROSE"]),
    ("purple", ["퍼플", "보라", "바이올렛", "라일락", "PURPLE", "VIOLET"]),
    ("orange", ["오렌지", "ORANGE"]),
    ("yellow", ["옐로", "노랑", "머스터드", "YELLOW", "MUSTARD"]),
    ("green", ["그린", "초록", "카키", "GREEN", "KHAKI"]),
    ("beige", ["베이지", "크림", "오트밀", "BEIGE", "CREAM", "OATMEAL"]),
    ("brown", ["브라운", "갈색", "카멜", "BROWN", "CAMEL"]),
]


COLOR_HEX_MAP: Dict[str, str] = {
    "black": "#111111",
    "white": "#f5f5f5",
    "gray": "#7d7d7d",
    "navy": "#1b2a49",
    "blue": "#2f6cc0",
    "red": "#c0392b",
    "pink": "#e67ea2",
    "purple": "#7a4fb3",
    "orange": "#f08a24",
    "yellow": "#f2c94c",
    "green": "#2e7d32",
    "beige": "#d8c3a5",
    "brown": "#6d4c41",
}


def _match_keywords(title: str, keywords: List[str]) -> bool:
    lowered = title.lower()
    for key in keywords:
        if key.lower() in lowered:
            return True
    return False


def extract_style_tags(title: Optional[str]) -> List[str]:
    """Extract ordered style tags from product title."""
    if not title:
        return []
    tags: List[str] = []
    for style, keywords in STYLE_KEYWORDS:
        if _match_keywords(title, keywords):
            tags.append(style)
    return tags


def extract_color_keys(title: Optional[str]) -> List[str]:
    """Extract color keyword keys from title."""
    if not title:
        return []
    keys: List[str] = []
    for color_key, keywords in COLOR_KEYWORDS:
        if _match_keywords(title, keywords):
            keys.append(color_key)
    return keys


def infer_color_from_title(title: Optional[str]) -> Optional[Dict[str, object]]:
    """
    Infer a PCCS-like color payload from title keywords.
    Returns dict aligned with analyze_product_colors output.
    """
    color_keys = extract_color_keys(title)
    if not color_keys:
        return None

    primary_key = color_keys[0]
    hex_color = COLOR_HEX_MAP.get(primary_key)
    if not hex_color:
        return None

    r, g, b = hex_to_rgb(hex_color)
    pccs = analyze_rgb_color(r, g, b)
    temperature = determine_color_temperature(pccs.hue)

    return {
        "pccs_hue": pccs.hue,
        "pccs_value": pccs.value,
        "pccs_chroma": pccs.chroma,
        "pccs_tone": pccs.tone,
        "primary_color_hex": pccs.hex_color,
        "color_palette": [pccs.hex_color],
        "color_temperature": temperature,
    }

