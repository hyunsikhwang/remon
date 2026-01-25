import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime

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
    """법정동 코드 데이터를 캐싱하여 로드합니다."""
    return code_bdong()

def get_region_code(region_name):
    """지역명을 입력받아 5자리 시군구 코드를 반환합니다."""
    try:
        bdong = load_bdong_data()
        df = bdong.code
        
        # 1. 입력된 지역명이 포함되어 있고, 폐지되지 않은 데이터 필터링
        condition = (df['법정동명'].str.contains(region_name)) & (df['폐지여부'] == '존재')
        code_df = df[condition].copy()
        
        if not code_df.empty:
            # 2. 시군구 코드(5자리)를 추출하기 위해 가장 상위 단계(보통 끝이 00000으로 끝남)를 우선 선택
            # 법정동코드 예: 1171000000 (송파구 전체)
            sigungu_candidates = code_df[code_df['법정동코드'].str.endswith('00000')]
            
            if not sigungu_candidates.empty:
                target = sigungu_candidates.iloc[0]
            else:
                target = code_df.iloc[0]
                
            return target['법정동코드'][:5], target['법정동명']
        return None, None
    except Exception as e:
        st.error(f"지역 코드 로드 중 오류: {e}")
        return None, None

# --- UI 레이아웃 ---
st.title("🏠 아파트 전월세 실거래가 조회")
st.markdown("""
`PublicDataReader`를 사용하여 국토교통부 실거래가 데이터를 조회합니다.
지역명(예: **송파구**, **강남구**, **성남시 분당구**)을 입력하세요.
""")

with st.sidebar:
    st.header("⚙️ 설정 및 조회 조건")
    
    # 1. 서비스키 입력
    service_key = st.text_input(
        "공공데이터포털 서비스키",
        type="password",
        help="공공데이터포털에서 발급받은 인증키를 입력하세요."
    )
    
    st.divider()
    
    # 2. 지역 선택
    region_input = st.text_input("조회 지역명", value="송파구", help="예: 송파구, 강남구, 분당구 등")
    
    # 3. 기간 선택
    today = datetime.date.today()
    col1, col2 = st.columns(2)
    with col1:
        # 기본값을 이번 달로 설정
        start_date = st.date_input("시작 월", value=datetime.date(today.year, today.month, 1))
    with col2:
        end_date = st.date_input("종료 월", value=today)
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    
    # 4. 필터링 키워드
    apt_keyword = st.text_input("아파트명 키워드 (선택)", placeholder="예: 엘스, 리센츠")
    
    # 조회 버튼
    run_query = st.button("🔍 데이터 조회 실행", use_container_width=True, type="primary")

# --- 메인 로직 ---
if run_query:
    if not service_key:
        st.error("❗ 서비스키를 입력해 주세요.")
    else:
        with st.spinner("데이터를 가져오는 중입니다..."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}' 지역을 찾을 수 없습니다. 명칭을 확인해 주세요 (예: 송파, 송파구).")
            else:
                try:
                    # TransactionPrice 인스턴스 생성
                    api = TransactionPrice(service_key)
                    
                    # 데이터 조회
                    df = api.get_data(
                        property_type="아파트",
                        trade_type="전월세",
                        sigungu_code=sigungu_code,
                        start_year_month=start_ym,
                        end_year_month=end_ym
                    )
                    
                    if df is not None and not df.empty:
                        # 키워드 필터링
                        if apt_keyword:
                            df = df[df['아파트'].str.contains(apt_keyword, na=False)]
                        
                        # 정렬 컬럼 확인 및 정렬
                        sort_cols = [c for c in ['년', '월', '일'] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.region_name = full_region_name
                    else:
                        st.session_state.df = None
                        st.warning(f"⚠️ {full_region_name} ({start_ym}~{end_ym}) 기간에 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ API 조회 오류: {e}")
                    st.info("서비스키가 유효한지, 그리고 공공데이터포털에서 '아파트 전월세 실거래 자료' API 신청이 승인되었는지 확인하세요.")

# --- 결과 전시 ---
if st.session_state.df is not None:
    df = st.session_state.df
    
    st.subheader(f"📊 {st.session_state.region_name} 조회 결과 (총 {len(df):,}건)")
    
    # 지표 요약
    try:
        # 데이터 정제: 숫자형 변환
        df['보증금'] = pd.to_numeric(df['보증금'].toString().replace(',', ''), errors='coerce').fillna(0).astype(int)
        df['월세'] = pd.to_numeric(df['월세'].toString().replace(',', ''), errors='coerce').fillna(0).astype(int)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("평균 보증금", f"{df['보증금'].mean():,.0f} 만원")
        c2.metric("평균 월세", f"{df['월세'].mean():,.0f} 만원")
        c3.metric("최고 보증금", f"{df['보증금'].max():,} 만원")
    except:
        pass

    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"apt_rent_{st.session_state.region_name}_{start_ym}.csv",
        mime="text/csv",
    )
elif not run_query:
    st.info("💡 사이드바에 정보를 입력하고 조회를 클릭하세요.")