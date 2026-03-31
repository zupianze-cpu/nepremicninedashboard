import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="ETN · Trg nepremičnin SLO 2025",
    page_icon="🏘",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; font-size: 15px; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

.metric-card {
    background: #fafafa;
    border: 1px solid #e4e4e4;
    border-radius: 8px;
    padding: 1rem 1.2rem;
}
.metric-label {
    font-size: 11px;
    font-weight: 500;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 5px;
}
.metric-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1a1a1a;
    line-height: 1.15;
}
.metric-sub {
    font-size: 11px;
    color: #bbb;
    margin-top: 3px;
}
.section-title {
    font-size: 11px;
    font-weight: 500;
    color: #aaa;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.75rem;
    padding-bottom: 5px;
    border-bottom: 1px solid #efefef;
}
</style>
""", unsafe_allow_html=True)

# Samo stanovanja in hiše
DOVOLJENE_RABE_KODE = {"1", "2", "3", "47"}

@st.cache_data
def load_data():
    df = pd.read_csv(
        "ETN_SLO_2025_KPP_KPP_DELISTAVB_20260329.csv",
        dtype=str,
        low_memory=False,
    )
    for col in ["CENA", "POVRSINA_DELA_STAVBE", "UPORABNA_POVRSINA", "LETO_IZGRADNJE_DELA_STAVBE"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Hardlock na stanovanja/hiše
    df["RABA_KODA"] = (
        df["DEJANSKA_RABA_DELA_STAVBE"]
        .str.strip()
        .str.extract(r"^(\d+)")
        .iloc[:, 0]
        .fillna("")
    )
    df = df[df["RABA_KODA"].isin(DOVOLJENE_RABE_KODE)]

    df["POVRSINA_ZA_IZRACUN"] = df["UPORABNA_POVRSINA"].where(
        df["UPORABNA_POVRSINA"] > 5, df["POVRSINA_DELA_STAVBE"]
    )
    df["CENA_M2"] = df["CENA"] / df["POVRSINA_ZA_IZRACUN"]

    df = df[
        df["CENA"].between(5_000, 5_000_000) &
        df["POVRSINA_ZA_IZRACUN"].between(10, 1000) &
        df["CENA_M2"].between(100, 15_000)
    ]
    for col in ["OBCINA", "NASELJE", "ULICA", "LEGA_DELA_STAVBE_V_STAVBI", "DEJANSKA_RABA_DELA_STAVBE"]:
        df[col] = df[col].fillna("").str.strip()
    return df

df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filtri")

    obcine = sorted(df["OBCINA"].unique())
    sel_obcina = st.multiselect("Občina", obcine, default=["LJUBLJANA"])

    df_ob = df[df["OBCINA"].isin(sel_obcina)] if sel_obcina else df
    naselja = sorted(df_ob["NASELJE"].unique())
    sel_naselje = st.multiselect("Naselje", naselja)

    lege = sorted([l for l in df["LEGA_DELA_STAVBE_V_STAVBI"].unique() if l])
    sel_lega = st.multiselect("Lega v stavbi", lege)

    st.markdown("---")

    pov_min = int(df["POVRSINA_ZA_IZRACUN"].min())
    pov_max = int(df["POVRSINA_ZA_IZRACUN"].max())
    sel_pov = st.slider("Površina (m²)", pov_min, pov_max, (30, 150))

    cena_min = int(df["CENA"].min())
    cena_max = int(df["CENA"].max())
    sel_cena = st.slider("Cena (€)", cena_min, cena_max, (50_000, 800_000), step=5_000)

    leto_vals = df["LETO_IZGRADNJE_DELA_STAVBE"].dropna()
    sel_leto = st.slider("Leto izgradnje", int(leto_vals.min()), int(leto_vals.max()), (1950, 2025))

# ── Filter ────────────────────────────────────────────────────────────────────
filt = df.copy()
if sel_obcina:
    filt = filt[filt["OBCINA"].isin(sel_obcina)]
if sel_naselje:
    filt = filt[filt["NASELJE"].isin(sel_naselje)]
if sel_lega:
    filt = filt[filt["LEGA_DELA_STAVBE_V_STAVBI"].isin(sel_lega)]
filt = filt[filt["POVRSINA_ZA_IZRACUN"].between(*sel_pov)]
filt = filt[filt["CENA"].between(*sel_cena)]
filt = filt[
    filt["LETO_IZGRADNJE_DELA_STAVBE"].between(*sel_leto) |
    filt["LETO_IZGRADNJE_DELA_STAVBE"].isna()
]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## ETN · Trg nepremičnin SLO 2025")
st.markdown(
    f"<div class='section-title'>Stanovanja in hiše &nbsp;·&nbsp; {len(filt):,} poslov v izboru</div>",
    unsafe_allow_html=True
)

if len(filt) == 0:
    st.warning("Ni podatkov za izbrane filtre.")
    st.stop()

# ── KPI ───────────────────────────────────────────────────────────────────────
avg_m2   = filt["CENA_M2"].mean()
med_m2   = filt["CENA_M2"].median()
avg_cena = filt["CENA"].mean()
med_cena = filt["CENA"].median()
n_poslov = len(filt)
avg_pov  = filt["POVRSINA_ZA_IZRACUN"].mean()
p25      = filt["CENA_M2"].quantile(0.25)
p75      = filt["CENA_M2"].quantile(0.75)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena / m²</div>
        <div class='metric-value'>{avg_m2:,.0f} €</div>
        <div class='metric-sub'>mediana {med_m2:,.0f} €/m²</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena posla</div>
        <div class='metric-value'>{avg_cena/1000:,.0f} k€</div>
        <div class='metric-sub'>mediana {med_cena/1000:,.0f} k€</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Število poslov</div>
        <div class='metric-value'>{n_poslov:,}</div>
        <div class='metric-sub'>v izbranem filtru</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. površina</div>
        <div class='metric-value'>{avg_pov:.0f} m²</div>
        <div class='metric-sub'>uporabna / neto</div>
    </div>""", unsafe_allow_html=True)

with c5:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Razpon cen / m²</div>
        <div class='metric-value'>{p25:,.0f} – {p75:,.0f}</div>
        <div class='metric-sub'>25. – 75. percentil</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabela ────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Posli v izboru — razvrščeni po ceni / m²</div>", unsafe_allow_html=True)

tabela = (
    filt[[
        "OBCINA", "NASELJE", "ULICA", "HISNA_STEVILKA",
        "LETO_IZGRADNJE_DELA_STAVBE", "POVRSINA_ZA_IZRACUN",
        "CENA", "CENA_M2", "DEJANSKA_RABA_DELA_STAVBE", "LEGA_DELA_STAVBE_V_STAVBI"
    ]]
    .sort_values("CENA_M2", ascending=False)
    .copy()
)
tabela["CENA"]                       = tabela["CENA"].apply(lambda x: f"{x:,.0f} €")
tabela["CENA_M2"]                    = tabela["CENA_M2"].apply(lambda x: f"{x:,.0f} €/m²")
tabela["POVRSINA_ZA_IZRACUN"]        = tabela["POVRSINA_ZA_IZRACUN"].apply(lambda x: f"{x:.1f} m²")
tabela["LETO_IZGRADNJE_DELA_STAVBE"] = tabela["LETO_IZGRADNJE_DELA_STAVBE"].apply(
    lambda x: str(int(x)) if pd.notna(x) else ""
)
tabela.columns = ["Občina", "Naselje", "Ulica", "Hišna št.", "Leto izgr.",
                  "Površina", "Cena", "Cena/m²", "Raba", "Lega"]
st.dataframe(tabela, use_container_width=True, hide_index=True)
