---
name: exchange-rate
description: >
  원화 기준 환율 조회 스킬. "오늘 달러 환율 알려줘", "EUR 환율 조회",
  "이번 달 엔화 평균 환율 보여줘" 같은 요청에 사용하세요.
  일별·월평균 매매기준율을 제공하고, 휴일에는 직전 영업일로 자동 폴백합니다.
license: Apache-2.0
compatibility: Designed for Claude Cowork
user-invocable: true
argument-hint: "[YYYY-MM-DD|YYYY-MM] [currency] - Date/month and optional currency code (default: USD)"
allowed-tools: Read WebFetch Bash(python3:* date:*)
metadata:
  author: "스킬.잇다 <dev@itda.work>"
  category: "domain"
  version: "0.10.2"
  created_at: "2026-03-18"
  updated_at: "2026-04-18"
  tags: "exchange-rate, currency, forex, korea, 환율, 매매기준율"
---

# Exchange Rate (매매기준율 조회)

## Instructions for Claude

When this skill is invoked, follow these steps exactly.

### Step 1: Determine the Skill Directory

The skill directory is the directory containing this SKILL.md file.

### Step 2: Parse the Argument

The argument (if any) is in `$ARGUMENTS`. Parse it to extract:
- **Date or month**: `YYYY-MM-DD`, `YYYY.MM.DD`, or `YYYY-MM`
- **Currency code or alias**: e.g., `USD`, `JPY`, `달러`, `엔`

If no date/month is provided, use today's date: run `date +%Y-%m-%d`.

If no currency is provided, default to `USD`.

| Input format | Example | Mode |
|---|---|---|
| YYYY-MM-DD | `2025-01-03` | Daily rate |
| YYYY.MM.DD | `2025.01.03` | Daily rate |
| YYYY-MM | `2025-01` | Monthly average |

### Step 3: Run the Exchange Rate Script

Run the following command from the skill directory:

```bash
python3 {SKILL_DIR}/scripts/exchange_rate.py [--date DATE | --month MONTH] [--currency CODE]
```

Examples:
- `python3 scripts/exchange_rate.py --date 2025-01-05 --currency USD`
- `python3 scripts/exchange_rate.py --date 2025.01.05 --currency JPY`
- `python3 scripts/exchange_rate.py --month 2025-01 --currency EUR`
- `python3 scripts/exchange_rate.py --month 2025-01`
- `python3 scripts/exchange_rate.py --date 2025-01-05`

### Step 4: Display the Output

Display the script output directly to the user without modification.

### Error Handling

If the script exits with an error, display the error message from the script output.
The script outputs Korean error messages for user-facing errors.
