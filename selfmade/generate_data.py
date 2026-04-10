"""
카카오톡 선물하기 Mock Data Generator
====================================
생성 근거: mock_data_generation_logic.md 참고

테이블:
  users          50,000행
  orders         ~200,000행
  gift_receipts  ~200,000행 (orders와 1:1)
  campaigns      ~48행
  campaign_logs  ~120,000행

실행:
  python generate_data.py

출력:
  users.csv, orders.csv, gift_receipts.csv, campaigns.csv, campaign_logs.csv
"""

import csv
import math
import random
from datetime import date, datetime, timedelta

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# ── 생성 기간 ──────────────────────────────────────────────────────────────
START_DATE = date(2023, 1, 1)
END_DATE   = date(2024, 12, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days + 1

N_USERS    = 50_000
OUTPUT_DIR = "."


# ══════════════════════════════════════════════════════════════════════════════
# 유틸
# ══════════════════════════════════════════════════════════════════════════════

def rand_ts(d: date, hour_min: int = 8, hour_max: int = 23) -> datetime:
    h = random.randint(hour_min, hour_max)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, h, m, s)

def lognormal_int(mu: float, sigma: float, lo: int = 1_000, hi: int = 500_000) -> int:
    v = int(math.exp(random.gauss(mu, sigma)))
    return max(lo, min(hi, v))

def weighted_choice(options: list, weights: list):
    total = sum(weights)
    r = random.random() * total
    cumul = 0.0
    for opt, w in zip(options, weights):
        cumul += w
        if r <= cumul:
            return opt
    return options[-1]


# ══════════════════════════════════════════════════════════════════════════════
# 시즌 이벤트 설정
# ══════════════════════════════════════════════════════════════════════════════

def get_seasonal_multiplier(d: date) -> float:
    """날짜별 GMV 부스트 배율
    근거: mock_data_generation_logic.md + 쿠팡Ads/SSG/컬리 실제 데이터 리서치
    """
    m, day = d.month, d.day

    # ── 11월: 빼빼로데이(#1) + 수능 + 블랙프라이데이 ──────────────────
    # 빼빼로데이: 카카오 공식 연중 최고 거래일. 건수 폭발적
    # D-7~D-4: 사전 구매 준비 (×2.5), D-3~D-1: 피크 직전 (×5.0)
    # D-day: ×12.0, D+1~D+2: 여파 (×5.0), D+3~D+4: 잔여 (×2.5)
    if m == 11 and day == 11:           return 12.0  # 당일
    if m == 11 and 8 <= day <= 10:      return 5.0   # D-3~D-1
    if m == 11 and 12 <= day <= 13:     return 5.0   # D+1~D+2
    if m == 11 and 4 <= day <= 7:       return 2.5   # D-7~D-4
    if m == 11 and 14 <= day <= 15:     return 2.5   # D+3~D+4
    # 수능 전날: 카카오 공식 #5. 일평균 +260% (매일경제 2021)
    if m == 11 and 14 <= day <= 15: return 2.5
    # 블랙프라이데이: 11월 넷째 주 금요일 주변 (22~29일)
    # 한국 선물하기에서는 영향 제한적 — 해외직구/패션 중심 (리서치 확인)
    if m == 11 and 22 <= day <= 29: return 1.8

    # ── 5월: 어버이날(상위) + 스승의 날(#3) ──────────────────────────
    # 어버이날: SSG 꽃배달 전월比 +700~800% (뉴스1 2023). 고단가 세트 견인
    if m == 5 and day == 8:          return 4.5
    if m == 5 and 6 <= day <= 7:     return 2.5   # D-2~D-1
    if m == 5 and 9 <= day <= 11:    return 2.0   # 여파
    # 스승의 날: 카카오 공식 #3. 상품권/뷰티 건수 많음
    if m == 5 and day == 15:         return 3.0
    if m == 5 and 13 <= day <= 14:   return 1.8

    # ── 설날: 쿠팡 로켓프레시 전전주比 +258% (쿠팡Ads 2025) ──────────
    # 준비기간 D-14→D-7로 단축 (주문건수 누적 억제)
    if (m == 1 and 28 <= day <= 31) or (m == 2 and day <= 3):  return 4.0   # 당일±3일
    if (m == 1 and 21 <= day <= 27) or (m == 2 and 4 <= day <= 7): return 2.0  # 준비 기간 (D-7~D-4)

    # ── 발렌타인데이: 카카오 공식 #2 ─────────────────────────────────
    if m == 2 and day == 14:         return 4.0
    if m == 2 and 12 <= day <= 13:   return 2.5
    if m == 2 and 15 <= day <= 16:   return 2.0

    # ── 화이트데이: 카카오 공식 #4 ───────────────────────────────────
    if m == 3 and day == 14:         return 2.5
    if m == 3 and 12 <= day <= 13:   return 1.6
    if m == 3 and 15 <= day <= 16:   return 1.4

    # ── 추석: 쿠팡/컬리 전주比 +238~258% (약 3.4~3.6배) ─────────────
    # 준비기간 D-14→D-7로 단축 (주문건수 누적 억제)
    if (m == 9 and 27 <= day <= 30) or (m == 10 and day <= 3):  return 4.0   # 당일±3일
    if (m == 9 and 23 <= day <= 26) or (m == 10 and 4 <= day <= 7): return 2.0  # 준비 기간 (D-7~D-4)

    # ── 크리스마스: 12월 화장품 이커머스 전년比 +28% (데이터라이즈 2025) ─
    if m == 12 and day == 25:        return 3.0
    if m == 12 and 22 <= day <= 24:  return 2.0
    if m == 12 and 26 <= day <= 28:  return 1.6

    # ── 연말연시 ─────────────────────────────────────────────────────
    if (m == 12 and day >= 29) or (m == 1 and day <= 3): return 2.0

    return 1.0

def get_season_occasion(d: date):
    """날짜 → (occasion_category, occasion_subcategory, gift_occasion) 또는 None"""
    m, day = d.month, d.day
    if m == 11 and 4 <= day <= 15:
        return ('special', 'seasonal', 'pepero_day')
    if m == 11 and 14 <= day <= 15:
        return ('special', 'seasonal', 'suneung')
    if m == 11 and 22 <= day <= 29:
        return ('special', 'seasonal', 'black_friday')
    if m == 2 and 12 <= day <= 16:
        return ('special', 'seasonal', 'valentines_day')
    if m == 5 and 6 <= day <= 11:
        return ('special', 'seasonal', 'parents_day')
    if m == 5 and 13 <= day <= 17:
        return ('special', 'seasonal', 'teachers_day')
    if m == 3 and 12 <= day <= 16:
        return ('special', 'seasonal', 'white_day')
    if m == 12 and 22 <= day <= 28:
        return ('special', 'seasonal', 'christmas')
    if (m == 1 and day >= 18) or (m == 2 and day <= 12):
        return ('special', 'seasonal', 'new_year')
    if (m == 9 and day >= 22) or (m == 10 and day <= 10):
        return ('special', 'seasonal', 'chuseok')
    if (m == 12 and day >= 29) or (m == 1 and day <= 3):
        return ('special', 'seasonal', 'year_end')
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 상품 카탈로그
# ══════════════════════════════════════════════════════════════════════════════

PRODUCTS = [
    # (product_id, brand_name, category_l1, category_l2, price_mu, price_sigma)
    ('PRD0001', '스타벅스',     'voucher',   'cafe_voucher',        8.5, 0.3),
    ('PRD0002', '스타벅스',     'voucher',   'cafe_voucher',        9.2, 0.2),
    ('PRD0003', '투썸플레이스', 'voucher',   'cafe_voucher',        8.3, 0.3),
    ('PRD0004', '파리바게뜨',   'food',      'cake',               10.5, 0.4),
    ('PRD0005', '뚜레쥬르',     'food',      'cake',               10.3, 0.4),
    ('PRD0006', '빙그레',       'food',      'snack',               9.5, 0.4),   # 세트 1~2만원
    ('PRD0007', '롯데제과',     'food',      'snack',               9.8, 0.4),   # 빼빼로 세트
    ('PRD0008', '오리온',       'food',      'snack',               9.6, 0.3),
    ('PRD0009', '한우자조금',   'food',      'set_gift',           12.5, 0.5),
    ('PRD0010', '광동제약',     'health',    'red_ginseng',        11.8, 0.6),
    ('PRD0011', '설화수',       'beauty',    'skincare',           11.5, 0.5),
    ('PRD0012', 'LANEIGE',     'beauty',    'skincare',           10.8, 0.5),
    ('PRD0013', '이니스프리',   'beauty',    'skincare',           10.0, 0.4),
    ('PRD0014', '조말론',       'beauty',    'perfume',            12.0, 0.4),
    ('PRD0015', '딥디크',       'beauty',    'perfume',            12.2, 0.4),
    ('PRD0016', 'KGC인삼공사', 'health',    'red_ginseng',        12.3, 0.5),
    ('PRD0017', '한국야쿠르트', 'health',    'wellness',            9.8, 0.4),
    ('PRD0018', '배달의민족',   'voucher',   'restaurant',          9.5, 0.3),
    ('PRD0019', 'CU',          'voucher',   'convenience_store',   8.0, 0.3),
    ('PRD0020', 'GS25',        'voucher',   'convenience_store',   8.0, 0.3),
    ('PRD0021', '신세계백화점', 'voucher',   'department_store',   11.5, 0.5),
    ('PRD0022', '문화상품권',   'voucher',   'culture',            10.0, 0.4),
    ('PRD0023', '꽃다발닷컴',   'lifestyle', 'flower',              9.5, 0.4),
    ('PRD0024', '무인양품',     'lifestyle', 'home_living',        10.0, 0.4),
    ('PRD0025', '카카오프렌즈', 'lifestyle', 'toy',                10.5, 0.5),
]

SEASON_PRODUCT_BIAS = {
    # 빼빼로데이: 과자 외에 스타벅스·케이크·뷰티 포함 → 가격대 다양화
    'pepero_day':    ['PRD0006', 'PRD0007', 'PRD0008',
                      'PRD0001', 'PRD0002', 'PRD0004', 'PRD0011', 'PRD0013'],
    'valentines_day':['PRD0006', 'PRD0007', 'PRD0014', 'PRD0015',
                      'PRD0011', 'PRD0012', 'PRD0001'],
    'parents_day':   ['PRD0010', 'PRD0016', 'PRD0009',
                      'PRD0021', 'PRD0023'],
    'teachers_day':  ['PRD0021', 'PRD0022', 'PRD0011',
                      'PRD0001', 'PRD0002'],
    'white_day':     ['PRD0006', 'PRD0007', 'PRD0013',
                      'PRD0001', 'PRD0011'],
    'christmas':     ['PRD0004', 'PRD0005', 'PRD0014', 'PRD0025',
                      'PRD0011', 'PRD0021'],
    'new_year':      ['PRD0009', 'PRD0010', 'PRD0016',
                      'PRD0021', 'PRD0022'],
    'chuseok':       ['PRD0009', 'PRD0010', 'PRD0016',
                      'PRD0021', 'PRD0022'],
    'birthday':      ['PRD0001', 'PRD0002', 'PRD0004', 'PRD0014', 'PRD0023'],
    'self_gift':     ['PRD0011', 'PRD0012', 'PRD0001', 'PRD0018'],
    'suneung':       ['PRD0006', 'PRD0007', 'PRD0008',
                      'PRD0001', 'PRD0002', 'PRD0019', 'PRD0020'],
    # 블랙프라이데이: 뷰티·라이프스타일·상품권 할인 중심
    'black_friday':  ['PRD0011', 'PRD0012', 'PRD0013', 'PRD0014',
                      'PRD0021', 'PRD0022', 'PRD0024', 'PRD0018'],
}
PRODUCT_INDEX = {p[0]: p for p in PRODUCTS}

def pick_product(gift_occasion: str):
    bias = SEASON_PRODUCT_BIAS.get(gift_occasion, [])
    if bias and random.random() < 0.65:
        pid = random.choice(bias)
        return PRODUCT_INDEX[pid]
    return random.choice(PRODUCTS)


# ══════════════════════════════════════════════════════════════════════════════
# 일반 occasion 분포 (비시즌)
# ══════════════════════════════════════════════════════════════════════════════

DAILY_OCCASIONS = [
    # (category, subcategory, occasion, weight)
    ('daily',   'personal', 'birthday',       0.30),
    ('daily',   'social',   'congratulations',0.14),
    ('daily',   'social',   'daily_cheer',    0.13),
    ('daily',   'social',   'thank_you',      0.12),
    ('daily',   'social',   'just_because',   0.08),
    ('daily',   'self',     'self_gift',       0.12),
    ('daily',   'social',   'get_well',        0.05),
    ('daily',   'social',   'apology',         0.03),
    ('special', 'seasonal', 'day33',           0.03),
]

def pick_daily_occasion():
    weights = [x[3] for x in DAILY_OCCASIONS]
    idx = weighted_choice(range(len(DAILY_OCCASIONS)), weights)
    r = DAILY_OCCASIONS[idx]
    return r[0], r[1], r[2]


# ══════════════════════════════════════════════════════════════════════════════
# 1. USERS
# ══════════════════════════════════════════════════════════════════════════════

def generate_users(n: int) -> list:
    print(f"[users] 생성 중... ({n:,}행)")
    genders      = ['F', 'M']
    gender_w     = [0.62, 0.38]
    age_groups   = ['10대', '20대', '30대', '40대', '50대+']
    age_w        = [0.06, 0.28, 0.38, 0.22, 0.06]
    devices      = ['ios', 'android']
    device_w     = [0.48, 0.52]
    acq_channels = ['organic', 'ad', 'gift_received', 'search']
    acq_w        = [0.30, 0.20, 0.40, 0.10]
    gen_dist     = [0, 1, 2, 3]
    gen_w        = [0.35, 0.45, 0.17, 0.03]

    rows = []
    user_ids = [f"U{i:05d}" for i in range(1, n + 1)]

    for uid in user_ids:
        gender    = weighted_choice(genders, gender_w)
        age_group = weighted_choice(age_groups, age_w)
        device    = weighted_choice(devices, device_w)
        acq       = weighted_choice(acq_channels, acq_w)
        gen       = weighted_choice(gen_dist, gen_w)

        faction = 'received' if acq == 'gift_received' else weighted_choice(['sent', 'received'], [0.55, 0.45])

        if gen > 0 and len(rows) > 0:
            ref_idx = random.randint(0, len(rows) - 1)
            referred_by = rows[ref_idx]['user_id']
        else:
            referred_by = ''
            gen = 0

        rows.append({
            'user_id':             uid,
            'gender':              gender,
            'age_group':           age_group,
            'device_type':         device,
            'acquisition_channel': acq,
            'first_action_type':   faction,
            'referral_generation': gen,
            'referred_by_user_id': referred_by,
        })

    print(f"  → {len(rows):,}행 완료")
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# 2. ORDERS + GIFT_RECEIPTS
# ══════════════════════════════════════════════════════════════════════════════

ENTRY_ROUTES      = ['friend_list', 'chat_room', 'gift_tab_direct', 'campaign_link', 'search_direct']
ENTRY_W           = [0.28, 0.22, 0.25, 0.15, 0.10]
DISCOVERY_METHODS = ['ranking', 'curation', 'search', 'category_browse', 'campaign_banner']
DISCOVERY_W       = [0.30, 0.25, 0.18, 0.17, 0.10]
ORDER_STATUSES    = ['accepted', 'pending_accepted', 'expired', 'refunded']
ORDER_STATUS_W    = [0.82, 0.07, 0.08, 0.03]
RECEIPT_STATUSES  = ['accepted', 'pending', 'expired', 'option_changed']
RECEIPT_STATUS_W  = [0.82, 0.07, 0.08, 0.03]


def build_daily_order_count() -> dict:
    """
    연도별 성장률 반영:
      2023: 87,000건 (기준)
      2024: 113,000건 (+30% YoY) → 실제 카카오 선물하기 매년 성장 추세 반영
    """
    YEAR_TARGET = {2023: 87_000, 2024: 113_000}

    all_days    = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]
    multipliers = [get_seasonal_multiplier(d) for d in all_days]

    # 연도별로 base 따로 계산
    days_2023 = [d for d in all_days if d.year == 2023]
    days_2024 = [d for d in all_days if d.year == 2024]
    mult_2023 = [get_seasonal_multiplier(d) for d in days_2023]
    mult_2024 = [get_seasonal_multiplier(d) for d in days_2024]

    base_2023 = YEAR_TARGET[2023] / sum(mult_2023)
    base_2024 = YEAR_TARGET[2024] / sum(mult_2024)

    base_by_year = {2023: base_2023, 2024: base_2024}

    result = {}
    for d, m in zip(all_days, multipliers):
        base  = base_by_year[d.year]
        mu    = base * m
        sigma = max(1.0, mu ** 0.5)
        count = max(1, int(random.gauss(mu, sigma)))
        result[d] = count
    return result


def generate_orders_and_receipts(users: list, daily_counts: dict) -> tuple:
    print("[orders + gift_receipts] 생성 중...")
    user_ids  = [u['user_id'] for u in users]
    orders    = []
    receipts  = []
    order_idx = receipt_idx = 1

    for d in sorted(daily_counts):
        count      = daily_counts[d]
        season_occ = get_season_occasion(d)

        for _ in range(count):
            oid = f"ORD{order_idx:06d}"
            rid = f"RCP{receipt_idx:06d}"
            order_idx   += 1
            receipt_idx += 1

            sender_uid = random.choice(user_ids)

            if season_occ and random.random() < 0.60:
                occ_cat, occ_sub, occ_val = season_occ
            else:
                occ_cat, occ_sub, occ_val = pick_daily_occasion()

            if occ_val == 'self_gift':
                receiver_uid = sender_uid
                is_code_gift = False
            else:
                receiver_uid = random.choice(user_ids)
                while receiver_uid == sender_uid:
                    receiver_uid = random.choice(user_ids)
                is_code_gift = random.random() < 0.20

            prod = pick_product(occ_val)
            pid, brand, cat_l1, cat_l2, price_mu, price_sig = prod

            unit_price = lognormal_int(price_mu, price_sig)
            discount   = 0 if random.random() > 0.25 else int(unit_price * random.uniform(0.05, 0.20))
            total_amt  = max(0, unit_price - discount)

            created_ts    = rand_ts(d)
            updated_ts    = created_ts + timedelta(hours=random.randint(0, 72))
            order_status  = weighted_choice(ORDER_STATUSES, ORDER_STATUS_W)
            entry_route   = weighted_choice(ENTRY_ROUTES, ENTRY_W)
            discovery     = weighted_choice(DISCOVERY_METHODS, DISCOVERY_W)

            orders.append({
                'order_id':             oid,
                'sender_user_id':       sender_uid,
                'occasion_category':    occ_cat,
                'occasion_subcategory': occ_sub,
                'gift_occasion':        occ_val,
                'entry_route':          entry_route,
                'discovery_method':     discovery,
                'product_id':           pid,
                'brand_name':           brand,
                'category_l1':          cat_l1,
                'category_l2':          cat_l2,
                'unit_price_krw':       unit_price,
                'total_amount_krw':     total_amt,
                'discount_amount_krw':  discount,
                'order_status':         order_status,
                'is_code_gift':         str(is_code_gift).lower(),
                'created_at':           created_ts.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at':           updated_ts.strftime('%Y-%m-%d %H:%M:%S'),
            })

            # receipt
            receipt_status = weighted_choice(RECEIPT_STATUSES, RECEIPT_STATUS_W)
            expires_ts     = created_ts + timedelta(days=30)
            if receipt_status in ('accepted', 'option_changed'):
                accepted_ts = created_ts + timedelta(hours=random.randint(1, 96))
            else:
                accepted_ts = None

            receipts.append({
                'receipt_id':       rid,
                'order_id':         oid,
                'receiver_user_id': receiver_uid,
                'accepted_at':      accepted_ts.strftime('%Y-%m-%d %H:%M:%S') if accepted_ts else '',
                'expires_at':       expires_ts.strftime('%Y-%m-%d %H:%M:%S'),
                'receipt_status':   receipt_status,
            })

    print(f"  → orders {len(orders):,}행, gift_receipts {len(receipts):,}행 완료")
    return orders, receipts


# ══════════════════════════════════════════════════════════════════════════════
# 3. CAMPAIGNS
# ══════════════════════════════════════════════════════════════════════════════

CAMPAIGN_TEMPLATES = [
    # (suffix, channel, segment, occ_cat, occ_sub, occ_val, msg_type, day_offset)
    # 빼빼로데이
    ('pepero_d7_A',   'brand_message',  'champions',       'special', 'seasonal', 'pepero_day',    'curation', -7),
    ('pepero_d7_B',   'brand_message',  'champions',       'special', 'seasonal', 'pepero_day',    'ranking',  -7),
    ('pepero_d3_A',   'brand_message',  'at_risk',         'special', 'seasonal', 'pepero_day',    'seasonal', -3),
    ('pepero_d3_B',   'brand_message',  'at_risk',         'special', 'seasonal', 'pepero_day',    'discount', -3),
    # 발렌타인데이
    ('val_d7_A',      'friendtalk',     'loyal_customers', 'special', 'seasonal', 'valentines_day','curation', -7),
    ('val_d7_B',      'friendtalk',     'loyal_customers', 'special', 'seasonal', 'valentines_day','ranking',  -7),
    ('val_d3_A',      'brand_message',  'new_customers',   'special', 'seasonal', 'valentines_day','seasonal', -3),
    ('val_d3_B',      'brand_message',  'new_customers',   'special', 'seasonal', 'valentines_day','discount', -3),
    # 어버이날
    ('parents_d14_A', 'friendtalk',     'champions',       'special', 'seasonal', 'parents_day',   'curation',-14),
    ('parents_d14_B', 'friendtalk',     'champions',       'special', 'seasonal', 'parents_day',   'seasonal',-14),
    ('parents_d7_A',  'brand_message',  'need_attention',  'special', 'seasonal', 'parents_day',   'discount', -7),
    ('parents_d7_B',  'brand_message',  'need_attention',  'special', 'seasonal', 'parents_day',   'ranking',  -7),
    # 스승의 날
    ('teachers_d7_A', 'friendtalk',     'loyal_customers', 'special', 'seasonal', 'teachers_day',  'curation', -7),
    ('teachers_d7_B', 'friendtalk',     'loyal_customers', 'special', 'seasonal', 'teachers_day',  'ranking',  -7),
    # 화이트데이
    ('white_d3_A',    'brand_message',  'promising',       'special', 'seasonal', 'white_day',     'curation', -3),
    ('white_d3_B',    'brand_message',  'promising',       'special', 'seasonal', 'white_day',     'discount', -3),
    # 추석
    ('chuseok_d14_A', 'friendtalk',     'champions',       'special', 'seasonal', 'chuseok',       'seasonal',-14),
    ('chuseok_d14_B', 'friendtalk',     'champions',       'special', 'seasonal', 'chuseok',       'curation',-14),
    # 크리스마스
    ('xmas_d7_A',     'brand_message',  'new_customers',   'special', 'seasonal', 'christmas',     'curation', -7),
    ('xmas_d7_B',     'brand_message',  'new_customers',   'special', 'seasonal', 'christmas',     'seasonal', -7),
]

SEASON_ANCHOR = {
    'pepero_day':    (11, 11),
    'valentines_day':(2,  14),
    'parents_day':   (5,   8),
    'teachers_day':  (5,  15),
    'white_day':     (3,  14),
    'chuseok':       (9,  29),
    'christmas':     (12, 25),
}

# 상시 캠페인 (생일·at_risk) 별도 정의
ALWAYS_ON_CAMPAIGNS = [
    ('birthday_curation_A', 'in_app_message', 'loyal_customers', 'daily', 'personal', 'birthday',    'curation', 'A'),
    ('birthday_ranking_B',  'in_app_message', 'loyal_customers', 'daily', 'personal', 'birthday',    'ranking',  'B'),
    ('at_risk_discount_A',  'friendtalk',     'at_risk',         'daily', 'social',   'daily_cheer', 'discount', 'A'),
    ('at_risk_curation_B',  'friendtalk',     'at_risk',         'daily', 'social',   'daily_cheer', 'curation', 'B'),
]


def generate_campaigns() -> list:
    print("[campaigns] 생성 중...")
    rows    = []
    cmp_idx = 1

    for year in [2023, 2024]:
        # 시즌 캠페인
        for tmpl in CAMPAIGN_TEMPLATES:
            suffix, channel, seg, occ_cat, occ_sub, occ_val, msg_type, offset = tmpl
            anchor = SEASON_ANCHOR[occ_val]
            send_date = date(year, anchor[0], anchor[1]) + timedelta(days=offset)
            variation = 'A' if suffix.endswith('_A') else 'B'
            rows.append({
                'campaign_id':          f"CMP{cmp_idx:03d}",
                'campaign_name':        f"{year}_{suffix}",
                'channel':              channel,
                'target_segment':       seg,
                'occasion_category':    occ_cat,
                'occasion_subcategory': occ_sub,
                'gift_occasion':        occ_val,
                'message_type':         msg_type,
                'message_variation':    variation,
                'send_date':            send_date.strftime('%Y-%m-%d'),
                'target_user_count':    random.randint(1_500, 4_000),
            })
            cmp_idx += 1

        # 상시 캠페인: 짝수달 15일
        for month in [2, 4, 6, 8, 10, 12]:
            for tmpl in ALWAYS_ON_CAMPAIGNS:
                suffix, channel, seg, occ_cat, occ_sub, occ_val, msg_type, variation = tmpl
                rows.append({
                    'campaign_id':          f"CMP{cmp_idx:03d}",
                    'campaign_name':        f"{year}_{month:02d}_{suffix}",
                    'channel':              channel,
                    'target_segment':       seg,
                    'occasion_category':    occ_cat,
                    'occasion_subcategory': occ_sub,
                    'gift_occasion':        occ_val,
                    'message_type':         msg_type,
                    'message_variation':    variation,
                    'send_date':            date(year, month, 15).strftime('%Y-%m-%d'),
                    'target_user_count':    random.randint(1_000, 3_000),
                })
                cmp_idx += 1

    print(f"  → {len(rows):,}행 완료")
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# 4. CAMPAIGN_LOGS
# ══════════════════════════════════════════════════════════════════════════════

AB_METRICS = {
    # 출처: 카카오 공식 발표(Open Rate 60%, CTR 7.8%) + 업계 벤치마크(RESEARCH.md Tier 1)
    # ctr/cvr은 "오픈한 사람 중" 조건부 확률. 실제 발송→구매 = open × ctr × cvr
    'curation': {'open_rate': 0.62, 'ctr': 0.10, 'cvr': 0.12, 'block_rate': 0.007},
    'ranking':  {'open_rate': 0.55, 'ctr': 0.08, 'cvr': 0.04, 'block_rate': 0.012},
    'discount': {'open_rate': 0.65, 'ctr': 0.14, 'cvr': 0.10, 'block_rate': 0.010},
    'seasonal': {'open_rate': 0.58, 'ctr': 0.10, 'cvr': 0.07, 'block_rate': 0.009},
}


def generate_campaign_logs(campaigns: list, users: list) -> list:
    print("[campaign_logs] 생성 중...")
    user_ids = [u['user_id'] for u in users]
    rows     = []
    log_idx  = 1

    for cmp in campaigns:
        cid       = cmp['campaign_id']
        msg_type  = cmp['message_type']
        variation = cmp['message_variation']
        send_date = datetime.strptime(cmp['send_date'], '%Y-%m-%d')
        n_target  = cmp['target_user_count']
        metrics   = AB_METRICS.get(msg_type, AB_METRICS['seasonal'])

        sample_n = min(n_target, len(user_ids))
        targets  = random.sample(user_ids, sample_n)

        for uid in targets:
            device  = random.choice(['ios', 'android'])
            base_ts = send_date + timedelta(
                hours=random.randint(9, 21),
                minutes=random.randint(0, 59)
            )

            def log(event, ts):
                nonlocal log_idx
                rows.append({
                    'log_id':               f"LOG{log_idx:07d}",
                    'campaign_id':          cid,
                    'user_id':              uid,
                    'message_type':         msg_type,
                    'message_variation_id': variation,
                    'event_type':           event,
                    'occurred_at':          ts.strftime('%Y-%m-%d %H:%M:%S'),
                    'device_type':          device,
                    'platform':             'kakao',
                })
                log_idx += 1

            log('send', base_ts)

            if random.random() < metrics['block_rate']:
                log('block', base_ts + timedelta(minutes=random.randint(1, 30)))
                continue

            if random.random() < metrics['open_rate']:
                open_ts = base_ts + timedelta(minutes=random.randint(5, 180))
                log('open', open_ts)

                if random.random() < metrics['ctr']:
                    click_ts = open_ts + timedelta(seconds=random.randint(10, 120))
                    log('click', click_ts)

                    if random.random() < metrics['cvr']:
                        log('purchase', click_ts + timedelta(minutes=random.randint(2, 60)))

    print(f"  → {len(rows):,}행 완료")
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# CSV 저장
# ══════════════════════════════════════════════════════════════════════════════

def save_csv(rows: list, filename: str):
    if not rows:
        print(f"  [경고] {filename}: 데이터 없음")
        return
    path = f"{OUTPUT_DIR}/{filename}"
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  → {path} 저장 ({len(rows):,}행)")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("카카오톡 선물하기 Mock Data Generator")
    print(f"  기간: {START_DATE} ~ {END_DATE}")
    print(f"  유저: {N_USERS:,}명 | SEED: {RANDOM_SEED}")
    print("=" * 60)

    users = generate_users(N_USERS)
    save_csv(users, "users.csv")

    daily_counts = build_daily_order_count()
    orders, receipts = generate_orders_and_receipts(users, daily_counts)
    save_csv(orders,   "orders.csv")
    save_csv(receipts, "gift_receipts.csv")

    campaigns = generate_campaigns()
    save_csv(campaigns, "campaigns.csv")

    logs = generate_campaign_logs(campaigns, users)
    save_csv(logs, "campaign_logs.csv")

    print()
    print("=" * 60)
    print("생성 완료!")
    print(f"  users.csv          {len(users):>10,}행")
    print(f"  orders.csv         {len(orders):>10,}행")
    print(f"  gift_receipts.csv  {len(receipts):>10,}행")
    print(f"  campaigns.csv      {len(campaigns):>10,}행")
    print(f"  campaign_logs.csv  {len(logs):>10,}행")
    print("=" * 60)


if __name__ == "__main__":
    main()
