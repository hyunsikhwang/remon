#!/usr/bin/env python3
"""Streamlit app to fetch apartment rent transaction data from public API."""

from __future__ import annotations

import datetime as dt
import inspect
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests
import streamlit as st

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"


def month_range(start_yyyymm: str, end_yyyymm: str) -> Iterable[str]:
    start = dt.datetime.strptime(start_yyyymm, "%Y%m")
    end = dt.datetime.strptime(end_yyyymm, "%Y%m")
    current = start
    while current <= end:
        yield current.strftime("%Y%m")
        year = current.year + (current.month // 12)
        month = (current.month % 12) + 1
        current = dt.datetime(year, month, 1)


def fetch_month(service_key: str, lawd_cd: str, deal_ymd: str) -> List[Dict[str, str]]:
    params = {
        "serviceKey": service_key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "numOfRows": 1000,
        "pageNo": 1,
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    items = root.findall(".//item")
    rows: List[Dict[str, str]] = []
    for item in items:
        row: Dict[str, str] = {}
        for child in item:
            if child.text is None:
                continue
            row[child.tag] = child.text.strip()
        rows.append(row)
    return rows


def _try_public_data_reader(
    service_key: str, lawd_cd: str, start_yyyymm: str, end_yyyymm: str
) -> Optional[pd.DataFrame]:
    try:
        import PublicDataReader as pdr
    except ImportError:
        return None

    api = None
    if hasattr(pdr, "TransactionPrice"):
        api = pdr.TransactionPrice(service_key)
    elif hasattr(pdr, "PublicDataReader"):
        api = pdr.PublicDataReader(service_key)

    if api is None:
        return None

    for method_name in ("get_data", "get_rent_data", "get_data_by_month"):
        if not hasattr(api, method_name):
            continue
        method = getattr(api, method_name)
        signature = inspect.signature(method)
        month_frames: List[pd.DataFrame] = []
        for deal_ymd in month_range(start_yyyymm, end_yyyymm):
            kwargs = {}
            if "lawd_cd" in signature.parameters:
                kwargs["lawd_cd"] = lawd_cd
            if "deal_ymd" in signature.parameters:
                kwargs["deal_ymd"] = deal_ymd
            if "trade_month" in signature.parameters:
                kwargs["trade_month"] = deal_ymd
            if "year" in signature.parameters:
                kwargs["year"] = deal_ymd[:4]
            if "month" in signature.parameters:
                kwargs["month"] = deal_ymd[4:]
            if "property_type" in signature.parameters:
                kwargs["property_type"] = "apt_rent"
            if "data_type" in signature.parameters:
                kwargs["data_type"] = "rent"
            try:
                result = method(**kwargs)
            except TypeError:
                continue
            if isinstance(result, pd.DataFrame):
                month_frames.append(result)
        if month_frames:
            return pd.concat(month_frames, ignore_index=True)

    return None


def _public_data_reader_available() -> bool:
    try:
        import PublicDataReader as pdr  # noqa: F401
    except ImportError:
        return False
    return True


def collect_transactions(
    service_key: str,
    lawd_cd: str,
    start_yyyymm: str,
    end_yyyymm: str,
    apt_name_keyword: str | None = None,
) -> pd.DataFrame:
    public_data_reader_df = _try_public_data_reader(
        service_key=service_key,
        lawd_cd=lawd_cd,
        start_yyyymm=start_yyyymm,
        end_yyyymm=end_yyyymm,
    )
    if public_data_reader_df is not None:
        df = public_data_reader_df
    else:
        all_rows: List[Dict[str, str]] = []
        for deal_ymd in month_range(start_yyyymm, end_yyyymm):
            all_rows.extend(fetch_month(service_key, lawd_cd, deal_ymd))

        df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    if apt_name_keyword and "아파트" in df.columns:
        df = df[df["아파트"].str.contains(apt_name_keyword, na=False)]

    df = df.sort_values(by=["년", "월", "일"]).reset_index(drop=True)
    return df


st.set_page_config(page_title="전월세 실거래가 조회", page_icon="🏠", layout="wide")

st.title("🏠 아파트 전월세 실거래가 조회")
st.caption(
    "공공데이터포털(국토교통부) 전월세 실거래가 API로 데이터를 조회합니다. "
    "서비스키는 공공데이터포털에서 발급받은 키를 입력하세요."
)

with st.sidebar:
    st.header("조회 조건")
    service_key = st.text_input(
        "서비스키(ServiceKey)",
        type="password",
        help="공공데이터포털에서 발급받은 서비스키를 입력하세요.",
    )
    lawd_cd = st.text_input(
        "법정동코드(LAWD_CD)",
        value="11680",
        help="5자리 법정동코드 (예: 서울 강남구 11680)",
    )
    start_yyyymm = st.text_input("조회 시작 월 (YYYYMM)", value="202401")
    end_yyyymm = st.text_input("조회 종료 월 (YYYYMM)", value="202403")
    apt_keyword = st.text_input("아파트명 키워드(선택)", value="")
    run_query = st.button("조회 실행")
    if _public_data_reader_available():
        st.success("PublicDataReader 사용 가능: 우선적으로 라이브러리를 사용합니다.")
    else:
        st.info(
            "PublicDataReader 미설치: 기본 API 호출로 동작합니다. "
            "Streamlit Cloud에서는 requirements.txt에 `PublicDataReader`를 추가하세요."
        )

st.markdown(
    """
    **사용 방법**
    1. 서비스키와 법정동코드를 입력합니다.
    2. 조회 기간(YYYYMM)을 설정합니다.
    3. 필요하면 아파트명 키워드를 입력합니다.
    4. "조회 실행" 버튼을 누릅니다.
    """
)

if run_query:
    if not service_key:
        st.error("서비스키를 입력해주세요.")
    elif not lawd_cd or len(lawd_cd) != 5:
        st.error("법정동코드는 5자리여야 합니다.")
    else:
        with st.spinner("데이터를 불러오는 중입니다..."):
            df = collect_transactions(
                service_key=service_key,
                lawd_cd=lawd_cd,
                start_yyyymm=start_yyyymm,
                end_yyyymm=end_yyyymm,
                apt_name_keyword=apt_keyword if apt_keyword else None,
            )

        if df.empty:
            st.warning("조회 결과가 없습니다.")
        else:
            st.success(f"총 {len(df):,}건의 거래를 찾았습니다.")
            st.dataframe(df, use_container_width=True)
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "CSV 다운로드",
                data=csv_bytes,
                file_name="apt_rent_transactions.csv",
                mime="text/csv",
            )
else:
    st.info("좌측 입력란을 채운 뒤 조회를 실행하세요.")
