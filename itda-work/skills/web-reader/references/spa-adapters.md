# SPA 어댑터 개발 가이드

> **이 문서는 SPA 어댑터를 직접 작성하려는 개발자를 위한 가이드입니다. 일반 사용자는 이 문서를 읽을 필요가 없습니다.**

## 언제 어댑터가 필요한가

WebSquare나 Nexacro 같은 기업용 SPA 프레임워크로 만들어진 웹사이트에서 일반 추출 방식으로는 내용이 0건입니다. 이 경우 사용자 정의 어댑터를 작성해 다음 작업을 자동화할 수 있습니다:

- **페이지 진입 자동화**: 로그인 또는 메뉴 클릭 등 초기 진입 과정
- **데이터 캡처**: 네트워크 응답에서 API 데이터 추출
- **데이터 정규화**: 캡처한 데이터를 Markdown/JSON으로 변환

## 어댑터 인터페이스

어댑터는 `Adapter` 베이스 클래스를 상속하며, 다음 속성과 메서드를 정의합니다:

```
domain_pattern      정규식 문자열. 어댑터가 적용될 대상 도메인
                    예: r"^(www\.)?example\.com$"

framework           SPA 프레임워크 이름 (문자열)
                    예: "websquare5", "nexacro"

pages               PageDef 객체로 이루어진 딕셔너리
                    예: {"main": PageDef(...), "detail": PageDef(...)}

entry(driver, page_key)
                    page_key에 해당하는 페이지로 진입하는 로직
                    driver: BrowserDriver 객체

extract(driver, captures)
                    캡처한 네트워크 데이터를 정규화하는 로직
                    returns: dict (정규화된 데이터)
```

## 5단계 작성 가이드

### 1단계: 대상 사이트 분석

- 사이트의 entry URL (메인 페이지)과 진입 경로 파악
- 로그인 필요 여부 확인
- 어떤 네트워크 요청에 실제 데이터가 포함되는지 확인 (브라우저 개발자 도구 Network 탭)

### 2단계: 어댑터 클래스 작성

`scripts/spa_adapters/` 디렉토리에 어댑터 파일을 만듭니다:

```
scripts/spa_adapters/myadapter.py
```

기본 구조:

```python
from spa_adapters.base import Adapter, PageDef, run_entry_steps

class MyAdapter(Adapter):
    domain_pattern = r"^(www\.)?example\.com$"
    framework = "websquare5"
    pages = {
        "main": PageDef(entry_url="https://www.example.com/"),
    }

    def entry(self, driver, page_key: str = "main") -> None:
        """페이지로 진입하는 자동화 로직"""
        run_entry_steps(driver, self.pages[page_key])

    def extract(self, driver, captures=None) -> dict:
        """네트워크 캡처 데이터를 정규화"""
        return {"items": captures or []}
```

### 3단계: manifest.json 등록

`scripts/spa_adapters/manifest.json` 에 어댑터를 등록합니다:

```json
{
  "adapters": [
    {
      "name": "myadapter",
      "module": "spa_adapters.myadapter",
      "domain_pattern": "^(www\\.)?example\\.com$",
      "framework": "websquare5",
      "default_page": "main",
      "pages": ["main"],
      "available": true
    }
  ]
}
```

**필드 설명:**
- `name`: 어댑터의 고유 식별자 (CLI에서 `--adapter` 값)
- `module`: Python 모듈 경로 (점 표기법)
- `domain_pattern`: 정규식 패턴 (JSON에서는 백슬래시 이스케이프)
- `framework`: SPA 프레임워크 이름
- `default_page`: --adapter-page 미지정 시 기본값
- `pages`: 지원하는 페이지 키 목록
- `available`: true일 때만 --list-adapters에 표시

### 4단계: 로컬 검증 — 캡처

```bash
# macOS/Linux
python3 scripts/fetch_dynamic.py \
  --url "https://www.example.com/" \
  --adapter myadapter \
  --adapter-page main \
  --capture-api '.*' \
  --output capture_result.html

# Windows
py -3 scripts/fetch_dynamic.py --url "https://www.example.com/" --adapter myadapter --adapter-page main --capture-api ".*" --output capture_result.html
```

캡처된 응답은 `.itda-skills/web-reader/captures/YYYYMMDDTHHMMSS.jsonl` 에 저장됩니다.

### 5단계: 로컬 검증 — 변환

```bash
# macOS/Linux
python3 scripts/extract_content.py \
  --from-capture .itda-skills/web-reader/captures/YYYYMMDDTHHMMSS.jsonl \
  --adapter myadapter \
  --format markdown

# Windows
py -3 scripts/extract_content.py --from-capture .itda-skills\web-reader\captures\YYYYMMDDTHHMMSS.jsonl --adapter myadapter --format markdown
```

## CLI 옵션 상세

### fetch_dynamic.py

```
--adapter NAME            사용할 어댑터 이름
--adapter-page KEY        어댑터 내 페이지 키 (기본값: manifest의 default_page)
--capture-api PATTERN     정규식 패턴. 매칭되는 네트워크 요청을 JSONL로 저장
--list-adapters           사용 가능한 모든 어댑터 목록 출력
```

### extract_content.py

```
--from-capture FILE       캡처된 JSONL 파일을 마크다운/JSON으로 변환
--adapter NAME            변환 시 사용할 어댑터 (필드 매핑)
--adapter-page KEY        어댑터 페이지 키 (기본값: 어댑터의 default_page)
```

## 주의사항

- **사이트 개편 리스크**: 사이트 UI가 변경되면 어댑터의 셀렉터가 동작하지 않을 수 있습니다. 이 경우 어댑터를 다시 업데이트해야 합니다.

- **인증/SSO 미지원**: 로그인이 필요한 페이지는 이 어댑터로는 처리되지 않습니다. 대신 `--profile` + `--interactive` 옵션을 사용해 수동으로 로그인한 후 세션을 유지하는 방식을 사용하세요.

- **성능 고려**: 반복적인 자동화로 대상 서버에 과도한 부하를 주지 않도록 주의하세요. 실험이나 일회성 조회 용도로만 사용할 것을 권장합니다.

- **테스트 픽스처**: 어댑터 개발 중에는 작은 샘플 데이터로 테스트하고, 완성 후 실제 사이트에서 전체 데이터로 검증하는 것을 권장합니다.
