import streamlit as st
from supabase import create_client
import pandas as pd

st.set_page_config(
    page_title="Vocabolario — Tutte le Parole",
    page_icon="📚",
    layout="wide",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:ital@0;1&display=swap');
  html, body, [class*="css"] { font-family: 'Lora', Georgia, serif; }
  h1, h2, h3 { font-family: 'Playfair Display', serif; }
  .badge {
    display: inline-block; color: #fdf8f0;
    font-size: 0.72rem; font-variant: small-caps; letter-spacing: 0.08em;
    padding: 2px 9px; border-radius: 3px;
  }
  .badge.italiano    { background: #2e6b3e; }
  .badge.siciliano   { background: #8b4513; }
  .badge.camillerese { background: #4a3070; }
  .stat-box {
    background: #fdf8f0; border-radius: 8px; padding: 1rem 1.5rem;
    text-align: center; border: 1px solid #e8d5b7;
  }
  .stat-number { font-family: 'Playfair Display', serif; font-size: 2.5rem; color: #8b4513; }
  .stat-label  { font-size: 0.85rem; color: #5a3e2b; font-variant: small-caps; letter-spacing: 0.05em; }
  .stButton > button {
    font-family: 'Lora', serif; background-color: #8b4513; color: #fdf8f0;
    border: none; border-radius: 4px;
  }
  .stButton > button:hover { background-color: #a0522d; color: #fff; }
  /* Zebra stripe the dataframe */
  [data-testid="stDataFrame"] { font-family: 'Lora', serif; }
</style>
""", unsafe_allow_html=True)

# ─── Password gate (same as main app) ───────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True
    st.markdown("<h1 style='text-align:center'>📖 Vocabolario Camillerese</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#8b4513;font-style:italic'>Accesso riservato</p>", unsafe_allow_html=True)
    st.divider()
    pw = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password…")
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Entra", use_container_width=True):
            if pw == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password errata.")
    return False

if not check_password():
    st.stop()

# ─── Load from Supabase ──────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def carica():
    try:
        res = get_supabase().table("vocabolario").select("*").order("parola").execute()
        return res.data
    except Exception as e:
        st.error(f"Errore: {e}")
        return []

# ─── Page ────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>📚 Tutte le Parole</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#8b4513;font-style:italic;margin-bottom:1.5rem'>"
    "Tutto il vocabolario raccolto finora"
    "</p>",
    unsafe_allow_html=True
)

if st.button("🔄 Aggiorna"):
    st.cache_data.clear()

rows = carica()

if not rows:
    st.info("Nessuna parola nel vocabolario ancora.")
    st.stop()

df = pd.DataFrame(rows)[["parola", "dizionario", "italiano", "inglese", "definizione"]]

# ─── Stats ───────────────────────────────────────────────────────────────────
counts = df["dizionario"].value_counts()
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='stat-box'><div class='stat-number'>{len(df)}</div><div class='stat-label'>Totale</div></div>", unsafe_allow_html=True)
with c2:
    n = counts.get("italiano", 0)
    st.markdown(f"<div class='stat-box'><div class='stat-number' style='color:#2e6b3e'>{n}</div><div class='stat-label'>Italiano</div></div>", unsafe_allow_html=True)
with c3:
    n = counts.get("siciliano", 0)
    st.markdown(f"<div class='stat-box'><div class='stat-number'>{n}</div><div class='stat-label'>Siciliano</div></div>", unsafe_allow_html=True)
with c4:
    n = counts.get("camillerese", 0)
    st.markdown(f"<div class='stat-box'><div class='stat-number' style='color:#4a3070'>{n}</div><div class='stat-label'>Camillerese</div></div>", unsafe_allow_html=True)

st.divider()

# ─── Filters ─────────────────────────────────────────────────────────────────
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    search = st.text_input("🔍 Filtra per parola o definizione", placeholder="cerca…", label_visibility="collapsed")
with col_f2:
    categoria = st.selectbox("Categoria", ["Tutte", "italiano", "siciliano", "camillerese"], label_visibility="collapsed")

filtered = df.copy()
if categoria != "Tutte":
    filtered = filtered[filtered["dizionario"] == categoria]
if search:
    mask = (
        filtered["parola"].str.contains(search, case=False, na=False) |
        filtered["italiano"].str.contains(search, case=False, na=False) |
        filtered["inglese"].str.contains(search, case=False, na=False) |
        filtered["definizione"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

st.caption(f"{len(filtered)} parole")

# ─── Table ───────────────────────────────────────────────────────────────────
st.dataframe(
    filtered.rename(columns={
        "parola": "Parola",
        "dizionario": "Tipo",
        "italiano": "Italiano",
        "inglese": "Inglese",
        "definizione": "Definizione",
    }),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Parola":      st.column_config.TextColumn(width="small"),
        "Tipo":        st.column_config.TextColumn(width="small"),
        "Italiano":    st.column_config.TextColumn(width="medium"),
        "Inglese":     st.column_config.TextColumn(width="medium"),
        "Definizione": st.column_config.TextColumn(width="large"),
    }
)
