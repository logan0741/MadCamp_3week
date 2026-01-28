"""
Recommendation Service - Style-based product recommendations
Uses PCCS color analysis to find matching products across categories.
"""

from typing import Dict, List, Optional, Tuple
import json
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from domain.entities import Product, PriceLog
from services.color_analyzer import (
    PCCSColor, analyze_rgb_color, hex_to_rgb,
    calculate_color_distance, find_complementary_colors,
    determine_color_temperature
)


# Category relationships for outfit coordination
CATEGORY_COORDINATION = {
    '상의': ['하의', '아우터', '신발', '가방', '액세서리'],
    '하의': ['상의', '아우터', '신발', '가방', '액세서리'],
    '아우터': ['상의', '하의', '신발', '가방'],
    '원피스': ['아우터', '신발', '가방', '액세서리'],
    '신발': ['상의', '하의', '가방', '액세서리'],
    '가방': ['상의', '하의', '아우터', '신발'],
    '액세서리': ['상의', '하의', '원피스'],
}

# PCCS Tone harmony rules
TONE_HARMONY = {
    'v': ['v', 'b', 's'],           # Vivid goes with vivid, bright, strong
    'b': ['b', 'v', 'lt', 's'],     # Bright harmonizes with bright, vivid, light
    's': ['s', 'v', 'b', 'dp'],     # Strong with strong, vivid, deep
    'dp': ['dp', 's', 'd', 'dk'],   # Deep with deep, strong, dull, dark
    'lt': ['lt', 'b', 'p', 'sf'],   # Light with light, bright, pale, soft
    'sf': ['sf', 'lt', 'd', 'g'],   # Soft with soft, light, dull, grayish
    'd': ['d', 'sf', 'dp', 'dk'],   # Dull with dull, soft, deep, dark
    'dk': ['dk', 'd', 'dp', 'dkg'], # Dark with dark, dull, deep
    'p': ['p', 'lt', 'ltg'],        # Pale with pale, light, light grayish
    'ltg': ['ltg', 'p', 'g', 'lt'], # Light grayish
    'g': ['g', 'sf', 'ltg', 'dkg'], # Grayish
    'dkg': ['dkg', 'g', 'dk'],      # Dark grayish
    'W': ['p', 'lt', 'ltg', 'Gy'],  # White
    'Bk': ['dk', 'dkg', 'v', 'Gy'], # Black
    'Gy': ['Gy', 'g', 'sf', 'd'],   # Gray
}


def get_compatible_categories(category: str) -> List[str]:
    """Get categories that coordinate well with given category."""
    return CATEGORY_COORDINATION.get(category, [])


def get_harmonious_tones(tone: str) -> List[str]:
    """Get PCCS tones that harmonize with given tone."""
    return TONE_HARMONY.get(tone, [tone])


def extract_category_from_path(category_path: str) -> Tuple[str, str]:
    """
    Extract main category and subcategory from Musinsa category path.
    Example: "Clothing > 바지 > 청/데님 팬츠" -> ("하의", "청바지")
    """
    if not category_path:
        return ('기타', '기타')

    parts = [p.strip() for p in category_path.split('>')]

    # Map Musinsa categories to our categories
    category_mapping = {
        '상의': '상의',
        '티셔츠': '상의',
        '셔츠': '상의',
        '니트': '상의',
        '맨투맨': '상의',
        '후드': '상의',
        '바지': '하의',
        '팬츠': '하의',
        '청바지': '하의',
        '데님': '하의',
        '슬랙스': '하의',
        '반바지': '하의',
        '쇼츠': '하의',
        '아우터': '아우터',
        '자켓': '아우터',
        '코트': '아우터',
        '점퍼': '아우터',
        '패딩': '아우터',
        '원피스': '원피스',
        '스커트': '원피스',
        '신발': '신발',
        '스니커즈': '신발',
        '구두': '신발',
        '가방': '가방',
        '백팩': '가방',
        '액세서리': '액세서리',
        '모자': '액세서리',
        '시계': '액세서리',
    }

    main_category = '기타'
    sub_category = parts[-1] if parts else '기타'

    for part in parts:
        for keyword, category in category_mapping.items():
            if keyword in part:
                main_category = category
                break
        if main_category != '기타':
            break

    return (main_category, sub_category)


class RecommendationService:
    """Service for finding style-matched product recommendations."""

    @staticmethod
    def get_color_matched_products(
        db: Session,
        source_product_id: int,
        target_categories: Optional[List[str]] = None,
        max_results: int = 10,
        color_distance_threshold: float = 0.3,
        tone_preference: Optional[str] = None,
        palette_colors: Optional[List[PCCSColor]] = None,
        palette_distance_threshold: float = 0.4,
    ) -> List[Dict]:
        """
        Find products that color-match with the source product.

        Args:
            db: Database session
            source_product_id: ID of the product to match
            target_categories: Categories to search (None = all coordinating categories)
            max_results: Maximum number of results
            color_distance_threshold: Max color distance (0-1, lower = more similar)

        Returns:
            List of matching products with scores
        """
        # Get source product
        source = db.query(Product).filter(Product.id == source_product_id).first()
        if not source:
            return []

        # Parse source color
        source_color = RecommendationService._get_pccs_color(source)
        if not source_color:
            return []
        source_is_neutral = source_color.chroma < 0.5 or source_color.tone in ("Bk", "Gy", "W")

        # Get products from coordinating categories
        source_category_raw = source.category_main or getattr(source, "category_path", "") or ""
        source_category = extract_category_from_path(source_category_raw)[0]
        if not target_categories:
            target_categories = get_compatible_categories(source_category)

        candidates = db.query(Product).filter(Product.id != source_product_id).limit(max_results * 5).all()

        # Score and rank products
        source_styles = RecommendationService._get_style_tags(source)

        def collect_matches(enforce_tone: bool, enforce_palette: bool) -> List[Dict]:
            matches: List[Dict] = []
            for product in candidates:
                candidate_raw = product.category_main or getattr(product, "category_path", "") or ""
                candidate_category = extract_category_from_path(candidate_raw)[0]
                if target_categories and candidate_category not in target_categories:
                    continue

                if source_styles:
                    candidate_styles = RecommendationService._get_style_tags(product)
                    if not set(source_styles) & set(candidate_styles):
                        continue

                candidate_color = RecommendationService._get_pccs_color(product)
                if not candidate_color:
                    continue

                if enforce_tone and tone_preference and product.color_temperature:
                    if product.color_temperature != tone_preference and product.color_temperature != "neutral":
                        continue

                color_distance = calculate_color_distance(source_color, candidate_color)
                if not (source_is_neutral and palette_colors):
                    if color_distance > color_distance_threshold:
                        continue

                if enforce_palette and palette_colors:
                    palette_distances = [
                        calculate_color_distance(candidate_color, palette_color)
                        for palette_color in palette_colors
                    ]
                    if min(palette_distances) > palette_distance_threshold:
                        continue

                score = RecommendationService._calculate_match_score(source, product, color_distance)
                if score > 0:
                    matches.append(
                        {
                            "product": product,
                            "score": score,
                            "match_type": "color_match" if enforce_tone else "color_match_relaxed",
                        }
                    )
            return matches

        scored_products = collect_matches(enforce_tone=True, enforce_palette=True)
        if not scored_products and palette_colors:
            scored_products = collect_matches(enforce_tone=True, enforce_palette=False)
        if not scored_products and tone_preference:
            scored_products = collect_matches(enforce_tone=False, enforce_palette=False)

        # Sort by score and return top results
        scored_products.sort(key=lambda x: x['score'], reverse=True)
        return scored_products[:max_results]

    @staticmethod
    def _calculate_match_score(
        source: Product,
        candidate: Product,
        color_distance: Optional[float] = None
    ) -> float:
        """
        Calculate matching score between two products.
        Higher score = better match.
        """
        score = 0.0

        # Brand match bonus
        if source.brand and candidate.brand:
            if source.brand.lower() == candidate.brand.lower():
                score += 0.3

        # Price range similarity (within 50% of source price)
        source_price = source.original_price or 0
        candidate_price = candidate.original_price or 0
        if source_price > 0 and candidate_price > 0:
            price_ratio = min(source_price, candidate_price) / max(source_price, candidate_price)
            if price_ratio > 0.5:
                score += 0.2 * price_ratio

        # Style tag overlap
        source_styles = RecommendationService._get_style_tags(source)
        candidate_styles = RecommendationService._get_style_tags(candidate)
        if source_styles and candidate_styles:
            overlap = len(set(source_styles) & set(candidate_styles))
            if overlap:
                score += min(0.4, 0.1 * overlap)

        # Color similarity (lower distance -> higher score)
        if color_distance is not None:
            score += max(0.0, 0.4 * (1 - color_distance))

        # Base score for having required data
        if candidate.thumbnail_url:
            score += 0.1

        return score

    @staticmethod
    def _get_style_tags(product: Product) -> List[str]:
        if not product.style_tags:
            return []
        try:
            return json.loads(product.style_tags)
        except Exception:
            return []

    @staticmethod
    def _get_pccs_color(product: Product) -> Optional[PCCSColor]:
        if product.pccs_hue is None or product.pccs_value is None or product.pccs_chroma is None:
            return None
        return PCCSColor(
            hue=float(product.pccs_hue),
            value=float(product.pccs_value),
            chroma=float(product.pccs_chroma),
            tone=product.pccs_tone or "g",
            hex_color=product.primary_color_hex or "#000000",
        )

    @staticmethod
    def get_complementary_style_products(
        db: Session,
        source_hex_color: str,
        target_categories: List[str],
        max_results: int = 5
    ) -> List[Dict]:
        """
        Find products with complementary colors for outfit coordination.
        """
        try:
            r, g, b = hex_to_rgb(source_hex_color)
            source_color = analyze_rgb_color(r, g, b)
        except:
            return []

        # Get complementary color suggestions
        suggestions = find_complementary_colors(source_color)

        results = []
        for suggestion in suggestions:
            # This is a placeholder - actual implementation needs
            # color data stored in products
            results.append({
                'suggestion_type': suggestion['type'],
                'description': suggestion['description'],
                'products': []  # Would be populated from DB query
            })

        return results

    @staticmethod
    def get_outfit_recommendations(
        db: Session,
        product_id: int,
        tone_preference: Optional[str] = None,
        palette_colors: Optional[List[PCCSColor]] = None,
        palette_distance_threshold: float = 0.4,
    ) -> Dict[str, List[Dict]]:
        """
        Get complete outfit recommendations based on a single product.

        Returns recommendations organized by category.
        """
        source = db.query(Product).filter(Product.id == product_id).first()
        if not source:
            return {}

        source_category_raw = source.category_main or getattr(source, "category_path", "") or ""
        source_category = extract_category_from_path(source_category_raw)[0]
        coordinating_categories = get_compatible_categories(source_category)

        recommendations = {}
        for category in coordinating_categories:
            matches = RecommendationService.get_color_matched_products(
                db=db,
                source_product_id=product_id,
                target_categories=[category],
                max_results=3,
                tone_preference=tone_preference,
                palette_colors=palette_colors,
                palette_distance_threshold=palette_distance_threshold,
            )
            if matches:
                recommendations[category] = [
                    {
                        'id': m['product'].id,
                        'title': m['product'].title,
                        'brand': m['product'].brand,
                        'thumbnail_url': m['product'].thumbnail_url,
                        'price': m['product'].original_price,
                        'match_score': m['score']
                    }
                    for m in matches
                ]

        return recommendations


# Helper function for API integration
def get_style_recommendations(
    db: Session,
    product_id: int,
    tone_preference: Optional[str] = None,
    preferred_palette_hex: Optional[List[str]] = None,
) -> Dict:
    """
    Main entry point for style recommendations API.
    """
    palette_colors: Optional[List[PCCSColor]] = None
    if preferred_palette_hex:
        palette_colors = []
        for hex_color in preferred_palette_hex:
            try:
                r, g, b = hex_to_rgb(hex_color)
                palette_colors.append(analyze_rgb_color(r, g, b))
            except Exception:
                continue

    recommendations = RecommendationService.get_outfit_recommendations(
        db,
        product_id,
        tone_preference=tone_preference,
        palette_colors=palette_colors,
    )

    return {
        'source_product_id': product_id,
        'recommendations': recommendations,
        'total_items': sum(len(items) for items in recommendations.values())
    }
