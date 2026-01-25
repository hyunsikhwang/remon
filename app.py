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
    """
    법정동 코드 데이터를 로드합니다. 
    최신 PublicDataReader 버전에서 code_bdong()은 DataFrame을 직접 반환합니다.
    """
    return code_bdong()

def get_region_code(region_name):
    """지역명을 입력받아 5자리 시군구 코드를 반환합니다."""
    try:
        df = load_bdong_data()
        
        # 1. 입력된 명칭이 포함되고 폐지되지 않은 데이터 필터링
        # 보통 '서울특별시 송파구'와 같은 형태이므로 문자열 포함 여부로 검색
        condition = (df['법정동명'].str.contains(region_name)) & (df['폐지여부'] == '존재')
        filtered_df = df[condition].copy()
        
        if not filtered_df.empty:
            # 2. 국토교통부 API는 5자리 시군구 코드를 사용함
            # 법정동코드 10자리 중 앞 5자리가 시군구 코드임
            # 가장 짧은 법정동명(구청/시청 단위)을 선택하기 위해 정렬
            filtered_df['name_len'] = filtered_df['법정동명'].str.len()
            target = filtered_df.sort_values(by='name_len').iloc[0]
            
            return target['법정동코드'][:5], target['법정동명']
        return None, None
    except Exception as e:
        st.error(f"지역 코드 검색 중 오류가 발생했습니다: {e}")
        return None, None

# --- UI 레이아웃 ---
st.title("🏠 아파트 전월세 실거래가 조회")
st.markdown("""
`PublicDataReader` 라이브러리를 활용하여 국토교통부 실거래가 데이터를 수집합니다.
지역명(예: **송파구**, **성남시 분당구**)을 입력하고 조회 버튼을 눌러주세요.
""")

with st.sidebar:
    st.header("⚙️ 조회 조건 설정")
    
    service_key = st.text_input(
        "공공데이터포털 서비스키",
        type="password",
        help="발급받은 일반 인증키(Encoding/Decoding)를 입력하세요."
    )
    
    st.divider()
    
    region_input = st.text_input("조회 지역명", value="송파구", help="예: 송파구, 강남구, 분당구 등")
    
    # 기간 선택 (최근 3개월 기본값)
    today = datetime.date.today()
    start_default = datetime.date(today.year, today.month, 1) - datetime.timedelta(days=60)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작 월", value=start_default)
    with col2:
        end_date = st.date_input("종료 월", value=today)
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    
    apt_keyword = st.text_input("아파트명 키워드 (선택)", placeholder="예: 엘스, 리센츠")
    
    run_query = st.button("🔍 데이터 조회 실행", use_container_width=True, type="primary")

# --- 메인 조회 로직 ---
if run_query:
    if not service_key:
        st.error("❗ 서비스키를 입력해 주세요.")
    else:
        with st.spinner("데이터를 요청 중입니다..."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}' 지역을 데이터베이스에서 찾을 수 없습니다. (예: 송파구, 송파)")
            else:
                try:
                    # TransactionPrice 인스턴스 생성
                    api = TransactionPrice(service_key)
                    
                    # 실거래가 데이터 수집
                    df = api.get_data(
                        property_type="아파트",
                        trade_type="전월세",
                        sigungu_code=sigungu_code,
                        start_year_month=start_ym,
                        end_year_month=end_ym
                    )
                    
                    if df is not None and not df.empty:
                        # 아파트명 키워드 필터링
                        if apt_keyword:
                            df = df[df['아파트'].str.contains(apt_keyword, na=False)]
                        
                        # 정렬 (최신순)
                        sort_cols = [c for c in ['년', '월', '일'] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.region_name = full_region_name
                    else:
                        st.session_state.df = None
                        st.warning(f"⚠️ {full_region_name} 지역의 {start_ym}~{end_ym} 기간 데이터가 존재하지 않습니다.")
                        
                except Exception as e:
                    st.error(f"❌ API 통신 중 오류 발생: {e}")
                    st.info("서비스키가 승인되었는지, 또는 오타가 없는지 공공데이터포털에서 확인하세요.")

# --- 결과 출력 ---
if st.session_state.df is not None:
    df = st.session_state.df
    
    st.subheader(f"📊 {st.session_state.region_name} 조회 결과 ({len(df):,}건)")
    
    # 지표 요약 및 전처리
    try:
        # 금액 데이터 숫자 변환 (콤마 제거 후 변환)
        def clean_price(x):
            if isinstance(x, str):
                return int(x.replace(',', ''))
            return x

        df['보증금'] = df['보증금'].apply(clean_price)
        df['월세'] = df['월세'].apply(clean_price)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("평균 보증금", f"{df['보증금'].mean():,.0f} 만원")
        c2.metric("평균 월세", f"{df['월세'].mean():,.0f} 만원")
        c3.metric("최고 보증금", f"{df['보증금'].max():,} 만원")
    except Exception as e:
        st.write("요약 지표를 계산할 수 없습니다.")

    # 데이터 테이블
    st.dataframe(df, use_container_width=True)
    
    # 다운로드 기능
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 결과 데이터(CSV) 다운로드",
        data=csv,
        file_name=f"apt_rent_{st.session_state.region_name}_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
elif not run_query:
    st.info("💡 사이드바의 조회 조건을 입력한 후 버튼을 클릭하세요.")