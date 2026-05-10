# Changelog — itda-web-reader

## [2.13.0] — 2026-05-10

### Improvements

- **description 트리거 범위 좁히기 (오발동 방지)**: 단순 URL 읽기 요청에서 progressive disclosure가 web-reader를 활성화하던 문제를 해결. description 첫 문장을 "WebFetch로 처리되지 않는 고급 웹 페치 전용"으로 좁히고, EUC-KR/CP949 · Playwright 동적 렌더링 · YouTube 자막 · 쿠키 인증 · SPA 어댑터 5종을 명시 활성화 조건으로 나열. "Do NOT use for" anti-trigger 절을 추가하여 일반 페치 요청은 Claude의 WebFetch로 위임되도록 유도. 기존 일반 트리거 문구("이 링크 읽어줘", "웹페이지 요약해줘", "사이트에서 ... 가져와")는 description에서 제거. SPEC-WEBREADER-TRIGGER-001 적용. (관련 SPEC: `.moai/specs/SPEC-WEBREADER-TRIGGER-001/`)

### 동작 영향 (Behavioral Impact)

- 스크립트 동작 · CLI 인터페이스 · Python API: **변경 없음** (v2.12.0과 100% 동일)
- 변경된 부분: SKILL.md frontmatter `description` 자연어 트리거 매칭 신호만 조정
- 사용자 영향: 단순 페치 요청은 WebFetch로 자동 위임되어 토큰 소비 감소. 고급 기능 5종 또는 스킬명 명시 호출 시에는 기존과 동일하게 web-reader 활성화

## [2.12.0] — 2026-05-01

### New Features

- **`diagnose_url.py` 신규 스크립트**: fetch 실패의 root cause를 레이어별로 진단. SSRF check → DNS → TCP → SSL → HTTP HEAD → robots.txt 단계 분리 측정 + baseline 비교 (google.com:443). itda-email v0.18.0의 `diagnose_smtp.py` 패턴을 HTTP 도메인에 일반화.

#### 진단 코드 (12종)

`ssrf_blocked` / `dns_failure` / `no_internet` / `tcp_blocked` / `ssl_cert_invalid` / `ssl_handshake_fail` / `http_timeout` / `redirect_loop` / `http_403_forbidden` / `http_404_not_found` / `http_429_rate_limit` / `http_5xx_server_error` / `non_html_content` / `robots_denied` / `empty_response` / `all_ok`

#### 사용법

```bash
python3 scripts/diagnose_url.py https://example.com
# 응답 JSON의 diagnosis.code 만 보면 root cause 식별 가능
```

`fetch_html.py` 가 빈 응답 / 403 / 알 수 없는 에러를 반환할 때 다음 단계 진단 도구로 사용.

#### Verification

| 시나리오 | 진단 코드 |
|---------|----------|
| `https://example.com` | `all_ok` |
| `https://nonexistent-...invalid` | `dns_failure` |
| `http://192.168.1.1/` (private IP) | `ssrf_blocked` |
| 404 URL | `http_404_not_found` |
| PDF URL (실제로 403 응답) | `http_403_forbidden` |
