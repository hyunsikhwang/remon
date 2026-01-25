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
    최신 PublicDataReader 버전에서 code_bdong()은 DataFrame을 직접 반환합니다.
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
        
        # 컬럼 이름이 버전에 따라 다를 수 있으므로 포함된 단어로 컬럼 탐색
        col_name = next((c for c in df.columns if '법정동명' in c or '명칭' in c), None)
        col_code = next((c for c in df.columns if '법정동코드' in c or '코드' in c), None)
        col_exist = next((c for c in df.columns if '폐지여부' in c), None)
        
        if not col_name or not col_code:
            st.error(f"데이터프레임 컬럼을 찾을 수 없습니다. (보유 컬럼: {list(df.columns)})")
            return None, None

        # 1. 입력된 명칭이 포함되고 폐지되지 않은 데이터 필터링
        condition = (df[col_name].str.contains(region_name, na=False))
        if col_exist:
            condition &= (df[col_exist] == '존재')
            
        filtered_df = df[condition].copy()
        
        if not filtered_df.empty:
            # 2. 시군구 단위(앞 5자리)를 정확히 추출하기 위해 이름 길이가 짧은 순으로 정렬
            # 예: '송파구' 검색 시 '서울특별시 송파구'가 '서울특별시 송파구 잠실동'보다 먼저 오게 함
            filtered_df['name_len'] = filtered_df[col_name].str.len()
            target = filtered_df.sort_values(by='name_len').iloc[0]
            
            # 국토교통부 API는 법정동코드 10자리 중 앞 5자리(시군구)를 사용함
            full_code = str(target[col_code])
            return full_code[:5], target[col_name]
        
        return None, None
    except Exception as e:
        st.error(f"지역 코드 검색 중 오류가 발생했습니다: {e}")
        return None, None

# --- UI 레이아웃 ---
st.title("🏠 아파트 전월세 실거래가 조회")
st.markdown("""
`PublicDataReader`를 활용하여 실시간 아파트 실거래가(전월세) 데이터를 조회합니다.
지역명(예: **송파**, **분당**, **수지**)을 입력하고 조회 버튼을 눌러주세요.
""")

with st.sidebar:
    st.header("⚙️ 조회 조건 설정")
    
    service_key = st.text_input(
        "공공데이터포털 서비스키",
        type="password",
        help="발급받은 일반 인증키(Encoding/Decoding)를 입력하세요."
    )
    
    st.divider()
    
    region_input = st.text_input("조회 지역명", value="송파구", help="구 단위로 입력하는 것이 정확합니다.")
    
    # 기간 선택 (기본값: 최근 3개월)
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
        with st.spinner("지역 코드를 찾고 데이터를 요청 중입니다..."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"❌ '{region_input}' 지역을 찾을 수 없습니다. (정확한 지명을 입력해 보세요)")
            else:
                try:
                    # TransactionPrice 클래스 사용
                    api = TransactionPrice(service_key)
                    
                    # API 호출
                    df = api.get_data(
                        property_type="아파트",
                        trade_type="전월세",
                        sigungu_code=sigungu_code,
                        start_year_month=start_ym,
                        end_year_month=end_ym
                    )
                    
                    if df is not None and not df.empty:
                        # 아파트명 필터링
                        if apt_keyword:
                            df = df[df['아파트'].str.contains(apt_keyword, na=False)]
                        
                        # 최신순 정렬
                        sort_cols = [c for c in ['년', '월', '일'] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.region_name = full_region_name
                    else:
                        st.session_state.df = None
                        st.warning(f"⚠️ {full_region_name} ({start_ym}~{end_ym}) 기간에 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ API 오류: {e}")
                    st.info("서비스키 승인 상태를 확인하거나 잠시 후 다시 시도하세요.")

# --- 결과 출력 ---
if st.session_state.df is not None:
    df = st.session_state.df.copy()
    
    st.subheader(f"📊 {st.session_state.region_name} 조회 결과 ({len(df):,}건)")
    
    # 금액 데이터 전처리 및 지표 계산
    try:
        def to_int(x):
            if pd.isna(x): return 0
            # 숫자 외 문자 제거 (콤마 등)
            val = re.sub(r'[^0-9]', '', str(x))
            return int(val) if val else 0

        df['보증금_int'] = df['보증금'].apply(to_int)
        df['월세_int'] = df['월세'].apply(to_int)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("평균 보증금", f"{df['보증금_int'].mean():,.0f} 만원")
        c2.metric("평균 월세", f"{df['월세_int'].mean():,.0f} 만원")
        c3.metric("최고 보증금", f"{df['보증금_int'].max():,} 만원")
        
        # 보조 컬럼은 제거하고 표시
        display_df = df.drop(columns=['보증금_int', '월세_int'])
    except:
        display_df = df

    st.dataframe(display_df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"apt_rent_{st.session_state.region_name}.csv",
        mime="text/csv",
    )
elif not run_query:
    st.info("💡 왼쪽 사이드바에서 조회 조건을 입력하고 버튼을 클릭하세요.")