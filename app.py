import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime
import re
import math
import os
import json
import hashlib
try:
    from pyecharts import options as opts
    from pyecharts.charts import Line, Bar, Polar
    from pyecharts.commons.utils import JsCode
    from streamlit_echarts import st_pyecharts
    HAS_PYECHARTS = True
except ModuleNotFoundError:
    opts = None
    Line = None
    Bar = None
    Polar = None
    JsCode = None
    st_pyecharts = None
    HAS_PYECHARTS = False

try:
    import streamlit_shadcn_ui as ui
    HAS_SHADCN_UI = True
except ModuleNotFoundError:
    ui = None
    HAS_SHADCN_UI = False

try:
    from awesome_table import AwesomeTable
    HAS_AWESOME_TABLE = True
except ImportError:
    # streamlit-awesome-table가 pandas<1.x 경로를 참조하는 문제 호환 처리
    try:
        from pandas import json_normalize as _json_normalize
        import pandas.io.json as _pandas_io_json

        if not hasattr(_pandas_io_json, "json_normalize"):
            _pandas_io_json.json_normalize = _json_normalize

        from awesome_table import AwesomeTable
        HAS_AWESOME_TABLE = True
    except Exception:
        AwesomeTable = None
        HAS_AWESOME_TABLE = False

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Real Estate Insights",
    page_icon="🏢",
    layout="wide"
)

# --- 커스텀 CSS (Shadcn Inspired Dashboard Theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&display=swap');
    :root {
        --bg: #f4f6f8;
        --panel: #ffffff;
        --ink: #0f172a;
        --muted: #64748b;
        --line: #e2e8f0;
        --brand: #0f766e;
        --brand-soft: #ccfbf1;
    }

    .block-container {
        padding-top: 1.1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1220px !important;
    }

    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }
    .stDeployButton, #MainMenu {
        display: none !important;
    }

    .stApp {
        background:
            radial-gradient(1300px 500px at 96% -10%, #d9f99d 0%, transparent 48%),
            radial-gradient(900px 420px at -5% -20%, #bfdbfe 0%, transparent 46%),
            var(--bg);
        color: var(--ink);
        font-family: 'Manrope', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .hero-container {
        border: 1px solid var(--line);
        border-radius: 18px;
        background: linear-gradient(125deg, rgba(255,255,255,0.9) 0%, rgba(240,253,250,0.9) 100%);
        box-shadow: 0 10px 30px rgba(2, 8, 23, 0.06);
        padding: 1.65rem;
        margin-bottom: 1.25rem;
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-bottom: 0.3rem;
    }
    .hero-subtitle {
        color: var(--muted);
        font-size: 0.95rem;
    }

    [data-testid="stMetric"] {
        background-color: var(--panel);
        border: 1px solid var(--line);
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        border-radius: 14px;
        padding: 1rem 1.1rem;
    }

    .stButton > button, button[kind="primary"] {
        width: 100%;
        border-radius: 11px;
        font-weight: 700;
        background-color: var(--brand);
        color: white;
        border: 1px solid var(--brand);
        padding: 0.56rem 1rem;
    }
    .stButton > button:hover, button[kind="primary"]:hover {
        background-color: #115e59;
        border-color: #115e59;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-right: 1px solid var(--line);
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--line) !important;
        border-radius: 16px !important;
        background: rgba(255,255,255,0.9) !important;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.03) !important;
        padding: 1rem !important;
        margin-bottom: 1.2rem !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid var(--line) !important;
        border-radius: 12px !important;
        background: #ffffff !important;
    }
    [data-testid="stExpander"] summary {
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- API 키 설정 (Streamlit Secrets) ---
if "service_key" in st.secrets:
    SECRET_KEY = st.secrets["service_key"]
else:
    SECRET_KEY = None

# --- 세션 상태 초기화 ---
if "df" not in st.session_state:
    st.session_state.df = None
if "region_name" not in st.session_state:
    st.session_state.region_name = ""
if "trade_type_val" not in st.session_state:
    st.session_state.trade_type_val = "전월세"
if "df_nonce" not in st.session_state:
    st.session_state.df_nonce = 0

# 필터링 조건 유지를 위한 상태 초기화
if "filter_deal_price" not in st.session_state: st.session_state.filter_deal_price = None
if "filter_dep_price" not in st.session_state: st.session_state.filter_dep_price = None
if "filter_rent_price" not in st.session_state: st.session_state.filter_rent_price = None
if "filter_areas" not in st.session_state: st.session_state.filter_areas = []
if "filter_floors" not in st.session_state: st.session_state.filter_floors = []
if "filter_area_unit" not in st.session_state: st.session_state.filter_area_unit = "공급면적(평형대)"
if "filter_supply_bands" not in st.session_state: st.session_state.filter_supply_bands = []

USER_PREFS_PATH = os.path.join(os.path.dirname(__file__), ".user_prefs.json")

def get_user_pref_key():
    """헤더/쿠키 기반 사용자 식별 키 생성"""
    raw = "anonymous"
    try:
        ctx = st.context
        headers = getattr(ctx, "headers", {}) or {}
        cookies = getattr(ctx, "cookies", {}) or {}

        cookie_seed = ""
        for k in ("_streamlit_user", "_streamlit_session", "ajs_anonymous_id"):
            v = cookies.get(k)
            if v:
                cookie_seed = str(v)
                break

        header_seed = "|".join([
            str(headers.get("x-forwarded-for", "")),
            str(headers.get("user-agent", "")),
            str(headers.get("accept-language", "")),
        ])
        raw = cookie_seed if cookie_seed else header_seed
        if not str(raw).strip():
            raw = "anonymous"
    except Exception:
        raw = "anonymous"

    return hashlib.sha256(str(raw).encode("utf-8")).hexdigest()[:24]

def load_user_preferences(user_key):
    """사용자별 입력값 복원"""
    if not os.path.exists(USER_PREFS_PATH):
        return {}
    try:
        with open(USER_PREFS_PATH, "r", encoding="utf-8") as f:
            all_prefs = json.load(f)
        if isinstance(all_prefs, dict):
            value = all_prefs.get(user_key, {})
            return value if isinstance(value, dict) else {}
    except Exception:
        pass
    return {}

def save_user_preferences(user_key, prefs):
    """사용자별 입력값 저장"""
    try:
        all_prefs = {}
        if os.path.exists(USER_PREFS_PATH):
            with open(USER_PREFS_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    all_prefs = loaded
        all_prefs[user_key] = prefs

        temp_path = f"{USER_PREFS_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(all_prefs, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, USER_PREFS_PATH)
    except Exception:
        pass

def parse_date_or_fallback(value, fallback):
    try:
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str) and value:
            return datetime.date.fromisoformat(value)
    except Exception:
        pass
    return fallback

# 사용자별 입력값 초기 복원
today_for_init = datetime.date.today()
try:
    default_start_for_init = today_for_init.replace(year=today_for_init.year - 1)
except ValueError:
    default_start_for_init = today_for_init.replace(year=today_for_init.year - 1, day=28)

if "user_pref_key" not in st.session_state:
    st.session_state.user_pref_key = get_user_pref_key()

if "inputs_restored" not in st.session_state:
    restored = load_user_preferences(st.session_state.user_pref_key)
    st.session_state.trade_type_val = restored.get("trade_type", st.session_state.trade_type_val)
    st.session_state.region_input_text = restored.get("region_input", "송파구")
    st.session_state.start_date_input = parse_date_or_fallback(
        restored.get("start_date"),
        default_start_for_init
    )
    st.session_state.end_date_input = parse_date_or_fallback(
        restored.get("end_date"),
        today_for_init
    )
    st.session_state.apt_keyword_input = restored.get("apt_keyword", "")
    st.session_state.inputs_restored = True

@st.cache_resource
def load_bdong_data():
    """법정동 코드 데이터 로드"""
    try:
        return code_bdong()
    except Exception as e:
        st.error(f"법정동 데이터를 불러올 수 없습니다: {e}")
        return pd.DataFrame()

def get_region_code(region_name):
    """지역명을 입력받아 5자리 시군구 코드를 반환"""
    try:
        df = load_bdong_data()
        if df.empty:
            return None, None
        
        active_df = df[df['말소일자'].isna() | (df['말소일자'] == '')].copy()
        mask = (active_df['시군구명'].str.contains(region_name, na=False)) | \
               (active_df['읍면동명'].str.contains(region_name, na=False))
        
        results = active_df[mask]
        if not results.empty:
            target = results.iloc[0]
            return str(target['시군구코드']), f"{target['시도명']} {target['시군구명']}"
        return None, None
    except Exception as e:
        st.error(f"지역 코드 검색 중 오류: {e}")
        return None, None

def standardize_columns(df):
    """API 반환 컬럼명을 앱에서 사용하는 표준 명칭으로 변경"""
    df.columns = [col.strip() for col in df.columns]
    mapping = {
        '아파트': ['단지', '단지명', '건물명', 'aptNm', '아파트'],
        '매매가': ['거래금액', '거래금액(만원)', 'dealAmount', '매매가'],
        '보증금': ['보증금액', '보증금(만원)', 'deposit', '보증금'],
        '월세': ['월세액', '월세(만원)', 'monthlyRent', '월세'],
        '전용면적': ['excluUseAr', '전용면적(㎡)', '면적', '전용면적'],
        '층': ['floor', '층수', '층'],
        '년': ['dealYear', '년'],
        '월': ['dealMonth', '월'],
        '일': ['dealDay', '일']
    }
    for standard, candidates in mapping.items():
        for col in candidates:
            if col in df.columns:
                df = df.rename(columns={col: standard})
                break
    return df

def to_numeric_safe(x):
    """문자열 숫자를 안전하게 숫자로 변환"""
    if pd.isna(x) or x == '': return 0.0
    val = re.sub(r'[^0-9.]', '', str(x))
    return float(val) if val else 0.0

SUPPLY_PYEONG_BANDS = [
    ((39, 40), "16~18평형"),
    ((49, 51), "20~22평형"),
    ((59, 59), "24~26평형"),
    ((72, 74), "28~30평형"),
    ((84, 85), "32~35평형"),
    ((101, 102), "39~41평형"),
]

SUPPLY_PYEONG_ANCHORS = [
    (39.5, 17.0),
    (50.0, 21.0),
    (59.0, 25.0),
    (73.0, 29.0),
    (84.5, 33.5),
    (101.5, 40.0),
]

SUPPLY_BAND_CENTERS = {
    "16~18평형": 17.0,
    "20~22평형": 21.0,
    "24~26평형": 25.0,
    "28~30평형": 29.0,
    "32~35평형": 33.5,
    "39~41평형": 40.0,
}

def estimate_supply_pyeong(area_m2):
    """기준 앵커를 이용해 전용면적(㎡)을 공급평수(평)로 선형 보간/외삽"""
    if pd.isna(area_m2):
        return None

    x = float(area_m2)
    anchors = SUPPLY_PYEONG_ANCHORS

    if x <= anchors[0][0]:
        x0, y0 = anchors[0]
        x1, y1 = anchors[1]
    elif x >= anchors[-1][0]:
        x0, y0 = anchors[-2]
        x1, y1 = anchors[-1]
    else:
        x0 = y0 = x1 = y1 = None
        for i in range(len(anchors) - 1):
            ax0, ay0 = anchors[i]
            ax1, ay1 = anchors[i + 1]
            if ax0 <= x <= ax1:
                x0, y0, x1, y1 = ax0, ay0, ax1, ay1
                break

    if x1 == x0:
        return y0
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)

def to_supply_pyeong_band(area_m2):
    """보간된 공급평수를 가장 가까운 평형대 라벨로 매핑"""
    est = estimate_supply_pyeong(area_m2)
    if est is None:
        return None
    return min(SUPPLY_BAND_CENTERS.keys(), key=lambda k: abs(SUPPLY_BAND_CENTERS[k] - est))

def apply_apt_keyword_filter(df, expr):
    """아파트 키워드 조건식(AND/OR/NOT)을 적용"""
    if df is None or df.empty or '아파트' not in df.columns:
        return df
    if not expr or not str(expr).strip():
        return df

    q = str(expr).strip()
    q = re.sub(r'\s+(?i:or)\s+', '|', q)
    q = re.sub(r'\s+(?i:and)\s+', '&', q)
    groups = [g.strip() for g in q.split('|') if g.strip()]
    if not groups:
        return df

    name_series = df['아파트'].astype(str)
    final_mask = pd.Series(False, index=df.index)

    for g in groups:
        terms = [t.strip() for t in re.split(r'&', g) if t.strip()]
        include_terms = []
        exclude_terms = []

        for t in terms:
            t_clean = t.strip()
            if t_clean.startswith('-') or t_clean.startswith('!'):
                word = t_clean[1:].strip()
                if word:
                    exclude_terms.append(word)
            elif re.match(r'(?i)^not\s+', t_clean):
                word = re.sub(r'(?i)^not\s+', '', t_clean).strip()
                if word:
                    exclude_terms.append(word)
            else:
                include_terms.append(t_clean)

        group_mask = pd.Series(True, index=df.index)
        for w in include_terms:
            group_mask &= name_series.str.contains(w, na=False, case=False)
        for w in exclude_terms:
            group_mask &= ~name_series.str.contains(w, na=False, case=False)

        final_mask |= group_mask

    return df[final_mask]

def apply_all_column_filters(df, key_prefix):
    """출력용 데이터프레임의 모든 컬럼에 대해 동적 필터 적용"""
    if df is None or df.empty:
        return df, 0

    selected_cols = st.multiselect(
        "필터 컬럼",
        options=list(df.columns),
        default=[],
        key=f"{key_prefix}_selected_cols"
    )

    if not selected_cols:
        return df, 0

    mask = pd.Series(True, index=df.index)
    active_count = 0
    for col in selected_cols:
        with st.expander(f"조건 설정: {col}", expanded=False):
            series = df[col]
            safe_col = re.sub(r'[^0-9a-zA-Z_가-힣]', '_', str(col))

            numeric_series = pd.to_numeric(series, errors='coerce')
            numeric_ratio = numeric_series.notna().mean() if len(series) else 0

            # 전용면적은 공급평수 변환을 지원하고 멀티선택 UI 사용
            if '전용면적' in str(col) and numeric_ratio >= 0.9 and numeric_series.notna().any():
                unit = st.radio(
                    "표시 단위",
                    options=["공급면적(평형대)", "전용면적(㎡)"],
                    horizontal=True,
                    key=f"{key_prefix}_{safe_col}_unit"
                )

                if unit == "공급면적(평형대)":
                    converted = numeric_series.apply(to_supply_pyeong_band)
                    band_order = [label for _, label in SUPPLY_PYEONG_BANDS]
                    existing = [b for b in band_order if b in converted.dropna().unique().tolist()]
                    options = existing
                    label = "공급평형대 선택"
                else:
                    converted = numeric_series.round(1)
                    options = sorted([v for v in converted.dropna().unique().tolist()])
                    label = "전용면적(㎡) 선택"

                selected_vals = st.multiselect(
                    label,
                    options=options,
                    default=options,
                    key=f"{key_prefix}_{safe_col}_area_values"
                )
                if len(selected_vals) != len(options):
                    active_count += 1
                mask &= converted.isin(selected_vals)
                continue

            # 숫자로 해석 가능한 컬럼은 범위 필터 제공
            if numeric_ratio >= 0.9 and numeric_series.notna().any():
                min_v = float(numeric_series.min())
                max_v = float(numeric_series.max())

                if min_v == max_v:
                    st.caption(f"단일 값({min_v:g})만 존재합니다.")
                    continue

                is_int_like = (numeric_series.dropna() % 1 == 0).all()
                # 층 컬럼은 슬라이더 대신 체크박스 선택 UI 제공
                if "층" in str(col) and is_int_like:
                    floor_values = sorted(numeric_series.dropna().astype(int).unique().tolist())
                    if not floor_values:
                        continue

                    for floor in floor_values:
                        floor_key = f"{key_prefix}_{safe_col}_chk_{floor}"
                        if floor_key not in st.session_state:
                            st.session_state[floor_key] = True

                    btn_col1, btn_col2 = st.columns(2)
                    select_all = btn_col1.button("전체 선택", key=f"{key_prefix}_{safe_col}_chk_all", use_container_width=True)
                    clear_all = btn_col2.button("전체 해제", key=f"{key_prefix}_{safe_col}_chk_clear", use_container_width=True)
                    if select_all:
                        for floor in floor_values:
                            st.session_state[f"{key_prefix}_{safe_col}_chk_{floor}"] = True
                    elif clear_all:
                        for floor in floor_values:
                            st.session_state[f"{key_prefix}_{safe_col}_chk_{floor}"] = False

                    selected_vals = []
                    floor_cols = st.columns(4)
                    for idx, floor in enumerate(floor_values):
                        with floor_cols[idx % 4]:
                            checked = st.checkbox(f"{floor}", key=f"{key_prefix}_{safe_col}_chk_{floor}")
                        if checked:
                            selected_vals.append(floor)

                    if len(selected_vals) != len(floor_values):
                        active_count += 1
                    mask &= numeric_series.astype("Int64").isin(selected_vals)
                    continue

                if is_int_like:
                    slider_min = int(min_v)
                    slider_max = int(max_v)
                    step = 1 if slider_max - slider_min <= 200 else max(1, (slider_max - slider_min) // 200)
                    selected_range = st.slider(
                        f"{col} 범위",
                        min_value=slider_min,
                        max_value=slider_max,
                        value=(slider_min, slider_max),
                        step=step,
                        key=f"{key_prefix}_{safe_col}_range"
                    )
                else:
                    selected_range = st.slider(
                        f"{col} 범위",
                        min_value=min_v,
                        max_value=max_v,
                        value=(min_v, max_v),
                        key=f"{key_prefix}_{safe_col}_range"
                    )

                if selected_range[0] > min_v or selected_range[1] < max_v:
                    active_count += 1
                mask &= numeric_series.between(selected_range[0], selected_range[1], inclusive='both')
                continue

            # 문자열 컬럼은 고유값 수에 따라 다중선택/부분검색 제공
            str_series = series.astype(str)
            unique_vals = sorted([v for v in str_series.dropna().unique().tolist() if v != "nan"])

            if len(unique_vals) <= 100:
                selected_vals = st.multiselect(
                    f"{col} 값 선택",
                    options=unique_vals,
                    default=unique_vals,
                    key=f"{key_prefix}_{safe_col}_values"
                )
                if len(selected_vals) != len(unique_vals):
                    active_count += 1
                mask &= str_series.isin(selected_vals)
            else:
                keyword = st.text_input(
                    f"{col} 부분검색",
                    value="",
                    key=f"{key_prefix}_{safe_col}_keyword",
                    placeholder=f"{col}에 포함될 텍스트 입력"
                )
                if keyword:
                    active_count += 1
                    mask &= str_series.str.contains(keyword, na=False, case=False)

    return df[mask], active_count

def reset_filter_state(key_prefix):
    """기본 필터/동적 컬럼 필터 상태 초기화"""
    st.session_state.filter_deal_price = None
    st.session_state.filter_dep_price = None
    st.session_state.filter_rent_price = None
    st.session_state.filter_areas = []
    st.session_state.filter_area_unit = "공급면적(평형대)"
    st.session_state.filter_supply_bands = []
    st.session_state.filter_floors = []
    st.session_state.quick_area_unit = "공급면적(평형대)"

    delete_keys = [k for k in st.session_state.keys() if str(k).startswith(key_prefix)]
    for k in delete_keys:
        del st.session_state[k]

def render_awesome_table(df):
    """실거래 리스트를 AwesomeTable로 렌더링"""
    if df is None or df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    safe_df = df.copy().fillna("")
    safe_df.columns = [str(col) for col in safe_df.columns]
    if HAS_AWESOME_TABLE:
        try:
            AwesomeTable(safe_df, show_order=True, show_search=True)
            return
        except Exception as e:
            st.warning(f"AwesomeTable 렌더링에 실패해 기본 테이블로 대체합니다: {e}")
    st.dataframe(safe_df, use_container_width=True, hide_index=True)

def render_metric_card(title, content, description, key):
    """Shadcn metric card 우선 렌더링, 미설치 시 기본 metric 사용"""
    if HAS_SHADCN_UI:
        try:
            ui.metric_card(title=title, content=content, description=description, key=key)
            return
        except Exception:
            pass
    st.metric(title, content, description)

def make_period_frame(df):
    """거래일 기준 월 단위 집계 프레임 생성"""
    if df is None or df.empty:
        return pd.DataFrame()
    if not all(c in df.columns for c in ['년', '월']):
        return pd.DataFrame()

    work = df.copy()
    if '일' in work.columns:
        day_vals = pd.to_numeric(work['일'], errors='coerce').fillna(1).astype(int)
    else:
        day_vals = pd.Series(1, index=work.index)

    date_str = (
        pd.to_numeric(work['년'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(4) + "-" +
        pd.to_numeric(work['월'], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2) + "-" +
        day_vals.astype(str).str.zfill(2)
    )
    work['deal_date'] = pd.to_datetime(date_str, errors='coerce')
    work = work.dropna(subset=['deal_date']).sort_values('deal_date')
    if work.empty:
        return pd.DataFrame()

    work['period'] = work['deal_date'].dt.to_period('M').astype(str)
    return work

def render_trade_type_chart(df, trade_type):
    """거래유형별 기간-가격 상관 차트 렌더링 (pyecharts)"""
    if not HAS_PYECHARTS:
        st.error("차트 라이브러리(pyecharts)가 설치되지 않았습니다. `pip install -r requirements.txt` 후 다시 실행해주세요.")
        return

    base = make_period_frame(df)
    if base.empty:
        st.info("차트를 그릴 기간 데이터가 부족합니다.")
        return

    def axis_bounds(values, pad_ratio=0.08, force_int=False):
        vals = [float(v) for v in values if pd.notna(v)]
        if not vals:
            return 0, 1
        v_min, v_max = min(vals), max(vals)
        if v_min == v_max:
            pad = max(abs(v_min) * 0.1, 1.0)
            low, high = v_min - pad, v_max + pad
        else:
            span = v_max - v_min
            pad = span * pad_ratio
            low, high = max(0, v_min - pad), v_max + pad

        if force_int:
            low = int(math.floor(low))
            high = int(math.ceil(high))
            if low == high:
                high = low + 1
            return low, high

        # 부동소수점 노이즈(예: 7.14800000002) 제거용 축값 정규화
        max_abs = max(abs(low), abs(high))
        if max_abs >= 1000:
            digits = 0
        elif max_abs >= 100:
            digits = 1
        elif max_abs >= 10:
            digits = 1
        elif max_abs >= 1:
            digits = 2
        else:
            digits = 3

        low = round(low, digits)
        high = round(high, digits)
        if low == high:
            high = round(high + (10 ** (-digits)), digits)
        return low, high

    if trade_type == "전월세":
        metric_options = []
        if '보증금_num' in base.columns:
            metric_options.append(("보증금", "보증금_num", "보증금(만원)"))
        if '월세_num' in base.columns:
            metric_options.append(("월세", "월세_num", "월세(만원)"))
        if not metric_options:
            st.info("전월세 차트를 위한 보증금/월세 데이터가 부족합니다.")
            return

        metric_map = {label: (col, y_name) for label, col, y_name in metric_options}
        metric_choice = st.radio(
            "전월세 차트 지표",
            options=[m[0] for m in metric_options],
            horizontal=True,
            key="rental_chart_metric"
        )
        value_col, y_axis_name = metric_map[metric_choice]
    else:
        if '매매가_num' not in base.columns:
            st.info("매매 차트를 위한 매매가 데이터가 부족합니다.")
            return
        value_col, y_axis_name = "매매가_num", "매매가(만원)"
        metric_choice = "매매가"

    apt_series = pd.Series(["전체"] * len(base), index=base.index)
    if '아파트' in base.columns:
        apt_series = base['아파트'].astype(str).replace("nan", "").replace("", "미상")
    base = base.assign(_apt=apt_series)
    apt_names = [n for n in sorted(base['_apt'].dropna().unique().tolist()) if str(n).strip() != ""]
    multi_apt = len(apt_names) >= 2

    monthly_cnt = (
        base.groupby('period', as_index=False)
        .agg(거래건수=('period', 'count'))
        .sort_values('period')
    )
    x_data = monthly_cnt['period'].tolist()
    cnt_month = monthly_cnt['거래건수'].tolist()
    cnt_min, cnt_max = axis_bounds(cnt_month, 0.2, force_int=True)

    apt_monthly = (
        base.groupby(['period', '_apt'], as_index=False)
        .agg(value=(value_col, 'mean'))
    )
    pivot = apt_monthly.pivot(index='period', columns='_apt', values='value').reindex(x_data)

    all_values = []
    for apt in pivot.columns.tolist():
        vals = pivot[apt].round(1).tolist()
        all_values.extend([v for v in vals if pd.notna(v)])
    val_min, val_max = axis_bounds(all_values, 0.12)

    line = Line()
    line.add_xaxis(x_data)
    for apt in pivot.columns.tolist():
        values = pivot[apt].round(1).tolist()
        line_values = [None if pd.isna(v) else float(v) for v in values]
        line.add_yaxis(
            f"{apt}",
            line_values,
            is_smooth=True,
            symbol="none",
            is_connect_nones=True,
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=2.4, type_="solid"),
        )

    line.extend_axis(
        yaxis=opts.AxisOpts(
            name="거래건수(건)",
            type_="value",
            position="right",
            min_=cnt_min,
            max_=cnt_max,
            axislabel_opts=opts.LabelOpts(formatter="{value}"),
        )
    )

    bar = Bar()
    bar.add_xaxis(x_data)
    if multi_apt:
        cnt_by_apt = (
            base.groupby(['period', '_apt'], as_index=False)
            .agg(cnt=('period', 'count'))
            .pivot(index='period', columns='_apt', values='cnt')
            .reindex(x_data)
            .fillna(0)
        )
        for apt in cnt_by_apt.columns.tolist():
            bar.add_yaxis(
                f"{apt} 거래건수",
                cnt_by_apt[apt].astype(int).tolist(),
                yaxis_index=1,
                stack="apt_cnt",
                bar_width="60%",
                category_gap="78%",
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(opacity=0.28),
            )
    else:
        bar.add_yaxis(
            "월별 거래건수",
            cnt_month,
            yaxis_index=1,
            bar_width="60%",
            category_gap="78%",
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(color="rgba(148, 163, 184, 0.20)"),
        )

    line.overlap(bar)
    title = f"월평균 추세 + 월별 거래건수 ({'전월세' if trade_type == '전월세' else '매매'})"
    subtitle = f"지표: {metric_choice} · {'아파트별 라인' if multi_apt else '단일 라인'}"
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=title, subtitle=subtitle),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        legend_opts=opts.LegendOpts(pos_top="4%", type_="scroll"),
        xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
        yaxis_opts=opts.AxisOpts(name=y_axis_name, type_="value", min_=val_min, max_=val_max),
        datazoom_opts=[
            opts.DataZoomOpts(type_="inside", range_start=0, range_end=100),
            opts.DataZoomOpts(type_="slider", range_start=0, range_end=100)
        ],
    )
    st_pyecharts(line, height="500px")

def render_rental_polar_scatter(df):
    """전월세 데이터의 보증금-월세 분포를 Polar Scatter로 렌더링"""
    if not HAS_PYECHARTS:
        return
    if df is None or df.empty:
        st.info("Polar Scatter를 표시할 데이터가 없습니다.")
        return
    if "보증금_num" not in df.columns or "월세_num" not in df.columns:
        st.info("Polar Scatter를 위한 보증금/월세 데이터가 부족합니다.")
        return

    scatter_df = df[["보증금_num", "월세_num"]].dropna().copy()
    scatter_df = scatter_df[
        (pd.to_numeric(scatter_df["보증금_num"], errors="coerce").notna()) &
        (pd.to_numeric(scatter_df["월세_num"], errors="coerce").notna())
    ]
    if scatter_df.empty:
        st.info("Polar Scatter를 표시할 유효한 전월세 데이터가 없습니다.")
        return

    deposits = scatter_df["보증금_num"].astype(float)
    rents = scatter_df["월세_num"].astype(float)
    # Polar 좌표는 [radius, angle] 순서이므로 [보증금, 월세]로 전달
    points = list(zip(deposits.round(1).tolist(), rents.round(1).tolist()))

    dep_min, dep_max = float(deposits.min()), float(deposits.max())
    rent_min, rent_max = float(rents.min()), float(rents.max())
    dep_pad = max((dep_max - dep_min) * 0.08, 1.0)
    rent_pad = max((rent_max - rent_min) * 0.08, 1.0)

    chart = Polar()
    chart.add_schema(
        angleaxis_opts=opts.AngleAxisOpts(
            type_="value",
            min_=max(0, rent_min - rent_pad),
            max_=rent_max + rent_pad,
            start_angle=90,
        ),
        radiusaxis_opts=opts.RadiusAxisOpts(
            type_="value",
            min_=max(0, dep_min - dep_pad),
            max_=dep_max + dep_pad,
        ),
    )
    chart.add(
        series_name="전월세 분포",
        data=points,
        type_="scatter",
        symbol_size=8,
        label_opts=opts.LabelOpts(is_show=False),
        itemstyle_opts=opts.ItemStyleOpts(color="#0f766e", opacity=0.72),
    )
    chart.set_global_opts(
        title_opts=opts.TitleOpts(
            title="보증금-월세 Polar Scatter",
            subtitle="각 점은 한 건의 전월세 거래를 의미합니다.",
        ),
        tooltip_opts=opts.TooltipOpts(
            trigger="item",
            formatter=JsCode("function (params) { var v = params.value || []; return v[0] + ' / ' + v[1]; }"),
        ),
        legend_opts=opts.LegendOpts(pos_top="4%"),
    )
    st_pyecharts(chart, height="520px")

# --- 사이드바 ---
with st.sidebar:
    st.markdown('<div style="font-size: 1.4rem; font-weight: 800; margin-bottom: 0.25rem;">Search Portal</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.85rem; color: #64748b; margin-bottom: 1.2rem;">실거래가 데이터 조회</div>', unsafe_allow_html=True)
    
    if not SECRET_KEY:
        current_key = st.text_input("🔑 API 인증키", type="password", help="공공데이터포털 API 키")
    else:
        st.info("✅ API 키가 설정되어 있습니다.")
        current_key = SECRET_KEY
        
    st.divider()
    
    trade_type = st.radio("🏠 거래 유형", ["매매", "전월세"], 
                         index=0 if st.session_state.trade_type_val == "매매" else 1, 
                         horizontal=True, key="trade_type_radio")
    st.session_state.trade_type_val = trade_type
    
    region_input = st.text_input("📍 지역명 (시군구)", value="송파구", key="region_input_text")
    
    today = datetime.date.today()
    try:
        default_start_date = today.replace(year=today.year - 1)
    except ValueError:
        # 윤년 2/29인 경우 1년 전 2/28로 보정
        default_start_date = today.replace(year=today.year - 1, day=28)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("🗓️ 시작월", value=default_start_date, key="start_date_input")
    with col2:
        end_date = st.date_input("🗓️ 종료월", value=today, key="end_date_input")
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    apt_keyword = st.text_input(
        "🔍 아파트명 조건식",
        key="apt_keyword_input",
        help="예시: 래미안&잠실 | 힐스테이트 -리센츠 (AND:& 또는 and, OR:| 또는 or, 제외:-단어/!단어/not 단어)",
        placeholder="예) 래미안&잠실 | 힐스테이트 -리센츠"
    )
    
    st.divider()
    if HAS_SHADCN_UI:
        run_query = ui.button(text="데이터 조회 실행", key="run_query_btn")
    else:
        run_query = st.button("데이터 조회 실행", type="primary", use_container_width=True)

# --- 조회 로직 ---
if run_query:
    save_user_preferences(
        st.session_state.user_pref_key,
        {
            "trade_type": trade_type,
            "region_input": str(region_input).strip(),
            "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else "",
            "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else "",
            "apt_keyword": str(apt_keyword).strip(),
        }
    )

    if not current_key:
        st.error("❗ 서비스키가 설정되지 않았습니다. Secrets 설정 혹은 수동 입력을 확인하세요.")
    else:
        with st.spinner(f"⚡ {trade_type} 데이터 수집 중..."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}' 지역을 찾을 수 없습니다.")
            else:
                try:
                    api = TransactionPrice(current_key)
                    df = api.get_data(
                        property_type="아파트",
                        trade_type=trade_type,
                        sigungu_code=sigungu_code,
                        start_year_month=start_ym,
                        end_year_month=end_ym
                    )
                    
                    if df is not None and not df.empty:
                        df = standardize_columns(df)
                        
                        target_cols = ['매매가', '보증금', '월세', '전용면적', '층']
                        for col in target_cols:
                            if col in df.columns:
                                df[f'{col}_num'] = df[col].apply(to_numeric_safe)
                        
                        if apt_keyword and '아파트' in df.columns:
                            df = apply_apt_keyword_filter(df, apt_keyword)
                        
                        sort_cols = [c for c in ['년', '월', '일'] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.df_nonce += 1
                        st.session_state.region_name = full_region_name
                        st.session_state.trade_type_val = trade_type
                        
                        # 새로운 데이터를 조회할 때 필터 초기화가 필요하다면 여기서 수행 (요구사항은 유지이므로 생략)
                    else:
                        st.session_state.df = None
                        st.warning(f"⚠️ {full_region_name} 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ API 오류: {e}")
                    st.session_state.df = None

# --- 메인 UI ---
if st.session_state.df is not None:
    raw_df = st.session_state.df.copy()
    current_type = st.session_state.trade_type_val
    
    # Hero Section
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Real Estate Insights</div>
        <div class="hero-subtitle">{st.session_state.region_name} {current_type} 실거래 분석 리포트</div>
    </div>
    """, unsafe_allow_html=True)
    
    filtered_df = raw_df.copy()
    quick_filter_active_count = 0
    col_filter_active_count = 0
    filter_key_prefix = f"list_filter_{st.session_state.df_nonce}"

    # 가공용 컬럼 제거 후 리스트 전체 컬럼 필터를 적용
    fixed_exclude = ['index', 'sggCd', 'umdNm', 'jibun', 'buildYear', 'aptSeq', 'umdCd', 'landCd', 'bonbun', 'bubun', 'cdealType', 'cdealDay', 'estateAgengSggNm', 'buerGbn']
    road_exclude = [c for c in filtered_df.columns if str(c).startswith('road')]
    internal_exclude = [c for c in filtered_df.columns if str(c).endswith('_num')]
    all_drop_cols = list(set(fixed_exclude + road_exclude + internal_exclude))
    actual_drop_cols = [c for c in all_drop_cols if c in filtered_df.columns]

    with st.expander("🎛️ Filter Studio", expanded=False):
        h1, h2 = st.columns([0.8, 0.2])
        with h1:
            st.caption("필터는 접힘 상태로 유지됩니다. 필요할 때만 열어 조정하세요.")
        with h2:
            if st.button("초기화", use_container_width=True, key=f"btn_reset_{st.session_state.df_nonce}"):
                reset_filter_state(filter_key_prefix)
                st.rerun()

        tab_quick, tab_columns = st.tabs(["빠른 필터", "컬럼 필터"])

        with tab_quick:
            c1, c2 = st.columns(2)
            if current_type == "매매":
                if '매매가_num' in raw_df.columns:
                    min_v, max_v = int(raw_df['매매가_num'].min()), int(raw_df['매매가_num'].max())
                    if min_v == max_v:
                        max_v += 1000

                    default_val = st.session_state.filter_deal_price if st.session_state.filter_deal_price else (min_v, max_v)
                    default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))

                    with c1:
                        deal_sel = st.slider("💰 매매가 (만원)", min_v, max_v, default_val, step=1000, key="slider_deal")
                        st.session_state.filter_deal_price = deal_sel
                        if deal_sel[0] > min_v or deal_sel[1] < max_v:
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['매매가_num'].between(deal_sel[0], deal_sel[1])]
            else:
                with c1:
                    if '보증금_num' in raw_df.columns:
                        min_v, max_v = int(raw_df['보증금_num'].min()), int(raw_df['보증금_num'].max())
                        if min_v == max_v:
                            max_v += 100

                        default_val = st.session_state.filter_dep_price if st.session_state.filter_dep_price else (min_v, max_v)
                        default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))

                        dep_sel = st.slider("💰 보증금 (만원)", min_v, max_v, default_val, step=500, key="slider_dep")
                        st.session_state.filter_dep_price = dep_sel
                        if dep_sel[0] > min_v or dep_sel[1] < max_v:
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['보증금_num'].between(dep_sel[0], dep_sel[1])]

                with c2:
                    if '월세_num' in raw_df.columns:
                        min_v, max_v = int(raw_df['월세_num'].min()), int(raw_df['월세_num'].max())
                        if min_v == max_v:
                            max_v += 10

                        default_val = st.session_state.filter_rent_price if st.session_state.filter_rent_price else (min_v, max_v)
                        default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))

                        rent_sel = st.slider("💵 월세 (만원)", min_v, max_v, default_val, step=10, key="slider_rent")
                        st.session_state.filter_rent_price = rent_sel
                        if rent_sel[0] > min_v or rent_sel[1] < max_v:
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['월세_num'].between(rent_sel[0], rent_sel[1])]

            c3, c4 = st.columns(2)
            if '전용면적_num' in raw_df.columns:
                with c3:
                    area_unit = st.radio(
                        "📐 면적 기준",
                        options=["공급면적(평형대)", "전용면적(㎡)"],
                        horizontal=True,
                        key="quick_area_unit"
                    )
                    st.session_state.filter_area_unit = area_unit

                    if area_unit == "공급면적(평형대)":
                        area_series = filtered_df['전용면적_num'].apply(to_supply_pyeong_band)
                        band_order = [label for _, label in SUPPLY_PYEONG_BANDS]
                        options = [b for b in band_order if b in area_series.dropna().unique().tolist()]

                        default_bands = st.session_state.filter_supply_bands if st.session_state.filter_supply_bands else options
                        default_bands = [b for b in default_bands if b in options]
                        if not default_bands:
                            default_bands = options

                        sel_bands = st.multiselect("공급평형대 선택", options=options, default=default_bands, key="ms_supply_bands")
                        st.session_state.filter_supply_bands = sel_bands
                        st.session_state.filter_areas = []
                        if len(sel_bands) != len(options):
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[area_series.isin(sel_bands)]
                    else:
                        area_list = sorted(filtered_df['전용면적_num'].unique())
                        default_areas = st.session_state.filter_areas if st.session_state.filter_areas else area_list
                        default_areas = [a for a in default_areas if a in area_list]
                        if not default_areas:
                            default_areas = area_list

                        sel_areas = st.multiselect("전용면적 (㎡)", options=area_list, default=default_areas, key="ms_areas")
                        st.session_state.filter_areas = sel_areas
                        st.session_state.filter_supply_bands = []
                        if len(sel_areas) != len(area_list):
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['전용면적_num'].isin(sel_areas)]

            if '층_num' in raw_df.columns:
                floor_list = sorted(raw_df['층_num'].unique().astype(int))

                default_floors = st.session_state.filter_floors if st.session_state.filter_floors else floor_list
                default_floors = [f for f in default_floors if f in floor_list]
                if not default_floors:
                    default_floors = floor_list

                with c4:
                    st.markdown("🏢 층수 선택")

                    for floor in floor_list:
                        floor_key = f"{filter_key_prefix}_floor_{floor}"
                        if floor_key not in st.session_state:
                            st.session_state[floor_key] = floor in default_floors

                    btn_col1, btn_col2 = st.columns(2)
                    select_all_floors = btn_col1.button("전체 선택", key=f"{filter_key_prefix}_floor_select_all", use_container_width=True)
                    clear_all_floors = btn_col2.button("전체 해제", key=f"{filter_key_prefix}_floor_clear_all", use_container_width=True)

                    if select_all_floors:
                        for floor in floor_list:
                            st.session_state[f"{filter_key_prefix}_floor_{floor}"] = True
                    elif clear_all_floors:
                        for floor in floor_list:
                            st.session_state[f"{filter_key_prefix}_floor_{floor}"] = False

                    floor_cols = st.columns(3)
                    sel_floors = []
                    for idx, floor in enumerate(floor_list):
                        with floor_cols[idx % 3]:
                            is_checked = st.checkbox(f"{floor}층", key=f"{filter_key_prefix}_floor_{floor}")
                        if is_checked:
                            sel_floors.append(floor)

                    st.session_state.filter_floors = sel_floors
                    if len(sel_floors) != len(floor_list):
                        quick_filter_active_count += 1
                    filtered_df = filtered_df[filtered_df['층_num'].isin(sel_floors)]

        disp_df_base = filtered_df.drop(columns=actual_drop_cols)
        with tab_columns:
            disp_df, col_filter_active_count = apply_all_column_filters(disp_df_base, key_prefix=filter_key_prefix)

    st.caption(f"활성 필터: 빠른 필터 {quick_filter_active_count}개 · 컬럼 필터 {col_filter_active_count}개 · 결과 {len(disp_df):,}건")

    # 리스트 필터 결과 인덱스를 원본 필터 결과에 매핑해 지표도 동일 기준으로 계산
    metric_df = filtered_df.loc[disp_df.index] if not disp_df.empty else filtered_df.iloc[0:0]

    # --- 핵심 지표 및 데이터 출력 ---
    if not metric_df.empty:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card("총 거래", f"{len(metric_df):,}건", "현재 필터 결과", key="metric_total")
        
        if current_type == "매매":
            if '매매가_num' in metric_df.columns:
                with m2:
                    render_metric_card("평균 매매", f"{metric_df['매매가_num'].mean():,.0f}만", "거래 단가 평균", key="metric_avg_sale")
                with m3:
                    render_metric_card("최고 매매", f"{metric_df['매매가_num'].max():,.0f}만", "최고 체결 금액", key="metric_max_sale")
        else:
            if '보증금_num' in metric_df.columns:
                with m2:
                    render_metric_card("평균 보증금", f"{metric_df['보증금_num'].mean():,.0f}만", "보증금 평균", key="metric_avg_dep")
            if '월세_num' in metric_df.columns:
                with m3:
                    render_metric_card("평균 월세", f"{metric_df['월세_num'].mean():,.0f}만", "월세 평균", key="metric_avg_rent")
        
        if '전용면적_num' in metric_df.columns:
            with m4:
                render_metric_card("평균 면적", f"{metric_df['전용면적_num'].mean():,.1f}㎡", "전용면적 평균", key="metric_avg_area")
        
        st.divider()

        st.subheader("📈 기간별 거래 추이")
        render_trade_type_chart(metric_df, current_type)
        if current_type == "전월세":
            st.subheader("🌀 보증금-월세 Polar Scatter")
            render_rental_polar_scatter(metric_df)
        st.divider()
        
        # 최종 리스트 출력
        st.subheader("📋 실거래 내역 리스트")
        render_awesome_table(disp_df)
        
        # 다운로드 버튼
        csv = disp_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Result CSV Download", data=csv, file_name=f"result_{datetime.datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
    else:
        st.warning("조회된 데이터가 없습니다. 필터 조건을 조정해 보세요.")
else:
    # 대기화면 Hero
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">Real Estate Insights</div>
        <div class="hero-subtitle">데이터 기반 아파트 실거래가 분석 대시보드</div>
    </div>
    """, unsafe_allow_html=True)
    st.info("👈 사이드바에서 조회할 지역과 거래 유형을 선택해 주세요.")
