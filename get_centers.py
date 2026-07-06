# get_centers.py
from azure.cosmos import CosmosClient
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# [로컬 우회 — 커밋 금지] COSMOS_ENDPOINT 비어있으면 container=None (단일 게이트웨이 env 로컬 테스트용).
# 위기 센터 조회(get_centers/get_sigungu_list)는 위기 분기에서만 호출되므로 일반 대화는 정상 동작한다.
# 근본 해결은 위기 센터를 게이트웨이 crisis payload(resources[])로 일원화하는 것(단일 API 감사 참고).
_ep, _key = os.getenv("COSMOS_ENDPOINT"), os.getenv("COSMOS_KEY")
container = (CosmosClient(url=_ep, credential=_key)
             .get_database_client("cbt-db").get_container_client("kfsp_centers")) if (_ep and _key) else None

# [팀 결정 필요] 순서 확정되면 숫자만 조정
PRIORITY = {
    "생명사랑위기대응센터": 1,
    "광역 자살예방센터": 2,
    "기초 자살예방센터": 2,
    "광역 정신건강복지센터": 3,
    "기초 정신건강복지센터": 3,
}

# 야간/주말 시간대에 노출 가능한 유형 — [팀 결정 필요]
NIGHT_AVAILABLE = {"생명사랑위기대응센터", "광역 정신건강복지센터", "광역 자살예방센터"}

# 유형별 태그라인 + 설명 (추천 결과에 함께 표시) — kfsp_centers_guide.md 표 1 반영
TYPE_INFO = {
    "생명사랑위기대응센터": {
        "tagline": "병원 안의 위기 전담 팀",
        "description": "응급실·정신건강의학과와 연계된 병원 내 전담 센터. 자살 시도 직후 즉각적인 의료·심리 개입이 필요할 때 찾아가세요.",
    },
    "광역 정신건강복지센터": {
        "tagline": "시·도 전체를 아우르는 광역 지원 허브",
        "description": "광역시·도 단위로 운영되며 기초 센터를 지원·조정하는 역할. 24시간 위기상담전화(1577-0199) 운영 주체.",
    },
    "광역 자살예방센터": {
        "tagline": "시·도 단위 자살예방 정책 실행 기관",
        "description": "광역 단위에서 자살예방 캠페인, 게이트키퍼 교육, 고위험군 관리 프로그램을 총괄합니다.",
    },
    "기초 자살예방센터": {
        "tagline": "자살예방에 집중하는 지역 전문 기관",
        "description": "정신건강복지센터와 협력하며 자살예방 특화 프로그램 운영. 고위험군 조기 발굴과 위기 개입에 특화.",
    },
    "기초 정신건강복지센터": {
        "tagline": "우리 동네 마음 건강 주치의",
        "description": "시·군·구 단위 공공 상담 기관. 위기 초기 상담부터 장기 사례관리까지 지속적인 돌봄 제공.",
    },
    "한국생명존중희망재단": {
        "tagline": "국가 자살예방 정책의 중추 기관",
        "description": "보건복지부 산하 공공재단으로 전국 자살예방 정책 연구·교육·유족 지원 총괄. 직접 상담보다 정책·교육·연구 기능 중심.",
    },
}

EMERGENCY_NUMBERS = {
    "109": "자살예방상담전화 (24시간)",
    "1577-0199": "정신건강위기상담전화 (24시간)",
    "119": "소방·응급 (24시간)",
    "112": "경찰 (24시간)",
}

SIDO_ALIASES = {
    "부산": "부산광역시", "부산시": "부산광역시",
    "서울": "서울특별시", "서울시": "서울특별시",
    "대구": "대구광역시", "대구시": "대구광역시",
    "인천": "인천광역시", "인천시": "인천광역시",
    "광주": "광주광역시", "광주시": "광주광역시",
    "대전": "대전광역시", "대전시": "대전광역시",
    "울산": "울산광역시", "울산시": "울산광역시",
    "세종": "세종특별자치시", "세종시": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도", "강원도": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도", "전라북도": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도", "제주도": "제주특별자치도",
}

def normalize_sido(sido: str) -> str:
    return SIDO_ALIASES.get(sido, sido)

def is_night_or_weekend(now: datetime = None) -> bool:
    now = now or datetime.now()
    is_weekend = now.weekday() >= 5  # 토(5), 일(6)
    is_night = now.hour >= 18 or now.hour < 9
    return is_weekend or is_night


def get_centers(sido: str, sigungu: str = None, is_crisis: bool = False) -> dict:
    """
    반환:
      centers: 추천 기관 리스트 (우선순위 정렬 + 야간 필터링 적용)
      foundation: 한국생명존중희망재단 정보 (항상 별도, 거리 추천에서 제외)
      emergency_numbers: 상시 표시용 비상연락처
      night_mode: 야간/주말 필터링 적용 여부
    """
    sido = normalize_sido(sido)
    
    query = "SELECT * FROM c WHERE c.시도 = @sido"
    params = [{"name": "@sido", "value": sido}]
    if sigungu:
        query += " AND c.시군구 = @sigungu"  # '시' 대신 '시군구' 사용 — null 누락 방지
        params.append({"name": "@sigungu", "value": sigungu})

    results = list(container.query_items(
        query=query, parameters=params, enable_cross_partition_query=True
    ))

    # 재단은 항상 별도 처리 (서울 1곳뿐, 거리 추천 부적합)
    local = [r for r in results if r["유형"] != "한국생명존중희망재단"]
    foundation = next((r for r in results if r["유형"] == "한국생명존중희망재단"), None)
    if foundation is None:
        foundation_list = list(container.query_items(
            query="SELECT * FROM c WHERE c.유형 = '한국생명존중희망재단'",
            parameters=[], enable_cross_partition_query=True
        ))
        foundation = foundation_list[0] if foundation_list else None

    night_mode = is_night_or_weekend()
    if night_mode:
        local = [r for r in local if r["유형"] in NIGHT_AVAILABLE]

    # 위기 상황이면 생명사랑위기대응센터 최우선 — [팀 결정 필요: 동적 우선순위 적용 여부]
    if is_crisis:
        local.sort(key=lambda x: (0 if x["유형"] == "생명사랑위기대응센터" else 1,
                                   PRIORITY.get(x["유형"], 99)))
    else:
        local.sort(key=lambda x: PRIORITY.get(x["유형"], 99))

    # 동일 주소·전화번호 중복 묶기 (강릉/원주/가평 등 기초자살예방·기초정신건강 중복 패턴)
    deduped = []
    seen_keys = set()
    for r in local:
        key = (r["주소"], r["전화"])
        if key in seen_keys:
            # 같은 위치의 기존 항목에 유형 추가 표시
            for d in deduped:
                if (d["주소"], d["전화"]) == key:
                    d["_merged_types"] = d.get("_merged_types", [d["유형"]]) + [r["유형"]]
            continue
        seen_keys.add(key)
        deduped.append(r)

    final = deduped[:2]  # [팀 결정 필요] 노출 개수

    # 태그라인/설명 부착 (대표 유형 기준 — 묶인 경우 첫 유형 기준)
    for r in final:
        primary_type = r.get("_merged_types", [r["유형"]])[0]
        r["_type_info"] = TYPE_INFO.get(primary_type, {})
    if foundation:
        foundation["_type_info"] = TYPE_INFO.get(foundation["유형"], {})

    return {
        "centers": final,
        "foundation": foundation,
        "emergency_numbers": EMERGENCY_NUMBERS,
        "night_mode": night_mode,
    }

def get_sigungu_list(sido: str) -> list:
    """선택된 시도에 속한 시군구 목록을 중복 제거해서 반환"""
    sido = normalize_sido(sido)
    query = "SELECT DISTINCT VALUE c.시군구 FROM c WHERE c.시도 = @sido"
    params = [{"name": "@sido", "value": sido}]
    results = list(container.query_items(
        query=query, parameters=params, enable_cross_partition_query=True
    ))
    return sorted([r for r in results if r])  # None/빈값 제외 후 정렬

if __name__ == "__main__":
    result = get_centers("부산")
    print(f"\n야간/주말 필터링: {result['night_mode']}")
    for c in result["centers"]:
        types = c.get("_merged_types", [c["유형"]])
        info = c.get("_type_info", {})
        print(f"  {c['기관명']} | {'+'.join(types)} | {c['전화']}")
        print(f"    └ {info.get('tagline', '')} — {info.get('description', '')}")
    if result["foundation"]:
        f = result["foundation"]
        print(f"  [정책기관 별도] {f['기관명']} — {f.get('_type_info', {}).get('tagline', '')}")

    print()
    result2 = get_centers("강원특별자치도", "강릉시")
    for c in result2["centers"]:
        types = c.get("_merged_types", [c["유형"]])
        info = c.get("_type_info", {})
        print(f"  {c['기관명']} | {'+'.join(types)} | {c['전화']}")
        print(f"    └ {info.get('tagline', '')}")
