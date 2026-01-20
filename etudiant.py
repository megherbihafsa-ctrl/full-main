"""
Interface étudiant complète avec toutes les fonctionnalités
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from queries import ExamQueries, AnalyticsQueries, UserQueries
from student_requests import StudentRequests  # NOUVEAU
import calendar
from connection import execute_query

# Importer les fonctions
from student_functions import (
    render_personal_schedule,
    render_room_view,
    render_student_statistics,
)

# ==============================
# DASHBOARD PRINCIPAL
# ==============================

def render_student_dashboard():
    """
    Dashboard principal pour les étudiants - VERSION COMPLÈTE
    """
    # Header avec informations personnelles
    student_info = st.session_state.user

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 1.5rem; border-radius: 10px; color: white;">
                <h3>👨‍🎓 {student_info.get('nom_complet', 'Étudiant')}</h3>
                <p>📚 {student_info.get('formation', 'Formation')}</p>
                <p>🏛️ {student_info.get('departement', 'Département')} • 🎓 Promo {student_info.get('promo', '')}</p>
                <p>📋 {student_info.get('modules_inscrits', 0)} modules • 📅 {student_info.get('examens_a_venir', 0)} examens à venir</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        today = datetime.now().date()
        exams_today = len([
            e for e in ExamQueries.get_student_exams(student_info['linked_id'], today, today)
        ])
        st.metric("📅 Examens aujourd'hui", exams_today)

    with col3:
        # Détection de conflits rapide
        conflicts = StudentRequests.detect_student_conflicts(student_info['linked_id'])
        st.metric("⚠️ Conflits détectés", len(conflicts),
                 delta="À résoudre" if conflicts else "Aucun")

    st.markdown("---")

    # Onglets complets
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📅 Planning Personnel",
        "📚 Mes Modules",
        "⚠️ Mes Conflits",
        "✏️ Demandes",
        "🗺️ Vue Salle",
        "📊 Statistiques"
    ])

    with tab1:
        render_personal_schedule(student_info['linked_id'])

    with tab2:
        render_registered_modules(student_info['linked_id'])

    with tab3:
        render_student_conflicts(student_info['linked_id'])

    with tab4:
        render_modification_requests(student_info['linked_id'])

    with tab5:
        render_room_view(student_info['linked_id'])

    with tab6:
        render_student_statistics(student_info['linked_id'])


# ==============================
# NOUVELLES FONCTIONS
# ==============================

def render_registered_modules(student_id: int):
    """
    Affiche uniquement les modules où l'étudiant est inscrit
    """
    st.subheader("📚 Mes Modules Inscrits")

    modules = StudentRequests.get_registered_modules(student_id)

    if not modules:
        st.info("Vous n'êtes inscrit à aucun module")
        return

    df = pd.DataFrame(modules)

    # Statistiques
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total modules", len(df))

    with col2:
        total_credits = df['credits'].sum() if 'credits' in df.columns else 0
        st.metric("Crédits totaux", total_credits)

    with col3:
        semesters = df['semestre'].nunique() if 'semestre' in df.columns else 0
        st.metric("Semestres", semesters)

    with col4:
        formations = df['formation_nom'].nunique() if 'formation_nom' in df.columns else 0
        st.metric("Formations", formations)

    st.markdown("### 📋 Liste détaillée")

    # Filtrer par semestre
    semestres = sorted(df['semestre'].unique()) if 'semestre' in df.columns else []
    selected_semester = st.selectbox("Filtrer par semestre", ["Tous"] + list(semestres))

    if selected_semester != "Tous" and 'semestre' in df.columns:
        df_filtered = df[df['semestre'] == selected_semester]
    else:
        df_filtered = df

    # Afficher les modules
    for idx, module in df_filtered.iterrows():
        code = module.get('code', '---')
        nom = module.get('nom', 'Module')
        with st.expander(f"📘 {code} - {nom}"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Semestre:** {module.get('semestre', '-')}")
                st.write(f"**Crédits:** {module.get('credits', '-')}")
                st.write(f"**Formation:** {module.get('formation_nom', '-')}")

            with col2:
                date_insc = module.get('date_inscription')
                if hasattr(date_insc, "strftime"):
                    st.write(f"**Date d'inscription:** {date_insc.strftime('%d/%m/%Y')}")
                else:
                    st.write("**Date d'inscription:** -")
                st.write(f"**Statut:** {module.get('statut_inscription', '-')}")

            with col3:
                exams = ExamQueries.get_student_exams(student_id)
                module_exams = [e for e in exams if e.get('module_code') == code]

                if module_exams:
                    st.write("**Examens:**")
                    for exam in module_exams:
                        d = exam.get('date_heure')
                        salle = exam.get('salle_nom', '-')
                        if hasattr(d, "strftime"):
                            st.write(f"• {d.strftime('%d/%m %H:%M')} - {salle}")
                        else:
                            st.write(f"• - - {salle}")
                else:
                    st.info("Aucun examen programmé")


def _build_conflict_uid(conflict: dict, idx: int) -> str:
    """
    Construit une clé unique et (si possible) stable pour Streamlit.
    - priorité à conflict['id'] si présent
    - sinon combinaison type + examens_ids + idx (évite doublons)
    """
    if conflict.get("id") is not None:
        return f"id_{conflict['id']}"

    type_c = str(conflict.get("type_conflit", "NA"))
    exams_ids = conflict.get("examens_ids", [])
    if isinstance(exams_ids, list):
        exams_part = "_".join(str(x) for x in exams_ids[:5])  # limiter longueur
    else:
        exams_part = str(exams_ids)

    return f"{type_c}_{exams_part}_{idx}"


def render_student_conflicts(student_id: int):
    """
    Affiche les conflits personnels de l'étudiant
    """
    st.subheader("⚠️ Mes Conflits d'Examens")

    conflicts = StudentRequests.detect_student_conflicts(student_id)

    if not conflicts:
        st.success("✅ Aucun conflit détecté dans votre emploi du temps")
        return

    st.warning(f"🚨 {len(conflicts)} conflit(s) détecté(s)")

    for idx, conflict in enumerate(conflicts):
        severity_color = {
            'CRITIQUE': '🔴',
            'ÉLEVÉ': '🟠',
            'MOYEN': '🟡',
            'FAIBLE': '🟢'
        }.get(conflict.get('severite', 'FAIBLE'), '⚪')

        conflict_uid = _build_conflict_uid(conflict, idx)

        with st.expander(f"{severity_color} {conflict.get('type_conflit', 'Conflit')}"):
            st.write(f"**Détails:** {conflict.get('details', '-')}")
            st.write(f"**Sévérité:** {conflict.get('severite', '-')}")


            if conflict.get('examens_ids'):
                st.write("**Examens concernés:**")
                exam_ids = conflict['examens_ids']
                if isinstance(exam_ids, list):
                    for exam_id in exam_ids:
                        exam_info = get_exam_info(exam_id)
                        if exam_info and hasattr(exam_info.get('date_heure'), "strftime"):
                            st.write(
                                f"• {exam_info.get('module_nom', '-')}"
                                f" - {exam_info['date_heure'].strftime('%d/%m %H:%M')}"
                            )
                        elif exam_info:
                            st.write(f"• {exam_info.get('module_nom', '-')}")
                else:
                    st.write(f"• {exam_ids}")

            # ✅ KEY UNIQUE ICI (fix de ton erreur)
            if st.button("📝 Demander un réajustement", key=f"request_{conflict_uid}"):
                st.session_state['show_request_form'] = True
                st.session_state['conflict_for_request'] = conflict
                st.rerun()


def render_modification_requests(student_id: int):
    """
    Gestion des demandes de modification d'examens
    """
    st.subheader("✏️ Mes Demandes de Modification")

    tab1, tab2 = st.tabs(["Nouvelle demande", "Mes demandes"])

    with tab1:
        render_new_request_form(student_id)

    with tab2:
        render_existing_requests(student_id)


def render_new_request_form(student_id: int):
    """
    Formulaire pour créer une nouvelle demande
    """
    st.markdown("### 📝 Nouvelle demande de modification")

    exams = ExamQueries.get_student_exams(student_id)
    future_exams = [e for e in exams if e.get('date_heure') and e['date_heure'] > datetime.now()]

    if not future_exams:
        st.info("Aucun examen à venir pour lequel faire une demande")
        return

    with st.form("new_request_form"):
        exam_options = {
            f"{e.get('module_nom','-')} - {e['date_heure'].strftime('%d/%m %H:%M')}": e['id']
            for e in future_exams
            if e.get('date_heure') and hasattr(e['date_heure'], "strftime")
        }

        if not exam_options:
            st.info("Aucun examen futur valide")
            return

        selected_exam_label = st.selectbox("Examen concerné", list(exam_options.keys()))
        exam_id = exam_options[selected_exam_label]

        request_type = st.selectbox("Type de demande", ["REPORT", "CHANGEMENT_SALLE", "AUTRE"])

        preferred_date = None
        if request_type == "REPORT":
            d = st.date_input(
                "Date souhaitée",
                min_value=datetime.now().date() + timedelta(days=1),
                max_value=datetime.now().date() + timedelta(days=30)
            )
            t = st.time_input("Heure souhaitée", datetime.strptime("09:00", "%H:%M").time())
            preferred_date = datetime.combine(d, t)

        preferred_room = None
        if request_type == "CHANGEMENT_SALLE":
            rooms_query = "SELECT id, nom FROM lieux_examen WHERE is_disponible = TRUE ORDER BY nom"
            rooms = execute_query(rooms_query)
            if rooms:
                room_options = {r['nom']: r['id'] for r in rooms}
                selected_room = st.selectbox("Salle souhaitée", list(room_options.keys()))
                preferred_room = room_options[selected_room]
            else:
                st.info("Aucune salle disponible")

        reason = st.text_area(
            "Motif de la demande",
            placeholder="Expliquez pourquoi vous avez besoin de cette modification...",
            height=100
        )

        justificatif = st.file_uploader("Justificatif (optionnel)", type=['pdf', 'jpg', 'png'])

        submitted = st.form_submit_button("Envoyer la demande")

        if submitted:
            if not reason:
                st.error("Veuillez indiquer un motif")
            else:
                success, message = StudentRequests.create_modification_request(
                    student_id=student_id,
                    exam_id=exam_id,
                    request_type=request_type,
                    reason=reason,
                    preferred_date=preferred_date,
                    preferred_room=preferred_room
                )

                if success:
                    st.success(message)

                    st.info("💡 Recherche de créneaux alternatifs...")
                    alternatives = StudentRequests.get_available_alternative_slots(student_id, exam_id)

                    if alternatives:
                        st.write("**Créneaux alternatifs suggérés:**")
                        for alt in alternatives[:3]:
                            if alt.get('creneau_libre') and alt.get('debut_creneau'):
                                debut = alt['debut_creneau']
                                if hasattr(debut, "strftime"):
                                    st.write(
                                        f"• {debut.strftime('%d/%m %H:%M')} "
                                        f"- Salle {alt.get('salle_suggeree','-')}"
                                    )
                else:
                    st.error(message)


def render_existing_requests(student_id: int):
    """
    Affiche les demandes existantes de l'étudiant
    """
    requests = StudentRequests.get_student_requests(student_id)

    if not requests:
        st.info("Vous n'avez fait aucune demande")
        return

    st.write(f"**Total demandes:** {len(requests)}")

    status_counts = {}
    for req in requests:
        status = req.get('statut', 'INCONNU')
        status_counts[status] = status_counts.get(status, 0) + 1

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("En attente", status_counts.get('EN_ATTENTE', 0))
    with col2:
        st.metric("Acceptées", status_counts.get('ACCEPTEE', 0))
    with col3:
        st.metric("Refusées", status_counts.get('REFUSEE', 0))
    with col4:
        st.metric("Traitées", status_counts.get('TRAITEE', 0))

    st.markdown("### 📋 Historique des demandes")

    for req in requests:
        status_icon = {
            'EN_ATTENTE': '⏳',
            'ACCEPTEE': '✅',
            'REFUSEE': '❌',
            'TRAITEE': '📋'
        }.get(req.get('statut'), '📄')

        req_id = req.get('id', '—')
        module_nom = req.get('module_nom', '-')

        with st.expander(f"{status_icon} Demande #{req_id} - {module_nom}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Type:** {req.get('type_demande', '-')}")
                dd = req.get('date_demande')
                if hasattr(dd, "strftime"):
                    st.write(f"**Date demande:** {dd.strftime('%d/%m/%Y %H:%M')}")
                else:
                    st.write("**Date demande:** -")

                deo = req.get('date_examen_originale')
                if hasattr(deo, "strftime"):
                    st.write(f"**Examen original:** {deo.strftime('%d/%m/%Y %H:%M')}")
                else:
                    st.write("**Examen original:** -")

                st.write(f"**Salle originale:** {req.get('salle_originale', '-')}")

            with col2:
                st.write(f"**Statut:** {req.get('statut', '-')}")
                ds = req.get('date_souhaitee')
                if ds and hasattr(ds, "strftime"):
                    st.write(f"**Date souhaitée:** {ds.strftime('%d/%m/%Y %H:%M')}")
                ss = req.get('salle_souhaitee')
                if ss:
                    st.write(f"**Salle souhaitée:** ID {ss}")

            st.write("**Motif:**")
            st.write(req.get('motif', '-'))

            rep = req.get('reponse_administration')
            if rep:
                st.write("**Réponse administration:**")
                st.info(rep)

            dr = req.get('date_reponse')
            if dr and hasattr(dr, "strftime"):
                st.write(f"**Date réponse:** {dr.strftime('%d/%m/%Y %H:%M')}")


# ==============================
# UTILITAIRE
# ==============================

def get_exam_info(exam_id: int):
    """
    Récupère les informations d'un examen
    """
    query = """
    SELECT
        e.date_heure,
        m.nom as module_nom,
        l.nom as salle_nom
    FROM examens e
    JOIN modules m ON e.module_id = m.id
    JOIN lieux_examen l ON e.salle_id = l.id
    WHERE e.id = %s
    """
    result = execute_query(query, (exam_id,))
    return result[0] if result else None
