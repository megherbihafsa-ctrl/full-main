# main.py
import streamlit as st
from datetime import datetime

from ui_theme import inject_premium_ui, hero_header
from auth import render_login_form
from admin_examens import admin_dashboard
from vice_doyen import vice_doyen_dashboard
from chef_departement import render_department_head_dashboard
from etudiant import render_student_dashboard
from professeur import render_professor_dashboard

st.set_page_config(
    page_title="🎓 Plateforme Examens Universitaires",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_premium_ui()

# ========================
# PAGE LOGIN
# ========================
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    hero_header(
        "🎓 Plateforme d'Optimisation des Examens",
        "Université • Planning • Conflits • Validation • Analytics",
        pills=["UI Glass", "PostgreSQL", "Streamlit"],
    )
    st.write("")
    render_login_form()
    st.write("")
    st.markdown(
        """
<div style="text-align:center; color: rgba(255,255,255,0.65); padding: 1.5rem 0;">
  <div style="font-weight:700;">Optimisation automatique en moins de 45 secondes</div>
  <div style="font-size:0.9rem;">© 2026 - Projet Numérique Examens</div>
</div>
""",
        unsafe_allow_html=True,
    )

else:
    user = st.session_state.user
    role = st.session_state.role

    # Sidebar Premium
    with st.sidebar:
        st.markdown(
            f"""
<div class="card fadeUp" style="text-align:center;">
  <div style="font-size:0.95rem; color: rgba(255,255,255,0.7);">Connecté</div>
  <div style="font-size:1.15rem; font-weight:800; margin-top:6px;">👤 {user.get("username","")}</div>
  <div style="margin-top:6px; color: rgba(255,255,255,0.7);">{role.replace("_"," ").title()}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.write("")

        if st.button("🚪 Déconnexion", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    role_names = {
        "admin_examens": "Administrateur Examens",
        "vice_doyen": "Vice-Doyen / Doyen",
        "etudiant": "Étudiant",
        "professeur": "Professeur",
        "chef_departement": "Chef de Département",
    }

    hero_header(
        f"📋 Tableau de bord — {role_names.get(role, role.title())}",
        "Vue adaptée automatiquement selon le rôle.",
        pills=["UI Moderne", "Analytics", "Exports"],
    )
    st.write("")

    # ROUTING
    if role == "admin_examens":
        admin_dashboard()
    elif role == "vice_doyen":
        vice_doyen_dashboard()
    elif role == "chef_departement":
        render_department_head_dashboard()
    elif role == "etudiant":
        render_student_dashboard()
    elif role == "professeur":
        render_professor_dashboard()
    else:
        st.error("Rôle non pris en charge.")
        st.info("Vérifiez la colonne role dans la table users.")

    st.markdown(
        """
<div style="text-align:center; color: rgba(255,255,255,0.65); padding: 1.5rem 0;">
  <div style="font-weight:700;">Plateforme d'Optimisation des Examens</div>
  <div style="font-size:0.9rem;">Génération EDT < 45s • Conflits • Validation</div>
</div>
""",
        unsafe_allow_html=True,
    )