import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="ETN · Trg nepremičnin SLO 2025",
    page_icon="🏘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Stil ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@300;400&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

.metric-card {
    background: #0f0f0f;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    text-align: left;
}
.metric-label {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #f0f0f0;
    line-height: 1;
}
.metric-sub {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #555;
    margin-top: 4px;
}
.section-title {
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #555;
    margin-bottom: 1rem;
    border-bottom: 1px solid #1e1e1e;
    padding-bottom: 8px;
}
h1 { font-family: 'Syne', sans-serif !important; font-weight: 800 !important; }
</style>
""", unsafe_allow_html=True)

# ── Podatki ───────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv(
        "ETN_SLO_2025_KPP_KPP_DELISTAVB_20260329.csv",
        dtype=str,
        low_memory=False,
    )
    # Numerični stolpci
    for col in ["CENA", "POVRSINA_DELA_STAVBE", "UPORABNA_POVRSINA", "LETO_IZGRADNJE_DELA_STAVBE"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Normalizacija rabe (lowercase, strip)
    df["DEJANSKA_RABA_DELA_STAVBE"] = df["DEJANSKA_RABA_DELA_STAVBE"].str.strip().str.lower()

    # Cena/m2 (po uporabni površini, fallback na POVRSINA)
    df["POVRSINA_ZA_IZRACUN"] = df["UPORABNA_POVRSINA"].where(
        df["UPORABNA_POVRSINA"] > 5, df["POVRSINA_DELA_STAVBE"]
    )
    df["CENA_M2"] = df["CENA"] / df["POVRSINA_ZA_IZRACUN"]

    # Filter outlierjev (razumne vrednosti)
    df = df[
        df["CENA"].between(5_000, 5_000_000) &
        df["POVRSINA_ZA_IZRACUN"].between(10, 1000) &
        df["CENA_M2"].between(100, 15_000)
    ]

    # String stolpci počisti
    for col in ["OBCINA", "NASELJE", "ULICA", "LEGA_DELA_STAVBE_V_STAVBI"]:
        df[col] = df[col].fillna("").str.strip()

    return df

df = load_data()

# ── Sidebar filtri ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Filtri")

    # Občina
    obcine = sorted(df["OBCINA"].unique())
    sel_obcina = st.multiselect("Občina", obcine, default=["LJUBLJANA"])

    # Naselje — odvisno od občine
    df_ob = df[df["OBCINA"].isin(sel_obcina)] if sel_obcina else df
    naselja = sorted(df_ob["NASELJE"].unique())
    sel_naselje = st.multiselect("Naselje", naselja)

    # Raba
    rabe_vse = sorted(df["DEJANSKA_RABA_DELA_STAVBE"].unique())
    # Privzeto: stanovanja
    default_rabe = [r for r in rabe_vse if "stanovanje" in r]
    sel_raba = st.multiselect("Dejanska raba", rabe_vse, default=default_rabe)

    # Lega
    lege = sorted(df["LEGA_DELA_STAVBE_V_STAVBI"].unique())
    sel_lega = st.multiselect("Lega v stavbi", lege)

    st.markdown("---")
    st.markdown("### 📐 Površina (m²)")
    pov_min, pov_max = int(df["POVRSINA_ZA_IZRACUN"].min()), int(df["POVRSINA_ZA_IZRACUN"].max())
    sel_pov = st.slider("Površina", pov_min, pov_max, (30, 150))

    st.markdown("### 💰 Cena (€)")
    cena_min, cena_max = int(df["CENA"].min()), int(df["CENA"].max())
    sel_cena = st.slider("Cena", cena_min, cena_max, (50_000, 800_000), step=5_000,
                         format="%d €")

    st.markdown("### 🏗 Leto izgradnje")
    leto_vals = df["LETO_IZGRADNJE_DELA_STAVBE"].dropna()
    sel_leto = st.slider("Leto", int(leto_vals.min()), int(leto_vals.max()), (1950, 2025))

# ── Filter podatkov ───────────────────────────────────────────────────────────
filt = df.copy()
if sel_obcina:
    filt = filt[filt["OBCINA"].isin(sel_obcina)]
if sel_naselje:
    filt = filt[filt["NASELJE"].isin(sel_naselje)]
if sel_raba:
    filt = filt[filt["DEJANSKA_RABA_DELA_STAVBE"].isin(sel_raba)]
if sel_lega:
    filt = filt[filt["LEGA_DELA_STAVBE_V_STAVBI"].isin(sel_lega)]
filt = filt[filt["POVRSINA_ZA_IZRACUN"].between(*sel_pov)]
filt = filt[filt["CENA"].between(*sel_cena)]
filt = filt[filt["LETO_IZGRADNJE_DELA_STAVBE"].between(*sel_leto) |
            filt["LETO_IZGRADNJE_DELA_STAVBE"].isna()]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🏘 ETN · Trg nepremičnin SLO 2025")
st.markdown(f"<div class='section-title'>Evidenca trga nepremičnin · {len(filt):,} poslov v izboru</div>",
            unsafe_allow_html=True)

if len(filt) == 0:
    st.warning("Ni podatkov za izbrane filtre.")
    st.stop()

# ── KPI kartice ───────────────────────────────────────────────────────────────
avg_m2   = filt["CENA_M2"].mean()
med_m2   = filt["CENA_M2"].median()
avg_cena = filt["CENA"].mean()
med_cena = filt["CENA"].median()
n_poslov = len(filt)
avg_pov  = filt["POVRSINA_ZA_IZRACUN"].mean()
p25 = filt["CENA_M2"].quantile(0.25)
p75 = filt["CENA_M2"].quantile(0.75)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena / m²</div>
        <div class='metric-value'>{avg_m2:,.0f} €</div>
        <div class='metric-sub'>mediana {med_m2:,.0f} €/m²</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena posla</div>
        <div class='metric-value'>{avg_cena/1000:,.0f}k €</div>
        <div class='metric-sub'>mediana {med_cena/1000:,.0f}k €</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Število poslov</div>
        <div class='metric-value'>{n_poslov:,}</div>
        <div class='metric-sub'>v izbranem filtru</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. površina</div>
        <div class='metric-value'>{avg_pov:.0f} m²</div>
        <div class='metric-sub'>uporabna / neto</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>IQR cena / m²</div>
        <div class='metric-value'>{p25:,.0f}–{p75:,.0f}</div>
        <div class='metric-sub'>25.–75. percentil</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Graf 1: Histogram cena/m2 + Graf 2: Scatter površina vs cena ──────────────
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("<div class='section-title'>Porazdelitev cene / m²</div>", unsafe_allow_html=True)
    fig_hist = px.histogram(
        filt, x="CENA_M2", nbins=60,
        color_discrete_sequence=["#e8ff47"],
        template="plotly_dark",
    )
    fig_hist.add_vline(x=avg_m2, line_dash="dash", line_color="#ff6b6b",
                       annotation_text=f"povp. {avg_m2:,.0f} €", annotation_position="top right")
    fig_hist.add_vline(x=med_m2, line_dash="dot", line_color="#6bffb8",
                       annotation_text=f"med. {med_m2:,.0f} €", annotation_position="top left")
    fig_hist.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="€/m²", yaxis_title="Število poslov",
        showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col_b:
    st.markdown("<div class='section-title'>Površina vs. cena posla</div>", unsafe_allow_html=True)
    fig_scatter = px.scatter(
        filt.sample(min(len(filt), 2000), random_state=42),
        x="POVRSINA_ZA_IZRACUN", y="CENA",
        color="CENA_M2",
        color_continuous_scale="YlOrRd",
        hover_data=["OBCINA", "NASELJE", "ULICA"],
        template="plotly_dark",
        opacity=0.7,
    )
    fig_scatter.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Površina (m²)", yaxis_title="Cena (€)",
        coloraxis_colorbar_title="€/m²",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# ── Graf 3: Top naselja po povp cena/m2 + Graf 4: Cena/m2 po letu izgradnje ──
col_c, col_d = st.columns(2)

with col_c:
    st.markdown("<div class='section-title'>Povp. cena / m² po naselju (top 20)</div>", unsafe_allow_html=True)
    top_naselja = (
        filt.groupby("NASELJE")["CENA_M2"]
        .agg(["mean", "count"])
        .query("count >= 3")
        .sort_values("mean", ascending=True)
        .tail(20)
        .reset_index()
    )
    fig_bar = px.bar(
        top_naselja, y="NASELJE", x="mean",
        orientation="h",
        color="mean",
        color_continuous_scale="YlOrRd",
        template="plotly_dark",
        text=top_naselja["mean"].apply(lambda x: f"{x:,.0f} €"),
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="€/m²", yaxis_title="",
        showlegend=False, coloraxis_showscale=False,
        margin=dict(l=0, r=60, t=10, b=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_d:
    st.markdown("<div class='section-title'>Cena / m² glede na leto izgradnje</div>", unsafe_allow_html=True)
    leto_grp = (
        filt.dropna(subset=["LETO_IZGRADNJE_DELA_STAVBE"])
        .groupby("LETO_IZGRADNJE_DELA_STAVBE")["CENA_M2"]
        .agg(["median", "count"])
        .query("count >= 3")
        .reset_index()
    )
    fig_leto = px.scatter(
        leto_grp,
        x="LETO_IZGRADNJE_DELA_STAVBE", y="median",
        size="count", size_max=30,
        color="median",
        color_continuous_scale="YlOrRd",
        template="plotly_dark",
        hover_data={"count": True, "median": ":.0f"},
    )
    fig_leto.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Leto izgradnje", yaxis_title="Mediana €/m²",
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_leto, use_container_width=True)

# ── Graf 5: Box plot po legi ───────────────────────────────────────────────────
st.markdown("<div class='section-title'>Razporeditev cene / m² po legi v stavbi</div>", unsafe_allow_html=True)

lega_data = filt[filt["LEGA_DELA_STAVBE_V_STAVBI"] != ""]
if len(lega_data) > 0:
    fig_box = px.box(
        lega_data, x="LEGA_DELA_STAVBE_V_STAVBI", y="CENA_M2",
        color="LEGA_DELA_STAVBE_V_STAVBI",
        color_discrete_sequence=["#e8ff47", "#6bffb8", "#ff6b6b"],
        template="plotly_dark",
        points="outliers",
    )
    fig_box.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Lega", yaxis_title="€/m²",
        showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
        height=300,
    )
    st.plotly_chart(fig_box, use_container_width=True)

# ── Tabela: Dražji posli ───────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Najdražji posli v izboru (top 20 po ceni/m²)</div>", unsafe_allow_html=True)

tabela = (
    filt[["OBCINA", "NASELJE", "ULICA", "HISNA_STEVILKA",
          "LETO_IZGRADNJE_DELA_STAVBE", "POVRSINA_ZA_IZRACUN",
          "CENA", "CENA_M2", "DEJANSKA_RABA_DELA_STAVBE", "LEGA_DELA_STAVBE_V_STAVBI"]]
    .sort_values("CENA_M2", ascending=False)
    .head(20)
    .copy()
)
tabela["CENA"] = tabela["CENA"].apply(lambda x: f"{x:,.0f} €")
tabela["CENA_M2"] = tabela["CENA_M2"].apply(lambda x: f"{x:,.0f} €/m²")
tabela["POVRSINA_ZA_IZRACUN"] = tabela["POVRSINA_ZA_IZRACUN"].apply(lambda x: f"{x:.1f} m²")
tabela["LETO_IZGRADNJE_DELA_STAVBE"] = tabela["LETO_IZGRADNJE_DELA_STAVBE"].apply(
    lambda x: str(int(x)) if pd.notna(x) else ""
)
tabela.columns = ["Občina", "Naselje", "Ulica", "Hišna št.", "Leto izgr.",
                  "Površina", "Cena", "Cena/m²", "Raba", "Lega"]
st.dataframe(tabela, use_container_width=True, hide_index=True)
