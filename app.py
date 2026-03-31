import streamlit as st
import pandas as pd
import re

st.set_page_config(layout="wide")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_csv(
        "ETN_SLO_2025_KPP_KPP_DELISTAVB_20260329.csv",
        sep=";"
    )
    df.columns = df.columns.str.strip().str.upper()
    return df

df = load_data()

# --- COLUMN MAP (prilagodi če treba) ---
cols = [
    "OBCINA",
    "NASELJE",
    "ULICA",
    "HISNA_STEVILKA",
    "LETO_IZGRADNJE",
    "PRODANA_POVRSINA",
    "DEJANSKA_RABA_DELA_STAVBE",
    "UPORABNA_POVRSINA",
    "CENA",
]

df = df[[c for c in cols if c in df.columns]]

# --- CLEAN DATA ---
df = df.dropna(subset=["CENA", "UPORABNA_POVRSINA"])

df = df[
    (df["CENA"] > 10000) &
    (df["UPORABNA_POVRSINA"] > 10) &
    (df["UPORABNA_POVRSINA"] < 300)
]

# €/m²
df["CENA_NA_M2"] = df["CENA"] / df["UPORABNA_POVRSINA"]

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Filtri")

obcine = st.sidebar.multiselect(
    "Občina",
    sorted(df["OBCINA"].dropna().unique()),
)

naselja = st.sidebar.multiselect(
    "Naselje",
    sorted(df["NASELJE"].dropna().unique()),
)

raba = st.sidebar.multiselect(
    "Dejanska raba",
    sorted(df["DEJANSKA_RABA_DELA_STAVBE"].dropna().unique()),
)

price_range = st.sidebar.slider(
    "Cena (€)",
    int(df["CENA"].min()),
    int(df["CENA"].max()),
    (100000, 400000),
)

# --- POPRAVLJEN SIZE FILTER ---
col1, col2 = st.sidebar.columns(2)
min_size = col1.number_input("Min m²", value=40)
max_size = col2.number_input("Max m²", value=120)

year_range = st.sidebar.slider(
    "Leto izgradnje",
    int(df["LETO_IZGRADNJE"].min()),
    int(df["LETO_IZGRADNJE"].max()),
    (2000, 2025),
)

# --- FILTER LOGIC ---
filtered = df.copy()

if obcine:
    filtered = filtered[filtered["OBCINA"].isin(obcine)]

if naselja:
    filtered = filtered[filtered["NASELJE"].isin(naselja)]

if raba:
    filtered = filtered[filtered["DEJANSKA_RABA_DELA_STAVBE"].isin(raba)]

filtered = filtered[
    (filtered["CENA"] >= price_range[0]) &
    (filtered["CENA"] <= price_range[1])
]

filtered = filtered[
    (filtered["UPORABNA_POVRSINA"] >= min_size) &
    (filtered["UPORABNA_POVRSINA"] <= max_size)
]

filtered = filtered[
    (filtered["LETO_IZGRADNJE"] >= year_range[0]) &
    (filtered["LETO_IZGRADNJE"] <= year_range[1])
]

# --- HEADER ---
st.title("🏠 Nepremičninski Dashboard")

# --- KPIs ---
col1, col2, col3, col4 = st.columns(4)

col1.metric("Št. oglasov", len(filtered))
col2.metric("Povp. cena", f"{int(filtered['CENA'].mean()):,} €")
col3.metric("Povp. m²", f"{int(filtered['UPORABNA_POVRSINA'].mean())}")
col4.metric("€/m²", f"{int(filtered['CENA_NA_M2'].mean())} €")

# --- GRAFI ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Cena distribucija")
    st.bar_chart(filtered["CENA"])

with col2:
    st.subheader("📐 Cena na m²")
    st.bar_chart(filtered["CENA_NA_M2"])

# --- TOP DEALS ---
st.subheader("🔥 Najboljši deali (najnižji €/m²)")

top_deals = filtered.sort_values("CENA_NA_M2").head(10)

st.dataframe(
    top_deals[
        [
            "OBCINA",
            "NASELJE",
            "UPORABNA_POVRSINA",
            "CENA",
            "CENA_NA_M2",
        ]
    ]
)

# --- FULL TABLE ---
st.subheader("📋 Vsi rezultati")

st.dataframe(filtered.sort_values("CENA"))