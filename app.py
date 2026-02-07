import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime
import re
import html

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
        padding: 0.8rem 0.9rem;
        border-bottom: 1px solid #e5e7eb;
        font-weight: 600;
        white-space: nowrap;
    }
    .modern-table tbody td {
        padding: 0.78rem 0.9rem;
        border-bottom: 1px solid #f1f3f5;
        white-space: nowrap;
    }
    .modern-table tbody tr:hover td {
        background: #f8fafc;
    }
    .modern-table tbody tr:last-child td {
        border-bottom: none;
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

def apply_all_column_filters(df, key_prefix):
    """출력용 데이터프레임의 모든 컬럼에 대해 동적 필터 적용"""
    if df is None or df.empty:
        return df

    st.markdown("**🔎 리스트 전체 컬럼 필터**")
    selected_cols = st.multiselect(
        "필터할 컬럼 선택",
        options=list(df.columns),
        default=[],
        key=f"{key_prefix}_selected_cols"
    )

    if not selected_cols:
        return df

    mask = pd.Series(True, index=df.index)
    for col in selected_cols:
        series = df[col]
        safe_col = re.sub(r'[^0-9a-zA-Z_가-힣]', '_', str(col))

        numeric_series = pd.to_numeric(series, errors='coerce')
        numeric_ratio = numeric_series.notna().mean() if len(series) else 0

        # 숫자로 해석 가능한 컬럼은 범위 필터 제공
        if numeric_ratio >= 0.9 and numeric_series.notna().any():
            min_v = float(numeric_series.min())
            max_v = float(numeric_series.max())

            if min_v == max_v:
                st.caption(f"`{col}`: 단일 값({min_v:g})만 존재하여 필터를 생략합니다.")
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
            mask &= str_series.isin(selected_vals)
        else:
            keyword = st.text_input(
                f"{col} 부분검색",
                value="",
                key=f"{key_prefix}_{safe_col}_keyword",
                placeholder=f"{col}에 포함될 텍스트 입력"
            )
            if keyword:
                mask &= str_series.str.contains(keyword, na=False, case=False)

    return df[mask]

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
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("🗓️ 시작월", value=datetime.date(today.year, today.month, 1) - datetime.timedelta(days=90), key="start_date_input")
    with col2:
        end_date = st.date_input("🗓️ 종료월", value=today, key="end_date_input")
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    apt_keyword = st.text_input("🔍 아파트명 키워드", key="apt_keyword_input")
    
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
                            df = df[df['아파트'].str.contains(apt_keyword, na=False)]
                        
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
    
    # --- 상세 필터 판넬 ---
    with st.container(border=True):
        st.markdown("**🛠️ 상세 필터링**")
        filtered_df = raw_df.copy()
        
        c1, c2 = st.columns(2)
        if current_type == "매매":
            if '매매가_num' in raw_df.columns:
                min_v, max_v = int(raw_df['매매가_num'].min()), int(raw_df['매매가_num'].max())
                if min_v == max_v: max_v += 1000
                
                default_val = st.session_state.filter_deal_price if st.session_state.filter_deal_price else (min_v, max_v)
                default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))
                
                with c1:
                    deal_sel = st.slider("💰 매매가 (만원)", min_v, max_v, default_val, step=1000, key="slider_deal")
                    st.session_state.filter_deal_price = deal_sel
                    filtered_df = filtered_df[filtered_df['매매가_num'].between(deal_sel[0], deal_sel[1])]
        else:
            with c1:
                if '보증금_num' in raw_df.columns:
                    min_v, max_v = int(raw_df['보증금_num'].min()), int(raw_df['보증금_num'].max())
                    if min_v == max_v: max_v += 100
                    
                    default_val = st.session_state.filter_dep_price if st.session_state.filter_dep_price else (min_v, max_v)
                    default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))
                    
                    dep_sel = st.slider("💰 보증금 (만원)", min_v, max_v, default_val, step=500, key="slider_dep")
                    st.session_state.filter_dep_price = dep_sel
                    filtered_df = filtered_df[filtered_df['보증금_num'].between(dep_sel[0], dep_sel[1])]
            
            with c2:
                if '월세_num' in raw_df.columns:
                    min_v, max_v = int(raw_df['월세_num'].min()), int(raw_df['월세_num'].max())
                    if min_v == max_v: max_v += 10
                    
                    default_val = st.session_state.filter_rent_price if st.session_state.filter_rent_price else (min_v, max_v)
                    default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))
                    
                    rent_sel = st.slider("💵 월세 (만원)", min_v, max_v, default_val, step=10, key="slider_rent")
                    st.session_state.filter_rent_price = rent_sel
                    filtered_df = filtered_df[filtered_df['월세_num'].between(rent_sel[0], rent_sel[1])]

        c3, c4 = st.columns(2)
        if '전용면적_num' in raw_df.columns:
            area_list = sorted(raw_df['전용면적_num'].unique())
            
            default_areas = st.session_state.filter_areas if st.session_state.filter_areas else area_list
            default_areas = [a for a in default_areas if a in area_list]
            if not default_areas: default_areas = area_list
            
            with c3:
                sel_areas = st.multiselect("📐 전용면적 (㎡)", options=area_list, default=default_areas, key="ms_areas")
                st.session_state.filter_areas = sel_areas
                filtered_df = filtered_df[filtered_df['전용면적_num'].isin(sel_areas)]

        if '층_num' in raw_df.columns:
            floor_list = sorted(raw_df['층_num'].unique().astype(int))
            
            default_floors = st.session_state.filter_floors if st.session_state.filter_floors else floor_list
            default_floors = [f for f in default_floors if f in floor_list]
            if not default_floors: default_floors = floor_list
            
            with c4:
                sel_floors = st.multiselect("🏢 층수 선택", options=floor_list, default=default_floors, key="ms_floors")
                st.session_state.filter_floors = sel_floors
                filtered_df = filtered_df[filtered_df['층_num'].isin(sel_floors)]

    # 가공용 컬럼 제거 후 리스트 전체 컬럼 필터를 적용
    fixed_exclude = ['index', 'sggCd', 'umdNm', 'jibun', 'buildYear', 'aptSeq', 'umdCd', 'landCd', 'bonbun', 'bubun', 'cdealType', 'cdealDay', 'estateAgengSggNm', 'buerGbn']
    road_exclude = [c for c in filtered_df.columns if str(c).startswith('road')]
    internal_exclude = [c for c in filtered_df.columns if str(c).endswith('_num')]
    all_drop_cols = list(set(fixed_exclude + road_exclude + internal_exclude))
    actual_drop_cols = [c for c in all_drop_cols if c in filtered_df.columns]

    disp_df_base = filtered_df.drop(columns=actual_drop_cols)
    disp_df = apply_all_column_filters(disp_df_base, key_prefix=f"list_filter_{st.session_state.df_nonce}")

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
