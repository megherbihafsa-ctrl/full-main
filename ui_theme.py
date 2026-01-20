# ui_theme.py
import streamlit as st

def inject_premium_ui():
    """Injecte un thème Glassmorphism premium + fixes overflow + styles composants."""
    st.markdown(
        """
<style>
/* =========================================================
   ✅ FIXES IMPORTANT (barre blanche / overflow)
========================================================= */
html, body { width: 100%; overflow-x: hidden !important; }
.stApp { overflow-x: hidden !important; }
.block-container { max-width: 100% !important; padding-top: 1rem; padding-bottom: 2rem; }
* { box-sizing: border-box; }

/* =========================================================
   🎨 THEME GLASS PREMIUM
========================================================= */
:root{
  --bg0: #050816;
  --bg1: #070b18;
  --glass: rgba(255,255,255,0.08);
  --glass2: rgba(255,255,255,0.11);
  --border: rgba(255,255,255,0.14);
  --txt: rgba(255,255,255,0.92);
  --muted: rgba(255,255,255,0.66);
  --accent: #7c3aed;
  --accent2: #22c55e;
  --warn: #f59e0b;
  --danger: #ef4444;
  --shadow: 0 18px 50px rgba(0,0,0,0.38);
}

.stApp{
  color: var(--txt);
  background:
    radial-gradient(60% 40% at 15% 10%, rgba(124,58,237,0.35), transparent 55%),
    radial-gradient(55% 35% at 85% 20%, rgba(34,197,94,0.23), transparent 50%),
    radial-gradient(40% 30% at 65% 90%, rgba(59,130,246,0.14), transparent 45%),
    linear-gradient(180deg, var(--bg0), var(--bg1) 45%, var(--bg0));
}

/* =========================================================
   Sidebar premium
========================================================= */
section[data-testid="stSidebar"]{
  background: rgba(255,255,255,0.06) !important;
  border-right: 1px solid var(--border);
  overflow-x: hidden !important;
}
section[data-testid="stSidebar"] *{ color: var(--txt) !important; }

/* =========================================================
   Buttons premium
========================================================= */
div.stButton>button{
  border-radius: 14px !important;
  border: 1px solid var(--border) !important;
  background: rgba(255,255,255,0.08) !important;
  box-shadow: 0 10px 25px rgba(0,0,0,0.18);
  transition: 0.18s ease;
}
div.stButton>button:hover{
  transform: translateY(-1px);
  border-color: rgba(124,58,237,0.65) !important;
  background: rgba(124,58,237,0.18) !important;
}

/* =========================================================
   Inputs premium
========================================================= */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid var(--border) !important;
  color: var(--txt) !important;
  border-radius: 12px !important;
}

/* =========================================================
   Dataframe / charts container premium
========================================================= */
[data-testid="stDataFrame"]{
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255,255,255,0.04);
}

/* =========================================================
   Animations (smooth)
========================================================= */
@keyframes fadeUp {
  from { opacity:0; transform: translateY(10px); }
  to   { opacity:1; transform: translateY(0px); }
}
.fadeUp { animation: fadeUp 0.35s ease-out; }

/* =========================================================
   COMPONENTS: cards, headers, badges, KPI
========================================================= */
.card{
  background: var(--glass);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 16px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.card:hover{
  transform: translateY(-2px);
  transition: 0.2s ease;
}

.h-title{
  font-size: 1.35rem;
  font-weight: 780;
  letter-spacing: 0.2px;
  margin-bottom: 6px;
}
.h-sub{
  color: var(--muted);
  margin-top: 0;
  font-size: 0.95rem;
}

.badge{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.78rem;
  border:1px solid var(--border);
  background: rgba(255,255,255,0.06);
  margin-left: 6px;
}

.badge.ok { border-color: rgba(34,197,94,0.40); }
.badge.warn { border-color: rgba(245,158,11,0.45); }
.badge.danger { border-color: rgba(239,68,68,0.45); }

.kpi-title{ font-size: 0.85rem; color: var(--muted); margin-bottom: 8px; }
.kpi-value{ font-size: 1.65rem; font-weight: 800; margin: 0; }
.kpi-sub{ font-size: 0.85rem; color: var(--muted); margin-top: 8px; }

/* Pills (top right tech chips) */
.pill{
  display:inline-flex;
  gap:8px;
  align-items:center;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(34,197,94,0.35);
  background: rgba(34,197,94,0.10);
  font-size: 0.80rem;
}

/* Header bar */
.hero{
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.14);
  background:
    linear-gradient(90deg, rgba(124,58,237,0.18), rgba(34,197,94,0.10)),
    rgba(255,255,255,0.06);
  box-shadow: var(--shadow);
  backdrop-filter: blur(14px);
}
</style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""
<div class="fadeUp">
  <div class="h-title">{title}</div>
  <div class="h-sub">{subtitle}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def kpi_card(title: str, value: str, sub: str = "", tone: str = "ok"):
    tone_cls = {"ok": "ok", "warn": "warn", "danger": "danger"}.get(tone, "ok")
    st.markdown(
        f"""
<div class="card fadeUp">
  <div class="kpi-title">{title} <span class="badge {tone_cls}">{tone.upper()}</span></div>
  <p class="kpi-value">{value}</p>
  <div class="kpi-sub">{sub}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def hero_header(title: str, subtitle: str, pills=None):
    pills = pills or []
    pills_html = "".join([f'<span class="pill">{p}</span>' for p in pills])
    st.markdown(
        f"""
<div class="hero fadeUp">
  <div style="display:flex; align-items:center; justify-content:space-between; gap:14px; flex-wrap:wrap;">
    <div>
      <div class="h-title">{title}</div>
      <div class="h-sub">{subtitle}</div>
    </div>
    <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end;">
      {pills_html}
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )