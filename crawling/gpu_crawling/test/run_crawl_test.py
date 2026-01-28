import json
import os
import time
import uuid
import requests


BASE_URL = "http://localhost:8000"
TEST_URL = "https://musinsa.onelink.me/ANAQ/wptytumt"
PHOTO_PATH = "/home/MadCamp/KakaoTalk_20260126_202233039.jpg"
OUTPUT_PATH = "/home/MadCamp/MadCamp_3week/test/crawl_personalcolor_recommendation_result.json"
MUSINSA_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://www.musinsa.com",
    "Referer": "https://www.musinsa.com/",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _post_json(url, payload, token=None, timeout=30):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(url, json=payload, headers=headers, timeout=timeout)


def _get(url, token=None, timeout=30):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(url, headers=headers, timeout=timeout)


def _fetch_top_categories():
    url = "https://api.musinsa.com/api2/dp/v1/categories"
    params = {"gf": "A"}
    resp = requests.get(url, headers=MUSINSA_API_HEADERS, params=params, timeout=15)
    if not resp.ok:
        return {}
    data = resp.json()
    mapping = {}
    for item in data.get("data", {}).get("list", []):
        title = item.get("categoryTitle")
        code = item.get("categoryCode")
        if title and code:
            mapping[title] = code
    return mapping


def _fetch_category_goods(category_code, page=1, size=12):
    url = "https://api.musinsa.com/api2/dp/v1/plp/goods"
    params = {
        "gf": "A",
        "sortCode": "POPULAR",
        "category": category_code,
        "size": size,
        "testGroup": "",
        "caller": "CATEGORY",
        "page": page,
        "seen": 0,
        "seenAds": "",
    }
    headers = dict(MUSINSA_API_HEADERS)
    headers["Referer"] = f"https://www.musinsa.com/categories/item/{category_code}"
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    if not resp.ok:
        return []
    return resp.json().get("data", {}).get("list", []) or []


def main():
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    password = "testpassword123!"

    results = {}

    # Register
    reg = _post_json(f"{BASE_URL}/auth/register", {"username": username, "password": password})
    results["register"] = {"status": reg.status_code, "body": reg.json() if reg.content else None}

    # Login
    login = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    results["login"] = {"status": login.status_code, "body": login.json() if login.content else None}
    token = login.json().get("access_token")

    # Personal color analysis
    if not os.path.exists(PHOTO_PATH):
        raise FileNotFoundError(f"Photo not found: {PHOTO_PATH}")

    with open(PHOTO_PATH, "rb") as f:
        files = {"image": ("user.jpg", f, "image/jpeg")}
        pc = requests.post(
            f"{BASE_URL}/personal-color/analyze",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            timeout=60,
        )
    results["personal_color_analyze"] = {"status": pc.status_code, "body": pc.json() if pc.content else None}

    # User status after analysis
    status = _get(f"{BASE_URL}/user/status", token=token)
    results["user_status"] = {"status": status.status_code, "body": status.json() if status.content else None}

    # Track product (source)
    track = _post_json(f"{BASE_URL}/products/track", {"url": TEST_URL}, token=token, timeout=60)
    results["track_product"] = {"status": track.status_code, "body": track.json() if track.content else None}
    product_id = None
    source_category = None
    if track.ok:
        body = track.json()
        product_id = body.get("id")
        source_category = body.get("category_main")

    # Pre-seed category products from host (API is blocked inside container)
    seed_summary = {"attempted": 0, "tracked": 0, "categories": {}}
    target_categories = ["상의", "아우터", "바지"]
    if source_category in target_categories:
        target_categories.remove(source_category)

    category_map = _fetch_top_categories()
    for cat in target_categories:
        code = category_map.get(cat)
        if not code:
            continue
        goods_list = _fetch_category_goods(code, page=1, size=12)
        seed_summary["categories"][cat] = {"fetched": len(goods_list), "tracked": 0}
        for goods in goods_list[:10]:
            goods_no = goods.get("goodsNo")
            if not goods_no:
                continue
            seed_summary["attempted"] += 1
            url = goods.get("goodsLinkUrl") or f"https://www.musinsa.com/products/{goods_no}"
            resp = _post_json(f"{BASE_URL}/products/track", {"url": url}, token=token, timeout=30)
            if resp.ok:
                seed_summary["tracked"] += 1
                seed_summary["categories"][cat]["tracked"] += 1
    results["seed_preload"] = seed_summary

    # Get recommendations (may trigger crawling)
    rec = None
    if product_id:
        rec = _get(f"{BASE_URL}/products/{product_id}/recommendations", token=token, timeout=180)
        results["recommendations"] = {"status": rec.status_code, "body": rec.json() if rec.content else None}
    else:
        results["recommendations"] = {"status": None, "body": None}

    # Final success check
    status_body = results.get("user_status", {}).get("body") or {}
    personal_fields_ok = all(
        status_body.get(k) is not None
        for k in [
            "personal_color_season",
            "personal_color_type",
            "personal_color_tone",
            "personal_color_kstyle",
            "skin_tone_hex",
        ]
    )

    rec_body = results.get("recommendations", {}).get("body") or {}
    total_items = rec_body.get("total_items", 0) if isinstance(rec_body, dict) else 0

    results["summary"] = {
        "personal_color_filled": personal_fields_ok,
        "recommendation_total_items": total_items,
        "overall_success": bool(personal_fields_ok and total_items > 0),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
