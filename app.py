import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime
import re

# --- 페이지 설정 ---
st.set_page_config(
    page_title="아파트 전월세 실거래가 조회",
    page_icon="🏠",
    layout="wide"
)

# --- 세션 상태 초기화 ---
if "df" not in st.session_state:
    st.session_state.df = None
if "region_name" not in st.session_state:
    st.session_state.region_name = ""

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
    # 아파트 이름 관련 컬럼 매핑 (aptNm 추가)
    apt_cols = ['단지', '아파트', '단지명', '건물명', 'aptNm']
    for col in apt_cols:
        if col in df.columns:
            df = df.rename(columns={col: '아파트'})
            break
            
    # 보증금 관련 컬럼 매핑
    deposit_cols = ['보증금', '보증금액', '보증금(만원)', 'deposit']
    for col in deposit_cols:
        if col in df.columns:
            df = df.rename(columns={col: '보증금'})
            break
            
    # 월세 관련 컬럼 매핑
    rent_cols = ['월세', '월세액', '월세(만원)', 'monthlyRent']
    for col in rent_cols:
        if col in df.columns:
            df = df.rename(columns={col: '월세'})
            break
            
    return df

# --- UI 레이아웃 ---
st.title("🏠 아파트 전월세 실거래가 조회")
st.markdown("""
`PublicDataReader`를 활용하여 실거래가 데이터를 수집합니다.
지역명(예: **송파구**, **강남**, **분당**)을 입력하고 조회 버튼을 눌러주세요.
""")

with st.sidebar:
    st.header("⚙️ 조회 조건 설정")
    service_key = st.text_input("공공데이터포털 서비스키", type="password")
    st.divider()
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
        with st.spinner("데이터를 수집 중입니다..."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}' 지역을 찾을 수 없습니다.")
            else:
                try:
                    api = TransactionPrice(service_key)
                    df = api.get_data(
                        property_type="아파트",
                        trade_type="전월세",
                        sigungu_code=sigungu_code,
                        start_year_month=start_ym,
                        end_year_month=end_ym
                    )
                    
                    if df is not None and not df.empty:
                        # 컬럼명 표준화 (aptNm -> 아파트)
                        df = standardize_columns(df)
                        
                        # 키워드 필터링
                        if apt_keyword and '아파트' in df.columns:
                            df = df[df['아파트'].str.contains(apt_keyword, na=False)]
                        
                        # 정렬
                        sort_cols = [c for c in ['년', '월', '일'] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.region_name = full_region_name
                    else:
                        st.session_state.df = None
                        st.warning(f"⚠️ {full_region_name}에 해당 기간 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ 데이터 처리 중 오류 발생: {e}")
                    if 'df' in locals() and df is not None:
                        st.info(f"수신된 컬럼명: {list(df.columns)}")

# --- 결과 출력 ---
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    st.subheader(f"📊 {st.session_state.region_name} 조회 결과 ({len(df):,}건)")
    
    try:
        def to_int(x):
            if pd.isna(x): return 0
            val = re.sub(r'[^0-9]', '', str(x))
            return int(val) if val else 0

        if '보증금' in df.columns:
            df['보증금_int'] = df['보증금'].apply(to_int)
            c1, c2, c3 = st.columns(3)
            c1.metric("평균 보증금", f"{df['보증금_int'].mean():,.0f} 만원")
            if '월세' in df.columns:
                df['월세_int'] = df['월세'].apply(to_int)
                c2.metric("평균 월세", f"{df['월세_int'].mean():,.0f} 만원")
            c3.metric("최고 보증금", f"{df['보증금_int'].max():,} 만원")
            
            display_df = df.drop(columns=[c for c in ['보증금_int', '월세_int'] if c in df.columns])
        else:
            display_df = df
    except:
        display_df = df

    st.dataframe(display_df, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 CSV 다운로드", data=csv, file_name=f"result_{start_ym}.csv", mime="text/csv")
elif not run_query:
    st.info("💡 사이드바에 정보를 입력하고 조회를 클릭하세요.")