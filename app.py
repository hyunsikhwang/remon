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
    """
    법정동 코드 데이터를 로드합니다. 
    사용자 환경의 컬럼 구성: ['시도코드', '시도명', '시군구코드', '시군구명', '법정동코드', '읍면동명', '동리명', '생성일자', '말소일자']
    """
    try:
        return code_bdong()
    except Exception as e:
        st.error(f"법정동 데이터를 불러올 수 없습니다: {e}")
        return pd.DataFrame()

def get_region_code(region_name):
    """지역명을 입력받아 5자리 시군구 코드를 반환합니다."""
    try:
        df = load_bdong_data()
        if df.empty:
            return None, None
        
        # 1. 활성 상태인 지역만 필터링 (말소일자가 없는 데이터)
        # 문자열 'NaN', 결측치, 빈 문자열 모두 체크
        active_df = df[df['말소일자'].isna() | (df['말소일자'] == '')].copy()
        
        # 2. 검색 대상 컬럼에서 지역명 찾기 (시군구명 또는 읍면동명)
        # 사용자가 '송파'라고 입력하면 '시군구명'에서 찾고, '잠실'이라고 입력하면 '읍면동명'에서 찾음
        mask = (active_df['시군구명'].str.contains(region_name, na=False)) | \
               (active_df['읍면동명'].str.contains(region_name, na=False))
        
        results = active_df[mask]
        
        if not results.empty:
            # 검색 결과 중 가장 상위 단계(대표성 있는 행) 선택
            # 보통 읍면동명이 비어있거나 시군구명만 있는 행이 대표 행임
            target = results.iloc[0]
            
            # 국토교통부 실거래가 API는 5자리 '시군구코드'를 요구함
            # 사용자 데이터에 '시군구코드' 컬럼이 존재하므로 이를 바로 사용
            sigungu_code = str(target['시군구코드'])
            
            # 전체 지역 명칭 생성
            full_name = f"{target['시도명']} {target['시군구명']}"
            return sigungu_code, full_name
        
        return None, None
    except Exception as e:
        st.error(f"지역 코드 검색 중 오류: {e}")
        return None, None

# --- UI 레이아웃 ---
st.title("🏠 아파트 전월세 실거래가 조회")
st.markdown("""
`PublicDataReader`를 활용하여 국토교통부 실거래가 데이터를 수집합니다.
지역명(예: **송파구**, **강남**, **분당**)을 입력하고 조회 버튼을 눌러주세요.
""")

with st.sidebar:
    st.header("⚙️ 조회 조건 설정")
    
    service_key = st.text_input(
        "공공데이터포털 서비스키",
        type="password",
        help="발급받은 일반 인증키(Encoding/Decoding)를 입력하세요."
    )
    
    st.divider()
    
    region_input = st.text_input("조회 지역명", value="송파구", help="예: 송파구, 서초구 등")
    
    # 기간 선택 (최근 3개월 기본값)
    today = datetime.date.today()
    start_default = datetime.date(today.year, today.month, 1) - datetime.timedelta(days=90)
    
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
        with st.spinner("지역 정보를 확인하고 데이터를 수집 중입니다..."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}' 지역을 찾을 수 없습니다. (예: 송파, 강남구)")
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
                        st.warning(f"⚠️ {full_region_name} 지역의 {start_ym}~{end_ym} 기간 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ API 조회 중 오류 발생: {e}")
                    st.info("서비스키 승인 상태를 확인하세요. (동기화에 1~2시간이 소요될 수 있습니다)")

# --- 결과 출력 ---
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    
    st.subheader(f"📊 {st.session_state.region_name} 조회 결과 ({len(df):,}건)")
    
    # 지표 요약 및 전처리
    try:
        def to_int(x):
            if pd.isna(x): return 0
            val = re.sub(r'[^0-9]', '', str(x))
            return int(val) if val else 0

        df['보증금_int'] = df['보증금'].apply(to_int)
        df['월세_int'] = df['월세'].apply(to_int)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("평균 보증금", f"{df['보증금_int'].mean():,.0f} 만원")
        c2.metric("평균 월세", f"{df['월세_int'].mean():,.0f} 만원")
        c3.metric("최고 보증금", f"{df['보증금_int'].max():,} 만원")
        
        # 보조 계산용 컬럼 제거 후 표시
        display_df = df.drop(columns=['보증금_int', '월세_int'])
    except:
        display_df = df

    st.dataframe(display_df, use_container_width=True)
    
    # 다운로드 기능
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 결과 데이터(CSV) 다운로드",
        data=csv,
        file_name=f"apt_rent_{st.session_state.region_name}_{start_ym}.csv",
        mime="text/csv",
    )
elif not run_query:
    st.info("💡 사이드바에 정보를 입력하고 조회를 클릭하세요.")