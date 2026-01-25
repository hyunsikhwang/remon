import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime
import re

# --- 페이지 설정 ---
st.set_page_config(
    page_title="아파트 실거래가 조회",
    page_icon="🏠",
    layout="wide"
)

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
    mapping = {
        '아파트': ['단지', '단지명', '건물명', 'aptNm', '아파트'],
        '매매가': ['거래금액', '거래금액(만원)', 'dealAmount', '매매가'],
        '보증금': ['보증금액', '보증금(만원)', 'deposit', '보증금'],
        '월세': ['월세액', '월세(만원)', 'monthlyRent', '월세'],
        '전용면적': ['excluUseAr', '전용면적(㎡)', '면적', '전용면적'],
        '층': ['floor', '층수', '층']
    }
    
    for standard, candidates in mapping.items():
        for col in candidates:
            if col in df.columns:
                df = df.rename(columns={col: standard})
                break
    return df

def to_numeric_safe(x):
    """문자열 숫자를 안전하게 숫자로 변환 (콤마 제거 등)"""
    if pd.isna(x): return 0.0
    val = re.sub(r'[^0-9.]', '', str(x))
    return float(val) if val else 0.0

# --- UI 레이아웃 ---
st.title("🏠 아파트 실거래가 조회 (매매/전월세)")
st.markdown("""
조회 버튼을 눌러 데이터를 먼저 가져오면, 상단에 **상세 필터(금액, 면적, 층)** UI가 나타납니다.
""")

with st.sidebar:
    st.header("⚙️ 조회 조건 설정")
    service_key = st.text_input("공공데이터포털 서비스키", type="password")
    
    st.divider()
    
    # 거래 유형 선택 추가
    trade_type = st.radio("거래 유형", ["매매", "전월세"], index=1, horizontal=True)
    
    region_input = st.text_input("조회 지역명", value="송파구")
    
    today = datetime.date.today()
    start_default = datetime.date(today.year, today.month, 1) - datetime.timedelta(days=90)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작 월", value=start_default)
    with col2:
        end_date = st.date_input("종료 월", value=today)
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    apt_keyword = st.text_input("아파트명 키워드 (선택)")
    run_query = st.button("🔍 데이터 조회 실행", use_container_width=True, type="primary")

# --- 메인 조회 로직 ---
if run_query:
    if not service_key:
        st.error("❗ 서비스키를 입력해 주세요.")
    else:
        with st.spinner(f"{trade_type} 데이터를 수집 중입니다..."):
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
                        
                        # 전처리 (숫자형 컬럼 생성)
                        target_cols = ['매매가', '보증금', '월세', '전용면적', '층']
                        for col in target_cols:
                            if col in df.columns:
                                df[f'{col}_num'] = df[col].apply(to_numeric_safe)
                        
                        # 키워드 필터링
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
                        st.warning(f"⚠️ {full_region_name} ({trade_type})에 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ 데이터 처리 중 오류 발생: {e}")

# --- 결과 및 필터 섹션 ---
if st.session_state.df is not None:
    raw_df = st.session_state.df.copy()
    current_trade_type = st.session_state.trade_type
    
    st.write("---")
    st.subheader(f"🔍 {st.session_state.region_name} {current_trade_type} 상세 필터링")
    
    # 필터용 컨테이너
    with st.container(border=True):
        filtered_df = raw_df.copy()
        
        # 1. 금액 필터 (매매일 때와 전월세일 때 구분)
        if current_trade_type == "매매":
            row1_col1, row1_col2 = st.columns([2, 1]) # 매매가는 넓게
            if '매매가_num' in raw_df.columns:
                min_v = int(raw_df['매매가_num'].min())
                max_v = int(raw_df['매매가_num'].max())
                if min_v == max_v: max_v += 1000
                deal_sel = row1_col1.slider("💰 매매가 범위 (만원)", min_v, max_v, (min_v, max_v), step=1000)
                filtered_df = filtered_df[(filtered_df['매매가_num'] >= deal_sel[0]) & (filtered_df['매매가_num'] <= deal_sel[1])]
        else:
            row1_col1, row1_col2 = st.columns(2)
            # 보증금 필터
            if '보증금_num' in raw_df.columns:
                min_v = int(raw_df['보증금_num'].min())
                max_v = int(raw_df['보증금_num'].max())
                if min_v == max_v: max_v += 100
                dep_sel = row1_col1.slider("💰 보증금 범위 (만원)", min_v, max_v, (min_v, max_v), step=500)
                filtered_df = filtered_df[(filtered_df['보증금_num'] >= dep_sel[0]) & (filtered_df['보증금_num'] <= dep_sel[1])]
            # 월세 필터
            if '월세_num' in raw_df.columns:
                min_v = int(raw_df['월세_num'].min())
                max_v = int(raw_df['월세_num'].max())
                if min_v == max_v: max_v += 10
                rent_sel = row1_col2.slider("💵 월세 범위 (만원)", min_v, max_v, (min_v, max_v), step=10)
                filtered_df = filtered_df[(filtered_df['월세_num'] >= rent_sel[0]) & (filtered_df['월세_num'] <= rent_sel[1])]

        st.divider()
        row2_col1, row2_col2 = st.columns(2)
        
        # 2. 전용면적 필터 (Multi-select)
        if '전용면적' in raw_df.columns:
            area_list = sorted(raw_df['전용면적_num'].unique())
            selected_areas = row2_col1.multiselect("📐 전용면적 선택 (㎡)", options=area_list, default=area_list)
            filtered_df = filtered_df[filtered_df['전용면적_num'].isin(selected_areas)]

        # 3. 층 필터 (Multi-select)
        if '층' in raw_df.columns:
            floor_list = sorted(raw_df['층_num'].unique().astype(int))
            selected_floors = row2_col2.multiselect("🏢 층수 선택", options=floor_list, default=floor_list)
            filtered_df = filtered_df[filtered_df['층_num'].isin(selected_floors)]

    # --- 요약 지표 ---
    st.write("")
    m1, m2, m3, m4 = st.columns(4)
    if not filtered_df.empty:
        m1.metric("검색 결과", f"{len(filtered_df):,} 건")
        
        if current_trade_type == "매매":
            if '매매가_num' in filtered_df.columns:
                m2.metric("평균 매매가", f"{filtered_df['매매가_num'].mean():,.0f} 만원")
            m3.metric("최고 매매가", f"{filtered_df['매매가_num'].max():,.0f} 만원" if '매매가_num' in filtered_df else "-")
        else:
            if '보증금_num' in filtered_df.columns:
                m2.metric("평균 보증금", f"{filtered_df['보증금_num'].mean():,.0f} 만원")
            if '월세_num' in filtered_df.columns:
                m3.metric("평균 월세", f"{filtered_df['월세_num'].mean():,.0f} 만원")
        
        if '전용면적_num' in filtered_df.columns:
            m4.metric("평균 면적", f"{filtered_df['전용면적_num'].mean():,.1f} ㎡")
            
        # 데이터 출력
        display_df = filtered_df.drop(columns=[c for c in filtered_df.columns if c.endswith('_num')])
        st.dataframe(display_df, use_container_width=True)
        
        csv = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 {current_trade_type} 결과 다운로드", data=csv, file_name=f"{current_trade_type}_data.csv", mime="text/csv")
    else:
        st.warning("선택하신 필터 조건에 일치하는 데이터가 없습니다.")

elif not run_query:
    st.info("💡 사이드바에서 [거래 유형]을 선택하고 지역과 기간을 설정한 후 [조회 실행] 버튼을 눌러주세요.")