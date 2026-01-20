"""
Interface professeur adaptée au projet de Plateforme d'Optimisation des Emplois du Temps d'Examens Universitaires
Version corrigée -
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from connection import execute_query, load_dataframe

# ========== CONSTANTES DU PROJET ==========
PROJECT_CONSTRAINTS = {
    'max_exams_per_day': 3,  # Professeurs: Maximum 3 examens par jour
    'max_exams_per_student_day': 1,  # Étudiants: Maximum 1 examen par jour
    'min_capacity_usage': 60,  # Utilisation minimale des salles (%)
    'target_generation_time': 45,  # Génération en moins de 45 secondes
    'department_priority': True,  # Priorité aux examens du département
    'balance_tolerance': 2,  # Tolérance pour l'équilibre entre professeurs
}

# ========== FONCTIONS DE SÉCURITÉ CONTRE LES VALEURS NULL ==========

def safe_int(value, default=0):
    """
    Convertit une valeur en entier de manière sécurisée
    Retourne default si la valeur est None ou invalide
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """
    Convertit une valeur en float de manière sécurisée
    Retourne default si la valeur est None ou invalide
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_str(value, default=""):
    """
    Convertit une valeur en string de manière sécurisée
    Retourne default si la valeur est None ou invalide
    """
    if value is None:
        return default
    try:
        return str(value)
    except:
        return default

def safe_date(value, default=None):
    """
    Convertit une valeur en date de manière sécurisée
    """
    if value is None:
        return default
    try:
        if isinstance(value, (datetime, date)):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return default
    except:
        return default

# ========== FONCTIONS UTILITAIRES ==========

def get_professor_dashboard_data(prof_id: int):
    """
    Récupère les données principales pour le dashboard du professeur
    Version sécurisée avec COALESCE
    """
    query = """
    SELECT 
        e.id as exam_id,
        e.date_heure,
        COALESCE(e.duree_minutes, 0) as duree_minutes,
        COALESCE(e.statut, 'Inconnu') as statut,
        COALESCE(m.nom, 'Non spécifié') as module_nom,
        COALESCE(m.code, 'N/A') as module_code,
        COALESCE(f.nom, 'Non spécifié') as formation_nom,
        COALESCE(f.code, 'N/A') as formation_code,
        COALESCE(l.nom, 'Non spécifié') as salle_nom,
        COALESCE(l.capacite, 0) as capacite,
        COALESCE(l.type, 'Non spécifié') as type_salle,
        COALESCE(l.batiment, 'Non spécifié') as batiment,
        COALESCE(COUNT(DISTINCT ins.etudiant_id), 0) as nb_etudiants_inscrits,
        CONCAT(COALESCE(p.nom, ''), ' ', COALESCE(p.prenom, '')) as professeur_nom,
        COALESCE(d.nom, 'Non spécifié') as departement_nom
    FROM examens e
    JOIN modules m ON e.module_id = m.id
    JOIN formations f ON m.formation_id = f.id
    JOIN departements d ON f.departement_id = d.id
    JOIN lieux_examen l ON e.salle_id = l.id
    JOIN professeurs p ON e.professeur_id = p.id
    LEFT JOIN inscriptions ins ON m.id = ins.module_id 
        AND ins.annee_academique = EXTRACT(YEAR FROM CURRENT_DATE)
        AND ins.statut = 'Inscrit'
    WHERE e.professeur_id = %s
        AND e.date_heure >= CURRENT_DATE
        AND e.statut IN ('Planifie', 'Confirme')
    GROUP BY e.id, e.date_heure, e.duree_minutes, e.statut, 
             m.nom, m.code, f.nom, f.code, l.nom, l.capacite, 
             l.type, l.batiment, p.nom, p.prenom, d.nom
    ORDER BY e.date_heure
    """
    return execute_query(query, (prof_id,))

def check_professor_constraints(prof_id: int):
    """
    Vérifie les contraintes spécifiques du projet pour un professeur
    Version sécurisée
    """
    constraints = []
    
    # Contrainte 1: Maximum 3 examens par jour
    query = """
    SELECT DATE(date_heure) as jour, COUNT(*) as nb_examens
    FROM examens
    WHERE professeur_id = %s
        AND statut IN ('planifie', 'confirme')
        AND DATE(date_heure) >= CURRENT_DATE
    GROUP BY DATE(date_heure)
    HAVING COUNT(*) > 3
    """
    
    violations = execute_query(query, (prof_id,))
    if violations:
        for v in violations:
            nb_examens = safe_int(v.get('nb_examens'), 0)
            jour = safe_str(v.get('jour'), 'Date inconnue')
            constraints.append({
                'type': 'MAX_EXAMS_PER_DAY',
                'severity': 'CRITIQUE',
                'message': f"⚠️ {nb_examens} examens le {jour} (max: 3)",
                'details': f"Jour: {jour}, Examens: {nb_examens}"
            })
    
    # Contrainte 2: Équilibre entre professeurs du même département
    query = """
    WITH stats_departement AS (
        SELECT 
            p.id,
            CONCAT(p.nom, ' ', p.prenom) as nom_prof,
            COUNT(e.id) as nb_examens,
            AVG(COUNT(e.id)) OVER () as moyenne_departement
        FROM professeurs p
        LEFT JOIN examens e ON p.id = e.professeur_id 
            AND e.statut IN ('planifie', 'confirme')
            AND e.date_heure >= CURRENT_DATE
        WHERE p.departement_id = (
            SELECT departement_id FROM professeurs WHERE id = %s
        )
        GROUP BY p.id, p.nom, p.prenom
    )
    SELECT * FROM stats_departement WHERE id = %s
    """
    
    stats = execute_query(query, (prof_id, prof_id))
    if stats:
        stats = stats[0]
        nb_examens = safe_int(stats.get('nb_examens'), 0)
        moyenne = safe_float(stats.get('moyenne_departement'), 0.0)
        
        diff = abs(nb_examens - moyenne)
        if diff > 2:  # Tolérance de 2 examens
            constraints.append({
                'type': 'BALANCE_IMBALANCE',
                'severity': 'MOYEN',
                'message': f"📊 Déséquilibre détecté: {nb_examens} vs moyenne {moyenne:.1f}",
                'details': f"Différence: {diff:.1f} examens"
            })
    
    return constraints

def get_professor_workload_stats(prof_id: int, start_date: date = None, end_date: date = None):
    """
    Statistiques de charge de travail du professeur
    Version sécurisée
    """
    if not start_date:
        start_date = datetime.now().date()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    query = """
    SELECT 
        DATE(e.date_heure) as jour,
        COUNT(*) as nb_examens,
        SUM(COALESCE(e.duree_minutes, 0)) / 60.0 as total_heures,
        COUNT(DISTINCT m.id) as nb_modules,
        STRING_AGG(DISTINCT f.nom, ', ') as formations
    FROM examens e
    JOIN modules m ON e.module_id = m.id
    JOIN formations f ON m.formation_id = f.id
    WHERE e.professeur_id = %s
        AND e.date_heure::date BETWEEN %s AND %s
        AND e.statut IN ('planifie', 'confirme')
    GROUP BY DATE(e.date_heure)
    ORDER BY jour
    """
    
    return load_dataframe(query, (prof_id, start_date, end_date))

def get_department_exams(prof_id: int):
    """
    Récupère les examens du département du professeur
    Version sécurisée
    """
    query = """
    SELECT 
        e.id,
        e.date_heure,
        COALESCE(e.duree_minutes, 0) as duree_minutes,
        COALESCE(m.nom, 'Non spécifié') as module_nom,
        COALESCE(f.nom, 'Non spécifié') as formation_nom,
        COALESCE(l.nom, 'Non spécifié') as salle_nom,
        CONCAT(COALESCE(p.nom, ''), ' ', COALESCE(p.prenom, '')) as professeur,
        COALESCE(e.statut, 'Inconnu') as statut
    FROM examens e
    JOIN modules m ON e.module_id = m.id
    JOIN formations f ON m.formation_id = f.id
    JOIN lieux_examen l ON e.salle_id = l.id
    JOIN professeurs p ON e.professeur_id = p.id
    WHERE p.departement_id = (
        SELECT departement_id FROM professeurs WHERE id = %s
    )
    AND e.date_heure >= CURRENT_DATE
    AND e.statut IN ('planifie', 'confirme')
    ORDER BY e.date_heure
    LIMIT 50
    """
    
    return execute_query(query, (prof_id,))

def format_date(date_value):
    """Formate une date de manière sécurisée"""
    date_value = safe_date(date_value)
    if not date_value:
        return "Date inconnue"
    return date_value.strftime('%d/%m/%Y %H:%M')

def format_duration(minutes):
    """Formate une durée en heures/minutes"""
    minutes_int = safe_int(minutes, 0)
    hours = minutes_int // 60
    mins = minutes_int % 60
    if hours > 0:
        return f"{hours}h{mins:02d}"
    return f"{mins}min"

# ========== INTERFACE PRINCIPALE ==========

def render_professor_dashboard():
    """
    Interface principale du professeur adaptée au projet
    Version sécurisée
    """
    try:
        # Vérification de session
        if 'user' not in st.session_state:
            st.error("🔒 Veuillez vous connecter")
            return
        
        user = st.session_state.user
        if user.get('role') != 'professeur':
            st.error("⛔ Cette page est réservée aux professeurs")
            return
        
        prof_id = safe_int(user.get('linked_id', 1))
        prof_name = safe_str(user.get('display_name', 'Professeur'))
        department = safe_str(user.get('departement', 'Non spécifié'))
        
        # Header
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                        padding: 2rem; border-radius: 10px; color: white; margin-bottom: 2rem;">
                <h1 style="margin: 0;">📋 Planning des Examens - Interface Professeur</h1>
                <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem;">
                    {prof_name} • Département: {department}
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Dashboard principal
        st.subheader("📊 Vue d'ensemble des surveillances")
        
        # Récupérer les données
        exams_data = get_professor_dashboard_data(prof_id)
        constraints = check_professor_constraints(prof_id)
        
        # KPI Cards - SÉCURISÉES
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_exams = safe_int(len(exams_data) if exams_data else 0)
            st.metric("📅 Examens programmés", total_exams)
        
        with col2:
            if exams_data:
                total_students = sum(safe_int(exam.get('nb_etudiants_inscrits', 0)) for exam in exams_data)
            else:
                total_students = 0
            st.metric("👨‍🎓 Étudiants concernés", safe_int(total_students))
        
        with col3:
            if exams_data:
                total_minutes = sum(safe_int(exam.get('duree_minutes', 0)) for exam in exams_data)
                total_hours = safe_float(total_minutes / 60.0)
            else:
                total_hours = 0.0
            st.metric("⏱️ Heures de surveillance", f"{total_hours:.1f}h")
        
        with col4:
            alert_count = safe_int(len(constraints))
            st.metric("⚠️ Alertes", alert_count, 
                     delta="À vérifier" if alert_count > 0 else "OK")
        
        # Onglets principaux
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Mes examens",
            "🏫 Examens du département",
            "📊 Statistiques",
            "ℹ️ Informations"
        ])
        
        with tab1:
            render_my_exams(prof_id, exams_data)
        
        with tab2:
            render_department_exams(prof_id)
        
        with tab3:
            render_statistics(prof_id)
        
        with tab4:
            render_information()
            
    except Exception as e:
        st.error(f"Une erreur est survenue: {str(e)}")
        st.info("Veuillez rafraîchir la page ou contacter le support technique")
        import traceback
        st.code(traceback.format_exc())

# ========== TAB 1: MES EXAMENS ==========

def render_my_exams(prof_id: int, exams_data):
    """
    Affiche les examens assignés au professeur
    Version sécurisée
    """
    st.subheader("📋 Mes examens de surveillance")
    
    if not exams_data:
        st.info("🎯 Aucun examen programmé pour vous surveiller")
        return
    
    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("Période", 
                            ["Aujourd'hui", "Cette semaine", "Ce mois", "Tout"],
                            key="period_filter")
    
    with col2:
        if st.checkbox("Afficher les détails", True, key="show_details"):
            detailed_view = True
        else:
            detailed_view = False
    
    # Filtrer les examens selon la période
    filtered_exams = []
    today = datetime.now().date()
    
    for exam in exams_data:
        exam_date = safe_date(exam.get('date_heure'))
        if not exam_date:
            continue
        
        # Appliquer filtre de période
        exam_date_date = exam_date.date()
        
        if period == "Aujourd'hui" and exam_date_date != today:
            continue
        elif period == "Cette semaine":
            week_end = today + timedelta(days=7)
            if not (today <= exam_date_date <= week_end):
                continue
        elif period == "Ce mois" and exam_date_date.month != today.month:
            continue
        
        filtered_exams.append(exam)
    
    if not filtered_exams:
        st.info("Aucun examen dans la période sélectionnée")
        return
    
    # Afficher les examens - SÉCURISÉ
    for exam in filtered_exams:
        exam_id = safe_int(exam.get('exam_id'), 0)
        exam_date = format_date(exam.get('date_heure'))
        module_name = safe_str(exam.get('module_nom', 'N/A'))
        formation = safe_str(exam.get('formation_nom', 'N/A'))
        
        with st.expander(f"{module_name} - {exam_date}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Formation:** {formation}")
                st.write(f"**Salle:** {safe_str(exam.get('salle_nom', 'N/A'))}")
                st.write(f"**Type salle:** {safe_str(exam.get('type_salle', 'N/A'))}")
                st.write(f"**Capacité:** {safe_int(exam.get('capacite', 0))} places")
            
            with col2:
                duree = safe_int(exam.get('duree_minutes', 0))
                st.write(f"**Durée:** {duree} minutes")
                
                statut = safe_str(exam.get('statut', 'N/A'))
                st.write(f"**Statut:** {statut.title()}")
                
                nb_etudiants = safe_int(exam.get('nb_etudiants_inscrits', 0))
                st.write(f"**Étudiants inscrits:** {nb_etudiants}")
            
            # Boutons d'action simples
            if statut == 'planifie':
                if st.button("✅ Confirmer disponibilité", key=f"confirm_{exam_id}"):
                    execute_query(
                        "UPDATE examens SET statut = 'confirme' WHERE id = %s",
                        (exam_id,), 
                        fetch=False
                    )
                    st.success("Disponibilité confirmée")
                    st.rerun()
    
    # Vérification des contraintes
    st.markdown("---")
    st.subheader("🔍 Vérification des contraintes")
    
    constraints = check_professor_constraints(prof_id)
    if constraints:
        for constraint in constraints:
            if constraint['severity'] == 'CRITIQUE':
                st.error(f"**{constraint['message']}**")
            else:
                st.warning(f"**{constraint['message']}**")
    else:
        st.success("✅ Toutes les contraintes sont respectées")

# ========== TAB 2: EXAMENS DU DÉPARTEMENT ==========

def render_department_exams(prof_id: int):
    """
    Affiche tous les examens du département du professeur
    Version sécurisée
    """
    st.subheader("🏫 Examens du département")
    
    dept_exams = get_department_exams(prof_id)
    
    if not dept_exams:
        st.info("Aucun examen programmé dans votre département")
        return
    
    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        show_all = st.checkbox("Afficher tous les examens", True, key="show_all_dept")
    
    with col2:
        if show_all:
            limit = safe_int(len(dept_exams))
        else:
            limit = st.slider("Nombre d'examens à afficher", 5, 50, 10, key="dept_limit")
    
    # Tableau des examens - SÉCURISÉ
    exam_list = []
    for exam in dept_exams[:safe_int(limit, 10)]:
        exam_list.append({
            'Date': format_date(exam.get('date_heure')),
            'Module': safe_str(exam.get('module_nom', 'N/A')),
            'Formation': safe_str(exam.get('formation_nom', 'N/A')),
            'Salle': safe_str(exam.get('salle_nom', 'N/A')),
            'Durée (min)': safe_int(exam.get('duree_minutes', 0)),
            'Professeur': safe_str(exam.get('professeur', 'N/A')),
            'Statut': safe_str(exam.get('statut', 'N/A')).title()
        })
    
    if exam_list:
        df = pd.DataFrame(exam_list)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Date': st.column_config.TextColumn(width="medium"),
                'Module': st.column_config.TextColumn(width="large"),
                'Formation': st.column_config.TextColumn(width="medium"),
                'Salle': st.column_config.TextColumn(width="small"),
                'Durée (min)': st.column_config.NumberColumn(width="small"),
                'Professeur': st.column_config.TextColumn(width="medium"),
                'Statut': st.column_config.TextColumn(width="small")
            }
        )
    
    # Statistiques du département
    st.markdown("---")
    st.subheader("📊 Statistiques du département")
    
    query = """
    SELECT 
        p.nom as professeur,
        COUNT(e.id) as nb_examens,
        SUM(COALESCE(e.duree_minutes, 0)) / 60.0 as heures_surveillance
    FROM professeurs p
    LEFT JOIN examens e ON p.id = e.professeur_id
        AND e.date_heure >= CURRENT_DATE
        AND e.statut IN ('planifie', 'confirme')
    WHERE p.departement_id = (
        SELECT departement_id FROM professeurs WHERE id = %s
    )
    GROUP BY p.id, p.nom
    ORDER BY nb_examens DESC
    """
    
    dept_stats = execute_query(query, (prof_id,))
    if dept_stats:
        # Créer un DataFrame
        stats_df = pd.DataFrame(dept_stats)
        
        # Graphique de répartition
        if not stats_df.empty:
            # Sécuriser les données pour le graphique
            stats_df['nb_examens'] = stats_df['nb_examens'].fillna(0).astype(int)
            stats_df['heures_surveillance'] = stats_df['heures_surveillance'].fillna(0.0).astype(float)
            
            fig = px.bar(
                stats_df,
                x='professeur',
                y='nb_examens',
                title="Répartition des examens par professeur",
                labels={'professeur': 'Professeur', 'nb_examens': "Nombre d'examens"},
                color='nb_examens',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Afficher le tableau des stats
            st.dataframe(
                stats_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'professeur': st.column_config.TextColumn("Professeur"),
                    'nb_examens': st.column_config.NumberColumn("Examens"),
                    'heures_surveillance': st.column_config.NumberColumn("Heures", format="%.1f")
                }
            )

# ========== TAB 3: STATISTIQUES ==========

def render_statistics(prof_id: int):
    """
    Affiche les statistiques de charge de travail
    Version sécurisée
    """
    st.subheader("📊 Statistiques de surveillance")
    
    # Période d'analyse
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Date de début", 
                                  datetime.now().date(), 
                                  key="stats_start")
    with col2:
        end_date = st.date_input("Date de fin", 
                                datetime.now().date() + timedelta(days=30),
                                key="stats_end")
    
    # Récupérer les statistiques
    stats_df = get_professor_workload_stats(prof_id, start_date, end_date)
    
    if stats_df.empty:
        st.info("Aucune donnée statistique pour cette période")
        return
    
    # KPI - SÉCURISÉS
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_exams = safe_int(stats_df['nb_examens'].sum() if not stats_df.empty else 0)
        st.metric("Total examens", total_exams)
    
    with col2:
        total_hours = safe_float(stats_df['total_heures'].sum() if not stats_df.empty else 0.0)
        st.metric("Heures totales", f"{total_hours:.1f}")
    
    with col3:
        if not stats_df.empty:
            avg_per_day = safe_float(stats_df['nb_examens'].mean())
        else:
            avg_per_day = 0.0
        st.metric("Moyenne/jour", f"{avg_per_day:.1f}")
    
    # Graphiques
    if not stats_df.empty:
        # Convertir la colonne 'jour' en datetime
        stats_df['jour'] = pd.to_datetime(stats_df['jour'])
        
        # S'assurer que les colonnes numériques sont valides
        stats_df['nb_examens'] = stats_df['nb_examens'].fillna(0).astype(int)
        stats_df['total_heures'] = stats_df['total_heures'].fillna(0.0).astype(float)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Graphique en barres
            fig1 = px.bar(
                stats_df,
                x='jour',
                y='nb_examens',
                title="Nombre d'examens par jour",
                labels={'jour': 'Date', 'nb_examens': "Nombre d'examens"},
                color='nb_examens'
            )
            fig1.add_hline(y=3, line_dash="dash", line_color="red", 
                          annotation_text="Limite: 3 examens/jour")
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Graphique des heures
            fig2 = px.line(
                stats_df,
                x='jour',
                y='total_heures',
                title="Heures de surveillance par jour",
                labels={'jour': 'Date', 'total_heures': 'Heures'},
                markers=True
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # Analyse des contraintes
    st.markdown("---")
    st.subheader("📈 Analyse de la charge")
    
    # Jours avec plus de 3 examens
    if not stats_df.empty:
        stats_df['nb_examens'] = stats_df['nb_examens'].fillna(0).astype(int)
        overload_days = stats_df[stats_df['nb_examens'] > 3]
        
        if not overload_days.empty:
            st.warning("**Jours avec surcharge détectée:**")
            for _, day in overload_days.iterrows():
                day_str = safe_date(day['jour'])
                if day_str:
                    day_str = day_str.strftime('%A %d/%m/%Y')
                    nb_examens = safe_int(day['nb_examens'])
                    st.write(f"- {day_str}: {nb_examens} examens")
        else:
            st.success("✅ Aucun jour avec surcharge détectée")

# ========== TAB 4: INFORMATIONS ==========

def render_information():
    """
    Affiche les informations sur le système et les contraintes
    """
    st.subheader("ℹ️ Informations système")
    
    # Contraintes du système
    st.markdown("### 📋 Contraintes du système")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Contraintes pour les professeurs:**
        - Maximum 3 examens par jour
        - Équilibre entre professeurs du même département
        - Priorité aux examens de son département
        - Tous les enseignants doivent avoir approximativement le même nombre de surveillances
        """)
    
    with col2:
        st.markdown("""
        **Contraintes générales:**
        - Respect des capacités des salles
        - Aucun chevauchement pour les étudiants
        - Optimisation de l'occupation des amphis
        - Génération automatique en moins de 45 secondes
        """)
    
    # Informations techniques
    st.markdown("---")
    st.markdown("### 🛠️ Informations techniques")
    
    st.markdown("""
    **Technologies utilisées:**
    - Base de données: PostgreSQL
    - Backend: Python
    - Interface: Streamlit
    - Optimisation: Algorithmes PL/pgSQL
    
    **Échelle du projet:**
    - 13 000+ étudiants
    - 7 départements
    - 200+ formations
    - 6-9 modules par formation
    
    **Objectif principal:**
    Générer des emplois du temps optimisés en moins de 45 secondes
    """)
    
    # Contact
    st.markdown("---")
    st.markdown("### 📞 Support")
    
    st.info("""
    **En cas de problème:**
    1. Vérifiez votre connexion internet
    2. Rafraîchissez la page (F5)
    3. Contactez l'administration des examens
    
    **Pour les demandes spéciales:**
    - Changement de disponibilité
    - Problèmes de chevauchement
    - Questions sur les contraintes
    """)

# ========== CONFIGURATION ==========

if __name__ == "__main__":
    st.set_page_config(
        page_title="Professeur - Plateforme d'Optimisation des Examens",
        page_icon="👨‍🏫",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Style minimal
    st.markdown("""
        <style>
        .stMetric {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #3498db;
            margin-bottom: 10px;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    try:
        render_professor_dashboard()
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'interface: {str(e)}")
        if st.button("🔄 Rafraîchir la page"):
            st.rerun()