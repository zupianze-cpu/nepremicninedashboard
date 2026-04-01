import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="ETN · Trg nepremičnin SLO 2015–2025",
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

DOVOLJENE_RABE_KODE = {"1", "2", "3", "47"}

@st.cache_data
def load_data():
    df = pd.read_excel(
        "2015-2025git.xlsx",
        dtype=str,
        engine="openpyxl",
    )

    # Numerični stolpci
    for col in ["CENA", "POVRSINA_DELA_STAVBE", "UPORABNA_POVRSINA",
                "LETO_IZGRADNJE_DELA_STAVBE", "LETO"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Hardlock raba
    df["RABA_KODA"] = (
        df["DEJANSKA_RABA_DELA_STAVBE"]
        .str.strip()
        .str.extract(r"^(\d+)")
        .iloc[:, 0]
        .fillna("")
    )
    df = df[df["RABA_KODA"].isin(DOVOLJENE_RABE_KODE)]

    # Površina za izračun
    df["POVRSINA_ZA_IZRACUN"] = df["UPORABNA_POVRSINA"].where(
        df["UPORABNA_POVRSINA"] > 5, df["POVRSINA_DELA_STAVBE"]
    )
    df["CENA_M2"] = df["CENA"] / df["POVRSINA_ZA_IZRACUN"]

    # Outlier filter
    df = df[
        df["CENA"].between(5_000, 5_000_000) &
        df["POVRSINA_ZA_IZRACUN"].between(10, 1000) &
        df["CENA_M2"].between(100, 15_000)
    ]

    # String stolpci
    for col in ["OBCINA", "NASELJE", "ULICA", "LEGA_DELA_STAVBE_V_STAVBI",
                "DEJANSKA_RABA_DELA_STAVBE", "PARCELA"]:
        if col in df.columns:
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

    # Leto posla
    if "LETO" in df.columns:
        leta_posla = sorted(df["LETO"].dropna().astype(int).unique())
        sel_leto_posla = st.multiselect(
            "Leto posla", leta_posla, default=leta_posla,
            help="Filtriraj po letu sklenitve posla"
        )
    else:
        sel_leto_posla = []

    st.markdown("---")

    pov_min = int(df["POVRSINA_ZA_IZRACUN"].min())
    pov_max = int(df["POVRSINA_ZA_IZRACUN"].max())
    sel_pov = st.slider("Površina (m²)", pov_min, pov_max, (30, 150))

    cena_min = int(df["CENA"].min())
    cena_max = int(df["CENA"].max())
    sel_cena = st.slider("Cena (€)", cena_min, cena_max, (50_000, 800_000), step=5_000)

    leto_izgr = df["LETO_IZGRADNJE_DELA_STAVBE"].dropna()
    sel_leto_izgr = st.slider(
        "Leto izgradnje", int(leto_izgr.min()), int(leto_izgr.max()), (1950, 2025)
    )

# ── Filter ────────────────────────────────────────────────────────────────────
filt = df.copy()
if sel_obcina:
    filt = filt[filt["OBCINA"].isin(sel_obcina)]
if sel_naselje:
    filt = filt[filt["NASELJE"].isin(sel_naselje)]
if sel_lega:
    filt = filt[filt["LEGA_DELA_STAVBE_V_STAVBI"].isin(sel_lega)]
if sel_leto_posla and "LETO" in filt.columns:
    filt = filt[filt["LETO"].isin([float(l) for l in sel_leto_posla])]
filt = filt[filt["POVRSINA_ZA_IZRACUN"].between(*sel_pov)]
filt = filt[filt["CENA"].between(*sel_cena)]
filt = filt[
    filt["LETO_IZGRADNJE_DELA_STAVBE"].between(*sel_leto_izgr) |
    filt["LETO_IZGRADNJE_DELA_STAVBE"].isna()
]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## ETN · Trg nepremičnin SLO 2015–2025")
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

# Delež z dodatno parcelo
has_parcela = "PARCELA" in filt.columns
if has_parcela:
    n_parcela = (filt["PARCELA"].str.len() > 0).sum()
    pct_parcela = n_parcela / len(filt) * 100

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
    if has_parcela:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Dodatna parcela</div>
            <div class='metric-value'>{n_parcela:,}</div>
            <div class='metric-sub'>{pct_parcela:.1f} % poslov</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Razpon cen / m²</div>
            <div class='metric-value'>{p25:,.0f} – {p75:,.0f}</div>
            <div class='metric-sub'>25. – 75. percentil</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Graf ──────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Cena / m² glede na uporabno površino — primerjava po občinah</div>", unsafe_allow_html=True)

vse_obcine = sorted(df["OBCINA"].unique())
top5 = df["OBCINA"].value_counts().head(5).index.tolist()

graf_obcine = st.multiselect(
    "Občine za primerjavo (max 10)",
    options=vse_obcine,
    default=top5,
    max_selections=10,
    key="graf_obcine"
)

if graf_obcine:
    bin_size = 10
    graf_df = df[df["OBCINA"].isin(graf_obcine)].copy()
    # Upoštevaj filter leta posla tudi v grafu
    if sel_leto_posla and "LETO" in graf_df.columns:
        graf_df = graf_df[graf_df["LETO"].isin([float(l) for l in sel_leto_posla])]
    graf_df["POV_RAZRED"] = (graf_df["POVRSINA_ZA_IZRACUN"] // bin_size * bin_size).astype(int)

    grp = (
        graf_df.groupby(["OBCINA", "POV_RAZRED"])["CENA_M2"]
        .agg(povprecje="mean", mediana="median", n="count")
        .reset_index()
        .query("n >= 3 and POV_RAZRED <= 200")
        .sort_values("POV_RAZRED")
    )

    tab1, tab2 = st.tabs(["Povprečje", "Mediana"])

    COLORS = [
        "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed",
        "#0891b2", "#be185d", "#65a30d", "#ea580c", "#6366f1",
    ]

    def make_fig(metric, label):
        fig = go.Figure()
        for i, obcina in enumerate(graf_obcine):
            d = grp[grp["OBCINA"] == obcina]
            if d.empty:
                continue
            color = COLORS[i % len(COLORS)]
            fig.add_trace(go.Scatter(
                x=d["POV_RAZRED"], y=d[metric],
                mode="lines+markers",
                name=obcina.title(),
                line=dict(color=color, width=2),
                marker=dict(size=5, color=color),
                hovertemplate=(
                    f"<b>{obcina.title()}</b><br>"
                    f"Površina: %{{x}}–{bin_size} m²<br>"
                    f"{label}: %{{y:,.0f}} €/m²<extra></extra>"
                ),
            ))
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Uporabna površina (m²)",
            yaxis_title=f"{label} cene (€/m²)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=0, r=0, t=40, b=0),
            height=420,
            font=dict(family="IBM Plex Sans", size=12),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#fafafa",
            xaxis=dict(gridcolor="#efefef"),
            yaxis=dict(gridcolor="#efefef"),
        )
        return fig

    with tab1:
        st.plotly_chart(make_fig("povprecje", "Povprečje"), use_container_width=True)
    with tab2:
        st.plotly_chart(make_fig("mediana", "Mediana"), use_container_width=True)
else:
    st.info("Izberi vsaj eno občino za prikaz grafa.")

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabela ────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Posli v izboru — razvrščeni po ceni / m²</div>", unsafe_allow_html=True)

tabela_cols = ["OBCINA", "NASELJE", "ULICA", "HISNA_STEVILKA",
               "LETO_IZGRADNJE_DELA_STAVBE", "POVRSINA_ZA_IZRACUN",
               "CENA", "CENA_M2", "DEJANSKA_RABA_DELA_STAVBE",
               "LEGA_DELA_STAVBE_V_STAVBI"]
col_names   = ["Občina", "Naselje", "Ulica", "Hišna št.", "Leto izgr.",
               "Površina", "Cena", "Cena/m²", "Raba", "Lega"]

if "LETO" in filt.columns:
    tabela_cols.insert(4, "LETO")
    col_names.insert(4, "Leto posla")

if "PARCELA" in filt.columns:
    tabela_cols.append("PARCELA")
    col_names.append("Dodatna parcela")

tabela = filt[tabela_cols].sort_values("CENA_M2", ascending=False).copy()
tabela["CENA"]                       = tabela["CENA"].apply(lambda x: f"{x:,.0f} €")
tabela["CENA_M2"]                    = tabela["CENA_M2"].apply(lambda x: f"{x:,.0f} €/m²")
tabela["POVRSINA_ZA_IZRACUN"]        = tabela["POVRSINA_ZA_IZRACUN"].apply(lambda x: f"{x:.1f} m²")
tabela["LETO_IZGRADNJE_DELA_STAVBE"] = tabela["LETO_IZGRADNJE_DELA_STAVBE"].apply(
    lambda x: str(int(x)) if pd.notna(x) else ""
)
if "LETO" in tabela.columns:
    tabela["LETO"] = tabela["LETO"].apply(lambda x: str(int(x)) if pd.notna(x) else "")

tabela.columns = col_names
st.dataframe(tabela, use_container_width=True, hide_index=True)
