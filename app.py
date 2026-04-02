import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random
import re

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
.zanimivost-card { background: #fff8e1; border: 2px solid #f9a825;
    border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 1rem;
    color: #1a1a1a; }
.zanimivost-card b { color: #003DA5; }
.realna-cena-card { background: #f0f4ff; border: 2px solid #003DA5;
    border-radius: 8px; padding: 1.2rem 1.4rem; margin-top: 1rem; color: #1a1a1a; }
.realna-cena-card .glavna { font-size: 2rem; font-weight: 700; color: #003DA5; }
.realna-cena-card .sub { font-size: 13px; color: #444; margin-top: 4px; }
h2 { color: #003DA5 !important; }
</style>
""", unsafe_allow_html=True)

def je_stanovanje(raba):
    m = re.match(r'^(\d+)', str(raba).strip())
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
    for col in ["CENA", "POVRSINA_DELA_STAVBE", "UPORABNA_POVRSINA",
                "LETO_IZGRADNJE_DELA_STAVBE", "LETO", "PARCELA"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["DEJANSKA_RABA_DELA_STAVBE"].apply(je_stanovanje)].copy()

    df["POVRSINA_ZA_IZRACUN"] = df["UPORABNA_POVRSINA"].where(
        df["UPORABNA_POVRSINA"] > 5, df["POVRSINA_DELA_STAVBE"]
    )
    df["CENA_M2_UPR"]  = df["CENA"] / df["POVRSINA_ZA_IZRACUN"]
    df["CENA_M2_DELA"] = df["CENA"] / df["POVRSINA_DELA_STAVBE"]

    df = df[
        df["CENA"].between(5_000, 5_000_000) &
        df["POVRSINA_ZA_IZRACUN"].between(10, 1000) &
        df["CENA_M2_UPR"].between(100, 15_000)
    ].copy()

    if "LETO" in df.columns:
        df = df[df["LETO"].notna()].copy()
        df["LETO"] = df["LETO"].astype(int)

    for col in ["OBCINA", "NASELJE", "ULICA", "HISNA_STEVILKA",
                "STEVILKA_STANOVANJA_ALI_POSLOVNEGA_PROSTORA",
                "LEGA_DELA_STAVBE_V_STAVBI", "DEJANSKA_RABA_DELA_STAVBE"]:
        if col in df.columns:
            df[col] = df[col].fillna("").str.strip()

    return df.reset_index(drop=True)

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

    st.markdown("---")

    if "LETO" in df.columns:
        leta_posla = sorted(df["LETO"].unique().tolist())
        sel_leto_posla = st.multiselect("Leto posla", leta_posla, default=leta_posla)
    else:
        sel_leto_posla = []

    st.markdown("---")

    # Površina — slider + ročni vnos
    pov_min_all = int(df["POVRSINA_ZA_IZRACUN"].min())
    pov_max_all = int(df["POVRSINA_ZA_IZRACUN"].max())
    st.markdown("**Površina (m²)**")
    pc1, pc2 = st.columns(2)
    pov_lo_inp = pc1.number_input("Od", min_value=pov_min_all, max_value=pov_max_all, value=20, step=5, key="pov_lo")
    pov_hi_inp = pc2.number_input("Do", min_value=pov_min_all, max_value=pov_max_all, value=250, step=5, key="pov_hi")
    sel_pov = st.slider("", pov_min_all, pov_max_all, (pov_lo_inp, pov_hi_inp), key="pov_slider", label_visibility="collapsed")
    # Sinhronizacija: number_input ima prednost
    sel_pov = (min(pov_lo_inp, sel_pov[0]), max(pov_hi_inp, sel_pov[1])) if pov_lo_inp != 20 or pov_hi_inp != 250 else sel_pov

    st.markdown("**Cena (€)**")
    cena_min_all = int(df["CENA"].min())
    cena_max_all = int(df["CENA"].max())
    cc1, cc2 = st.columns(2)
    cena_lo_inp = cc1.number_input("Od", min_value=cena_min_all, max_value=cena_max_all, value=30_000, step=5_000, key="cena_lo")
    cena_hi_inp = cc2.number_input("Do", min_value=cena_min_all, max_value=cena_max_all, value=3_000_000, step=5_000, key="cena_hi")
    sel_cena = st.slider("", cena_min_all, cena_max_all, (cena_lo_inp, cena_hi_inp), step=5_000, key="cena_slider", label_visibility="collapsed")
    sel_cena = (min(cena_lo_inp, sel_cena[0]), max(cena_hi_inp, sel_cena[1])) if cena_lo_inp != 30_000 or cena_hi_inp != 3_000_000 else sel_cena

    st.markdown("**Leto izgradnje**")
    lc1, lc2 = st.columns(2)
    leto_lo_inp = lc1.number_input("Od", min_value=1800, max_value=2025, value=1900, step=1, key="leto_lo")
    leto_hi_inp = lc2.number_input("Do", min_value=1800, max_value=2025, value=2025, step=1, key="leto_hi")
    sel_leto_izgr = st.slider("", 1800, 2025, (leto_lo_inp, leto_hi_inp), key="leto_slider", label_visibility="collapsed")
    sel_leto_izgr = (min(leto_lo_inp, sel_leto_izgr[0]), max(leto_hi_inp, sel_leto_izgr[1])) if leto_lo_inp != 1900 or leto_hi_inp != 2025 else sel_leto_izgr

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
st.markdown("<div class='section-title'>Posli v izboru — vsaka prodaja je svoja vrstica, razvrščeno po ceni / m²</div>",
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

tabela = filt[tabela_cols].sort_values("CENA_M2_UPR", ascending=False).copy()
tabela["CENA"]         = tabela["CENA"].apply(lambda x: f"{x:,.0f} €")
tabela["CENA_M2_UPR"]  = tabela["CENA_M2_UPR"].apply(lambda x: f"{x:,.0f} €/m²")
tabela["CENA_M2_DELA"] = tabela["CENA_M2_DELA"].apply(lambda x: f"{x:,.0f} €/m²" if pd.notna(x) else "")
tabela["POVRSINA_ZA_IZRACUN"]  = tabela["POVRSINA_ZA_IZRACUN"].apply(lambda x: f"{x:.1f} m²")
tabela["POVRSINA_DELA_STAVBE"] = tabela["POVRSINA_DELA_STAVBE"].apply(lambda x: f"{x:.1f} m²" if pd.notna(x) else "")
if "PARCELA" in tabela.columns:
    tabela["PARCELA"] = tabela["PARCELA"].apply(lambda x: f"{x:.1f} m²" if pd.notna(x) and x > 0 else "")
tabela["LETO_IZGRADNJE_DELA_STAVBE"] = tabela["LETO_IZGRADNJE_DELA_STAVBE"].apply(lambda x: str(int(x)) if pd.notna(x) else "")
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
    combos = df[df["CENA"] > 0].groupby(["OBCINA", "LETO"]).size().reset_index()
    combos = combos[combos[0] > 0][["OBCINA", "LETO"]].values.tolist()

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
    cena_z = posel["CENA"]
    m2_z   = posel["POVRSINA_ZA_IZRACUN"]
    cm2_z  = posel["CENA_M2_UPR"]
    raba_z = posel.get("DEJANSKA_RABA_DELA_STAVBE", "")

    st.markdown(f"""<div class='zanimivost-card'>
        <b>📍 {obcina_z.title()}, {leto_z}</b><br>
        Najdražji posel: <b>{naslov}</b><br>
        Cena: <b>{cena_z:,.0f} €</b> &nbsp;·&nbsp;
        Površina: <b>{m2_z:.0f} m²</b> &nbsp;·&nbsp;
        Cena/m²: <b>{cm2_z:,.0f} €/m²</b><br>
        <span style="font-size:12px; color:#555;">{raba_z}</span>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Realna cena ───────────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>Kakšna je realna cena nepremičnine?</div>",
            unsafe_allow_html=True)
st.markdown("Vnesi parametre in dobil boš oceno tržne cene na podlagi primerljivih prodaj iz 2025.")

MIN_VZOREC = 10  # minimalno število poslov za zanesljiv izračun

r1c1, r1c2, r1c3 = st.columns(3)
rc_obcina  = r1c1.selectbox("Občina", [""] + sorted(df["OBCINA"].unique()), key="rc_obcina")
rc_naselje = r1c2.selectbox("Naselje", [""] + sorted(
    df[df["OBCINA"] == rc_obcina]["NASELJE"].unique() if rc_obcina else df["NASELJE"].unique()
), key="rc_naselje")
rc_ulica   = r1c3.selectbox("Ulica", [""] + sorted(
    df[df["NASELJE"] == rc_naselje]["ULICA"].unique() if rc_naselje else (
        df[df["OBCINA"] == rc_obcina]["ULICA"].unique() if rc_obcina else []
    )
), key="rc_ulica")

r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
rc_hisna     = r2c1.text_input("Hišna številka", "", key="rc_hisna")
rc_povrsina  = r2c2.number_input("Površina (m²)", min_value=10, max_value=1000, value=60, step=5, key="rc_povrsina")
rc_leto_izgr = r2c3.number_input("Leto izgradnje", min_value=1800, max_value=2025, value=1990, step=1, key="rc_leto_izgr")
rc_parcela   = r2c4.number_input("Površina atrija/parkinga (m²)", min_value=0, max_value=5000, value=0, step=5, key="rc_parcela")

if r2c5.button("🔍 Oceni ceno", key="rc_btn"):
    # Baza: samo 2025
    baza = df[df["LETO"] == 2025].copy() if "LETO" in df.columns else df.copy()

    def izracunaj_ceno(vzorec, povrsina, label):
        if len(vzorec) < MIN_VZOREC:
            return None, len(vzorec)
        # Odstrani top 15% in bottom 15%
        p15 = vzorec["CENA_M2_UPR"].quantile(0.15)
        p85 = vzorec["CENA_M2_UPR"].quantile(0.85)
        ociscen = vzorec[vzorec["CENA_M2_UPR"].between(p15, p85)]
        if len(ociscen) < 3:
            return None, len(vzorec)
        avg_m2 = ociscen["CENA_M2_UPR"].mean()
        return avg_m2 * povrsina, len(ociscen)

    # Razširjevanje vzorca: ulica → naselje → občina → cela SLO
    lokacije = []
    if rc_ulica:
        lokacije.append(("ulica", baza[baza["ULICA"] == rc_ulica]))
    if rc_naselje:
        lokacije.append(("naselje", baza[baza["NASELJE"] == rc_naselje]))
    if rc_obcina:
        lokacije.append(("občina", baza[baza["OBCINA"] == rc_obcina]))
    lokacije.append(("Slovenija", baza))

    # Filtriraj po letu izgradnje ±15 let
    def filtriraj_leto(vzorec, leto, razpon=15):
        mask = vzorec["LETO_IZGRADNJE_DELA_STAVBE"].between(leto - razpon, leto + razpon)
        sub = vzorec[mask]
        return sub if len(sub) >= MIN_VZOREC else vzorec

    # Filtriraj po površini ±20%
    def filtriraj_povrsino(vzorec, pov, razpon=0.10):
        # ±10%
        sub10 = vzorec[vzorec["POVRSINA_ZA_IZRACUN"].between(pov * 0.90, pov * 1.10)]
        if len(sub10) >= MIN_VZOREC:
            return sub10, "±10%"
        # ±25% fallback
        sub25 = vzorec[vzorec["POVRSINA_ZA_IZRACUN"].between(pov * 0.75, pov * 1.25)]
        if len(sub25) >= MIN_VZOREC:
            return sub25, "±25%"
        # Nič — vrni kar je (lokacijski fallback bo poskrbel za razširitev)
        return sub25, "±25%"

    # ── Osnovna ocena (brez parcele) ──────────────────────────────────────────
    rezultat = None
    for lok_ime, lok_vzorec in lokacije:
        vzorec = filtriraj_leto(lok_vzorec, rc_leto_izgr)
        vzorec, pov_razpon = filtriraj_povrsino(vzorec, rc_povrsina)
        cena, n = izracunaj_ceno(vzorec, rc_povrsina, lok_ime)
        if cena is not None:
            rezultat = (cena, n, lok_ime, vzorec)
            break

    if not rezultat:
        st.warning("Premalo podatkov za zanesljivo oceno cene. Poskusi z manj specifičnimi parametri.")
    else:
        cena_r, n_r, lok_r, vzorec_r = rezultat

        # Izračun avg_m2 iz očiščenega vzorca (brez top/bottom 15%)
        p15 = vzorec_r["CENA_M2_UPR"].quantile(0.15)
        p85 = vzorec_r["CENA_M2_UPR"].quantile(0.85)
        ociscen = vzorec_r[vzorec_r["CENA_M2_UPR"].between(p15, p85)]
        avg_m2_val = ociscen["CENA_M2_UPR"].mean()
        cena_lo = p15 * rc_povrsina
        cena_hi = p85 * rc_povrsina

        # ── Parcela logika ─────────────────────────────────────────────────────
        dodatek_parcela = 0.0
        parcela_info    = ""

        if rc_parcela > 0 and "PARCELA" in baza.columns:
            # Išči med posli ki imajo > 1 m² parcele — po vseh lokacijskih fallbackih
            for lok_ime_p, lok_vzorec_p in lokacije:
                vzorec_p = filtriraj_leto(lok_vzorec_p, rc_leto_izgr)
                vzorec_p, _ = filtriraj_povrsino(vzorec_p, rc_povrsina)
                # Samo posli s parcelo > 1 m², brez top/bottom filter
                vzorec_parc = vzorec_p[vzorec_p["PARCELA"] > 1]

                if len(vzorec_parc) >= 5:
                    # ≥5 vzorcev — računaj direktno, brez top/bottom filtra
                    avg_m2_parc  = vzorec_parc["CENA_M2_UPR"].mean()
                    cena_r       = avg_m2_parc * rc_povrsina
                    avg_m2_val   = avg_m2_parc
                    cena_lo      = vzorec_parc["CENA_M2_UPR"].quantile(0.25) * rc_povrsina
                    cena_hi      = vzorec_parc["CENA_M2_UPR"].quantile(0.75) * rc_povrsina
                    parcela_info = f"{len(vzorec_parc)} poslov z atrij/parking · lokacija: {lok_ime_p}"
                    break

                elif len(vzorec_parc) >= 1:
                    # 1–4 vzorcev — preračunaj po skupni površini
                    skupna_pov   = rc_povrsina + rc_parcela
                    avg_m2_parc  = vzorec_parc["CENA_M2_UPR"].mean()
                    cena_r       = avg_m2_parc * skupna_pov
                    avg_m2_val   = avg_m2_parc
                    cena_lo      = cena_r * 0.85
                    cena_hi      = cena_r * 1.15
                    parcela_info = f"{len(vzorec_parc)} vzorec/vzorca z atrij/parking, skupna pov. {skupna_pov:.0f} m² · lokacija: {lok_ime_p}"
                    break

            else:
                # Nič vzorcev nikjer — parcela = avg_m2 × m² × 0.5
                vrednost_parcele = avg_m2_val * rc_parcela * 0.5
                cena_r          += vrednost_parcele
                cena_lo         += vrednost_parcele * 0.7
                cena_hi         += vrednost_parcele * 1.3
                parcela_info     = f"brez vzorcev z atrij/parking — dodano {vrednost_parcele:,.0f} € ({rc_parcela} m² × {avg_m2_val:,.0f}/2 €/m²)"

        # ── Prikaz ────────────────────────────────────────────────────────────
        meta = (f"Na podlagi {n_r} poslov · lokacija: {lok_r} · "
                f"površina {pov_razpon} · leto ±15 · brez top/bottom 15%")
        if parcela_info:
            meta += f"\nAtrij/parking: {parcela_info}"

        st.success(f"### {cena_r:,.0f} €")
        ka, kb, kc = st.columns(3)
        ka.metric("Razpon (od)", f"{cena_lo:,.0f} €")
        kb.metric("Razpon (do)", f"{cena_hi:,.0f} €")
        kc.metric("Povp. €/m²", f"{avg_m2_val:,.0f} €")
        st.caption(meta)
