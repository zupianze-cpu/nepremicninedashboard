import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_csv(
        "ETN_SLO_2025_KPP_KPP_DELISTAVB_20260329.csv",
        sep=";"
    )
    # normalizacija imen
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    return df

df = load_data()

# --- PREVERI KLJUČNE STOLPCE ---
required_cols = ["CENA", "UPORABNA_POVRSINA"]

missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Manjkajo stolpci: {missing}")
    st.write(df.columns.tolist())
    st.stop()

# --- LETO IZGRADNJE FIX ---
if "LETO_IZGRADNJE_DELA_STAVBE" in df.columns:
    df["LETO_IZGRADNJE"] = pd.to_numeric(
        df["LETO_IZGRADNJE_DELA_STAVBE"],
        errors="coerce"
    )
else:
    df["LETO_IZGRADNJE"] = None

# --- IZBOR STOLPCEV ---
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

available_cols = [c for c in cols if c in df.columns]
df = df[available_cols]

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
    sorted(df["OBCINA"].dropna().unique()) if "OBCINA" in df.columns else [],
)

naselja = st.sidebar.multiselect(
    "Naselje",
    sorted(df["NASELJE"].dropna().unique()) if "NASELJE" in df.columns else [],
)

raba = st.sidebar.multiselect(
    "Dejanska raba",
    sorted(df["DEJANSKA_RABA_DELA_STAVBE"].dropna().unique())
    if "DEJANSKA_RABA_DELA_STAVBE" in df.columns else [],
)

# cena slider
price_range = st.sidebar.slider(
    "Cena (€)",
    int(df["CENA"].min()),
    int(df["CENA"].max()),
    (100000, 400000),
)

# površina FIX (number input)
col1, col2 = st.sidebar.columns(2)
min_size = col1.number_input("Min m²", value=40)
max_size = col2.number_input("Max m²", value=120)

# leto slider (safe)
if df["LETO_IZGRADNJE"].notna().any():
    year_range = st.sidebar.slider(
        "Leto izgradnje",
        int(df["LETO_IZGRADNJE"].min()),
        int(df["LETO_IZGRADNJE"].max()),
        (2000, 2025),
    )
else:
    year_range = (1900, 2100)

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
        [c for c in ["OBCINA", "NASELJE", "UPORABNA_POVRSINA", "CENA", "CENA_NA_M2"] if c in df.columns]
    ]
)

# --- FULL TABLE ---
st.subheader("📋 Vsi rezultati")

st.dataframe(filtered.sort_values("CENA"))
