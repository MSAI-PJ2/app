# kakao_geo.py
import requests, os
from dotenv import load_dotenv
load_dotenv()

def coords_to_address(lat: float, lon: float) -> dict | None:
    """카카오 좌표→행정구역 변환. 실패 시 None 반환."""
    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_REST_API_KEY')}"}
    params = {"x": lon, "y": lat}  # ⚠️ 카카오는 x=경도, y=위도 순서

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        if not docs:
            return None
        region = docs[0]
        return {
            "시도": region["region_1depth_name"],
            "시군구": region["region_2depth_name"],
        }
    except Exception as e:
        print(f"카카오 API 호출 실패: {e}")
        return None