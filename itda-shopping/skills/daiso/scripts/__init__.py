"""daiso 스킬 스크립트 패키지.

다이소 상품·매장·재고 조회 CLI. 진입점은 `daiso.py`이며, 5개 서브커맨드
(products·price·stores·inventory·display-location)를 구현한다.
무인증 코어(products·price·stores)와 AES 경량 인증 기능(inventory·display-location)으로
구성되며, HTTP는 urllib 자체 호출, AES는 cryptography 선택 의존(미설치 시 graceful degrade)이다.
"""
