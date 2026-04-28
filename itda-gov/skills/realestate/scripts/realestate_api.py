"""국토교통부 실거래가 공공데이터 API 클라이언트.

지원 서비스:
    - 아파트 매매 실거래가 (RTMSDataSvcAptTrade)
    - 아파트 전월세 실거래가 (RTMSDataSvcAptRent)
    - 오피스텔 매매 실거래가 (RTMSDataSvcOffiTrade)
    - 오피스텔 전월세 실거래가 (RTMSDataSvcOffiRent)

엔드포인트: https://apis.data.go.kr/1613000/
인증: serviceKey 쿼리 파라미터 (공공데이터포털 발급)
"""
from __future__ import annotations

import logging
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1613000"
_TIMEOUT = 15

# 서비스명 + 엔드포인트 매핑: (service_name, endpoint)
_SERVICES: dict[str, tuple[str, str]] = {
    "apt_trade":  ("RTMSDataSvcAptTrade",  "getRTMSDataSvcAptTrade"),
    "apt_rent":   ("RTMSDataSvcAptRent",   "getRTMSDataSvcAptRent"),
    "offi_trade": ("RTMSDataSvcOffiTrade", "getRTMSDataSvcOffiTrade"),
    "offi_rent":  ("RTMSDataSvcOffiRent",  "getRTMSDataSvcOffiRent"),
}

# 데이터셋별 활용신청 URL (data.go.kr publicDataPk 기준)
# 각 서비스는 독립적으로 활용신청 필요. 자동승인.
_APPLY_URL: dict[str, str] = {
    "apt_trade":  "https://www.data.go.kr/data/15126469/openapi.do",
    "apt_rent":   "https://www.data.go.kr/data/15126474/openapi.do",
    "offi_trade": "https://www.data.go.kr/data/15126464/openapi.do",
    "offi_rent":  "https://www.data.go.kr/data/15126475/openapi.do",
}

# API 성공 응답 코드 집합
# PDF 명세 기준 정상 응답: <resultCode>000</resultCode>
# 일부 공공데이터 API는 "00" 또는 "0000"을 반환하므로 함께 허용.
_SUCCESS_CODES = {"000", "00", "0000"}

# PDF II장 OPEN API 에러 코드 매핑 (코드 → (의미, 조치))
# 참고: references/molit-realestate-api-guide.pdf
_ERROR_CODE_HINTS: dict[str, tuple[str, str]] = {
    "01": ("Application Error", "서비스 제공기관 관리자 문의"),
    "02": ("DB Error", "서비스 제공기관 관리자 문의"),
    "03": ("No Data", "데이터 없음 — 다른 년월/지역으로 재시도"),
    "04": ("HTTP Error", "서비스 제공기관 관리자 문의"),
    "05": ("Service Time Out", "잠시 후 재시도"),
    "10": ("잘못된 요청 파라미터", "ServiceKey 파라미터 누락 — URL 확인"),
    "11": ("필수 요청 파라미터 누락", "기술문서(references/molit-realestate-api-guide.pdf) 확인"),
    "12": ("해당 OpenAPI 서비스 없음/폐기", "활용신청한 API URL 재확인"),
    "20": (
        "서비스 접근 거부 (활용 미승인)",
        "마이페이지 활용신청 승인 상태 확인 — 자동승인이라도 게이트웨이 동기화에 5~30분 소요",
    ),
    "22": ("일일 트래픽 초과", "활용신청 상세에서 일일 트래픽 한도 확인 또는 변경신청"),
    "30": (
        "등록되지 않은 서비스키",
        "마이페이지에서 발급받은 일반 인증키(Decoding) 재확인 — URL 인코딩 누락 가능성",
    ),
    "31": ("기간 만료된 서비스키", "활용연장신청 후 재시도"),
    "32": ("등록되지 않은 도메인/IP", "활용신청정보의 도메인·IP 변경신청"),
}

# 법정동코드(LAWD_CD) 매핑 — 전국 시군구
# 중복 이름은 "광역시/도 구명" 형태로 구분
_LAWD_CD_MAP: dict[str, str] = {
    # === 서울특별시 (25개 자치구) ===
    "강남구": "11680",
    "강동구": "11740",
    "강북구": "11305",
    "강서구": "11500",
    "관악구": "11620",
    "광진구": "11215",
    "구로구": "11530",
    "금천구": "11545",
    "노원구": "11350",
    "도봉구": "11320",
    "동대문구": "11230",
    "동작구": "11590",
    "마포구": "11440",
    "서대문구": "11410",
    "서초구": "11650",
    "성동구": "11200",
    "성북구": "11290",
    "송파구": "11710",
    "양천구": "11470",
    "영등포구": "11560",
    "용산구": "11170",
    "은평구": "11380",
    "종로구": "11110",
    "중구": "11140",       # 중구 기본값 = 서울 중구
    "서울 중구": "11140",
    "중랑구": "11260",

    # === 부산광역시 (16개 자치구·군) ===
    "부산 중구": "26110",
    "서구": "26140",
    "동구": "26170",
    "부산 동구": "26170",
    "영도구": "26200",
    "부산진구": "26230",
    "동래구": "26260",
    "남구": "26290",
    "부산 남구": "26290",
    "북구": "26320",
    "부산 북구": "26320",
    "해운대구": "26350",
    "사하구": "26380",
    "금정구": "26410",
    "부산 강서구": "26440",
    "연제구": "26470",
    "수영구": "26500",
    "사상구": "26530",
    "기장군": "26710",

    # === 인천광역시 ===
    "인천 중구": "28110",
    "인천 동구": "28140",
    "미추홀구": "28177",
    "연수구": "28185",
    "남동구": "28200",
    "부평구": "28237",
    "계양구": "28245",
    "인천 서구": "28260",
    "강화군": "28710",
    "옹진군": "28720",

    # === 대구광역시 ===
    "대구 중구": "27110",
    "대구 동구": "27140",
    "대구 서구": "27170",
    "대구 남구": "27200",
    "대구 북구": "27230",
    "수성구": "27260",
    "달서구": "27290",
    "달성군": "27710",
    "군위군": "27720",

    # === 광주광역시 ===
    "광주 동구": "29110",
    "광주 서구": "29140",
    "광주 남구": "29155",
    "광주 북구": "29170",
    "광산구": "29200",

    # === 대전광역시 ===
    "대전 동구": "30110",
    "대전 중구": "30140",
    "대전 서구": "30170",
    "유성구": "30200",
    "대덕구": "30230",

    # === 울산광역시 ===
    "울산 중구": "31110",
    "울산 남구": "31140",
    "울산 동구": "31170",
    "울산 북구": "31200",
    "울주군": "31710",

    # === 세종특별자치시 ===
    "세종특별자치시": "36110",
    "세종시": "36110",

    # === 경기도 ===
    "수원시": "41111",
    "수원시 장안구": "41111",
    "수원시 권선구": "41113",
    "수원시 팔달구": "41115",
    "수원시 영통구": "41117",
    "성남시": "41131",
    "성남시 수정구": "41131",
    "성남시 중원구": "41133",
    "성남시 분당구": "41135",
    "의정부시": "41150",
    "안양시 만안구": "41171",
    "안양시만안구": "41171",
    "안양시 동안구": "41173",
    "안양시동안구": "41173",
    "부천시": "41190",
    "광명시": "41210",
    "평택시": "41220",
    "동두천시": "41250",
    "안산시 상록구": "41271",
    "안산시상록구": "41271",
    "안산시 단원구": "41273",
    "안산시단원구": "41273",
    "고양시 덕양구": "41281",
    "고양시덕양구": "41281",
    "고양시 일산동구": "41285",
    "고양시일산동구": "41285",
    "고양시 일산서구": "41287",
    "고양시일산서구": "41287",
    "과천시": "41290",
    "구리시": "41310",
    "남양주시": "41360",
    "오산시": "41370",
    "시흥시": "41390",
    "군포시": "41410",
    "의왕시": "41430",
    "하남시": "41450",
    "용인시 처인구": "41461",
    "용인시처인구": "41461",
    "용인시 기흥구": "41463",
    "용인시기흥구": "41463",
    "용인시 수지구": "41465",
    "용인시수지구": "41465",
    "파주시": "41480",
    "이천시": "41500",
    "안성시": "41550",
    "김포시": "41570",
    "화성시": "41590",
    "광주시": "41610",
    "양주시": "41630",
    "포천시": "41650",
    "여주시": "41670",
    "연천군": "41800",
    "가평군": "41820",
    "양평군": "41830",

    # === 강원특별자치도 ===
    "춘천시": "51110",
    "원주시": "51130",
    "강릉시": "51150",
    "동해시": "51170",
    "태백시": "51190",
    "속초시": "51210",
    "삼척시": "51230",
    "홍천군": "51720",
    "횡성군": "51730",
    "영월군": "51750",
    "평창군": "51760",
    "정선군": "51770",
    "철원군": "51780",
    "화천군": "51790",
    "양구군": "51800",
    "인제군": "51810",
    "고성군": "51820",
    "고성군(강원)": "51820",
    "양양군": "51830",

    # === 충청북도 ===
    "청주시 상당구": "43111",
    "청주시상당구": "43111",
    "청주시 서원구": "43112",
    "청주시서원구": "43112",
    "청주시 흥덕구": "43113",
    "청주시흥덕구": "43113",
    "청주시 청원구": "43114",
    "청주시청원구": "43114",
    "충주시": "43130",
    "제천시": "43150",
    "보은군": "43720",
    "옥천군": "43730",
    "영동군": "43740",
    "증평군": "43745",
    "진천군": "43750",
    "괴산군": "43760",
    "음성군": "43770",
    "단양군": "43800",

    # === 충청남도 ===
    "천안시 동남구": "44131",
    "천안시동남구": "44131",
    "천안시 서북구": "44133",
    "천안시서북구": "44133",
    "공주시": "44150",
    "보령시": "44180",
    "아산시": "44200",
    "서산시": "44210",
    "논산시": "44230",
    "계룡시": "44250",
    "당진시": "44270",
    "금산군": "44710",
    "부여군": "44760",
    "서천군": "44770",
    "청양군": "44790",
    "홍성군": "44800",
    "예산군": "44810",
    "태안군": "44825",

    # === 전북특별자치도 ===
    "전주시 완산구": "52111",
    "전주시완산구": "52111",
    "전주시 덕진구": "52113",
    "전주시덕진구": "52113",
    "군산시": "52130",
    "익산시": "52140",
    "정읍시": "52180",
    "남원시": "52190",
    "김제시": "52210",
    "완주군": "52710",
    "진안군": "52720",
    "무주군": "52730",
    "장수군": "52740",
    "임실군": "52750",
    "순창군": "52770",
    "고창군": "52790",
    "부안군": "52800",

    # === 전라남도 ===
    "목포시": "46110",
    "여수시": "46130",
    "순천시": "46150",
    "나주시": "46170",
    "광양시": "46230",
    "담양군": "46710",
    "곡성군": "46720",
    "구례군": "46730",
    "고흥군": "46770",
    "보성군": "46780",
    "화순군": "46790",
    "장흥군": "46800",
    "강진군": "46810",
    "해남군": "46820",
    "영암군": "46830",
    "무안군": "46840",
    "함평군": "46860",
    "영광군": "46870",
    "장성군": "46880",
    "완도군": "46890",
    "진도군": "46900",
    "신안군": "46910",

    # === 경상북도 ===
    "포항시 남구": "47111",
    "포항시남구": "47111",
    "포항시 북구": "47113",
    "포항시북구": "47113",
    "경주시": "47130",
    "김천시": "47150",
    "안동시": "47170",
    "구미시": "47190",
    "영주시": "47210",
    "영천시": "47230",
    "상주시": "47250",
    "문경시": "47280",
    "경산시": "47290",
    "의성군": "47730",
    "청송군": "47750",
    "영양군": "47760",
    "영덕군": "47770",
    "청도군": "47820",
    "고령군": "47830",
    "성주군": "47840",
    "칠곡군": "47850",
    "예천군": "47900",
    "봉화군": "47920",
    "울진군": "47930",
    "울릉군": "47940",

    # === 경상남도 ===
    "창원시 의창구": "48121",
    "창원시의창구": "48121",
    "창원시 성산구": "48123",
    "창원시성산구": "48123",
    "창원시 마산합포구": "48125",
    "창원시마산합포구": "48125",
    "창원시 마산회원구": "48127",
    "창원시마산회원구": "48127",
    "창원시 진해구": "48129",
    "창원시진해구": "48129",
    "진주시": "48170",
    "통영시": "48220",
    "사천시": "48240",
    "김해시": "48250",
    "밀양시": "48270",
    "거제시": "48310",
    "양산시": "48330",
    "의령군": "48720",
    "함안군": "48730",
    "창녕군": "48740",
    "고성군(경남)": "48820",
    "남해군": "48840",
    "하동군": "48850",
    "산청군": "48860",
    "함양군": "48870",
    "거창군": "48880",
    "합천군": "48890",

    # === 제주특별자치도 ===
    "제주시": "50110",
    "서귀포시": "50130",
}


class RealEstateAPIError(Exception):
    """국토교통부 실거래가 API 호출 오류."""


def resolve_lawd_cd(region: str) -> str:
    """한글 지역명으로 법정동코드(LAWD_CD) 5자리를 반환.

    Args:
        region: 한글 지역명 (예: "강남구", "성남시 분당구").

    Returns:
        LAWD_CD 5자리 문자열.

    Raises:
        ValueError: 매핑 테이블에 없는 지역명.
    """
    if not region:
        raise ValueError(f"지역명을 찾을 수 없습니다: '{region}'")

    code = _LAWD_CD_MAP.get(region)
    if code:
        return code

    raise ValueError(f"지역명을 찾을 수 없습니다: '{region}'. 전국 시군구명 또는 '부산 중구' 형식으로 입력하세요.")


def _parse_xml(xml_bytes: bytes, service_key: str | None = None) -> dict[str, Any]:
    """공공데이터 API XML 응답을 파싱.

    Args:
        xml_bytes: API 응답 XML 바이트.
        service_key: _SERVICES 키 (선택). 권한 오류 시 활용신청 URL을 hint에 부착.

    Returns:
        {"total_count": N, "items": [...]} 딕셔너리.

    Raises:
        RealEstateAPIError: resultCode가 성공 코드가 아닌 경우, XML 파싱 실패.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise RealEstateAPIError(f"XML 파싱 실패: {exc}") from exc

    # 에러 코드 확인
    header = root.find("header")
    if header is not None:
        result_code = header.findtext("resultCode", "").strip()
        if result_code and result_code not in _SUCCESS_CODES:
            result_msg = header.findtext("resultMsg", "오류")
            hint = _ERROR_CODE_HINTS.get(result_code)
            if hint:
                meaning, action = hint
                detail = f"API 오류 (resultCode={result_code}): {result_msg} — {meaning}. 조치: {action}"
            else:
                detail = f"API 오류 (resultCode={result_code}): {result_msg}"
            # 권한 관련 코드는 해당 서비스 활용신청 URL 부착
            if result_code in {"20", "30"} and service_key:
                apply_url = _APPLY_URL.get(service_key)
                if apply_url:
                    detail += f" 활용신청: {apply_url}"
            raise RealEstateAPIError(detail)

    body = root.find("body")
    if body is None:
        return {"total_count": 0, "items": [], "page": 1}

    # 전체 건수
    total_count_el = body.find("totalCount")
    total_count = int(total_count_el.text or "0") if total_count_el is not None else 0

    page_no_el = body.find("pageNo")
    page_no = int(page_no_el.text or "1") if page_no_el is not None else 1

    # items 파싱
    items_el = body.find("items")
    items: list[dict[str, str]] = []
    if items_el is not None:
        for item_el in items_el.findall("item"):
            item: dict[str, str] = {}
            for child in item_el:
                item[child.tag] = (child.text or "").strip()
            items.append(item)

    return {"total_count": total_count, "items": items, "page": page_no}


def parse_amount(val: str) -> int:
    """금액 문자열을 정수(만원 단위)로 변환.

    Args:
        val: 금액 문자열 (예: "115,000", "85500", "-", "").

    Returns:
        정수 금액. 빈 문자열이나 '-'는 0 반환.
    """
    if not val or val.strip() == "-":
        return 0
    try:
        return int(val.replace(",", "").strip())
    except ValueError:
        return 0


def compute_summary(items: list[dict[str, Any]], amount_field: str = "dealAmount") -> dict[str, Any]:
    """거래 목록에서 요약 통계를 계산.

    Args:
        items: 거래 항목 목록.
        amount_field: 금액 필드명 (매매: "dealAmount", 전세: "deposit").

    Returns:
        {"avg": N, "median": N, "max": N, "min": N, "count": N}
    """
    if not items:
        return {"avg": 0, "median": 0, "max": 0, "min": 0, "count": 0}

    amounts = sorted(parse_amount(item.get(amount_field, "0")) for item in items)
    n = len(amounts)
    total = sum(amounts)
    avg = total // n

    # 중위값
    mid = n // 2
    if n % 2 == 1:
        median = amounts[mid]
    else:
        median = (amounts[mid - 1] + amounts[mid]) // 2

    return {
        "avg": avg,
        "median": median,
        "max": amounts[-1],
        "min": amounts[0],
        "count": n,
    }


def _fetch(
    service_key: str,
    api_key: str,
    lawd_cd: str,
    deal_ymd: str,
    page: int,
    rows: int,
) -> dict[str, Any]:
    """실거래가 API 공통 요청 헬퍼.

    Args:
        service_key: _SERVICES 딕셔너리 키 (예: "apt_trade").
        api_key: 공공데이터포털 API 키.
        lawd_cd: 법정동코드 5자리.
        deal_ymd: 계약년월 (예: "202601").
        page: 페이지 번호.
        rows: 페이지당 건수.

    Returns:
        {"total_count": N, "items": [...], "page": N}

    Raises:
        RealEstateAPIError: 네트워크 오류, API 에러 응답.
    """
    service_name, endpoint = _SERVICES[service_key]
    url = (
        f"{_BASE_URL}/{service_name}/{endpoint}"
        f"?{urllib.parse.urlencode({'serviceKey': api_key, 'LAWD_CD': lawd_cd, 'DEAL_YMD': deal_ymd, 'pageNo': str(page), 'numOfRows': str(rows)})}"
    )

    logger.debug("실거래가 API 요청 (%s): %s", service_key, url)

    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        # 403은 일반적으로 게이트웨이 단계의 권한 거부 (활용 미승인 또는 동기화 지연)
        detail = f"네트워크 오류: HTTP Error {exc.code}: {exc.reason}"
        if exc.code == 403:
            apply_url = _APPLY_URL.get(service_key)
            if apply_url:
                detail += (
                    f" — 게이트웨이 권한 거부. 활용신청 확인: {apply_url}"
                    " (자동승인이라도 동기화에 5~30분 소요)"
                )
        raise RealEstateAPIError(detail) from exc
    except urllib.error.URLError as exc:
        raise RealEstateAPIError(f"네트워크 오류: {exc}") from exc

    return _parse_xml(raw, service_key=service_key)


def fetch_trade(
    api_key: str,
    lawd_cd: str,
    deal_ymd: str,
    prop_type: str = "apt",
    page: int = 1,
    rows: int = 100,
) -> dict[str, Any]:
    """매매 실거래가 조회.

    Args:
        api_key: 공공데이터포털 API 키 (KO_DATA_API_KEY).
        lawd_cd: 법정동코드 5자리.
        deal_ymd: 계약년월 (예: "202601").
        prop_type: "apt"(아파트) 또는 "offi"(오피스텔). 기본 "apt".
        page: 페이지 번호 (기본 1).
        rows: 페이지당 건수 (기본 100).

    Returns:
        {"total_count": N, "items": [...], "page": N}

    Raises:
        RealEstateAPIError: 네트워크 오류, API 에러 응답.
    """
    service_key = "apt_trade" if prop_type == "apt" else "offi_trade"
    return _fetch(service_key, api_key, lawd_cd, deal_ymd, page, rows)


def fetch_rent(
    api_key: str,
    lawd_cd: str,
    deal_ymd: str,
    prop_type: str = "apt",
    page: int = 1,
    rows: int = 100,
) -> dict[str, Any]:
    """전월세 실거래가 조회.

    Args:
        api_key: 공공데이터포털 API 키.
        lawd_cd: 법정동코드 5자리.
        deal_ymd: 계약년월 (예: "202601").
        prop_type: "apt"(아파트) 또는 "offi"(오피스텔). 기본 "apt".
        page: 페이지 번호.
        rows: 페이지당 건수.

    Returns:
        {"total_count": N, "items": [...], "page": N}

    Raises:
        RealEstateAPIError: 네트워크 오류, API 에러 응답.
    """
    service_key = "apt_rent" if prop_type == "apt" else "offi_rent"
    return _fetch(service_key, api_key, lawd_cd, deal_ymd, page, rows)
