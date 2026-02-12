import streamlit as st
import pandas as pd
from PublicDataReader import TransactionPrice, code_bdong
import datetime
import re
import math
import os
import json
import hashlib
try:
    from pyecharts import options as opts
    from pyecharts.charts import Line, Bar, Polar
    from pyecharts.commons.utils import JsCode
    from streamlit_echarts import st_pyecharts
    HAS_PYECHARTS = True
except ModuleNotFoundError:
    opts = None
    Line = None
    Bar = None
    Polar = None
    JsCode = None
    st_pyecharts = None
    HAS_PYECHARTS = False

try:
    import streamlit_shadcn_ui as ui
    HAS_SHADCN_UI = True
except ModuleNotFoundError:
    ui = None
    HAS_SHADCN_UI = False

try:
    from awesome_table import AwesomeTable
    HAS_AWESOME_TABLE = True
except ImportError:
    # streamlit-awesome-table媛 pandas<1.x 寃쎈줈瑜?李몄“?섎뒗 臾몄젣 ?명솚 泥섎━
    try:
        from pandas import json_normalize as _json_normalize
        import pandas.io.json as _pandas_io_json

        if not hasattr(_pandas_io_json, "json_normalize"):
            _pandas_io_json.json_normalize = _json_normalize

        from awesome_table import AwesomeTable
        HAS_AWESOME_TABLE = True
    except Exception:
        AwesomeTable = None
        HAS_AWESOME_TABLE = False

# --- ?섏씠吏 ?ㅼ젙 ---
st.set_page_config(
    page_title="Real Estate Insights",
    page_icon="?룫",
    layout="wide"
)

# --- 而ㅼ뒪? CSS (Tailwind-inspired dashboard theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons+Outlined');
    :root {
        --bg: #f8fafc;
        --panel: #ffffff;
        --ink: #0f172a;
        --muted: #64748b;
        --line: #e2e8f0;
        --brand: #0ea5e9;
        --brand-deep: #0284c7;
        --good: #10b981;
    }

    .block-container {
        padding-top: 1.1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1360px !important;
    }

    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }
    .stDeployButton, #MainMenu {
        display: none !important;
    }

    .stApp {
        background: var(--bg);
        color: var(--ink);
        font-family: 'Inter', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1.35rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    .sidebar-brand {
        font-size: 1.42rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 0.1rem;
    }

    .sidebar-sub {
        font-size: 0.82rem;
        color: #64748b;
        margin-bottom: 1rem;
    }

    .sidebar-api-ok {
        background: #f0f9ff;
        border: 1px solid #dbeafe;
        color: #0c4a6e;
        padding: 0.75rem 0.8rem;
        border-radius: 0.85rem;
        font-size: 0.83rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin-bottom: 0.8rem;
    }

    .stButton > button, button[kind="primary"], [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border-radius: 0.85rem;
        font-weight: 700;
        background: #0f172a;
        color: white;
        border: 1px solid #0f172a;
        padding: 0.68rem 1rem;
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.12);
    }
    .stButton > button:hover, button[kind="primary"]:hover {
        background: #1e293b;
        border-color: #1e293b;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #f1f5f9 !important;
        border-radius: 1rem !important;
        background: #ffffff !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid var(--line) !important;
        border-radius: 1rem !important;
        background: #ffffff !important;
    }

    [data-testid="stExpander"] summary {
        font-weight: 700;
    }

    .app-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.7rem;
        color: #64748b;
        font-size: 0.87rem;
    }

    .topbar-actions {
        display: flex;
        gap: 0.95rem;
        align-items: center;
    }

    .hero-container {
        position: relative;
        border: 1px solid #e2e8f0;
        border-radius: 1.5rem;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        padding: 2.1rem 2.1rem;
        margin-bottom: 1rem;
        overflow: hidden;
    }

    .hero-glow {
        position: absolute;
        right: -48px;
        top: -48px;
        width: 240px;
        height: 240px;
        border-radius: 9999px;
        background: rgba(14,165,233,0.12);
        filter: blur(28px);
    }

    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.2rem;
    }

    .hero-subtitle {
        color: #64748b;
        font-size: 1rem;
    }

    .filter-bar {
        border: 1px solid #e2e8f0;
        border-radius: 1rem;
        background: #ffffff;
        padding: 0.7rem 0.95rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
    }

    .filter-chip {
        border-radius: 0.65rem;
        background: #f1f5f9;
        padding: 0.35rem 0.6rem;
        font-size: 0.77rem;
        font-weight: 700;
        color: #334155;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
    }

    .filter-stat {
        font-size: 0.78rem;
        color: #64748b;
        white-space: nowrap;
    }

    .kpi-card {
        background: #ffffff;
        border: 1px solid #f1f5f9;
        border-radius: 1rem;
        padding: 1.05rem 1rem;
        min-height: 122px;
        transition: box-shadow 0.18s ease, transform 0.18s ease;
    }

    .kpi-card:hover {
        box-shadow: 0 10px 22px rgba(15,23,42,0.08);
        transform: translateY(-2px);
    }

    .kpi-title {
        font-size: 0.8rem;
        font-weight: 700;
        color: #64748b;
        margin-bottom: 0.72rem;
    }

    .kpi-val {
        font-size: 1.95rem;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -0.02em;
        color: #0f172a;
    }

    .kpi-unit {
        font-size: 1rem;
        color: #64748b;
        font-weight: 700;
        margin-left: 0.25rem;
    }

    .kpi-desc {
        margin-top: 0.62rem;
        font-size: 0.73rem;
        color: #94a3b8;
    }

    .chart-card-title {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 1.45rem;
        font-weight: 800;
        color: #0f172a;
    }

    .chart-sub {
        color: #64748b;
        font-size: 0.84rem;
    }

    [data-testid="stRadio"] label p,
    [data-testid="stRadio"] span {
        font-size: 0.86rem !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        border-radius: 0.8rem !important;
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
    }

    .main-note {
        color: #94a3b8;
        font-size: 0.79rem;
    }

    .material-icons-outlined {
        font-size: 1.1rem;
        line-height: 1;
        vertical-align: middle;
    }

    [data-testid="stMetric"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- API ???ㅼ젙 (Streamlit Secrets) ---
if "service_key" in st.secrets:
    SECRET_KEY = st.secrets["service_key"]
else:
    SECRET_KEY = None

# --- ?몄뀡 ?곹깭 珥덇린??---
if "df" not in st.session_state:
    st.session_state.df = None
if "region_name" not in st.session_state:
    st.session_state.region_name = ""
if "trade_type_val" not in st.session_state:
    st.session_state.trade_type_val = "?꾩썡??
if "df_nonce" not in st.session_state:
    st.session_state.df_nonce = 0

# ?꾪꽣留?議곌굔 ?좎?瑜??꾪븳 ?곹깭 珥덇린??
if "filter_deal_price" not in st.session_state: st.session_state.filter_deal_price = None
if "filter_dep_price" not in st.session_state: st.session_state.filter_dep_price = None
if "filter_rent_price" not in st.session_state: st.session_state.filter_rent_price = None
if "filter_areas" not in st.session_state: st.session_state.filter_areas = []
if "filter_floors" not in st.session_state: st.session_state.filter_floors = []
if "filter_area_unit" not in st.session_state: st.session_state.filter_area_unit = "怨듦툒硫댁쟻(?됲삎?)"
if "filter_supply_bands" not in st.session_state: st.session_state.filter_supply_bands = []

USER_PREFS_PATH = os.path.join(os.path.dirname(__file__), ".user_prefs.json")

def get_user_pref_key():
    """?ㅻ뜑/荑좏궎 湲곕컲 ?ъ슜???앸퀎 ???앹꽦"""
    raw = "anonymous"
    try:
        ctx = st.context
        headers = getattr(ctx, "headers", {}) or {}
        cookies = getattr(ctx, "cookies", {}) or {}

        cookie_seed = ""
        for k in ("_streamlit_user", "_streamlit_session", "ajs_anonymous_id"):
            v = cookies.get(k)
            if v:
                cookie_seed = str(v)
                break

        header_seed = "|".join([
            str(headers.get("x-forwarded-for", "")),
            str(headers.get("user-agent", "")),
            str(headers.get("accept-language", "")),
        ])
        raw = cookie_seed if cookie_seed else header_seed
        if not str(raw).strip():
            raw = "anonymous"
    except Exception:
        raw = "anonymous"

    return hashlib.sha256(str(raw).encode("utf-8")).hexdigest()[:24]

def load_user_preferences(user_key):
    """?ъ슜?먮퀎 ?낅젰媛?蹂듭썝"""
    if not os.path.exists(USER_PREFS_PATH):
        return {}
    try:
        with open(USER_PREFS_PATH, "r", encoding="utf-8") as f:
            all_prefs = json.load(f)
        if isinstance(all_prefs, dict):
            value = all_prefs.get(user_key, {})
            return value if isinstance(value, dict) else {}
    except Exception:
        pass
    return {}

def save_user_preferences(user_key, prefs):
    """?ъ슜?먮퀎 ?낅젰媛????""
    try:
        all_prefs = {}
        if os.path.exists(USER_PREFS_PATH):
            with open(USER_PREFS_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    all_prefs = loaded
        all_prefs[user_key] = prefs

        temp_path = f"{USER_PREFS_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(all_prefs, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, USER_PREFS_PATH)
    except Exception:
        pass

def parse_date_or_fallback(value, fallback):
    try:
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str) and value:
            return datetime.date.fromisoformat(value)
    except Exception:
        pass
    return fallback

# ?ъ슜?먮퀎 ?낅젰媛?珥덇린 蹂듭썝
today_for_init = datetime.date.today()
try:
    default_start_for_init = today_for_init.replace(year=today_for_init.year - 1)
except ValueError:
    default_start_for_init = today_for_init.replace(year=today_for_init.year - 1, day=28)

if "user_pref_key" not in st.session_state:
    st.session_state.user_pref_key = get_user_pref_key()

if "inputs_restored" not in st.session_state:
    restored = load_user_preferences(st.session_state.user_pref_key)
    st.session_state.trade_type_val = restored.get("trade_type", st.session_state.trade_type_val)
    st.session_state.region_input_text = restored.get("region_input", "?≫뙆援?)
    st.session_state.start_date_input = parse_date_or_fallback(
        restored.get("start_date"),
        default_start_for_init
    )
    st.session_state.end_date_input = parse_date_or_fallback(
        restored.get("end_date"),
        today_for_init
    )
    st.session_state.apt_keyword_input = restored.get("apt_keyword", "")
    st.session_state.inputs_restored = True

@st.cache_resource
def load_bdong_data():
    """踰뺤젙??肄붾뱶 ?곗씠??濡쒕뱶"""
    try:
        return code_bdong()
    except Exception as e:
        st.error(f"踰뺤젙???곗씠?곕? 遺덈윭?????놁뒿?덈떎: {e}")
        return pd.DataFrame()

def get_region_code(region_name):
    """吏??챸???낅젰諛쏆븘 5?먮━ ?쒓뎔援?肄붾뱶瑜?諛섑솚"""
    try:
        df = load_bdong_data()
        if df.empty:
            return None, None
        
        active_df = df[df['留먯냼?쇱옄'].isna() | (df['留먯냼?쇱옄'] == '')].copy()
        mask = (active_df['?쒓뎔援щ챸'].str.contains(region_name, na=False)) | \
               (active_df['?띾㈃?숇챸'].str.contains(region_name, na=False))
        
        results = active_df[mask]
        if not results.empty:
            target = results.iloc[0]
            return str(target['?쒓뎔援ъ퐫??]), f"{target['?쒕룄紐?]} {target['?쒓뎔援щ챸']}"
        return None, None
    except Exception as e:
        st.error(f"吏??肄붾뱶 寃??以??ㅻ쪟: {e}")
        return None, None

def standardize_columns(df):
    """API 諛섑솚 而щ읆紐낆쓣 ?깆뿉???ъ슜?섎뒗 ?쒖? 紐낆묶?쇰줈 蹂寃?""
    df.columns = [col.strip() for col in df.columns]
    mapping = {
        '?꾪뙆??: ['?⑥?', '?⑥?紐?, '嫄대Ъ紐?, 'aptNm', '?꾪뙆??],
        '留ㅻℓ媛': ['嫄곕옒湲덉븸', '嫄곕옒湲덉븸(留뚯썝)', 'dealAmount', '留ㅻℓ媛'],
        '蹂댁쬆湲?: ['蹂댁쬆湲덉븸', '蹂댁쬆湲?留뚯썝)', 'deposit', '蹂댁쬆湲?],
        '?붿꽭': ['?붿꽭??, '?붿꽭(留뚯썝)', 'monthlyRent', '?붿꽭'],
        '?꾩슜硫댁쟻': ['excluUseAr', '?꾩슜硫댁쟻(??', '硫댁쟻', '?꾩슜硫댁쟻'],
        '痢?: ['floor', '痢듭닔', '痢?],
        '??: ['dealYear', '??],
        '??: ['dealMonth', '??],
        '??: ['dealDay', '??]
    }
    for standard, candidates in mapping.items():
        for col in candidates:
            if col in df.columns:
                df = df.rename(columns={col: standard})
                break
    return df

def to_numeric_safe(x):
    """臾몄옄???レ옄瑜??덉쟾?섍쾶 ?レ옄濡?蹂??""
    if pd.isna(x) or x == '': return 0.0
    val = re.sub(r'[^0-9.]', '', str(x))
    return float(val) if val else 0.0

SUPPLY_PYEONG_BANDS = [
    ((39, 40), "16~18?됲삎"),
    ((49, 51), "20~22?됲삎"),
    ((59, 59), "24~26?됲삎"),
    ((72, 74), "28~30?됲삎"),
    ((84, 85), "32~35?됲삎"),
    ((101, 102), "39~41?됲삎"),
]

SUPPLY_PYEONG_ANCHORS = [
    (39.5, 17.0),
    (50.0, 21.0),
    (59.0, 25.0),
    (73.0, 29.0),
    (84.5, 33.5),
    (101.5, 40.0),
]

SUPPLY_BAND_CENTERS = {
    "16~18?됲삎": 17.0,
    "20~22?됲삎": 21.0,
    "24~26?됲삎": 25.0,
    "28~30?됲삎": 29.0,
    "32~35?됲삎": 33.5,
    "39~41?됲삎": 40.0,
}

def estimate_supply_pyeong(area_m2):
    """湲곗? ?듭빱瑜??댁슜???꾩슜硫댁쟻(????怨듦툒?됱닔(??濡??좏삎 蹂닿컙/?몄궫"""
    if pd.isna(area_m2):
        return None

    x = float(area_m2)
    anchors = SUPPLY_PYEONG_ANCHORS

    if x <= anchors[0][0]:
        x0, y0 = anchors[0]
        x1, y1 = anchors[1]
    elif x >= anchors[-1][0]:
        x0, y0 = anchors[-2]
        x1, y1 = anchors[-1]
    else:
        x0 = y0 = x1 = y1 = None
        for i in range(len(anchors) - 1):
            ax0, ay0 = anchors[i]
            ax1, ay1 = anchors[i + 1]
            if ax0 <= x <= ax1:
                x0, y0, x1, y1 = ax0, ay0, ax1, ay1
                break

    if x1 == x0:
        return y0
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)

def to_supply_pyeong_band(area_m2):
    """蹂닿컙??怨듦툒?됱닔瑜?媛??媛源뚯슫 ?됲삎? ?쇰꺼濡?留ㅽ븨"""
    est = estimate_supply_pyeong(area_m2)
    if est is None:
        return None
    return min(SUPPLY_BAND_CENTERS.keys(), key=lambda k: abs(SUPPLY_BAND_CENTERS[k] - est))

def apply_apt_keyword_filter(df, expr):
    """?꾪뙆???ㅼ썙??議곌굔??AND/OR/NOT)???곸슜"""
    if df is None or df.empty or '?꾪뙆?? not in df.columns:
        return df
    if not expr or not str(expr).strip():
        return df

    q = str(expr).strip()
    q = re.sub(r'\s+(?i:or)\s+', '|', q)
    q = re.sub(r'\s+(?i:and)\s+', '&', q)
    groups = [g.strip() for g in q.split('|') if g.strip()]
    if not groups:
        return df

    name_series = df['?꾪뙆??].astype(str)
    final_mask = pd.Series(False, index=df.index)

    for g in groups:
        terms = [t.strip() for t in re.split(r'&', g) if t.strip()]
        include_terms = []
        exclude_terms = []

        for t in terms:
            t_clean = t.strip()
            if t_clean.startswith('-') or t_clean.startswith('!'):
                word = t_clean[1:].strip()
                if word:
                    exclude_terms.append(word)
            elif re.match(r'(?i)^not\s+', t_clean):
                word = re.sub(r'(?i)^not\s+', '', t_clean).strip()
                if word:
                    exclude_terms.append(word)
            else:
                include_terms.append(t_clean)

        group_mask = pd.Series(True, index=df.index)
        for w in include_terms:
            group_mask &= name_series.str.contains(w, na=False, case=False)
        for w in exclude_terms:
            group_mask &= ~name_series.str.contains(w, na=False, case=False)

        final_mask |= group_mask

    return df[final_mask]

def apply_all_column_filters(df, key_prefix):
    """異쒕젰???곗씠?고봽?덉엫??紐⑤뱺 而щ읆??????숈쟻 ?꾪꽣 ?곸슜"""
    if df is None or df.empty:
        return df, 0

    selected_cols = st.multiselect(
        "?꾪꽣 而щ읆",
        options=list(df.columns),
        default=[],
        key=f"{key_prefix}_selected_cols"
    )

    if not selected_cols:
        return df, 0

    mask = pd.Series(True, index=df.index)
    active_count = 0
    for col in selected_cols:
        with st.expander(f"議곌굔 ?ㅼ젙: {col}", expanded=False):
            series = df[col]
            safe_col = re.sub(r'[^0-9a-zA-Z_媛-??', '_', str(col))

            numeric_series = pd.to_numeric(series, errors='coerce')
            numeric_ratio = numeric_series.notna().mean() if len(series) else 0

            # ?꾩슜硫댁쟻? 怨듦툒?됱닔 蹂?섏쓣 吏?먰븯怨?硫?곗꽑??UI ?ъ슜
            if '?꾩슜硫댁쟻' in str(col) and numeric_ratio >= 0.9 and numeric_series.notna().any():
                unit = st.radio(
                    "?쒖떆 ?⑥쐞",
                    options=["怨듦툒硫댁쟻(?됲삎?)", "?꾩슜硫댁쟻(??"],
                    horizontal=True,
                    key=f"{key_prefix}_{safe_col}_unit"
                )

                if unit == "怨듦툒硫댁쟻(?됲삎?)":
                    converted = numeric_series.apply(to_supply_pyeong_band)
                    band_order = [label for _, label in SUPPLY_PYEONG_BANDS]
                    existing = [b for b in band_order if b in converted.dropna().unique().tolist()]
                    options = existing
                    label = "怨듦툒?됲삎? ?좏깮"
                else:
                    converted = numeric_series.round(1)
                    options = sorted([v for v in converted.dropna().unique().tolist()])
                    label = "?꾩슜硫댁쟻(?? ?좏깮"

                selected_vals = st.multiselect(
                    label,
                    options=options,
                    default=options,
                    key=f"{key_prefix}_{safe_col}_area_values"
                )
                if len(selected_vals) != len(options):
                    active_count += 1
                mask &= converted.isin(selected_vals)
                continue

            # ?レ옄濡??댁꽍 媛?ν븳 而щ읆? 踰붿쐞 ?꾪꽣 ?쒓났
            if numeric_ratio >= 0.9 and numeric_series.notna().any():
                min_v = float(numeric_series.min())
                max_v = float(numeric_series.max())

                if min_v == max_v:
                    st.caption(f"?⑥씪 媛?{min_v:g})留?議댁옱?⑸땲??")
                    continue

                is_int_like = (numeric_series.dropna() % 1 == 0).all()
                # 痢?而щ읆? ?щ씪?대뜑 ???泥댄겕諛뺤뒪 ?좏깮 UI ?쒓났
                if "痢? in str(col) and is_int_like:
                    floor_values = sorted(numeric_series.dropna().astype(int).unique().tolist())
                    if not floor_values:
                        continue

                    for floor in floor_values:
                        floor_key = f"{key_prefix}_{safe_col}_chk_{floor}"
                        if floor_key not in st.session_state:
                            st.session_state[floor_key] = True

                    btn_col1, btn_col2 = st.columns(2)
                    select_all = btn_col1.button("?꾩껜 ?좏깮", key=f"{key_prefix}_{safe_col}_chk_all", use_container_width=True)
                    clear_all = btn_col2.button("?꾩껜 ?댁젣", key=f"{key_prefix}_{safe_col}_chk_clear", use_container_width=True)
                    if select_all:
                        for floor in floor_values:
                            st.session_state[f"{key_prefix}_{safe_col}_chk_{floor}"] = True
                    elif clear_all:
                        for floor in floor_values:
                            st.session_state[f"{key_prefix}_{safe_col}_chk_{floor}"] = False

                    selected_vals = []
                    floor_cols = st.columns(4)
                    for idx, floor in enumerate(floor_values):
                        with floor_cols[idx % 4]:
                            checked = st.checkbox(f"{floor}", key=f"{key_prefix}_{safe_col}_chk_{floor}")
                        if checked:
                            selected_vals.append(floor)

                    if len(selected_vals) != len(floor_values):
                        active_count += 1
                    mask &= numeric_series.astype("Int64").isin(selected_vals)
                    continue

                if is_int_like:
                    slider_min = int(min_v)
                    slider_max = int(max_v)
                    step = 1 if slider_max - slider_min <= 200 else max(1, (slider_max - slider_min) // 200)
                    selected_range = st.slider(
                        f"{col} 踰붿쐞",
                        min_value=slider_min,
                        max_value=slider_max,
                        value=(slider_min, slider_max),
                        step=step,
                        key=f"{key_prefix}_{safe_col}_range"
                    )
                else:
                    selected_range = st.slider(
                        f"{col} 踰붿쐞",
                        min_value=min_v,
                        max_value=max_v,
                        value=(min_v, max_v),
                        key=f"{key_prefix}_{safe_col}_range"
                    )

                if selected_range[0] > min_v or selected_range[1] < max_v:
                    active_count += 1
                mask &= numeric_series.between(selected_range[0], selected_range[1], inclusive='both')
                continue

            # 臾몄옄??而щ읆? 怨좎쑀媛??섏뿉 ?곕씪 ?ㅼ쨷?좏깮/遺遺꾧????쒓났
            str_series = series.astype(str)
            unique_vals = sorted([v for v in str_series.dropna().unique().tolist() if v != "nan"])

            if len(unique_vals) <= 100:
                selected_vals = st.multiselect(
                    f"{col} 媛??좏깮",
                    options=unique_vals,
                    default=unique_vals,
                    key=f"{key_prefix}_{safe_col}_values"
                )
                if len(selected_vals) != len(unique_vals):
                    active_count += 1
                mask &= str_series.isin(selected_vals)
            else:
                keyword = st.text_input(
                    f"{col} 遺遺꾧???,
                    value="",
                    key=f"{key_prefix}_{safe_col}_keyword",
                    placeholder=f"{col}???ы븿???띿뒪???낅젰"
                )
                if keyword:
                    active_count += 1
                    mask &= str_series.str.contains(keyword, na=False, case=False)

    return df[mask], active_count

def reset_filter_state(key_prefix):
    """湲곕낯 ?꾪꽣/?숈쟻 而щ읆 ?꾪꽣 ?곹깭 珥덇린??""
    st.session_state.filter_deal_price = None
    st.session_state.filter_dep_price = None
    st.session_state.filter_rent_price = None
    st.session_state.filter_areas = []
    st.session_state.filter_area_unit = "怨듦툒硫댁쟻(?됲삎?)"
    st.session_state.filter_supply_bands = []
    st.session_state.filter_floors = []
    st.session_state.quick_area_unit = "怨듦툒硫댁쟻(?됲삎?)"

    delete_keys = [k for k in st.session_state.keys() if str(k).startswith(key_prefix)]
    for k in delete_keys:
        del st.session_state[k]

def render_awesome_table(df):
    """실거래 리스트를 테이블로 렌더링"""
    if df is None or df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    st.markdown(
        """
        <style>
            [data-testid="stDataFrame"] {
                --gdg-font-size: 8pt !important;
            }
            [data-testid="stDataFrame"] div,
            [data-testid="stDataFrame"] span,
            [data-testid="stDataFrame"] p {
                font-size: 8pt !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    safe_df = df.copy().fillna("")
    safe_df.columns = [str(col) for col in safe_df.columns]
    st.dataframe(safe_df, use_container_width=True, hide_index=True)
def render_metric_card(title, content, description, key):
    """Dashboard KPI 移대뱶 ?뚮뜑留?""
    text = str(content)
    m = re.match(r'^([0-9,\.\-]+)\s*(.*)$', text)
    if m:
        value, unit = m.group(1), m.group(2).strip()
    else:
        value, unit = text, ""

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div><span class="kpi-val">{value}</span>{f'<span class="kpi-unit">{unit}</span>' if unit else ''}</div>
            <div class="kpi-desc">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def make_period_frame(df):
    """嫄곕옒??湲곗? ???⑥쐞 吏묎퀎 ?꾨젅???앹꽦"""
    if df is None or df.empty:
        return pd.DataFrame()
    if not all(c in df.columns for c in ['??, '??]):
        return pd.DataFrame()

    work = df.copy()
    if '?? in work.columns:
        day_vals = pd.to_numeric(work['??], errors='coerce').fillna(1).astype(int)
    else:
        day_vals = pd.Series(1, index=work.index)

    date_str = (
        pd.to_numeric(work['??], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(4) + "-" +
        pd.to_numeric(work['??], errors='coerce').fillna(0).astype(int).astype(str).str.zfill(2) + "-" +
        day_vals.astype(str).str.zfill(2)
    )
    work['deal_date'] = pd.to_datetime(date_str, errors='coerce')
    work = work.dropna(subset=['deal_date']).sort_values('deal_date')
    if work.empty:
        return pd.DataFrame()

    work['period'] = work['deal_date'].dt.to_period('M').astype(str)
    return work

def render_trade_type_chart(df, trade_type):
    """嫄곕옒?좏삎蹂?湲곌컙-媛寃??곴? 李⑦듃 ?뚮뜑留?(pyecharts)"""
    if not HAS_PYECHARTS:
        st.error("李⑦듃 ?쇱씠釉뚮윭由?pyecharts)媛 ?ㅼ튂?섏? ?딆븯?듬땲?? `pip install -r requirements.txt` ???ㅼ떆 ?ㅽ뻾?댁＜?몄슂.")
        return

    base = make_period_frame(df)
    if base.empty:
        st.info("李⑦듃瑜?洹몃┫ 湲곌컙 ?곗씠?곌? 遺議깊빀?덈떎.")
        return

    def axis_bounds(values, pad_ratio=0.08, force_int=False):
        vals = [float(v) for v in values if pd.notna(v)]
        if not vals:
            return 0, 1
        v_min, v_max = min(vals), max(vals)
        if v_min == v_max:
            pad = max(abs(v_min) * 0.1, 1.0)
            low, high = v_min - pad, v_max + pad
        else:
            span = v_max - v_min
            pad = span * pad_ratio
            low, high = max(0, v_min - pad), v_max + pad

        if force_int:
            low = int(math.floor(low))
            high = int(math.ceil(high))
            if low == high:
                high = low + 1
            return low, high

        # 遺?숈냼?섏젏 ?몄씠利??? 7.14800000002) ?쒓굅??異뺢컪 ?뺢퇋??
        max_abs = max(abs(low), abs(high))
        if max_abs >= 1000:
            digits = 0
        elif max_abs >= 100:
            digits = 1
        elif max_abs >= 10:
            digits = 1
        elif max_abs >= 1:
            digits = 2
        else:
            digits = 3

        low = round(low, digits)
        high = round(high, digits)
        if low == high:
            high = round(high + (10 ** (-digits)), digits)
        return low, high

    if trade_type == "?꾩썡??:
        metric_options = []
        if '蹂댁쬆湲?num' in base.columns:
            metric_options.append(("蹂댁쬆湲?, "蹂댁쬆湲?num", "蹂댁쬆湲?留뚯썝)"))
        if '?붿꽭_num' in base.columns:
            metric_options.append(("?붿꽭", "?붿꽭_num", "?붿꽭(留뚯썝)"))
        if {'蹂댁쬆湲?num', '?붿꽭_num'}.issubset(base.columns):
            metric_options.append(("蹂댁쬆湲??붿꽭", "combined", "湲덉븸(留뚯썝)"))
        if not metric_options:
            st.info("?꾩썡??李⑦듃瑜??꾪븳 蹂댁쬆湲??붿꽭 ?곗씠?곌? 遺議깊빀?덈떎.")
            return

        metric_map = {label: (col, y_name) for label, col, y_name in metric_options}
        metric_choice = st.radio(
            "?꾩썡??李⑦듃 吏??,
            options=[m[0] for m in metric_options],
            horizontal=True,
            key="rental_chart_metric"
        )
        value_col, y_axis_name = metric_map[metric_choice]
    else:
        if '留ㅻℓ媛_num' not in base.columns:
            st.info("留ㅻℓ 李⑦듃瑜??꾪븳 留ㅻℓ媛 ?곗씠?곌? 遺議깊빀?덈떎.")
            return
        value_col, y_axis_name = "留ㅻℓ媛_num", "留ㅻℓ媛(留뚯썝)"
        metric_choice = "留ㅻℓ媛"

    apt_series = pd.Series(["?꾩껜"] * len(base), index=base.index)
    if '?꾪뙆?? in base.columns:
        apt_series = base['?꾪뙆??].astype(str).replace("nan", "").replace("", "誘몄긽")
    base = base.assign(_apt=apt_series)
    apt_names = [n for n in sorted(base['_apt'].dropna().unique().tolist()) if str(n).strip() != ""]
    multi_apt = len(apt_names) >= 2

    monthly_cnt = (
        base.groupby('period', as_index=False)
        .agg(嫄곕옒嫄댁닔=('period', 'count'))
        .sort_values('period')
    )
    x_data = monthly_cnt['period'].tolist()
    cnt_month = monthly_cnt['嫄곕옒嫄댁닔'].tolist()
    cnt_min, cnt_max = axis_bounds(cnt_month, 0.2, force_int=True)

    all_values = []
    dep_values_all = []
    rent_values_all = []
    combined_dual_axis = trade_type == "?꾩썡?? and metric_choice == "蹂댁쬆湲??붿꽭"
    line = Line()
    line.add_xaxis(x_data)
    if combined_dual_axis:
        dep_monthly = (
            base.groupby(['period', '_apt'], as_index=False)
            .agg(value=('蹂댁쬆湲?num', 'mean'))
        )
        dep_pivot = dep_monthly.pivot(index='period', columns='_apt', values='value').reindex(x_data)

        rent_monthly = (
            base.groupby(['period', '_apt'], as_index=False)
            .agg(value=('?붿꽭_num', 'mean'))
        )
        rent_pivot = rent_monthly.pivot(index='period', columns='_apt', values='value').reindex(x_data)

        for apt in dep_pivot.columns.tolist():
            dep_values = dep_pivot[apt].round(1).tolist()
            dep_values_all.extend([v for v in dep_values if pd.notna(v)])
            all_values.extend([v for v in dep_values if pd.notna(v)])
            dep_line_values = [None if pd.isna(v) else float(v) for v in dep_values]
            line.add_yaxis(
                f"{apt} 蹂댁쬆湲?,
                dep_line_values,
                yaxis_index=0,
                is_smooth=True,
                symbol="none",
                is_connect_nones=True,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=2.4, type_="solid"),
            )

        for apt in rent_pivot.columns.tolist():
            rent_values = rent_pivot[apt].round(1).tolist()
            rent_values_all.extend([v for v in rent_values if pd.notna(v)])
            all_values.extend([v for v in rent_values if pd.notna(v)])
            rent_line_values = [None if pd.isna(v) else float(v) for v in rent_values]
            line.add_yaxis(
                f"{apt} ?붿꽭",
                rent_line_values,
                yaxis_index=1,
                is_smooth=True,
                symbol="none",
                is_connect_nones=True,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=2.0, type_="dashed"),
            )
    else:
        apt_monthly = (
            base.groupby(['period', '_apt'], as_index=False)
            .agg(value=(value_col, 'mean'))
        )
        pivot = apt_monthly.pivot(index='period', columns='_apt', values='value').reindex(x_data)

        for apt in pivot.columns.tolist():
            values = pivot[apt].round(1).tolist()
            all_values.extend([v for v in values if pd.notna(v)])
            line_values = [None if pd.isna(v) else float(v) for v in values]
            line.add_yaxis(
                f"{apt}",
                line_values,
                is_smooth=True,
                symbol="none",
                is_connect_nones=True,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=2.4, type_="solid"),
            )

    val_min, val_max = axis_bounds(all_values, 0.12)

    cnt_axis_index = 1
    if combined_dual_axis:
        rent_min, rent_max = axis_bounds(rent_values_all, 0.12)
        dep_min, dep_max = axis_bounds(dep_values_all, 0.12)
        line.extend_axis(
            yaxis=opts.AxisOpts(
                name="?붿꽭(留뚯썝)",
                type_="value",
                position="right",
                min_=rent_min,
                max_=rent_max,
                axislabel_opts=opts.LabelOpts(formatter="{value}"),
            )
        )
        cnt_axis_index = 2
    else:
        dep_min, dep_max = val_min, val_max

    line.extend_axis(
        yaxis=opts.AxisOpts(
            name="嫄곕옒嫄댁닔(嫄?",
            type_="value",
            position="right",
            offset=56 if combined_dual_axis else 0,
            min_=cnt_min,
            max_=cnt_max,
            axislabel_opts=opts.LabelOpts(formatter="{value}"),
        )
    )

    bar = Bar()
    bar.add_xaxis(x_data)
    if multi_apt:
        cnt_by_apt = (
            base.groupby(['period', '_apt'], as_index=False)
            .agg(cnt=('period', 'count'))
            .pivot(index='period', columns='_apt', values='cnt')
            .reindex(x_data)
            .fillna(0)
        )
        for apt in cnt_by_apt.columns.tolist():
            bar.add_yaxis(
                f"{apt} 嫄곕옒嫄댁닔",
                cnt_by_apt[apt].astype(int).tolist(),
                yaxis_index=cnt_axis_index,
                stack="apt_cnt",
                bar_width="60%",
                category_gap="78%",
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts=opts.ItemStyleOpts(opacity=0.28),
            )
    else:
        bar.add_yaxis(
            "?붾퀎 嫄곕옒嫄댁닔",
            cnt_month,
            yaxis_index=cnt_axis_index,
            bar_width="60%",
            category_gap="78%",
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(color="rgba(148, 163, 184, 0.20)"),
        )

    line.overlap(bar)
    title = f"?뷀룊洹?異붿꽭 + ?붾퀎 嫄곕옒嫄댁닔 ({'?꾩썡?? if trade_type == '?꾩썡?? else '留ㅻℓ'})"
    subtitle = f"吏?? {metric_choice} 쨌 {'?꾪뙆?몃퀎 ?쇱씤' if multi_apt else '?⑥씪 ?쇱씤'}"
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=title, subtitle=subtitle),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        legend_opts=opts.LegendOpts(pos_top="4%", type_="scroll"),
        xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
        yaxis_opts=opts.AxisOpts(
            name="蹂댁쬆湲?留뚯썝)" if combined_dual_axis else y_axis_name,
            type_="value",
            min_=dep_min,
            max_=dep_max,
        ),
        datazoom_opts=[
            opts.DataZoomOpts(type_="inside", range_start=0, range_end=100),
            opts.DataZoomOpts(type_="slider", range_start=0, range_end=100)
        ],
    )
    st_pyecharts(line, height="500px")

def render_rental_polar_scatter(df):
    """?꾩썡???곗씠?곗쓽 蹂댁쬆湲??붿꽭 遺꾪룷瑜?Polar Scatter濡??뚮뜑留?""
    if not HAS_PYECHARTS:
        return
    if df is None or df.empty:
        st.info("Polar Scatter瑜??쒖떆???곗씠?곌? ?놁뒿?덈떎.")
        return
    if "蹂댁쬆湲?num" not in df.columns or "?붿꽭_num" not in df.columns:
        st.info("Polar Scatter瑜??꾪븳 蹂댁쬆湲??붿꽭 ?곗씠?곌? 遺議깊빀?덈떎.")
        return

    scatter_df = df[["蹂댁쬆湲?num", "?붿꽭_num"]].dropna().copy()
    scatter_df = scatter_df[
        (pd.to_numeric(scatter_df["蹂댁쬆湲?num"], errors="coerce").notna()) &
        (pd.to_numeric(scatter_df["?붿꽭_num"], errors="coerce").notna())
    ]
    if scatter_df.empty:
        st.info("Polar Scatter瑜??쒖떆???좏슚???꾩썡???곗씠?곌? ?놁뒿?덈떎.")
        return

    deposits = scatter_df["蹂댁쬆湲?num"].astype(float)
    rents = scatter_df["?붿꽭_num"].astype(float)
    # Polar 醫뚰몴??[radius, angle] ?쒖꽌?대?濡?[蹂댁쬆湲? ?붿꽭]濡??꾨떖
    points = list(zip(deposits.round(1).tolist(), rents.round(1).tolist()))

    dep_min, dep_max = float(deposits.min()), float(deposits.max())
    rent_min, rent_max = float(rents.min()), float(rents.max())
    dep_pad = max((dep_max - dep_min) * 0.08, 1.0)
    rent_pad = max((rent_max - rent_min) * 0.08, 1.0)

    chart = Polar()
    chart.add_schema(
        angleaxis_opts=opts.AngleAxisOpts(
            type_="value",
            min_=max(0, rent_min - rent_pad),
            max_=rent_max + rent_pad,
            start_angle=90,
        ),
        radiusaxis_opts=opts.RadiusAxisOpts(
            type_="value",
            min_=max(0, dep_min - dep_pad),
            max_=dep_max + dep_pad,
        ),
    )
    chart.add(
        series_name="?꾩썡??遺꾪룷",
        data=points,
        type_="scatter",
        symbol_size=8,
        label_opts=opts.LabelOpts(is_show=False),
        itemstyle_opts=opts.ItemStyleOpts(color="#0f766e", opacity=0.72),
    )
    chart.set_global_opts(
        title_opts=opts.TitleOpts(
            title="蹂댁쬆湲??붿꽭 Polar Scatter",
            subtitle="媛??먯? ??嫄댁쓽 ?꾩썡??嫄곕옒瑜??섎??⑸땲??",
        ),
        tooltip_opts=opts.TooltipOpts(
            trigger="item",
            formatter=JsCode("function (params) { var v = params.value || []; return v[0] + ' / ' + v[1]; }"),
        ),
        legend_opts=opts.LegendOpts(pos_top="4%"),
    )
    st_pyecharts(chart, height="520px")

# --- ?ъ씠?쒕컮 ---
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><span class="material-icons-outlined" style="color:#0ea5e9;">analytics</span>Search Portal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">?ㅺ굅?섍? ?곗씠??議고쉶 ?쒖뒪??/div>', unsafe_allow_html=True)
    
    if not SECRET_KEY:
        current_key = st.text_input("API ?몄쬆??, type="password", help="怨듦났?곗씠?고룷??API ??)
    else:
        st.markdown('<div class="sidebar-api-ok"><span class="material-icons-outlined">check_circle</span>API ?ㅺ? ?ㅼ젙?섏뼱 ?덉뒿?덈떎.</div>', unsafe_allow_html=True)
        current_key = SECRET_KEY
        
    st.divider()
    
    trade_type = st.radio("嫄곕옒 ?좏삎", ["留ㅻℓ", "?꾩썡??], 
                         index=0 if st.session_state.trade_type_val == "留ㅻℓ" else 1, 
                         horizontal=True, key="trade_type_radio")
    st.session_state.trade_type_val = trade_type
    
    region_input = st.text_input("吏??챸 (?쒓뎔援?", value="?≫뙆援?, key="region_input_text")
    
    today = datetime.date.today()
    try:
        default_start_date = today.replace(year=today.year - 1)
    except ValueError:
        # ?ㅻ뀈 2/29??寃쎌슦 1????2/28濡?蹂댁젙
        default_start_date = today.replace(year=today.year - 1, day=28)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("?쒖옉??, value=default_start_date, key="start_date_input")
    with col2:
        end_date = st.date_input("醫낅즺??, value=today, key="end_date_input")
        
    start_ym = start_date.strftime("%Y%m")
    end_ym = end_date.strftime("%Y%m")
    apt_keyword = st.text_input(
        "?꾪뙆?몃챸 議곌굔??,
        key="apt_keyword_input",
        help="?덉떆: ?섎????좎떎 | ?먯뒪?뚯씠??-由ъ꽱痢?(AND:& ?먮뒗 and, OR:| ?먮뒗 or, ?쒖쇅:-?⑥뼱/!?⑥뼱/not ?⑥뼱)",
        placeholder="?? ?섎????좎떎 | ?먯뒪?뚯씠??-由ъ꽱痢?
    )
    
    st.divider()
    run_query = st.button("?곗씠??議고쉶 ?ㅽ뻾", type="primary", use_container_width=True)

# --- 議고쉶 濡쒖쭅 ---
if run_query:
    save_user_preferences(
        st.session_state.user_pref_key,
        {
            "trade_type": trade_type,
            "region_input": str(region_input).strip(),
            "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else "",
            "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else "",
            "apt_keyword": str(apt_keyword).strip(),
        }
    )

    if not current_key:
        st.error("???쒕퉬?ㅽ궎媛 ?ㅼ젙?섏? ?딆븯?듬땲?? Secrets ?ㅼ젙 ?뱀? ?섎룞 ?낅젰???뺤씤?섏꽭??")
    else:
        with st.spinner(f"??{trade_type} ?곗씠???섏쭛 以?.."):
            sigungu_code, full_region_name = get_region_code(region_input)
            
            if not sigungu_code:
                st.error(f"??'{region_input}' 吏??쓣 李얠쓣 ???놁뒿?덈떎.")
            else:
                try:
                    api = TransactionPrice(current_key)
                    df = api.get_data(
                        property_type="?꾪뙆??,
                        trade_type=trade_type,
                        sigungu_code=sigungu_code,
                        start_year_month=start_ym,
                        end_year_month=end_ym
                    )
                    
                    if df is not None and not df.empty:
                        df = standardize_columns(df)
                        
                        target_cols = ['留ㅻℓ媛', '蹂댁쬆湲?, '?붿꽭', '?꾩슜硫댁쟻', '痢?]
                        for col in target_cols:
                            if col in df.columns:
                                df[f'{col}_num'] = df[col].apply(to_numeric_safe)
                        
                        if apt_keyword and '?꾪뙆?? in df.columns:
                            df = apply_apt_keyword_filter(df, apt_keyword)
                        
                        sort_cols = [c for c in ['??, '??, '??] if c in df.columns]
                        if sort_cols:
                            df = df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
                        
                        st.session_state.df = df
                        st.session_state.df_nonce += 1
                        st.session_state.region_name = full_region_name
                        st.session_state.trade_type_val = trade_type
                        
                        # ?덈줈???곗씠?곕? 議고쉶?????꾪꽣 珥덇린?붽? ?꾩슂?섎떎硫??ш린???섑뻾 (?붽뎄?ы빆? ?좎??대?濡??앸왂)
                    else:
                        st.session_state.df = None
                        st.warning(f"?좑툘 {full_region_name} ?곗씠?곌? ?놁뒿?덈떎.")
                        
                except Exception as e:
                    st.error(f"??API ?ㅻ쪟: {e}")
                    st.session_state.df = None

# --- 硫붿씤 UI ---
if st.session_state.df is not None:
    raw_df = st.session_state.df.copy()
    current_type = st.session_state.trade_type_val

    # Hero Section
    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-glow"></div>
        <div class="hero-title">Real Estate Insights</div>
        <div class="hero-subtitle">{st.session_state.region_name} {current_type} ?ㅺ굅??遺꾩꽍 由ы룷??/div>
    </div>
    """, unsafe_allow_html=True)
    
    filtered_df = raw_df.copy()
    quick_filter_active_count = 0
    col_filter_active_count = 0
    filter_key_prefix = f"list_filter_{st.session_state.df_nonce}"

    # 媛怨듭슜 而щ읆 ?쒓굅 ??由ъ뒪???꾩껜 而щ읆 ?꾪꽣瑜??곸슜
    fixed_exclude = ['index', 'sggCd', 'umdNm', 'jibun', 'buildYear', 'aptSeq', 'umdCd', 'landCd', 'bonbun', 'bubun', 'cdealType', 'cdealDay', 'estateAgengSggNm', 'buerGbn']
    road_exclude = [c for c in filtered_df.columns if str(c).startswith('road')]
    internal_exclude = [c for c in filtered_df.columns if str(c).endswith('_num')]
    all_drop_cols = list(set(fixed_exclude + road_exclude + internal_exclude))
    actual_drop_cols = [c for c in all_drop_cols if c in filtered_df.columns]

    with st.expander("?럾截?Filter Studio", expanded=False):
        h1, h2 = st.columns([0.8, 0.2])
        with h1:
            st.caption("?꾪꽣???묓옒 ?곹깭濡??좎??⑸땲?? ?꾩슂???뚮쭔 ?댁뼱 議곗젙?섏꽭??")
        with h2:
            if st.button("珥덇린??, use_container_width=True, key=f"btn_reset_{st.session_state.df_nonce}"):
                reset_filter_state(filter_key_prefix)
                st.rerun()

        tab_quick, tab_columns = st.tabs(["鍮좊Ⅸ ?꾪꽣", "而щ읆 ?꾪꽣"])

        with tab_quick:
            c1, c2 = st.columns(2)
            if current_type == "留ㅻℓ":
                if '留ㅻℓ媛_num' in raw_df.columns:
                    min_v, max_v = int(raw_df['留ㅻℓ媛_num'].min()), int(raw_df['留ㅻℓ媛_num'].max())
                    if min_v == max_v:
                        max_v += 1000

                    default_val = st.session_state.filter_deal_price if st.session_state.filter_deal_price else (min_v, max_v)
                    default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))

                    with c1:
                        deal_sel = st.slider("?뮥 留ㅻℓ媛 (留뚯썝)", min_v, max_v, default_val, step=1000, key="slider_deal")
                        st.session_state.filter_deal_price = deal_sel
                        if deal_sel[0] > min_v or deal_sel[1] < max_v:
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['留ㅻℓ媛_num'].between(deal_sel[0], deal_sel[1])]
            else:
                with c1:
                    if '蹂댁쬆湲?num' in raw_df.columns:
                        min_v, max_v = int(raw_df['蹂댁쬆湲?num'].min()), int(raw_df['蹂댁쬆湲?num'].max())
                        if min_v == max_v:
                            max_v += 100

                        default_val = st.session_state.filter_dep_price if st.session_state.filter_dep_price else (min_v, max_v)
                        default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))

                        dep_sel = st.slider("?뮥 蹂댁쬆湲?(留뚯썝)", min_v, max_v, default_val, step=500, key="slider_dep")
                        st.session_state.filter_dep_price = dep_sel
                        if dep_sel[0] > min_v or dep_sel[1] < max_v:
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['蹂댁쬆湲?num'].between(dep_sel[0], dep_sel[1])]

                with c2:
                    if '?붿꽭_num' in raw_df.columns:
                        min_v, max_v = int(raw_df['?붿꽭_num'].min()), int(raw_df['?붿꽭_num'].max())
                        if min_v == max_v:
                            max_v += 10

                        default_val = st.session_state.filter_rent_price if st.session_state.filter_rent_price else (min_v, max_v)
                        default_val = (max(min_v, default_val[0]), min(max_v, default_val[1]))

                        rent_sel = st.slider("?뮫 ?붿꽭 (留뚯썝)", min_v, max_v, default_val, step=10, key="slider_rent")
                        st.session_state.filter_rent_price = rent_sel
                        if rent_sel[0] > min_v or rent_sel[1] < max_v:
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['?붿꽭_num'].between(rent_sel[0], rent_sel[1])]

            c3, c4 = st.columns(2)
            if '?꾩슜硫댁쟻_num' in raw_df.columns:
                with c3:
                    area_unit = st.radio(
                        "?뱪 硫댁쟻 湲곗?",
                        options=["怨듦툒硫댁쟻(?됲삎?)", "?꾩슜硫댁쟻(??"],
                        horizontal=True,
                        key="quick_area_unit"
                    )
                    st.session_state.filter_area_unit = area_unit

                    if area_unit == "怨듦툒硫댁쟻(?됲삎?)":
                        area_series = filtered_df['?꾩슜硫댁쟻_num'].apply(to_supply_pyeong_band)
                        band_order = [label for _, label in SUPPLY_PYEONG_BANDS]
                        options = [b for b in band_order if b in area_series.dropna().unique().tolist()]

                        default_bands = st.session_state.filter_supply_bands if st.session_state.filter_supply_bands else options
                        default_bands = [b for b in default_bands if b in options]
                        if not default_bands:
                            default_bands = options

                        sel_bands = st.multiselect("怨듦툒?됲삎? ?좏깮", options=options, default=default_bands, key="ms_supply_bands")
                        st.session_state.filter_supply_bands = sel_bands
                        st.session_state.filter_areas = []
                        if len(sel_bands) != len(options):
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[area_series.isin(sel_bands)]
                    else:
                        area_list = sorted(filtered_df['?꾩슜硫댁쟻_num'].unique())
                        default_areas = st.session_state.filter_areas if st.session_state.filter_areas else area_list
                        default_areas = [a for a in default_areas if a in area_list]
                        if not default_areas:
                            default_areas = area_list

                        sel_areas = st.multiselect("?꾩슜硫댁쟻 (??", options=area_list, default=default_areas, key="ms_areas")
                        st.session_state.filter_areas = sel_areas
                        st.session_state.filter_supply_bands = []
                        if len(sel_areas) != len(area_list):
                            quick_filter_active_count += 1
                        filtered_df = filtered_df[filtered_df['?꾩슜硫댁쟻_num'].isin(sel_areas)]

            if '痢?num' in raw_df.columns:
                floor_list = sorted(raw_df['痢?num'].unique().astype(int))

                default_floors = st.session_state.filter_floors if st.session_state.filter_floors else floor_list
                default_floors = [f for f in default_floors if f in floor_list]
                if not default_floors:
                    default_floors = floor_list

                with c4:
                    st.markdown("?룫 痢듭닔 ?좏깮")

                    for floor in floor_list:
                        floor_key = f"{filter_key_prefix}_floor_{floor}"
                        if floor_key not in st.session_state:
                            st.session_state[floor_key] = floor in default_floors

                    btn_col1, btn_col2 = st.columns(2)
                    select_all_floors = btn_col1.button("?꾩껜 ?좏깮", key=f"{filter_key_prefix}_floor_select_all", use_container_width=True)
                    clear_all_floors = btn_col2.button("?꾩껜 ?댁젣", key=f"{filter_key_prefix}_floor_clear_all", use_container_width=True)

                    if select_all_floors:
                        for floor in floor_list:
                            st.session_state[f"{filter_key_prefix}_floor_{floor}"] = True
                    elif clear_all_floors:
                        for floor in floor_list:
                            st.session_state[f"{filter_key_prefix}_floor_{floor}"] = False

                    floor_cols = st.columns(3)
                    sel_floors = []
                    for idx, floor in enumerate(floor_list):
                        with floor_cols[idx % 3]:
                            is_checked = st.checkbox(f"{floor}痢?, key=f"{filter_key_prefix}_floor_{floor}")
                        if is_checked:
                            sel_floors.append(floor)

                    st.session_state.filter_floors = sel_floors
                    if len(sel_floors) != len(floor_list):
                        quick_filter_active_count += 1
                    filtered_df = filtered_df[filtered_df['痢?num'].isin(sel_floors)]

        disp_df_base = filtered_df.drop(columns=actual_drop_cols)
        with tab_columns:
            disp_df, col_filter_active_count = apply_all_column_filters(disp_df_base, key_prefix=filter_key_prefix)

    st.markdown(
        f"""
        <div class="filter-bar">
            <div class="filter-chip">
                <span class="material-icons-outlined" style="font-size:14px;">dashboard_customize</span>
                Filter Studio
            </div>
            <div class="filter-stat">?쒖꽦 ?꾪꽣: 鍮좊Ⅸ ?꾪꽣 {quick_filter_active_count}媛?쨌 而щ읆 ?꾪꽣 {col_filter_active_count}媛?쨌 寃곌낵 <b style="color:#0ea5e9;">{len(disp_df):,}嫄?/b></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 由ъ뒪???꾪꽣 寃곌낵 ?몃뜳?ㅻ? ?먮낯 ?꾪꽣 寃곌낵??留ㅽ븨??吏?쒕룄 ?숈씪 湲곗??쇰줈 怨꾩궛
    metric_df = filtered_df.loc[disp_df.index] if not disp_df.empty else filtered_df.iloc[0:0]

    # --- ?듭떖 吏??諛??곗씠??異쒕젰 ---
    if not metric_df.empty:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card("珥?嫄곕옒", f"{len(metric_df):,}嫄?, "?꾩옱 ?꾪꽣 寃곌낵", key="metric_total")
        
        if current_type == "留ㅻℓ":
            if '留ㅻℓ媛_num' in metric_df.columns:
                with m2:
                    render_metric_card("?됯퇏 留ㅻℓ", f"{metric_df['留ㅻℓ媛_num'].mean():,.0f}留?, "嫄곕옒 ?④? ?됯퇏", key="metric_avg_sale")
                with m3:
                    render_metric_card("理쒓퀬 留ㅻℓ", f"{metric_df['留ㅻℓ媛_num'].max():,.0f}留?, "理쒓퀬 泥닿껐 湲덉븸", key="metric_max_sale")
        else:
            if '蹂댁쬆湲?num' in metric_df.columns:
                with m2:
                    render_metric_card("?됯퇏 蹂댁쬆湲?, f"{metric_df['蹂댁쬆湲?num'].mean():,.0f}留?, "蹂댁쬆湲??됯퇏", key="metric_avg_dep")
            if '?붿꽭_num' in metric_df.columns:
                with m3:
                    render_metric_card("?됯퇏 ?붿꽭", f"{metric_df['?붿꽭_num'].mean():,.0f}留?, "?붿꽭 ?됯퇏", key="metric_avg_rent")
        
        if '?꾩슜硫댁쟻_num' in metric_df.columns:
            with m4:
                render_metric_card("?됯퇏 硫댁쟻", f"{metric_df['?꾩슜硫댁쟻_num'].mean():,.1f}??, "?꾩슜硫댁쟻 ?됯퇏", key="metric_avg_area")
        
        st.divider()

        st.markdown('<div class="chart-card-title"><span class="material-icons-outlined" style="color:#ef4444;">trending_up</span>湲곌컙蹂?嫄곕옒 異붿씠</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-sub">?꾩썡??留ㅻℓ 吏?쒖? 嫄곕옒嫄댁닔瑜??④퍡 ?뺤씤?⑸땲??</div>', unsafe_allow_html=True)
        render_trade_type_chart(metric_df, current_type)
        if current_type == "?꾩썡??:
            st.markdown('<div class="chart-card-title" style="font-size:1.15rem; margin-top:0.9rem;"><span class="material-icons-outlined" style="color:#0ea5e9;">scatter_plot</span>蹂댁쬆湲??붿꽭 Polar Scatter</div>', unsafe_allow_html=True)
            render_rental_polar_scatter(metric_df)
        st.divider()
        
        # 理쒖쥌 由ъ뒪??異쒕젰
        st.markdown('<div class="chart-card-title" style="font-size:1.15rem;"><span class="material-icons-outlined" style="color:#0ea5e9;">table_chart</span>?ㅺ굅???댁뿭 由ъ뒪??/div>', unsafe_allow_html=True)
        render_awesome_table(disp_df)
        
        # ?ㅼ슫濡쒕뱶 踰꾪듉
        csv = disp_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("?뱿 Result CSV Download", data=csv, file_name=f"result_{datetime.datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
    else:
        st.warning("議고쉶???곗씠?곌? ?놁뒿?덈떎. ?꾪꽣 議곌굔??議곗젙??蹂댁꽭??")
else:
    # ?湲고솕硫?Hero
    st.markdown("""
    <div class="hero-container">
        <div class="hero-glow"></div>
        <div class="hero-title">Real Estate Insights</div>
        <div class="hero-subtitle">?곗씠??湲곕컲 ?꾪뙆???ㅺ굅?섍? 遺꾩꽍 ??쒕낫??/div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="main-note">?ъ씠?쒕컮?먯꽌 議고쉶??吏??낵 嫄곕옒 ?좏삎???좏깮??二쇱꽭??</div>', unsafe_allow_html=True)

