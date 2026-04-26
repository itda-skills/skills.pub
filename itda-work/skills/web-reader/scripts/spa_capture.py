#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spa_capture.py — Playwright 네트워크 응답 캡처 핸들러.

SPEC-WEBREADER-006 FR-CAPTURE-01/02/03, FR-SEC-02 구현.
page.on("response", handler) 시그니처로 사용 가능한 callable 클래스.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from itda_path import resolve_data_dir

# 캡처 가능한 Content-Type 접두사 목록
_CAPTURABLE_CONTENT_TYPES = ("application/json", "application/xml")

# 50MB 기본 상한선 (FR-SEC-02)
# @MX:NOTE: [AUTO] 50MB 상한선은 SPEC FR-SEC-02 보안 요구사항.
#           과도하게 큰 응답 body가 디스크를 소진하거나 메모리 문제를 일으키는 것을 방지.
_DEFAULT_MAX_BYTES = 50 * 1024 * 1024


class CaptureHandler:
    """Playwright 응답 캡처 핸들러.

    page.on("response", handler) 콜백으로 등록하여 사용한다.
    status 200 + 지원 Content-Type + URL 패턴 매칭 응답만 JSONL 파일에 기록한다.

    사용 예:
        handler = CaptureHandler(pattern=r"api/v1")
        page.on("response", handler)
        # ... 페이지 탐색 ...
        print(handler.output_path)  # 캡처 파일 경로 확인
    """

    def __init__(
        self,
        pattern: str,
        output_path: Path | None = None,
        max_bytes: int = _DEFAULT_MAX_BYTES,
        *,
        stderr: IO[str] = sys.stderr,
    ) -> None:
        """핸들러를 초기화한다.

        인자:
            pattern: URL 매칭에 사용할 정규식 문자열.
            output_path: JSONL 출력 파일 경로.
                         None이면 resolve_data_dir("web-reader", "captures") / timestamp.jsonl 사용.
            max_bytes: body 크기 상한 (기본 50MB). 초과 시 폐기 + 경고.
            stderr: 경고 메시지 출력 스트림 (테스트에서 교체 가능).

        예외:
            ValueError: pattern이 유효하지 않은 정규식인 경우.
            re.error: pattern 컴파일 실패 시 re 모듈에서 직접 전파.
        """
        # ReDoS 방지: 패턴 길이 256자 상한 (FR-SEC-02)
        if len(pattern) > 256:
            raise ValueError(
                f"패턴 길이 {len(pattern)}자가 256자 상한을 초과합니다 — ReDoS 방지"
            )
        # 정규식 컴파일 — 잘못된 패턴은 즉시 예외
        self._pattern = re.compile(pattern)
        self._max_bytes = max_bytes
        self._stderr = stderr

        # 출력 경로 결정
        if output_path is None:
            captures_dir = resolve_data_dir("web-reader", "captures")
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
            output_path = captures_dir / f"{timestamp}.jsonl"
        else:
            # 지정된 경로의 부모 디렉토리 자동 생성
            output_path.parent.mkdir(parents=True, exist_ok=True)

        self._output_path = output_path

    @property
    def output_path(self) -> Path:
        """JSONL 캡처 파일 경로를 반환한다."""
        return self._output_path

    # @MX:ANCHOR: [AUTO] CaptureHandler.__call__ — Playwright response 이벤트 진입점
    # @MX:REASON: [AUTO] fetch_dynamic.py에서 page.on("response", handler) 등록,
    #             테스트 코드, 향후 어댑터 통합 등 fan_in >= 3 예상.
    #             응답 필터링·저장 정책이 이 메서드를 통해서만 수행됨.
    # @MX:WARN: [AUTO] Playwright sync API 컨텍스트 내에서 동기 stderr write 수행.
    # @MX:REASON: [AUTO] Playwright sync_playwright 콘텍스트 안에서만 안전.
    #             async context에서 호출하면 블로킹 I/O 문제가 발생할 수 있음.
    def __call__(self, response: object) -> None:
        """Playwright response 이벤트 핸들러.

        인자:
            response: Playwright Response 객체.
                      .url (str), .status (int), .headers (dict), .body() -> bytes 를 가져야 함.
        """
        # status 200 검증
        if response.status != 200:  # type: ignore[attr-defined]
            return

        # Content-Type 검증 — application/json 또는 application/xml 시작
        content_type: str = response.headers.get("content-type", "")  # type: ignore[attr-defined]
        matched_type: str | None = None
        for ct in _CAPTURABLE_CONTENT_TYPES:
            if content_type.startswith(ct):
                matched_type = ct
                break
        if matched_type is None:
            return

        # URL 패턴 검증
        url: str = response.url  # type: ignore[attr-defined]
        if not re.search(self._pattern, url):
            return

        # body 읽기 전 Content-Length 헤더 사전 검사 (FR-SEC-02, ISS-MEMGUARD-015)
        # Content-Length가 있으면 body() 호출 전에 크기 초과를 조기 차단하여 OOM 위험을 줄인다.
        content_length_str: str = response.headers.get("content-length", "")  # type: ignore[attr-defined]
        try:
            content_length: int | None = int(content_length_str) if content_length_str else None
        except ValueError:
            content_length = None
        if content_length is not None and content_length > self._max_bytes:
            # 헤더 기준 50MB 초과 → body() 호출 없이 폐기
            print(
                f"[web-reader] 응답 크기 {content_length:,}B (헤더 기준)가 "
                f"한도 {self._max_bytes:,}B 초과로 폐기: {url}",
                file=self._stderr,
            )
            return

        # body 읽기 및 실제 크기 검사 (chunked transfer 등 헤더 누락 케이스 폴백)
        body_bytes: bytes = response.body()  # type: ignore[attr-defined]
        if len(body_bytes) > self._max_bytes:
            # 50MB 초과 → 폐기 + 한국어 경고
            print(
                f"[web-reader] 응답 크기 50MB 초과로 폐기: {url} "
                f"({len(body_bytes):,} bytes)",
                file=self._stderr,
            )
            return

        # body 파싱
        body_value: object
        effective_content_type = matched_type

        if matched_type == "application/json":
            # JSON 파싱 시도 — 실패 시 raw 문자열로 fallback
            try:
                body_value = json.loads(body_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError):
                body_value = body_bytes.decode("utf-8", errors="replace")
                effective_content_type = matched_type + "+raw"
        else:
            # XML 등 나머지 — raw 문자열로 저장
            body_value = body_bytes.decode("utf-8", errors="replace")

        # JSONL 항목 구성
        entry = {
            "url": url,
            "status": response.status,  # type: ignore[attr-defined]
            "content_type": effective_content_type,
            "body": body_value,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        # 추가 모드로 파일에 기록
        with self._output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_captures(self) -> list[dict]:
        """캡처된 JSONL 파일을 읽어 항목 목록을 반환한다.

        반환:
            캡처 항목 dict의 리스트.
            output_path 파일이 없거나 비어 있으면 빈 리스트 반환.
        """
        # 파일이 없으면 빈 리스트 반환
        if not self._output_path.exists():
            return []

        captures: list[dict] = []
        try:
            with self._output_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        captures.append(json.loads(line))
                    except json.JSONDecodeError:
                        # 손상된 라인은 건너뜀
                        continue
        except (OSError, IOError):
            return []
        return captures
