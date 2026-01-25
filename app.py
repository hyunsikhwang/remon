import streamlit as st
import pandas as pd
from PublicDataReader import TransactionReader, code_bdong
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

def get_region_code(region_name):
    """지역명을 입력받아 5자리 시군구 코드를 반환합니다."""
    try:
        bdong = code_bdong()
        # 시군구 단위까지 검색하여 가장 적절한 코드 추출
        code_df = bdong.get_code(region_name)
        # 법정동 코드 10자리 중 앞 5자리가 시군구 코드 (MOLIT API 기준)
        if not code_df.empty:
            # 폐지되지 않은 코드 중 가장 짧은 명칭 매칭 (보통 시군구 본청)
            target = code_df[code_df['폐지여부'] == '존재'].iloc[0]
            return target['법정동코드'][:5], target['법정동명']
        return None, None
    except Exception:
        return None, None

# --- UI 레이아웃 ---
st.title("🏠 아파트 전월세 실거래가 조회")
st.markdown("""
`PublicDataReader` 라이브러리를 사용하여 국토교통부 실거래가 데이터를 편리하게 조회합니다.
지역명(시군구)을 입력하고 조회 기간을 설정하세요.
""")

with st.sidebar:
    st.header("⚙️ 설정 및 조회 조건")
    
    # 1. 서비스키 입력
    service_key = st.text_input(
        "공공데이터포털 서비스키",
        type="password",
        help="공공데이터포털(data.go.kr)에서 발급받은 '주택실거래가' 관련 일반 인증키(Encoding/Decoding)를 입력하세요."
    )
    
    st.divider()
    
    # 2. 지역 선택 (법정동 코드 대신 지명 입력 가능하도록 개선)
    region_input = st.text_input("조회 지역명", value="강남구", help="예: 강남구, 서초구, 수지구, 용인시 처인구 등")
    
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
        with st.spinner("지역 코드를 확인하고 데이터를 가져오는 중입니다..."):
            # 지역 코드로 변환
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}'에 해당하는 지역 코드를 찾을 수 없습니다. 지역명을 정확히 입력해 주세요.")
            else:
                try:
                    # PublicDataReader를 이용한 데이터 조회
                    # TransactionReader는 내부적으로 루프를 돌며 월별 데이터를 수집합니다.
                    api = TransactionReader(service_key)
                    
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
                        
                        # 데이터 정렬 및 정리
                        df = df.sort_values(by=['년', '월', '일'], ascending=False).reset_index(drop=True)
                        st.session_state.df = df
                        st.session_state.region_name = full_region_name
                    else:
                        st.session_state.df = None
                        st.warning("⚠️ 해당 조건에 맞는 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ 데이터 조회 중 오류가 발생했습니다: {e}")

# --- 결과 전시 ---
if st.session_state.df is not None:
    df = st.session_state.df
    region_info = st.session_state.region_name
    
    st.subheader(f"📊 {region_info} 조회 결과 (총 {len(df):,}건)")
    
    # 지표 요약
    c1, c2, c3 = st.columns(3)
    avg_deposit = df['보증금'].astype(int).mean()
    avg_rent = df['월세'].astype(int).mean()
    c1.metric("평균 보증금", f"{avg_deposit:,.0f} 만원")
    c2.metric("평균 월세", f"{avg_rent:,.0f} 만원")
    c3.metric("최근 거래일", f"{df.iloc[0]['년']}-{df.iloc[0]['월']}-{df.iloc[0]['일']}")

    # 데이터프레임 표시
    st.dataframe(df, use_container_width=True)
    
    # 다운로드 버튼
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV 데이터 다운로드",
        data=csv,
        file_name=f"apt_rent_{start_ym}_{end_ym}.csv",
        mime="text/csv",
    )
else:
    if not run_query:
        st.info("💡 사이드바에서 조회 조건을 설정한 후 '조회 실행' 버튼을 클릭하세요.")

# --- 하단 안내 ---
st.divider()
st.caption("본 앱은 PublicDataReader 라이브러리를 활용하여 공공데이터포털 실거래가 API 데이터를 시각화합니다.")