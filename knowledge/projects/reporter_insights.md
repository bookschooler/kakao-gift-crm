# Reporter Stage — 프로젝트 인사이트

**작성일:** 2026-04-04
**단계:** Layer 1-5 완료 → Reporter Stage
**QA 판정:** Grade A PASS (신뢰도 95%+)

---

## 핵심 수치 요약 (재사용 참조용)

| 지표 | 값 | 출처 레이어 |
|------|-----|-----------|
| 총 GMV | ₩137.2억 | Layer 1 |
| YoY 성장률 | +31% | Layer 1 |
| GMV 피크 | 2024-01 ₩10.2억 | Layer 1 |
| GMV 저점 | 2023-06 ₩2.9억 | Layer 1 |
| beauty GMV 비중 | 35.0% | Layer 1 |
| voucher 주문 비중 | 34.5% | Layer 1 |
| Champions 유저 비중 | 3.2% | Layer 2 |
| Champions GMV 비중 | 9.3% | Layer 2 |
| Champions 평균 M | ₩499,416 | Layer 2 |
| At Risk 평균 M | ₩242,600 | Layer 2 |
| 1개월 Retention | 15.1% | Layer 3 |
| 12개월 LTV | ₩203,169 (2.7배) | Layer 3 |
| K-factor | 3.95 | Layer 4 |
| Reciprocity (30일) | 58.4% | Layer 4 |
| Reciprocity (90일) | 67.6% | Layer 4 |
| Gen 1 GMV | ₩61.7억 > Gen 0 ₩47.8억 | Layer 4 |
| Open Rate | 53.7% | Layer 5 |
| Purchase CVR | 0.53% | Layer 5 |
| Champions ROAS | 1,665배 | Layer 5 |
| At Risk ROAS | 809배 | Layer 5 |
| Need Attention 예상 수익 | ₩7,010만 | Layer 5 |

---

## 프레임워크 — 선물하기 CRM 분석의 5가지 교훈

### 1. 바이럴 루프는 수치로 검증 가능하다
K-factor 공식(invites × conversion_rate)은 네트워크 성장을 단 1개 숫자로 압축한다. 카카오 선물하기의 K=3.95는 자가 증식 성장(K>1)을 통계적으로 확정(Bootstrap CI [3.87, 4.02])한다.

### 2. 세그먼트 크기와 가치는 반드시 역전된다
Champions(3.2%) = GMV 9.3%, Hibernating(23.2%) = GMV 11.7%. 유저 분포와 GMV 분포를 함께 보아야 실제 가치 있는 세그먼트가 보인다.

### 3. 이탈 방지가 신규 유치보다 ROAS가 높다
At Risk ROAS 809배 vs 신규 고객 캠페인 ROAS는 단순 수치 비교로도 기존 유저 관리의 효율이 압도적이다.

### 4. 시즌 집중도가 높을수록 타이밍이 전략이다
빼빼로데이 ×12 폭증 패턴. 캠페인 예산을 D-7~D-3에 집중하는 것만으로 예산 효율을 극대화할 수 있다.

### 5. 수신 후 30일이 구매 전환 골든타임이다
Reciprocity 30일 58.4% → 이 구간에 리마인더 1회만 발송해도 Viral Loop 속도를 2배로 높일 수 있다.

---

## 산출물 파일 경로

| 산출물 | 경로 |
|--------|------|
| PPTX (13슬라이드) | `report/kakao_gift_analysis.pptx` |
| Markdown 보고서 | `report/kakao_gift_analysis_report.md` |
| 차트 6개 | `report/charts/chart_01~06_*.png` |
| PPTX 생성 스크립트 | `report/generate_pptx.py` |
| 차트 생성 스크립트 | `report/generate_report_charts.py` |

---

## Blameless Post-mortem

### 병목 분석

| 단계 | 상황 | 원인 (시스템) | 개선 제안 |
|------|------|------------|---------|
| Gamma MCP | tool_use_error 발생 | MCP 서버가 Bash 환경에서 직접 호출 불가 | 다음 프로젝트에서는 Claude UI에서 직접 Gamma 요청으로 분리 |
| PPTX 레이아웃 | 텍스트 위치 정밀도 한계 | python-pptx EMU 단위 계산 복잡 | 슬라이드 템플릿(.potx) 기반으로 시작하면 좌표 계산 단순화 |
| 차트 생성 | 한글 인코딩 로그 깨짐 | Windows bash 터미널 인코딩 이슈 | PYTHONIOENCODING=utf-8 환경변수 설정 |

### 다음 프로젝트 개선 규칙
1. Gamma 생성은 Bash 스크립트가 아닌 Claude 대화에서 직접 MCP 툴 호출로 처리
2. PPTX 생성 스크립트는 슬라이드별 함수로 분리하여 재사용성 높이기
3. 차트 생성 전 `plt.style.use('seaborn-v0_8-whitegrid')` 기본 적용으로 스타일 일관성 확보
4. ANALYSIS_RESULTS.md의 수치를 딕셔너리로 파싱해서 스크립트에서 직접 import — 수치 변경 시 단일 소스 관리

---

**작성자:** DESA Reporter
**검토:** QA Reviewer Grade A PASS 기준
