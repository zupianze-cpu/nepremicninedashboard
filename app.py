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
st.markdown(
    "Ocena tržne vrednosti na podlagi primerljivih prodaj iz podatkov ETN. "
    "Vsak del površine se vrednoti posebej — uporabna, skupna in parcela imajo različno ceno/m²."
)

# ── Vnosni filtri ─────────────────────────────────────────────────────────────
rc1, rc2, rc3 = st.columns(3)
rc_obcina  = rc1.selectbox("Občina", [""] + sorted(df["OBCINA"].unique()), key="rc3_obcina")
_naselja   = sorted(df[df["OBCINA"]==rc_obcina]["NASELJE"].unique()) if rc_obcina else sorted(df["NASELJE"].unique())
rc_naselje = rc2.selectbox("Naselje", [""] + _naselja, key="rc3_naselje")
_ulice     = sorted(df[df["NASELJE"]==rc_naselje]["ULICA"].unique()) if rc_naselje else (
             sorted(df[df["OBCINA"]==rc_obcina]["ULICA"].unique()) if rc_obcina else [])
rc_ulica   = rc3.selectbox("Ulica", [""] + _ulice, key="rc3_ulica")

rd1, rd2, rd3, rd4, rd5 = st.columns(5)
rc_upr      = rd1.number_input("Uporabna površina (m²)", 10, 1000, 60, 5, key="rc3_upr")
rc_skupna   = rd2.number_input("Skupna površina (m²)",   10, 1000, 65, 5, key="rc3_skupna")
rc_parcela  = rd3.number_input("Parcela/atrij (m²)",      0, 9999,  0, 5, key="rc3_parc")
rc_leto     = rd4.number_input("Leto izgradnje",        1800, 2025, 1990, 1, key="rc3_leto")
rc_btn      = rd5.button("🔍 Oceni", key="rc3_btn")

if rc_btn:
    MIN_RC = 5
    IMA_PARCELO = rc_parcela > 0

    # ── Pomožne funkcije ──────────────────────────────────────────────────────
    def trimmed_mean(series, lo=0.10, hi=0.90):
        """Povprečje brez spodnjih lo% in zgornjih hi% vrednosti."""
        p_lo = series.quantile(lo)
        p_hi = series.quantile(hi)
        trimmed = series[series.between(p_lo, p_hi)]
        return trimmed.mean(), trimmed.quantile(0.25), trimmed.quantile(0.75), len(trimmed)

    def lokacijski_vzorec(bazel, upr, leto, ima_parcelo, razpon_pov=0.10, razpon_leto=5):
        """Vrni vzorec z danimi parametri."""
        v = bazel[
            bazel["POVRSINA_ZA_IZRACUN"].between(upr*(1-razpon_pov), upr*(1+razpon_pov)) &
            bazel["LETO_IZGRADNJE_DELA_STAVBE"].between(leto-razpon_leto, leto+razpon_leto)
        ]
        if ima_parcelo:
            v = v[v["PARCELA"] > 0]
        else:
            v = v[v["PARCELA"] == 0]
        return v

    # Lokacijski fallback — od najožjega do najširšega
    lokacije_rc = []
    if rc_ulica:
        lokacije_rc.append(("ulica", df[df["ULICA"]==rc_ulica]))
    if rc_naselje:
        lokacije_rc.append(("naselje", df[df["NASELJE"]==rc_naselje]))
    if rc_obcina:
        lokacije_rc.append(("občina", df[df["OBCINA"]==rc_obcina]))
    lokacije_rc.append(("Slovenija", df))

    # Poišči vzorec — najprej ±10%/±5let, potem ±20%/±10let, potem ±30%/±15let
    razponi = [
        (0.10,  5, "±10% površine, ±5 let"),
        (0.20, 10, "±20% površine, ±10 let"),
        (0.30, 15, "±30% površine, ±15 let"),
    ]

    vzorec_final = None
    lok_final    = None
    razpon_final = None

    for lok_ime, lok_df in lokacije_rc:
        for razpon_pov, razpon_leto, razpon_opis in razponi:
            v = lokacijski_vzorec(lok_df, rc_upr, rc_leto, IMA_PARCELO, razpon_pov, razpon_leto)
            if len(v) >= MIN_RC:
                vzorec_final = v
                lok_final    = lok_ime
                razpon_final = razpon_opis
                break
        if vzorec_final is not None:
            break

    if vzorec_final is None:
        st.warning(
            "Premalo primerljivih poslov za oceno. "
            "Razširi lokacijo ali preveri vnešene parametre."
        )
    else:
        v = vzorec_final

        # ── Izračun cene ──────────────────────────────────────────────────────
        razlika_m2 = max(rc_skupna - rc_upr, 0)

        # Avg cena/m2 uporabne površine
        avg_upr, p25_upr, p75_upr, n_upr = trimmed_mean(v["CENA_M2_UPR"].dropna())

        # Avg cena/m2 skupne površine (dela stavbe)
        avg_dela, p25_dela, p75_dela, _ = trimmed_mean(v["CENA_M2_DELA"].dropna())

        if IMA_PARCELO:
            # Izračunaj implicitno ceno parcele iz poslov ki imajo parcelo
            # cena_parcele = cena_posla - avg_upr*upr - avg_dela*(skupna-upr)
            # avg_m2_parcele = cena_parcele / parcela
            v2 = v[v["PARCELA"]>0].copy()
            v2["CENA_IMPL_PARCELE"] = (
                v2["CENA"]
                - avg_upr  * v2["POVRSINA_ZA_IZRACUN"]
                - avg_dela * (v2["POVRSINA_DELA_STAVBE"].fillna(v2["POVRSINA_ZA_IZRACUN"]) - v2["POVRSINA_ZA_IZRACUN"])
            )
            v2["CENA_M2_PARCELE"] = v2["CENA_IMPL_PARCELE"] / v2["PARCELA"]
            # Filtriraj smiselne vrednosti (0–5000 €/m2)
            v2_ok = v2[v2["CENA_M2_PARCELE"].between(0, 5000)]
            if len(v2_ok) >= 3:
                avg_parc, p25_parc, p75_parc, _ = trimmed_mean(v2_ok["CENA_M2_PARCELE"])
            else:
                # Fallback: parcela vrednoti po 20% cene uporabne površine
                avg_parc  = avg_upr  * 0.20
                p25_parc  = p25_upr  * 0.20
                p75_parc  = p75_upr  * 0.20

            cena_upr_del  = avg_upr  * rc_upr
            cena_razl_del = avg_dela * razlika_m2
            cena_parc_del = avg_parc * rc_parcela
            cena_total    = cena_upr_del + cena_razl_del + cena_parc_del

            cena_lo = p25_upr * rc_upr + p25_dela * razlika_m2 + p25_parc * rc_parcela
            cena_hi = p75_upr * rc_upr + p75_dela * razlika_m2 + p75_parc * rc_parcela

            razclenjeno = (
                f"Uporabna: {avg_upr:,.0f} €/m² × {rc_upr} m² = **{cena_upr_del:,.0f} €**  \n"
                f"Skupna–uporabna: {avg_dela:,.0f} €/m² × {razlika_m2:.0f} m² = **{cena_razl_del:,.0f} €**  \n"
                f"Parcela/atrij: {avg_parc:,.0f} €/m² × {rc_parcela} m² = **{cena_parc_del:,.0f} €**"
            )
        else:
            cena_upr_del  = avg_upr  * rc_upr
            cena_razl_del = avg_dela * razlika_m2
            cena_total    = cena_upr_del + cena_razl_del

            cena_lo = p25_upr * rc_upr + p25_dela * razlika_m2
            cena_hi = p75_upr * rc_upr + p75_dela * razlika_m2

            razclenjeno = (
                f"Uporabna: {avg_upr:,.0f} €/m² × {rc_upr} m² = **{cena_upr_del:,.0f} €**  \n"
                f"Skupna–uporabna: {avg_dela:,.0f} €/m² × {razlika_m2:.0f} m² = **{cena_razl_del:,.0f} €**"
            )

        # ── Prikaz ────────────────────────────────────────────────────────────
        st.success(f"### Ocenjena vrednost: {cena_total:,.0f} €")

        ka, kb, kc, kd = st.columns(4)
        ka.metric("Spodnji razpon", f"{cena_lo:,.0f} €")
        kb.metric("Zgornji razpon", f"{cena_hi:,.0f} €")
        kc.metric("Poslov v vzorcu", f"{len(v)}")
        kd.metric("Lokacija vzorca", lok_final)

        st.markdown("**Razčlenitev ocene:**")
        st.markdown(razclenjeno)
        st.caption(
            f"Vzorec: {lok_final} · {razpon_final} · leto izgr. ±5/10/15 · "
            f"brez top/bottom 10% cen · {'posli s parcelo' if IMA_PARCELO else 'posli brez parcele'}"
        )
