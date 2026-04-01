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
    background: #003DA5;
    border: 1px solid #0031a0;
    border-radius: 8px;
    padding: 1rem 1.2rem;
}
.metric-label {
    font-size: 11px;
    font-weight: 600;
    color: #a8c4f0;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 5px;
}
.metric-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.15;
}
.metric-sub {
    font-size: 11px;
    color: #7aaee8;
    margin-top: 3px;
}
.section-title {
    font-size: 11px;
    font-weight: 600;
    color: #003DA5;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.75rem;
    padding-bottom: 5px;
    border-bottom: 2px solid #003DA5;
}
h2 { color: #003DA5 !important; }
</style>
""", unsafe_allow_html=True)

DOVOLJENE_RABE_KODE = {"1", "2", "3", "47"}

@st.cache_data
def load_data():
    df = pd.read_excel("2015-2025git.xlsx", dtype=str, engine="openpyxl")

    for col in ["CENA", "POVRSINA_DELA_STAVBE", "UPORABNA_POVRSINA",
                "LETO_IZGRADNJE_DELA_STAVBE", "LETO"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["RABA_KODA"] = (
        df["DEJANSKA_RABA_DELA_STAVBE"]
        .str.strip()
        .str.extract(r"^(\d+)")
        .iloc[:, 0]
        .fillna("")
    )
    df = df[df["RABA_KODA"].isin(DOVOLJENE_RABE_KODE)]

    # Površina za izračun cena/m2 = uporabna, fallback na POVRSINA_DELA_STAVBE
    df["POVRSINA_ZA_IZRACUN"] = df["UPORABNA_POVRSINA"].where(
        df["UPORABNA_POVRSINA"] > 5, df["POVRSINA_DELA_STAVBE"]
    )
    df["CENA_M2_UPR"]  = df["CENA"] / df["POVRSINA_ZA_IZRACUN"]
    df["CENA_M2_DELA"] = df["CENA"] / df["POVRSINA_DELA_STAVBE"]

    df = df[
        df["CENA"].between(5_000, 5_000_000) &
        df["POVRSINA_ZA_IZRACUN"].between(10, 1000) &
        df["CENA_M2_UPR"].between(100, 15_000)
    ]

    for col in ["OBCINA", "NASELJE", "ULICA", "HISNA_STEVILKA",
                "STEVILKA_STANOVANJA_ALI_POSLOVNEGA_PROSTORA",
                "LEGA_DELA_STAVBE_V_STAVBI", "DEJANSKA_RABA_DELA_STAVBE", "PARCELA"]:
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

    ulice = sorted([u for u in df_ob["ULICA"].unique() if u])
    sel_ulica = st.multiselect("Ulica", ulice)

    sel_hisna = st.text_input("Hišna številka", "")

    sel_st_stanovanja = st.text_input("Številka stanovanja / poslovnega prostora", "")

    lege = sorted([l for l in df["LEGA_DELA_STAVBE_V_STAVBI"].unique() if l])
    sel_lega = st.multiselect("Lega v stavbi", lege)

    st.markdown("---")

    if "LETO" in df.columns:
        leta_posla = sorted(df["LETO"].dropna().astype(int).unique())
        sel_leto_posla = st.multiselect("Leto posla", leta_posla, default=leta_posla)
    else:
        sel_leto_posla = []

    st.markdown("---")

    pov_min = int(df["POVRSINA_ZA_IZRACUN"].min())
    pov_max = int(df["POVRSINA_ZA_IZRACUN"].max())
    sel_pov = st.slider("Površina (m²)", pov_min, pov_max, (30, 150))

    cena_min = int(df["CENA"].min())
    cena_max = int(df["CENA"].max())
    sel_cena = st.slider("Cena (€)", cena_min, cena_max, (50_000, 800_000), step=5_000)

    sel_leto_izgr = st.slider("Leto izgradnje", 1800, 2025, (1900, 2025))

# ── Filter ────────────────────────────────────────────────────────────────────
filt = df.copy()
if sel_obcina:
    filt = filt[filt["OBCINA"].isin(sel_obcina)]
if sel_naselje:
    filt = filt[filt["NASELJE"].isin(sel_naselje)]
if sel_ulica:
    filt = filt[filt["ULICA"].isin(sel_ulica)]
if sel_hisna.strip():
    filt = filt[filt["HISNA_STEVILKA"].str.contains(sel_hisna.strip(), case=False, na=False)]
if sel_st_stanovanja.strip():
    filt = filt[filt["STEVILKA_STANOVANJA_ALI_POSLOVNEGA_PROSTORA"].str.contains(
        sel_st_stanovanja.strip(), case=False, na=False)]
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
st.markdown("## Trg nepremičnin SLO 2015–2025")
st.markdown(
    f"<div class='section-title'>Stanovanja in hiše &nbsp;·&nbsp; {len(filt):,} poslov v izboru</div>",
    unsafe_allow_html=True
)

if len(filt) == 0:
    st.warning("Ni podatkov za izbrane filtre.")
    st.stop()

# ── KPI ───────────────────────────────────────────────────────────────────────
avg_m2_upr  = filt["CENA_M2_UPR"].mean()
med_m2_upr  = filt["CENA_M2_UPR"].median()
avg_m2_dela = filt["CENA_M2_DELA"].dropna().mean()
med_m2_dela = filt["CENA_M2_DELA"].dropna().median()
avg_cena    = filt["CENA"].mean()
med_cena    = filt["CENA"].median()
n_poslov    = len(filt)
avg_pov_upr = filt["POVRSINA_ZA_IZRACUN"].mean()

has_parcela = "PARCELA" in filt.columns
if has_parcela:
    n_parcela   = (filt["PARCELA"].str.len() > 0).sum()
    pct_parcela = n_parcela / len(filt) * 100

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena / m² (upr.)</div>
        <div class='metric-value'>{avg_m2_upr:,.0f} €</div>
        <div class='metric-sub'>mediana {med_m2_upr:,.0f} €/m²</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena / m² (dela)</div>
        <div class='metric-value'>{avg_m2_dela:,.0f} €</div>
        <div class='metric-sub'>mediana {med_m2_dela:,.0f} €/m²</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena posla</div>
        <div class='metric-value'>{avg_cena/1000:,.0f} k€</div>
        <div class='metric-sub'>mediana {med_cena/1000:,.0f} k€</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Število poslov</div>
        <div class='metric-value'>{n_poslov:,}</div>
        <div class='metric-sub'>povp. upr. površina {avg_pov_upr:.0f} m²</div>
    </div>""", unsafe_allow_html=True)
with c5:
    if has_parcela:
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Dodatna parcela (atrij ipd.)</div>
            <div class='metric-value'>{n_parcela:,}</div>
            <div class='metric-sub'>{pct_parcela:.1f} % poslov</div>
        </div>""", unsafe_allow_html=True)
    else:
        p25 = filt["CENA_M2_UPR"].quantile(0.25)
        p75 = filt["CENA_M2_UPR"].quantile(0.75)
        st.markdown(f"""<div class='metric-card'>
            <div class='metric-label'>Razpon cen / m²</div>
            <div class='metric-value'>{p25:,.0f} – {p75:,.0f}</div>
            <div class='metric-sub'>25. – 75. percentil</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabela ────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Posli v izboru — razvrščeni po ceni / m² (upr. površina)</div>",
            unsafe_allow_html=True)

tabela_cols = ["OBCINA", "NASELJE", "ULICA", "HISNA_STEVILKA"]
col_names   = ["Občina", "Naselje", "Ulica", "Hišna št."]

if "STEVILKA_STANOVANJA_ALI_POSLOVNEGA_PROSTORA" in filt.columns:
    tabela_cols.append("STEVILKA_STANOVANJA_ALI_POSLOVNEGA_PROSTORA")
    col_names.append("Št. stanovanja")

tabela_cols += ["LETO_IZGRADNJE_DELA_STAVBE"]
col_names   += ["Leto izgr."]

if "LETO" in filt.columns:
    tabela_cols.append("LETO")
    col_names.append("Leto posla")

tabela_cols += ["POVRSINA_DELA_STAVBE", "POVRSINA_ZA_IZRACUN",
                "CENA", "CENA_M2_UPR", "CENA_M2_DELA",
                "DEJANSKA_RABA_DELA_STAVBE", "LEGA_DELA_STAVBE_V_STAVBI"]
col_names   += ["Površina", "Uporabna površina",
                "Cena", "Cena/m² (upr.)", "Cena/m² (dela)",
                "Raba", "Lega"]

if "PARCELA" in filt.columns:
    tabela_cols.append("PARCELA")
    col_names.append("Dodatna parcela (atrij ipd.)")

tabela = filt[tabela_cols].sort_values("CENA_M2_UPR", ascending=False).copy()

tabela["CENA"]                       = tabela["CENA"].apply(lambda x: f"{x:,.0f} €")
tabela["CENA_M2_UPR"]               = tabela["CENA_M2_UPR"].apply(lambda x: f"{x:,.0f} €/m²")
tabela["CENA_M2_DELA"]              = tabela["CENA_M2_DELA"].apply(
    lambda x: f"{x:,.0f} €/m²" if pd.notna(x) else "")
tabela["POVRSINA_ZA_IZRACUN"]        = tabela["POVRSINA_ZA_IZRACUN"].apply(lambda x: f"{x:.1f} m²")
tabela["POVRSINA_DELA_STAVBE"]       = tabela["POVRSINA_DELA_STAVBE"].apply(
    lambda x: f"{x:.1f} m²" if pd.notna(x) else "")
tabela["LETO_IZGRADNJE_DELA_STAVBE"] = tabela["LETO_IZGRADNJE_DELA_STAVBE"].apply(
    lambda x: str(int(x)) if pd.notna(x) else "")
if "LETO" in tabela.columns:
    tabela["LETO"] = tabela["LETO"].apply(lambda x: str(int(x)) if pd.notna(x) else "")

tabela.columns = col_names
st.dataframe(tabela, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Graf — povp. cena/m² po letu, primerjava občin ───────────────────────────
st.markdown("<div class='section-title'>Povp. cena / m² po letu posla — primerjava po občinah</div>",
            unsafe_allow_html=True)

vse_obcine = sorted(df["OBCINA"].unique())
top5 = df["OBCINA"].value_counts().head(5).index.tolist()

graf_obcine = st.multiselect(
    "Občine za primerjavo (max 10)",
    options=vse_obcine,
    default=top5,
    max_selections=10,
    key="graf_obcine"
)

if graf_obcine and "LETO" in df.columns:
    graf_df = df[df["OBCINA"].isin(graf_obcine)].copy()
    # Upoštevaj filter leta posla
    if sel_leto_posla:
        graf_df = graf_df[graf_df["LETO"].isin([float(l) for l in sel_leto_posla])]

    grp = (
        graf_df.groupby(["OBCINA", "LETO"])["CENA_M2_UPR"]
        .agg(povprecje="mean", mediana="median", n="count")
        .reset_index()
        .query("n >= 3")
        .sort_values("LETO")
    )

    tab1, tab2 = st.tabs(["Povprečje", "Mediana"])

    COLORS = [
        "#003DA5", "#C8102E", "#1a6fd4", "#e8384f", "#5b9bd5",
        "#ff6b7a", "#0a2d7a", "#8b0a1a", "#4a90d9", "#d4505a",
    ]

    def make_fig(metric, label):
        fig = go.Figure()
        for i, obcina in enumerate(graf_obcine):
            d = grp[grp["OBCINA"] == obcina]
            if d.empty:
                continue
            color = COLORS[i % len(COLORS)]
            fig.add_trace(go.Scatter(
                x=d["LETO"], y=d[metric],
                mode="lines+markers",
                name=obcina.title(),
                line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                hovertemplate=(
                    f"<b>{obcina.title()}</b><br>"
                    "Leto: %{x}<br>"
                    f"{label}: %{{y:,.0f}} €/m²<extra></extra>"
                ),
            ))
        fig.update_layout(
            template="plotly_white",
            xaxis_title="Leto posla",
            yaxis_title=f"{label} cene (€/m²)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=0, r=0, t=40, b=0),
            height=420,
            font=dict(family="IBM Plex Sans", size=12),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#f5f8ff",
            xaxis=dict(gridcolor="#dce8ff", dtick=1),
            yaxis=dict(gridcolor="#dce8ff"),
        )
        return fig

    with tab1:
        st.plotly_chart(make_fig("povprecje", "Povprečje"), use_container_width=True)
    with tab2:
        st.plotly_chart(make_fig("mediana", "Mediana"), use_container_width=True)
elif graf_obcine:
    st.info("Stolpec LETO ni na voljo v podatkih.")
else:
    st.info("Izberi vsaj eno občino za prikaz grafa.")
