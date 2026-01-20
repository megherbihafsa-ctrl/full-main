"""
Fonctions d'affichage pour l'interface étudiant - VERSION CORRIGÉE
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# IMPORT CORRECT - Utiliser execute_query directement
from connection import execute_query

def get_student_exams_simple(student_id: int, start_date=None, end_date=None):
    """
    Fonction simple pour récupérer les examens d'un étudiant
    """
    try:
        query = """
        SELECT 
            e.id,
            e.date_heure,
            e.duree_minutes,
            e.type_examen,
            e.statut,
            m.nom as module_nom,
            l.nom as salle_nom,
            l.batiment,
            l.capacite,
            CONCAT(p.nom, ' ', p.prenom) as professeur_nom,
            d.nom as departement_nom
        FROM inscriptions i
        JOIN examens e ON i.module_id = e.module_id
        JOIN modules m ON e.module_id = m.id
        JOIN lieux_examen l ON e.salle_id = l.id
        JOIN professeurs p ON e.professeur_id = p.id
        JOIN formations f ON m.formation_id = f.id
        JOIN departements d ON f.departement_id = d.id
        WHERE i.etudiant_id = %s
            AND i.statut = 'Inscrit'
            AND e.statut IN ('Planifie', 'Confirme')
        """
        
        params = [student_id]
        
        if start_date:
            query += " AND e.date_heure::date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND e.date_heure::date <= %s"
            params.append(end_date)
        
        query += " ORDER BY e.date_heure"
        
        return execute_query(query, tuple(params)) or []
        
    except Exception as e:
        st.error(f"Erreur récupération examens: {e}")
        return []

def render_personal_schedule(student_id: int):
    """
    Affiche le planning personnel de l'étudiant
    """
    st.subheader("📅 Mon planning personnel")
    
    # Filtrage des dates
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Date de début", datetime.now().date())
    with col2:
        end_date = st.date_input("Date de fin", datetime.now().date() + timedelta(days=30))
    
    # Récupération des examens
    exams = get_student_exams_simple(student_id, start_date, end_date)
    
    if not exams:
        st.info("🎉 Aucun examen prévu pour cette période")
        return
    
    # Conversion en DataFrame
    df = pd.DataFrame(exams)
    
    # Affichage
    if not df.empty:
        # Tableau simple
        st.dataframe(
            df[['date_heure', 'module_nom', 'salle_nom', 'professeur_nom', 'duree_minutes', 'type_examen']],
            use_container_width=True,
            hide_index=True
        )
        
        # Graphique simple
        try:
            df['date_heure'] = pd.to_datetime(df['date_heure'])
            df['date_fin'] = df['date_heure'] + pd.to_timedelta(df['duree_minutes'], unit='m')
            
            if len(df) > 1:
                fig = px.timeline(
                    df,
                    x_start="date_heure",
                    x_end="date_fin",
                    y="module_nom",
                    title="Vos examens"
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
        except:
            pass

def render_room_view(student_id: int):
    """
    Affiche les informations sur les salles
    """
    st.subheader("🗺️ Vue des salles")
    
    # Données simples
    exams = get_student_exams_simple(student_id)
    
    if not exams:
        st.info("Aucun examen trouvé")
        return
    
    df = pd.DataFrame(exams)
    
    # Afficher les salles
    if 'salle_nom' in df.columns and 'batiment' in df.columns:
        st.write("**Vos salles d'examen:**")
        for salle in df[['salle_nom', 'batiment']].drop_duplicates().values:
            st.write(f"• {salle[0]} (Bâtiment {salle[1]})")
    else:
        st.info("Informations sur les salles non disponibles")

def render_student_statistics(student_id: int):
    """
    Affiche les statistiques de l'étudiant
    """
    st.subheader("📊 Mes statistiques")
    
    exams = get_student_exams_simple(student_id)
    
    if not exams:
        st.info("Aucune donnée disponible")
        return
    
    df = pd.DataFrame(exams)
    
    # Statistiques simples
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total examens", len(df))
    
    with col2:
        if 'duree_minutes' in df.columns:
            avg = df['duree_minutes'].mean()
            st.metric("Durée moyenne", f"{avg:.0f} min")
    
    with col3:
        if 'type_examen' in df.columns:
            types = df['type_examen'].nunique()
            st.metric("Types différents", types)
    
    with col4:
        if 'salle_nom' in df.columns:
            salles = df['salle_nom'].nunique()
            st.metric("Salles différentes", salles)
    
    # Graphique simple
    if 'type_examen' in df.columns:
        type_counts = df['type_examen'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Répartition par type d'examen"
        )
        st.plotly_chart(fig, use_container_width=True)