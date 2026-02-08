import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime
import re
import html
import math
try:
    from pyecharts import options as opts
    from pyecharts.charts import Line, Bar
    from streamlit_echarts import st_pyecharts
    HAS_PYECHARTS = True
except ModuleNotFoundError:
    opts = None
    Line = None
    Bar = None
    st_pyecharts = None
    HAS_PYECHARTS = False

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Premium 아파트 실거래가 대시보드",
    page_icon="🏢",
    layout="wide"
)

# --- 커스텀 CSS (Value Horizon UI 스타일) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* 컨테이너 최적화 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1100px !important;
    }
    
    /* 헤더 영역 투명화 및 불필요 요소 숨김 (사이드바 토글 버튼은 유지) */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }
    .stDeployButton, #MainMenu {
        display: none !important;
    }

    /* 전역 스타일 */
    .stApp {
        background-color: #ffffff;
        color: #1a1a1a;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Hero Section */
    .hero-container {
        padding: 2rem 0;
        text-align: center;
        border-bottom: 1px solid #f5f5f5;
        margin-bottom: 2.5rem;
    }

    .hero-title {
        font-size: 2.4rem;
        font-weight: 700;
        color: #111111;
        margin-bottom: 0.5rem;
        letter-spacing: -0.8px;
    }

    .hero-subtitle {
        font-size: 1rem;
        font-weight: 400;
        color: #666666;
    }

    /* Metric Card 스타일 수정 */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid #eaeaea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        transition: all 0.2s ease;
    }
    
    [data-testid="stMetric"]:hover {
        border-color: #007aff;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #888888 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #111111 !important;
    }

    /* 버튼 스타일 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        background-color: #007aff;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #0063d1;
        box-shadow: 0 4px 8px rgba(0,122,255,0.2);
    }

    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #fcfcfc;
        border-right: 1px solid #f0f0f0;
    }

    /* 컨테이너 보더 강제 적용 (레이아웃 버그 방지) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #eeeeee !important;
        border-radius: 12px !important;
        padding: 20px !important;
        background-color: #fdfdfd !important;
        margin-bottom: 2rem !important;
    }

    /* 위젯 간격 조정 */
    .stSlider, .stMultiSelect {
        margin-bottom: 1rem !important;
    }

    /* 실거래 리스트 모던 테이블 */
    .modern-table-wrap {
        border: 1px solid #e9ecef;
        border-radius: 12px;
        overflow: auto;
        max-height: 550px;
        background: #ffffff;
    }
    .modern-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.9rem;
        color: #1f2937;
    }
    .modern-table thead th {
        position: sticky;
        top: 0;
        z-index: 2;
        background: #f8fafc;
        color: #374151;
        text-align: left;
        padding: 0.64rem 0.82rem;
        border-bottom: 1px solid #e5e7eb;
        font-weight: 600;
        white-space: nowrap;
        font-size: 0.85rem;
    }
    .modern-table tbody td {
        padding: 0.52rem 0.82rem;
        border-bottom: 1px solid #f1f3f5;
        white-space: nowrap;
        font-size: 0.84rem;
        line-height: 1.25;
    }
    .modern-table tbody tr:hover td {
        background: #f8fafc;
    }
    .modern-table tbody tr:last-child td {
        border-bottom: none;
    }

    /* Filter Studio 미니멀 스타일 */
    [data-testid="stExpander"] {
        border: 1px solid #eceff3 !important;
        border-radius: 12px !important;
        background: #ffffff !important;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600;
        color: #1f2937;
    }
    [data-testid="stTabs"] [role="tab"] {
        border-radius: 8px !important;
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

def render_modern_table(df):
    """실거래 리스트를 모던 HTML 테이블로 렌더링"""
    if df is None or df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    safe_df = df.copy().fillna("")
    headers = "".join(f"<th>{html.escape(str(c))}</th>" for c in safe_df.columns)
    rows = []
    for row in safe_df.itertuples(index=False, name=None):
        cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        rows.append(f"<tr>{cells}</tr>")
    body = "".join(rows)

    st.markdown(
        f"""
        <div class="modern-table-wrap">
            <table class="modern-table">
                <thead><tr>{headers}</tr></thead>
                <tbody>{body}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True
    )

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

    chart_mode = st.radio(
        "차트 모드",
        options=["기본", "Line Race"],
        horizontal=True,
        key=f"chart_mode_{trade_type}"
    )

    all_values = []
    for apt in pivot.columns.tolist():
        vals = pivot[apt].round(1).tolist()
        all_values.extend([v for v in vals if pd.notna(v)])
    val_min, val_max = axis_bounds(all_values, 0.12)

    if chart_mode == "Line Race":
        race = Line()
        race.add_xaxis(x_data)
        for apt in pivot.columns.tolist():
            values = pivot[apt].round(1).tolist()
            line_values = [None if pd.isna(v) else float(v) for v in values]
            race.add_yaxis(
                f"{apt}",
                line_values,
                is_smooth=True,
                symbol="none",
                is_connect_nones=True,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=2.8),
                is_symbol_show=False,
            )

        race.set_global_opts(
            title_opts=opts.TitleOpts(
                title=f"Line Race ({'전월세' if trade_type == '전월세' else '매매'})",
                subtitle=f"지표: {metric_choice} · 아파트별 월평균"
            ),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            legend_opts=opts.LegendOpts(pos_top="4%", type_="scroll"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(name=y_axis_name, type_="value", min_=val_min, max_=val_max),
            datazoom_opts=[
                opts.DataZoomOpts(type_="inside", range_start=0, range_end=100),
                opts.DataZoomOpts(type_="slider", range_start=0, range_end=100)
            ],
        )
        st_pyecharts(race, height="500px")
        return

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

# --- 사이드바 ---
with st.sidebar:
    st.markdown('<div style="font-size: 1.5rem; font-weight: 700; color: #111111; margin-bottom: 0.5rem;">🏢 Search Portal</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.85rem; color: #888888; margin-bottom: 1.5rem;">실거래가 데이터 조회</div>', unsafe_allow_html=True)
    
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
    run_query = st.button("데이터 조회 실행", type="primary", use_container_width=True)

# --- 조회 로직 ---
if run_query:
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
                    sel_floors = st.multiselect("🏢 층수 선택", options=floor_list, default=default_floors, key="ms_floors")
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
        m1.metric("📊 총 거래", f"{len(metric_df):,}건")
        
        if current_type == "매매":
            if '매매가_num' in metric_df.columns:
                m2.metric("📉 평균 매매", f"{metric_df['매매가_num'].mean():,.0f}만")
                m3.metric("📈 최고 매매", f"{metric_df['매매가_num'].max():,.0f}만")
        else:
            if '보증금_num' in metric_df.columns:
                m2.metric("📉 평균 보증금", f"{metric_df['보증금_num'].mean():,.0f}만")
            if '월세_num' in metric_df.columns:
                m3.metric("💵 평균 월세", f"{metric_df['월세_num'].mean():,.0f}만")
        
        if '전용면적_num' in metric_df.columns:
            m4.metric("📐 평균 면적", f"{metric_df['전용면적_num'].mean():,.1f}㎡")
        
        st.divider()

        st.subheader("📈 기간별 거래 추이")
        render_trade_type_chart(metric_df, current_type)
        st.divider()
        
        # 최종 리스트 출력
        st.subheader("📋 실거래 내역 리스트")
        render_modern_table(disp_df)
        
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
