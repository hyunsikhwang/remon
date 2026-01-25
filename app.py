import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime
import re

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Premium 아파트 실거래가 대시보드",
    page_icon="🏢",
    layout="wide"
)

# --- 커스텀 CSS (UI 스타일링 고도화) ---
st.markdown("""
    <style>
    /* 메인 배경색 */
    .main {
        background-color: #f8f9fa;
    }
    
    /* 지표 카드 스타일 */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #edf2f7;
    }
    
    /* 지표 텍스트 스타일 */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        color: #1a365d !important;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        background-color: #2b6cb0;
        color: white;
    }
    
    /* 데이터프레임 여백 조절 */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 상태 초기화 ---
if "df" not in st.session_state:
    st.session_state.df = None
if "region_name" not in st.session_state:
    st.session_state.region_name = ""
if "trade_type" not in st.session_state:
    st.session_state.trade_type = "전월세"

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

# --- 사이드바 ---
with st.sidebar:
    st.title("🏢 Search Portal")
    st.divider()
    
    service_key = st.text_input("🔑 API 인증키", type="password", placeholder="공공데이터포털 서비스키")
    st.divider()
    
    trade_type = st.radio("🏠 거래 유형", ["매매", "전월세"], index=1, horizontal=True)
    region_input = st.text_input("📍 지역명", value="송파구")
    
    today = datetime.date.today()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("🗓️ 시작월", value=datetime.date(today.year, today.month, 1) - datetime.timedelta(days=90))
    with col2:
        end_date = st.date_input("🗓️ 종료월", value=today)
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    apt_keyword = st.text_input("🔍 아파트명 키워드")
    
    st.divider()
    run_query = st.button("🚀 데이터 조회 실행", type="primary")

# --- 조회 로직 ---
if run_query:
    if not service_key:
        st.error("❗ 서비스키를 입력해 주세요.")
    else:
        with st.spinner(f"⚡ {trade_type} 데이터 수집 중..."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}' 지역을 찾을 수 없습니다.")
            else:
                try:
                    api = TransactionPrice(service_key)
                    df = api.get_data(
                        property_type="아파트",
                        trade_type=trade_type,
                        sigungu_code=sigungu_code,
                        start_year_month=start_ym,
                        end_year_month=end_ym
                    )
                    
                    if df is not None and not df.empty:
                        df = standardize_columns(df)
                        
                        # 숫자 변환
                        target_cols = ['매매가', '보증금', '월세', '전용면적', '층']
                        for col in target_cols:
                            if col in df.columns:
                                df[f'{col}_num'] = df[col].apply(to_numeric_safe)
                        
                        # 필터링
                        if apt_keyword and '아파트' in df.columns:
                            df = df[df['아파트'].str.contains(apt_keyword, na=False)]
                        
                        # 정렬
                        sort_cols = [c for c in ['년', '월', '일'] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.region_name = full_region_name
                        st.session_state.trade_type = trade_type
                    else:
                        st.session_state.df = None
                        st.warning(f"⚠️ {full_region_name} 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ API 오류: {e}")

# --- 메인 UI ---
if st.session_state.df is not None:
    raw_df = st.session_state.df.copy()
    current_type = st.session_state.trade_type
    
    st.header(f"📊 {st.session_state.region_name} {current_type} 실거래 분석")
    
    # --- 상세 필터 (내장 컨테이너 사용으로 레이아웃 수정) ---
    with st.container(border=True):
        st.markdown("**🛠️ 상세 필터링 판넬**")
        filtered_df = raw_df.copy()
        
        c1, c2 = st.columns(2)
        if current_type == "매매":
            if '매매가_num' in raw_df.columns:
                min_v, max_v = int(raw_df['매매가_num'].min()), int(raw_df['매매가_num'].max())
                if min_v == max_v: max_v += 1000
                deal_sel = c1.slider("💰 매매가 (만원)", min_v, max_v, (min_v, max_v), step=1000)
                filtered_df = filtered_df[filtered_df['매매가_num'].between(deal_sel[0], deal_sel[1])]
        else:
            if '보증금_num' in raw_df.columns:
                min_v, max_v = int(raw_df['보증금_num'].min()), int(raw_df['보증금_num'].max())
                if min_v == max_v: max_v += 100
                dep_sel = c1.slider("💰 보증금 (만원)", min_v, max_v, (min_v, max_v), step=500)
                filtered_df = filtered_df[filtered_df['보증금_num'].between(dep_sel[0], dep_sel[1])]
            if '월세_num' in raw_df.columns:
                min_v, max_v = int(raw_df['월세_num'].min()), int(raw_df['월세_num'].max())
                if min_v == max_v: max_v += 10
                rent_sel = c2.slider("💵 월세 (만원)", min_v, max_v, (min_v, max_v), step=10)
                filtered_df = filtered_df[filtered_df['월세_num'].between(rent_sel[0], rent_sel[1])]

        c3, c4 = st.columns(2)
        if '전용면적' in raw_df.columns:
            area_list = sorted(raw_df['전용면적_num'].unique())
            sel_areas = c3.multiselect("📐 전용면적 (㎡)", options=area_list, default=area_list)
            filtered_df = filtered_df[filtered_df['전용면적_num'].isin(sel_areas)]

        if '층' in raw_df.columns:
            floor_list = sorted(raw_df['층_num'].unique().astype(int))
            sel_floors = c4.multiselect("🏢 층수 선택", options=floor_list, default=floor_list)
            filtered_df = filtered_df[filtered_df['층_num'].isin(sel_floors)]

    # --- 대시보드 탭 ---
    t1, t2 = st.tabs(["📈 핵심 지표", "📋 거래 목록"])
    
    with t1:
        if not filtered_df.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📊 총 거래", f"{len(filtered_df):,}건")
            
            if current_type == "매매":
                if '매매가_num' in filtered_df.columns:
                    m2.metric("📉 평균 매매", f"{filtered_df['매매가_num'].mean():,.0f}만")
                    m3.metric("📈 최고 매매", f"{filtered_df['매매가_num'].max():,.0f}만")
            else:
                if '보증금_num' in filtered_df.columns:
                    m2.metric("📉 평균 보증금", f"{filtered_df['보증금_num'].mean():,.0f}만")
                if '월세_num' in filtered_df.columns:
                    m3.metric("💵 평균 월세", f"{filtered_df['월세_num'].mean():,.0f}만")
            
            if '전용면적_num' in filtered_df.columns:
                m4.metric("📐 평균 면적", f"{filtered_df['전용면적_num'].mean():,.1f}㎡")
            
            # 차트 에러 방지 (날짜 컬럼 존재 확인)
            st.markdown("#### 최근 가격 추이")
            chart_df = filtered_df.copy()
            
            # 날짜 인덱스 생성 시도
            if all(k in chart_df.columns for k in ['년', '월', '일']):
                chart_df['날짜'] = pd.to_datetime(chart_df[['년', '월', '일']].astype(str).agg('-'.join, axis=1))
                price_col = '매매가_num' if current_type == "매매" else '보증금_num'
                if price_col in chart_df.columns:
                    # 날짜순 정렬 후 표시
                    plot_data = chart_df.sort_values('날짜').set_index('날짜')[price_col]
                    st.area_chart(plot_data, height=250)
            else:
                st.info("차트를 생성하기 위한 날짜 정보('일' 등)가 부족합니다.")
        else:
            st.warning("조회된 데이터가 없습니다.")

    with t2:
        # 가공용 컬럼 제거 후 표시
        disp_df = filtered_df.drop(columns=[c for c in filtered_df.columns if c.endswith('_num')])
        st.dataframe(disp_df, use_container_width=True, height=450)
        
        csv = disp_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 결과 CSV 다운로드", data=csv, file_name=f"result.csv", use_container_width=True)
else:
    st.info("👈 사이드바에서 조회할 지역과 거래 유형을 선택해 주세요.")