import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# --- LOAD DATA ---
df = pd.read_csv("ETN_SLO_2025_KPP_KPP_DELISTAVB_20260329.csv")

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

df = df[cols].dropna(subset=["CENA", "UPORABNA_POVRSINA"])

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

price_range = st.sidebar.slider(
    "Cena (€)",
    int(df["CENA"].min()),
    int(df["CENA"].max()),
    (100000, 400000),
)

size_range = st.sidebar.slider(
    "Površina (m²)",
    int(df["UPORABNA_POVRSINA"].min()),
    int(df["UPORABNA_POVRSINA"].max()),
    (40, 120),
)

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

filtered = filtered[
    (filtered["CENA"] >= price_range[0])
    & (filtered["CENA"] <= price_range[1])
]

filtered = filtered[
    (filtered["UPORABNA_POVRSINA"] >= size_range[0])
    & (filtered["UPORABNA_POVRSINA"] <= size_range[1])
]

filtered = filtered[
    (filtered["LETO_IZGRADNJE"] >= year_range[0])
    & (filtered["LETO_IZGRADNJE"] <= year_range[1])
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