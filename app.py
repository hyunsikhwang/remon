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

def get_region_code(region_name):
    """지역명을 입력받아 5자리 시군구 코드를 반환합니다."""
    try:
        bdong = code_bdong()
        # 시군구 단위까지 검색하여 가장 적절한 코드 추출
        code_df = bdong.get_code(region_name)
        if not code_df.empty:
            # 폐지되지 않은 코드 중 가장 적절한 명칭 매칭
            target = code_df[code_df['폐지여부'] == '존재'].iloc[0]
            # 법정동 코드 10자리 중 앞 5자리가 시군구 코드 (MOLIT API 기준)
            return target['법정동코드'][:5], target['법정동명']
        return None, None
    except Exception:
        return None, None

# --- UI 레이아웃 ---
st.title("🏠 아파트 전월세 실거래가 조회")
st.markdown("""
`PublicDataReader` 최신 버전을 사용하여 국토교통부 실거래가 데이터를 조회합니다.
지역명(시군구)을 입력하고 조회 기간을 설정하세요.
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
    region_input = st.text_input("조회 지역명", value="강남구", help="예: 강남구, 성남시 분당구 등")
    
    # 3. 기간 선택
    today = datetime.date.today()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작 월", value=datetime.date(today.year, 1, 1))
    with col2:
        end_date = st.date_input("종료 월", value=today)
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    
    # 4. 필터링 키워드
    apt_keyword = st.text_input("아파트명 키워드 (선택)", placeholder="예: 자이, 래미안")
    
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
                st.error(f"❌ '{region_input}' 지역을 찾을 수 없습니다.")
            else:
                try:
                    # [수정] TransactionReader -> TransactionPrice 로 변경됨
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
                        
                        # 정렬 (년, 월, 일 순)
                        # API 반환 컬럼명 확인 후 정렬 (최신 라이브러리는 컬럼명이 한글로 반환됨)
                        sort_cols = [c for c in ['년', '월', '일'] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.region_name = full_region_name
                    else:
                        st.session_state.df = None
                        st.warning("⚠️ 해당 조건에 맞는 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ 오류 발생: {e}")
                    st.info("서비스키가 올바른지, 또는 공공데이터포털의 API 승인이 완료되었는지 확인하세요.")

# --- 결과 전시 ---
if st.session_state.df is not None:
    df = st.session_state.df
    
    st.subheader(f"📊 {st.session_state.region_name} 조회 결과 (총 {len(df):,}건)")
    
    # 지표 요약 (데이터 타입 변환 후 계산)
    try:
        # 보증금과 월세에서 콤마 제거 및 숫자 변환
        df['보증금'] = df['보증금'].replace({',': ''}, regex=True).astype(int)
        df['월세'] = df['월세'].replace({',': ''}, regex=True).astype(int)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("평균 보증금", f"{df['보증금'].mean():,.0f} 만원")
        c2.metric("평균 월세", f"{df['월세'].mean():,.0f} 만원")
        c3.metric("최대 보증금", f"{df['보증금'].max():,} 만원")
    except:
        pass

    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"result_{start_ym}_{end_ym}.csv",
        mime="text/csv",
    )
elif not run_query:
    st.info("💡 사이드바에서 조건을 입력하고 조회를 시작하세요.")