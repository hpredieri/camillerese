import json
import anthropic
from difflib import get_close_matches
import streamlit as st
from supabase import create_client

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vocabolario Camillerese",
    page_icon="📖",
    layout="centered",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lora:ital@0;1&display=swap');
  html, body, [class*="css"] { font-family: 'Lora', Georgia, serif; }
  h1, h2, h3 { font-family: 'Playfair Display', serif; }
  .result-card {
    background: #fdf8f0; border-left: 4px solid #8b4513;
    border-radius: 6px; padding: 1.2rem 1.5rem; margin-top: 1rem; color: #2c1810;
  }
  .badge {
    display: inline-block; background: #8b4513; color: #fdf8f0;
    font-size: 0.75rem; font-variant: small-caps; letter-spacing: 0.08em;
    padding: 2px 10px; border-radius: 3px; margin-bottom: 0.6rem;
  }
  .word-title { font-family: 'Playfair Display', serif; font-size: 1.8rem; font-style: italic; margin: 0 0 0.3rem 0; }
  .translation-line { margin: 0.25rem 0; font-size: 1rem; }
  .similar-words {
    background: #f5ede0; border-radius: 4px; padding: 0.5rem 1rem;
    margin-top: 0.8rem; font-size: 0.9rem; color: #5a3e2b;
  }
  .stTextInput > div > div > input { font-family: 'Lora', serif; font-size: 1.1rem; }
  .stButton > button {
    font-family: 'Lora', serif; background-color: #8b4513; color: #fdf8f0;
    border: none; border-radius: 4px; padding: 0.4rem 1.4rem;
  }
  .stButton > button:hover { background-color: #a0522d; color: #fff; }
</style>
""", unsafe_allow_html=True)

# ─── Password gate ───────────────────────────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True
    st.markdown("<h1 style='text-align:center'>📖 Vocabolario Camillerese</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#8b4513;font-style:italic'>Accesso riservato — inserire la password</p>", unsafe_allow_html=True)
    st.divider()
    pw = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password…")
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        login = st.button("Entra", use_container_width=True)
    if login:
        if pw == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Password errata.")
    return False

if not check_password():
    st.stop()

# ─── Supabase connection ─────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )

@st.cache_resource
def get_anthropic_client():
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# ─── Load / save ─────────────────────────────────────────────────────────────
def carica():
    """Load all words from Supabase into a local dict."""
    try:
        sb = get_supabase()
        res = sb.table("vocabolario").select("*").execute()
        vocab = {}
        for row in res.data:
            parola = row["parola"].strip().lower()
            vocab[parola] = {
                "dizionario":  row.get("dizionario", ""),
                "italiano":    row.get("italiano", ""),
                "inglese":     row.get("inglese", ""),
                "definizione": row.get("definizione", ""),
            }
        return vocab
    except Exception as e:
        st.warning(f"Impossibile caricare il vocabolario: {e}")
        return {}

def salva(parola, dati):
    """Upsert a word to Supabase and update local session cache."""
    try:
        sb = get_supabase()
        sb.table("vocabolario").upsert({
            "parola":      parola,
            "dizionario":  dati.get("dizionario", ""),
            "italiano":    dati.get("italiano", ""),
            "inglese":     dati.get("inglese", ""),
            "definizione": dati.get("definizione", ""),
        }).execute()
        st.session_state.vocab[parola] = dati
    except Exception as e:
        st.warning(f"Impossibile salvare la parola: {e}")

# ─── AI lookup ───────────────────────────────────────────────────────────────
def parse_json(raw):
    raw = raw.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    return json.loads(raw[start:end])

def traduci_ai(parola):
    client = get_anthropic_client()
    prompt = (
        f"Analizza questa parola di origine dialettale: '{parola}'.\n"
        "Determina se è siciliana (dialetto tradizionale) o camillerese (inventato da Camilleri).\n"
        "Rispondi SOLO con un oggetto JSON, niente altro, senza backticks:\n"
        '{"dizionario": "siciliano|camillerese", "italiano": "...", "inglese": "...", "definizione": "..."}'
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_json(message.content[0].text.strip())

# ─── Search logic ─────────────────────────────────────────────────────────────
def cerca(vocab, parola):
    # 1. Exact match — free, instant
    if parola in vocab:
        return vocab[parola], [], "cache"

    # 2. Fuzzy suggestions
    simili = get_close_matches(parola, vocab.keys(), n=3, cutoff=0.6)

    # 3. AI — costs a call, saves result permanently
    risultato = traduci_ai(parola)
    if risultato:
        salva(parola, risultato)
        return risultato, simili, "ai"

    return None, simili, None

# ─── Main UI ─────────────────────────────────────────────────────────────────
if "vocab" not in st.session_state:
    with st.spinner("Caricamento vocabolario…"):
        st.session_state.vocab = carica()

st.markdown("<h1 style='text-align:center'>📖 Vocabolario Camillerese</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#8b4513;font-style:italic;margin-bottom:1.5rem'>"
    "Dizionario siciliano, camillerese e italiano"
    "</p>",
    unsafe_allow_html=True
)

col_input, col_btn = st.columns([4, 1])
with col_input:
    parola = st.text_input("Parola", label_visibility="collapsed", placeholder="Cerca una parola…", key="search_input")
with col_btn:
    cerca_btn = st.button("Cerca", use_container_width=True)

if cerca_btn and parola.strip():
    parola = parola.strip().lower()
    with st.spinner("Ricerca in corso…"):
        risultato, simili, source = cerca(st.session_state.vocab, parola)

    if simili and not risultato:
        st.markdown(
            f"<div class='similar-words'>💡 <strong>Parole simili:</strong> {', '.join(simili)}</div>",
            unsafe_allow_html=True
        )

    if risultato:
        badge = risultato.get("dizionario", "?").upper()
        italiano = risultato.get("italiano", "—")
        inglese = risultato.get("inglese", "")
        definizione = risultato.get("definizione", "—")
        source_label = {"cache": "📚 da vocabolario", "ai": "🤖 via AI"}.get(source, "")

        st.markdown(f"""
        <div class='result-card'>
          <span class='badge'>{badge}</span>
          {"<span style='float:right;font-size:0.75rem;color:#a0522d'>" + source_label + "</span>" if source_label else ""}
          <div class='word-title'>{parola}</div>
          <div class='translation-line'>🇮🇹 &nbsp;<strong>{italiano}</strong></div>
          {"<div class='translation-line'>🇬🇧 &nbsp;" + inglese + "</div>" if inglese else ""}
          <div class='translation-line' style='margin-top:0.5rem;color:#5a3e2b'>📝 &nbsp;{definizione}</div>
        </div>
        """, unsafe_allow_html=True)

        if simili:
            st.markdown(
                f"<div class='similar-words' style='margin-top:0.6rem'>💡 <strong>Parole simili:</strong> {', '.join(simili)}</div>",
                unsafe_allow_html=True
            )
    elif not simili:
        st.warning(f"Nessun risultato trovato per «{parola}».")

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Vocabolario")
    vocab = st.session_state.get("vocab", {})
    counts = {"italiano": 0, "siciliano": 0, "camillerese": 0}
    for dati in vocab.values():
        d = dati.get("dizionario", "")
        if d in counts:
            counts[d] += 1
    st.metric("Italiano", counts["italiano"])
    st.metric("Siciliano", counts["siciliano"])
    st.metric("Camillerese", counts["camillerese"])
    st.divider()
    if st.button("🔄 Ricarica vocabolario"):
        st.session_state.vocab = carica()
        st.rerun()
    st.markdown("<small style='color:#8b4513'>Vocabolario Camillerese &copy; 2025</small>", unsafe_allow_html=True)
