import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_csv(
        "ETN_SLO_2025_KPP_KPP_DELISTAVB_20260329.csv",
        sep=";",
        encoding="utf-8-sig",
        low_memory=False
    )

    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )

    return df

df = load_data()

# --- FIND COLUMNS ---
def find_col(df, keyword):
    for c in df.columns:
        if keyword in c:
            return c
    return None

CENA_COL = find_col(df, "CENA")
SIZE_COL = find_col(df, "UPORABNA")
YEAR_COL = find_col(df, "LETO_IZGRADNJE")
RABA_COL = find_col(df, "DEJANSKA_RABA")
OBCINA_COL = find_col(df, "OBCINA")
NASELJE_COL = find_col(df, "NASELJE")

# --- CHECK ---
if not CENA_COL or not SIZE_COL:
    st.error("Ne najdem stolpcev za CENO ali POVRŠINO")
    st.write(df.columns.tolist())
    st.stop()

# --- PRETVORBA V ŠTEVILKE ---
def to_numeric(series):
    return (
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
    )

df[CENA_COL] = pd.to_numeric(to_numeric(df[CENA_COL]), errors="coerce")
df[SIZE_COL] = pd.to_numeric(to_numeric(df[SIZE_COL]), errors="coerce")

if YEAR_COL:
    df[YEAR_COL] = pd.to_numeric(df[YEAR_COL], errors="coerce")

# --- CLEAN DATA ---
df = df.dropna(subset=[CENA_COL, SIZE_COL])

df = df[
    (df[CENA_COL] > 10000) &
    (df[CENA_COL] < 10_000_000) &
    (df[SIZE_COL] > 10) &
    (df[SIZE_COL] < 300)
]

df["CENA_NA_M2"] = df[CENA_COL] / df[SIZE_COL]

# --- SIDEBAR ---
st.sidebar.title("🔍 Filtri")

obcine = st.sidebar.multiselect(
    "Občina",
    sorted(df[OBCINA_COL].dropna().unique()) if OBCINA_COL else [],
)

naselja = st.sidebar.multiselect(
    "Naselje",
    sorted(df[NASELJE_COL].dropna().unique()) if NASELJE_COL else [],
)

raba = st.sidebar.multiselect(
    "Dejanska raba",
    sorted(df[RABA_COL].dropna().unique()) if RABA_COL else [],
)

# --- SAFE PRICE SLIDER ---
price_clean = df[CENA_COL].dropna()
price_clean = price_clean[(price_clean > 0) & (price_clean < 10_000_000)]

if price_clean.empty:
    min_price, max_price = 0, 500000
else:
    min_price = int(price_clean.min())
    max_price = int(price_clean.max())

default_min = max(min_price, 100000)
default_max = min(max_price, 400000)

if default_min >= default_max:
    default_min, default_max = min_price, max_price

price_range = st.sidebar.slider(
    "Cena (€)",
    min_price,
    max_price,
    (default_min, default_max),
)

# --- SIZE FILTER ---
col1, col2 = st.sidebar.columns(2)
min_size = col1.number_input("Min m²", value=40)
max_size = col2.number_input("Max m²", value=120)

# --- YEAR FILTER ---
if YEAR_COL and df[YEAR_COL].notna().any():
    year_clean = df[YEAR_COL].dropna()
    year_range = st.sidebar.slider(
        "Leto izgradnje",
        int(year_clean.min()),
        int(year_clean.max()),
        (2000, 2025),
    )
else:
    year_range = (1900, 2100)

# --- FILTER LOGIC ---
filtered = df.copy()

if obcine and OBCINA_COL:
    filtered = filtered[filtered[OBCINA_COL].isin(obcine)]

if naselja and NASELJE_COL:
    filtered = filtered[filtered[NASELJE_COL].isin(naselja)]

if raba and RABA_COL:
    filtered = filtered[filtered[RABA_COL].isin(raba)]

filtered = filtered[
    (filtered[CENA_COL] >= price_range[0]) &
    (filtered[CENA_COL] <= price_range[1])
]

filtered = filtered[
    (filtered[SIZE_COL] >= min_size) &
    (filtered[SIZE_COL] <= max_size)
]

if YEAR_COL:
    filtered = filtered[
        (filtered[YEAR_COL] >= year_range[0]) &
        (filtered[YEAR_COL] <= year_range[1])
    ]

# --- UI ---
st.title("🏠 Nepremičninski Dashboard")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Št. oglasov", len(filtered))
col2.metric("Povp. cena", f"{int(filtered[CENA_COL].mean()):,} €")
col3.metric("Povp. m²", f"{int(filtered[SIZE_COL].mean())}")
col4.metric("€/m²", f"{int(filtered['CENA_NA_M2'].mean())} €")

col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Cena")
    st.bar_chart(filtered[CENA_COL])

with col2:
    st.subheader("📐 €/m²")
    st.bar_chart(filtered["CENA_NA_M2"])

st.subheader("🔥 Najboljši deali")

top = filtered.sort_values("CENA_NA_M2").head(10)

st.dataframe(
    top[[c for c in [OBCINA_COL, NASELJE_COL, SIZE_COL, CENA_COL, "CENA_NA_M2"] if c]]
)

st.subheader("📋 Vsi rezultati")
st.dataframe(filtered)
