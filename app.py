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
    # 컬럼 매핑 사전
    mapping = {
        '아파트': ['단지', '단지명', '건물명', 'aptNm', '아파트'],
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
                        # 컬럼명 표준화
                        df = standardize_columns(df)
                        
                        # 숫자형 데이터 전처리 (필터링을 위해 미리 수행)
                        for col in ['보증금', '월세', '전용면적', '층']:
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
                    else:
                        st.session_state.df = None
                        st.warning(f"⚠️ {full_region_name}에 해당 기간 데이터가 없습니다.")
                        
                except Exception as e:
                    st.error(f"❌ 데이터 처리 중 오류 발생: {e}")

# --- 결과 및 필터 섹션 ---
if st.session_state.df is not None:
    raw_df = st.session_state.df.copy()
    
    st.subheader(f"📊 {st.session_state.region_name} 조회 결과")

    # --- 필터 레이아웃 ---
    with st.expander("🔍 상세 필터 조건 설정 (전용면적, 금액, 층수)", expanded=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        
        # 필터링용 데이터 복사
        filtered_df = raw_df.copy()
        
        # 1. 전용면적 필터
        if '전용면적_num' in raw_df.columns:
            min_area = float(raw_df['전용면적_num'].min())
            max_area = float(raw_df['전용면적_num'].max())
            if min_area == max_area: max_area += 0.1
            area_range = f_col1.slider("전용면적 (㎡)", min_area, max_area, (min_area, max_area), step=0.1)
            filtered_df = filtered_df[
                (filtered_df['전용면적_num'] >= area_range[0]) & 
                (filtered_df['전용면적_num'] <= area_range[1])
            ]

        # 2. 보증금 필터
        if '보증금_num' in raw_df.columns:
            min_dep = int(raw_df['보증금_num'].min())
            max_dep = int(raw_df['보증금_num'].max())
            if min_dep == max_dep: max_dep += 100
            dep_range = f_col2.slider("보증금 (만원)", min_dep, max_dep, (min_dep, max_dep), step=100)
            filtered_df = filtered_df[
                (filtered_df['보증금_num'] >= dep_range[0]) & 
                (filtered_df['보증금_num'] <= dep_range[1])
            ]

        # 3. 월세 필터
        if '월세_num' in raw_df.columns:
            min_rent = int(raw_df['월세_num'].min())
            max_rent = int(raw_df['월세_num'].max())
            if min_rent == max_rent: max_rent += 10
            rent_range = f_col3.slider("월세 (만원)", min_rent, max_rent, (min_rent, max_rent), step=10)
            filtered_df = filtered_df[
                (filtered_df['월세_num'] >= rent_range[0]) & 
                (filtered_df['월세_num'] <= rent_range[1])
            ]

        # 4. 층 필터
        if '층_num' in raw_df.columns:
            min_floor = int(raw_df['층_num'].min())
            max_floor = int(raw_df['층_num'].max())
            if min_floor == max_floor: max_floor += 1
            floor_range = f_col4.slider("층수", min_floor, max_floor, (min_floor, max_floor), step=1)
            filtered_df = filtered_df[
                (filtered_df['층_num'] >= floor_range[0]) & 
                (filtered_df['층_num'] <= floor_range[1])
            ]

    # --- 요약 지표 (필터링된 결과 기준) ---
    m1, m2, m3, m4 = st.columns(4)
    if not filtered_df.empty:
        m1.metric("검색 결과", f"{len(filtered_df):,} 건")
        
        # 보증금 통계
        if '보증금_num' in filtered_df.columns:
            m2.metric("평균 보증금", f"{filtered_df['보증금_num'].mean():,.0f} 만원")
        else:
            m2.metric("평균 보증금", "N/A")
            
        # 월세 통계
        if '월세_num' in filtered_df.columns:
            m3.metric("평균 월세", f"{filtered_df['월세_num'].mean():,.0f} 만원")
        else:
            m3.metric("평균 월세", "N/A")
            
        # 면적 통계
        if '전용면적_num' in filtered_df.columns:
            m4.metric("평균 면적", f"{filtered_df['전용면적_num'].mean():,.1f} ㎡")
        else:
            m4.metric("평균 면적", "N/A")
    else:
        st.warning("선택한 필터 조건에 맞는 데이터가 없습니다.")

    # 계산용 임시 컬럼 제거 후 표시
    display_df = filtered_df.drop(columns=[c for c in filtered_df.columns if c.endswith('_num')])
    
    # 데이터 테이블
    st.dataframe(display_df, use_container_width=True)
    
    # 다운로드 버튼
    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 필터링된 결과 CSV 다운로드", data=csv, file_name=f"filtered_result.csv", mime="text/csv")

elif not run_query:
    st.info("💡 사이드바에 정보를 입력하고 조회를 클릭하세요.")