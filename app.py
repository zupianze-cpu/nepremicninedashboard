import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random

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
    background: #003DA5; border: 1px solid #0031a0;
    border-radius: 8px; padding: 1rem 1.2rem;
}
.metric-label { font-size: 11px; font-weight: 600; color: #a8c4f0;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 5px; }
.metric-value { font-size: 1.5rem; font-weight: 600; color: #ffffff; line-height: 1.15; }
.metric-sub { font-size: 11px; color: #FFD700; margin-top: 3px; font-weight: 500; }
.section-title { font-size: 11px; font-weight: 600; color: #003DA5;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 0.75rem; padding-bottom: 5px; border-bottom: 2px solid #003DA5; }
.zanimivost-card { background: #fff8e1; border: 1px solid #ffe082;
    border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 1rem; }
h2 { color: #003DA5 !important; }
</style>
""", unsafe_allow_html=True)

import re as _re

# Stanovanja: novi sistem (1,2,3,47) + stari sistem CC-SI (111x, 112x)
# Robustno: izvleče vodečo številčno kodo ne glede na opis za njo
def je_stanovanje(raba: str) -> bool:
    r = str(raba).strip()
    m = _re.match(r"^(\d+)", r)
    if not m:
        return False
    koda = m.group(1)
    if koda in {"1", "2", "3", "47"}:
        return True
    if koda[:3] in {"111", "112"}:
        return True
    return False

@st.cache_data
def load_data():
    df = pd.read_excel("2015-2025git.xlsx", dtype=str, engine="openpyxl")

    num_cols = ["CENA", "POVRSINA_DELA_STAVBE", "UPORABNA_POVRSINA",
                "LETO_IZGRADNJE_DELA_STAVBE", "LETO", "PARCELA"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filter: stanovanja po obeh sistemih kodiranja
    df = df[df["DEJANSKA_RABA_DELA_STAVBE"].apply(je_stanovanje)]

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

    if "LETO" in df.columns:
        df["LETO"] = df["LETO"].round().astype("Int64")

    str_cols = ["OBCINA", "NASELJE", "ULICA", "HISNA_STEVILKA",
                "STEVILKA_STANOVANJA_ALI_POSLOVNEGA_PROSTORA",
                "LEGA_DELA_STAVBE_V_STAVBI", "DEJANSKA_RABA_DELA_STAVBE"]
    for col in str_cols:
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
        leta_posla = sorted([int(l) for l in df["LETO"].dropna().unique()])
        sel_leto_posla = st.multiselect("Leto posla", leta_posla, default=leta_posla)
    else:
        sel_leto_posla = []

    st.markdown("---")

    pov_min = int(df["POVRSINA_ZA_IZRACUN"].min())
    pov_max = int(df["POVRSINA_ZA_IZRACUN"].max())
    sel_pov = st.slider("Površina (m²)", pov_min, pov_max, (20, 250))

    cena_min = int(df["CENA"].min())
    cena_max = int(df["CENA"].max())
    sel_cena = st.slider("Cena (€)", cena_min, cena_max, (30_000, 3_000_000), step=5_000)

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
    filt = filt[filt["LETO"].isin(sel_leto_posla)]
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

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena / m² (uporabne)</div>
        <div class='metric-value'>{avg_m2_upr:,.0f} €</div>
        <div class='metric-sub'>mediana {med_m2_upr:,.0f} €/m²</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Povp. cena / m² (skupne)</div>
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

tabela_cols += ["POVRSINA_DELA_STAVBE", "POVRSINA_ZA_IZRACUN"]
col_names   += ["Površina", "Uporabna površina"]

if "PARCELA" in filt.columns:
    tabela_cols.append("PARCELA")
    col_names.append("Atrij/parking ipd.")

tabela_cols += ["CENA", "CENA_M2_UPR", "CENA_M2_DELA",
                "DEJANSKA_RABA_DELA_STAVBE", "LEGA_DELA_STAVBE_V_STAVBI"]
col_names   += ["Cena", "Cena/m² uporabne", "Cena/m² skupne", "Raba", "Lega"]

# Vsak posel je svoja vrstica — ista nepremičnina z različnimi leti se pojavi večkrat
tabela = filt[tabela_cols].sort_values("CENA_M2_UPR", ascending=False).reset_index(drop=True).copy()
tabela["CENA"]         = tabela["CENA"].apply(lambda x: f"{x:,.0f} €")
tabela["CENA_M2_UPR"]  = tabela["CENA_M2_UPR"].apply(lambda x: f"{x:,.0f} €/m²")
tabela["CENA_M2_DELA"] = tabela["CENA_M2_DELA"].apply(
    lambda x: f"{x:,.0f} €/m²" if pd.notna(x) else "")
tabela["POVRSINA_ZA_IZRACUN"]  = tabela["POVRSINA_ZA_IZRACUN"].apply(lambda x: f"{x:.1f} m²")
tabela["POVRSINA_DELA_STAVBE"] = tabela["POVRSINA_DELA_STAVBE"].apply(
    lambda x: f"{x:.1f} m²" if pd.notna(x) else "")
if "PARCELA" in tabela.columns:
    tabela["PARCELA"] = tabela["PARCELA"].apply(
        lambda x: f"{x:.1f} m²" if pd.notna(x) and x > 0 else "")
tabela["LETO_IZGRADNJE_DELA_STAVBE"] = tabela["LETO_IZGRADNJE_DELA_STAVBE"].apply(
    lambda x: str(int(x)) if pd.notna(x) else "")
if "LETO" in tabela.columns:
    tabela["LETO"] = tabela["LETO"].apply(lambda x: str(int(x)) if pd.notna(x) else "")

tabela.columns = col_names
st.dataframe(tabela, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Graf ──────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Povp. cena / m² po letu posla — primerjava po občinah</div>",
            unsafe_allow_html=True)

vse_obcine = sorted(df["OBCINA"].unique())
top5 = df["OBCINA"].value_counts().head(5).index.tolist()
graf_obcine = st.multiselect(
    "Občine za primerjavo (max 10)", options=vse_obcine, default=top5,
    max_selections=10, key="graf_obcine"
)

if graf_obcine and "LETO" in df.columns:
    graf_df = df[df["OBCINA"].isin(graf_obcine)].copy()
    if sel_leto_posla:
        graf_df = graf_df[graf_df["LETO"].isin(sel_leto_posla)]
    grp = (
        graf_df.groupby(["OBCINA", "LETO"])["CENA_M2_UPR"]
        .agg(povprecje="mean", mediana="median", n="count")
        .reset_index().query("n >= 3").sort_values("LETO")
    )
    tab1, tab2 = st.tabs(["Povprečje", "Mediana"])
    COLORS = ["#003DA5","#C8102E","#1a6fd4","#e8384f","#5b9bd5",
              "#ff6b7a","#0a2d7a","#8b0a1a","#4a90d9","#d4505a"]

    def make_fig(metric, label):
        fig = go.Figure()
        for i, obcina in enumerate(graf_obcine):
            d = grp[grp["OBCINA"] == obcina]
            if d.empty:
                continue
            color = COLORS[i % len(COLORS)]
            fig.add_trace(go.Scatter(
                x=d["LETO"], y=d[metric], mode="lines+markers",
                name=obcina.title(), line=dict(color=color, width=2),
                marker=dict(size=6, color=color),
                hovertemplate=(f"<b>{obcina.title()}</b><br>Leto: %{{x}}<br>"
                               f"{label}: %{{y:,.0f}} €/m²<extra></extra>"),
            ))
        fig.update_layout(
            template="plotly_white", xaxis_title="Leto posla",
            yaxis_title=f"{label} cene (€/m²)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=0, r=0, t=40, b=0), height=420,
            font=dict(family="IBM Plex Sans", size=12),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#f5f8ff",
            xaxis=dict(gridcolor="#dce8ff", dtick=1), yaxis=dict(gridcolor="#dce8ff"),
        )
        return fig

    with tab1:
        st.plotly_chart(make_fig("povprecje", "Povprečje"), use_container_width=True)
    with tab2:
        st.plotly_chart(make_fig("mediana", "Mediana"), use_container_width=True)
else:
    st.info("Izberi vsaj eno občino za prikaz grafa.")

st.markdown("<br>", unsafe_allow_html=True)

# ── Zanimivost ────────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Zanimivost — najdražji posel po kraju in letu</div>",
            unsafe_allow_html=True)

if "LETO" in df.columns:
    combos = (
        df[df["CENA"] > 0]
        .groupby(["OBCINA", "LETO"])
        .size()
        .reset_index()
    )
    combos = combos[combos[0] > 0][["OBCINA", "LETO"]].dropna().values.tolist()

    if "zanimivost_idx" not in st.session_state:
        st.session_state.zanimivost_idx = random.randint(0, len(combos) - 1)

    if st.button("🎲 Naslednja zanimivost"):
        st.session_state.zanimivost_idx = random.randint(0, len(combos) - 1)

    obcina_z, leto_z = combos[st.session_state.zanimivost_idx]
    leto_z = int(leto_z)

    posel = (
        df[(df["OBCINA"] == obcina_z) & (df["LETO"] == leto_z)]
        .sort_values("CENA", ascending=False)
        .iloc[0]
    )

    naslov = f"{posel.get('ULICA','')} {posel.get('HISNA_STEVILKA','')}".strip() or "neznan naslov"
    cena_z  = posel["CENA"]
    m2_z    = posel["POVRSINA_ZA_IZRACUN"]
    cm2_z   = posel["CENA_M2_UPR"]
    raba_z  = posel.get("DEJANSKA_RABA_DELA_STAVBE", "")

    st.markdown(f"""<div class='zanimivost-card'>
        <b>📍 {obcina_z.title()}, {leto_z}</b><br>
        Najdražji posel: <b>{naslov}</b><br>
        Cena: <b>{cena_z:,.0f} €</b> &nbsp;·&nbsp;
        Površina: <b>{m2_z:.0f} m²</b> &nbsp;·&nbsp;
        Cena/m²: <b>{cm2_z:,.0f} €/m²</b><br>
        <span style="color:#888; font-size:12px;">{raba_z}</span>
    </div>""", unsafe_allow_html=True)
else:
    st.info("Stolpec LETO ni na voljo.")
