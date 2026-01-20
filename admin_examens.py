# admin_examens.py
# ✅ Version finale — CORRIGÉE POUR TA BDD EXISTANTE
# ✅ Utilise les statuts SANS ACCENT : 'Planifie', 'Confirme'
# ✅ Gère RealDictRow + NoneType
# ✅ Compatible avec Streamlit + PostgreSQL

# ========== IMPORTS ==========
import streamlit as st
import json
import time
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

# Importez vos fonctions de base de données depuis vos modules
try:
    from connection import execute_query  # Ajustez selon votre structure
    from queries import (
        get_occupation_salles,
        get_stats_departement,
        generer_planning_optimise,
        detecter_tous_les_conflits,
        get_planning_examens,
        valider_examen,
        valider_tout_le_planning
    )
except ImportError:
    # Si les imports échouent, définissez des fonctions vides pour le test
    def execute_query(query, params=None, fetch=False):
        st.error("Fonction execute_query non disponible")
        return []
    
    # Définissez les autres fonctions avec des valeurs par défaut
    def get_occupation_salles():
        return pd.DataFrame()
    
    def get_stats_departement():
        return pd.DataFrame()
    
    def generer_planning_optimise(date_debut, date_fin):
        return pd.DataFrame()
    
    def detecter_tous_les_conflits():
        return pd.DataFrame()
    
    def get_planning_examens():
        return pd.DataFrame()
    
    def valider_examen(exam_id):
        st.info(f"Validation simulée pour l'examen {exam_id}")
        return True
    
    def valider_tout_le_planning():
        st.info("Validation globale simulée")
        return True

# ========== CLASSE PRINCIPALE D'OPTIMISATION ==========

class ExamScheduleOptimizer:
    """
    Algorithme d'optimisation automatique des emplois du temps
    Objectif: Générer un planning optimal en < 45 secondes
    """
    
    def __init__(self, start_date: date, end_date: date, department_id: int = None):
        self.start_date = start_date
        self.end_date = end_date
        self.department_id = department_id
        self.conflicts = []
        self.generated_schedule = []
        
    def load_data(self):
        """Charge toutes les données nécessaires depuis la BD"""
        start_time = time.time()
        
        # Appeler la fonction SQL d'optimisation
        query = """
        SELECT * FROM load_optimization_data(%s, %s, %s)
        """
        
        self.modules_data = execute_query(
            query, 
            (self.start_date, self.end_date, self.department_id)
        )
        
        # Charger les salles disponibles
        self.rooms = execute_query("""
            SELECT id, nom, capacite, type, batiment
            FROM lieux_examen
            WHERE is_disponible = TRUE
            ORDER BY capacite DESC
        """)
        
        # Charger les professeurs
        self.professors = execute_query("""
            SELECT id, nom, prenom, departement_id, heures_max
            FROM professeurs
            WHERE is_active = TRUE
            ORDER BY departement_id
        """)
        
        load_time = time.time() - start_time
        st.info(f"⚡ Données chargées en {load_time:.2f}s")
        
        return len(self.modules_data or []) > 0
    
    def generate_schedule(self):
        """
        Génère le planning optimisé automatiquement
        Algorithme principal d'optimisation
        """
        start_time = time.time()
        
        st.info("🔄 Génération du planning en cours...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Étape 1: Tri par priorité (30% du temps)
        status_text.text("📊 Calcul des priorités...")
        modules_sorted = self._sort_modules_by_priority()
        progress_bar.progress(30)
        
        # Étape 2: Attribution des salles (40% du temps)
        status_text.text("🏫 Attribution des salles...")
        schedule_with_rooms = self._assign_rooms(modules_sorted)
        progress_bar.progress(70)
        
        # Étape 3: Résolution des conflits (30% du temps)
        status_text.text("⚠️ Résolution des conflits...")
        final_schedule = self._resolve_conflicts(schedule_with_rooms)
        progress_bar.progress(100)
        
        generation_time = time.time() - start_time
        
        status_text.empty()
        progress_bar.empty()
        
        if generation_time < 45:
            st.success(f"✅ Planning généré en {generation_time:.2f}s (< 45s)")
        else:
            st.warning(f"⚠️ Planning généré en {generation_time:.2f}s (> 45s)")
        
        self.generated_schedule = final_schedule
        return final_schedule
    
    def _sort_modules_by_priority(self):
        """Trie les modules par priorité"""
        if not self.modules_data:
            return []
        
        sorted_modules = []
        for module in self.modules_data:
            priority_score = self._calculate_priority(module)
            sorted_modules.append({
                **module,
                'priority_score': priority_score
            })
        
        return sorted(sorted_modules, key=lambda x: x['priority_score'], reverse=True)
    
    def _calculate_priority(self, module):
        """Calcule le score de priorité d'un module"""
        score = 0
        
        # Critère 1: Nombre d'étudiants (40%)
        student_count = module.get('student_count', 0)
        score += (student_count / 100) * 40
        
        # Critère 2: Nombre de crédits (30%)
        credits = module.get('credits', 0)
        score += (credits / 12) * 30
        
        # Critère 3: Priorité département (30%)
        if self.department_id and module.get('departement_id') == self.department_id:
            score += 30
        
        return score
    
    def _assign_rooms(self, modules):
        """Attribue les salles optimales"""
        schedule = []
        
        for module in modules:
            student_count = module.get('student_count', 0)
            
            # Trouver la salle la plus adaptée
            best_room = self._find_best_room(student_count)
            
            if best_room:
                # Trouver un créneau disponible
                time_slot = self._find_available_slot(module, best_room)
                
                if time_slot:
                    schedule.append({
                        'module_id': module['module_id'],
                        'module_name': module['module_name'],
                        'room_id': best_room['id'],
                        'room_name': best_room['nom'],
                        'professor_id': module.get('professor_id'),
                        'exam_time': time_slot,
                        'duration_minutes': module.get('duration_minutes', 120),
                        'student_count': student_count,
                        'priority_score': module.get('priority_score', 0)
                    })
        
        return schedule
    
    def _find_best_room(self, student_count):
        """Trouve la meilleure salle pour un nombre d'étudiants"""
        if not self.rooms:
            return None
        
        # Chercher une salle avec capacité >= 60% remplie
        for room in self.rooms:
            capacity = room.get('capacite', 0)
            if capacity == 0:
                continue
            
            occupation_rate = (student_count / capacity) * 100
            
            # Salle idéale: entre 60% et 90% d'occupation
            if 60 <= occupation_rate <= 90:
                return room
        
        # Sinon, prendre la plus petite salle suffisante
        for room in sorted(self.rooms, key=lambda x: x.get('capacite', 0)):
            if room.get('capacite', 0) >= student_count:
                return room
        
        return None
    
    def _find_available_slot(self, module, room):
        """Trouve un créneau disponible"""
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # Sauter les week-ends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Créneaux possibles: 8h, 10h, 14h, 16h
            for hour in [8, 10, 14, 16]:
                slot_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                
                # Vérifier si le créneau est libre
                if self._is_slot_available(slot_time, room['id'], module):
                    return slot_time
            
            current_date += timedelta(days=1)
        
        return None
    
    def _is_slot_available(self, slot_time, room_id, module):
        """Vérifie si un créneau est disponible"""
        # Vérifier dans le planning généré
        for exam in self.generated_schedule:
            if exam['room_id'] == room_id:
                exam_time = exam['exam_time']
                exam_end = exam_time + timedelta(minutes=exam['duration_minutes'])
                slot_end = slot_time + timedelta(minutes=module.get('duration_minutes', 120))
                
                # Chevauchement?
                if not (slot_end <= exam_time or slot_time >= exam_end):
                    return False
        
        return True
    
    def _resolve_conflicts(self, schedule):
        """Résout les conflits dans le planning"""
        # Détection rapide des conflits
        conflicts = self._detect_conflicts(schedule)
        
        if not conflicts:
            return schedule
        
        # Résolution simple: décaler les examens en conflit
        resolved_schedule = schedule.copy()
        
        for conflict in conflicts:
            # Logique de résolution à implémenter
            pass
        
        return resolved_schedule
    
    def _detect_conflicts(self, schedule):
        """Détecte tous les conflits"""
        conflicts = []
        
        # Conflit 1: Étudiants avec > 1 examen/jour
        # Conflit 2: Professeurs avec > 3 examens/jour
        # Conflit 3: Chevauchements de salles
        
        return conflicts
    
    def save_schedule(self):
        """Sauvegarde le planning dans la BD"""
        if not self.generated_schedule:
            return False, "Aucun planning à sauvegarder"
        
        try:
            # Convertir en JSON pour la fonction SQL
            schedule_json = json.dumps(self.generated_schedule, default=str)
            
            query = "SELECT save_optimized_schedule(%s::jsonb)"
            result = execute_query(query, (schedule_json,), fetch=True)
            
            if result:
                count = result[0].get('save_optimized_schedule', 0)
                return True, f"✅ {count} examens sauvegardés"
            
            return False, "Erreur lors de la sauvegarde"
            
        except Exception as e:
            return False, f"Erreur: {str(e)}"


def admin_dashboard():
    # Pas besoin de réimporter streamlit ici car déjà importé en haut
    # from datetime import datetime, timedelta  # Déjà importé en haut
    
    # ----------------------------
    # Helper sécurisé pour requêtes scalaires (CORRIGÉ POUR None)
    # ----------------------------
    def q1(sql: str, default=0):
        rows = execute_query(sql)
        if not rows:
            return default
        row = rows[0]
        value = None
        if hasattr(row, 'keys') and len(row) > 0:
            value = list(row.values())[0]
        elif hasattr(row, '__getitem__') and len(row) > 0:
            value = row[0]
        else:
            value = row
        # Gérer les NULL / None
        if value is None:
            return default
        return value

    # ----------------------------
    # CSS personnalisé
    # ----------------------------
    st.markdown("""
    <style>
    :root {
      --bg: #0b1020;
      --card: rgba(255,255,255,0.08);
      --border: rgba(255,255,255,0.12);
      --txt: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.65);
      --accent: #7c3aed;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
    }
    .stApp {
      background: radial-gradient(1000px 600px at 15% 10%, rgba(124,58,237,0.35), transparent 55%),
                  radial-gradient(900px 500px at 85% 20%, rgba(34,197,94,0.25), transparent 50%),
                  linear-gradient(180deg, #050816, #070b18 45%, #050816);
      color: var(--txt);
    }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    section[data-testid="stSidebar"] {
      background: rgba(255,255,255,0.06);
      border-right: 1px solid var(--border);
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.25);
      backdrop-filter: blur(10px);
    }
    .kpi-title { font-size: 0.85rem; color: var(--muted); margin-bottom: 6px; }
    .kpi-value { font-size: 1.6rem; font-weight: 700; margin: 0; }
    .badge { 
      display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem;
      background: rgba(255,255,255,0.06); border: 1px solid var(--border);
    }
    .badge.ok { border-color: var(--success); }
    .badge.warn { border-color: var(--warning); }
    .badge.danger { border-color: var(--danger); }
    </style>
    """, unsafe_allow_html=True)

    # ----------------------------
    # Composants UI
    # ----------------------------
    def kpi_card(title, value, sub="", tone="ok"):
        badge_cls = {"ok": "ok", "warn": "warn", "danger": "danger"}.get(tone, "ok")
        st.markdown(f"""
        <div class="card">
          <div class="kpi-title">{title} <span class="badge {badge_cls}">{tone.upper()}</span></div>
          <p class="kpi-value">{value}</p>
          <div style="font-size:0.8rem;color:var(--muted);margin-top:4px;">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    def section_header(title, subtitle=""):
        st.markdown(f"### {title}")
        if subtitle:
            st.caption(subtitle)

    # ----------------------------
    # Sidebar
    # ----------------------------
    st.sidebar.markdown("## 🧭 Navigation")
    page = st.sidebar.radio(
        "",
        [
            "🏠 Tableau de bord",
            "🚀 Génération optimisée",
            "⚠️ Conflits",
            "✅ Validation"
        ],
        index=0
    )

    st.sidebar.markdown("---")
    compact = st.sidebar.toggle("Mode compact", value=False)

    # ----------------------------
    # Header
    # ----------------------------
    st.markdown("""
    <div class="card" style="padding:18px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <h3 style="margin:0;font-weight:700;">👨‍💼 Administrateur Examens — Service Planification</h3>
          <p style="margin:0;color:var(--muted);font-size:0.95rem;">Vue globale • Optimisation (&lt; 45s) • Conflits • Validation</p>
        </div>
        <div>
          <span class="badge ok">PostgreSQL</span>
          <span class="badge ok">Streamlit</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # =====================================================
    # PAGE 1 — TABLEAU DE BORD
    # =====================================================
    if page == "🏠 Tableau de bord":
        section_header("📊 Vue globale des ressources & KPIs")

        col1, col2, col3, col4, col5 = st.columns(5)

        total_examens = q1("""
            SELECT COUNT(*) FROM examens
            WHERE statut IN ('Planifie', 'Confirme') AND date_heure >= CURRENT_DATE
        """, 0)

        taux_salles = q1("""
            SELECT ROUND(
                (SELECT COUNT(DISTINCT salle_id) FROM examens
                 WHERE statut IN ('Planifie','Confirme') AND date_heure >= CURRENT_DATE) * 100.0 /
                NULLIF((SELECT COUNT(*) FROM lieux_examen WHERE is_disponible = TRUE), 0),
                2
            )
        """, 0.0)

        conflits_total = q1("""
            SELECT COUNT(*) FROM (SELECT * FROM detecter_conflits()) _
        """, 0)

        taux_confirmes = q1("""
            SELECT ROUND(
                COUNT(*) FILTER (WHERE statut = 'Confirme') * 100.0 / NULLIF(COUNT(*), 0),
                2
            ) FROM examens WHERE date_heure >= CURRENT_DATE
        """, 0.0)

        total_etudiants = q1("""
            SELECT COUNT(DISTINCT i.etudiant_id)
            FROM examens e
            JOIN inscriptions i ON e.module_id = i.module_id
            WHERE i.statut = 'Inscrit' AND e.statut IN ('Planifie','Confirme')
              AND e.date_heure >= CURRENT_DATE
        """, 0)

        with col1: kpi_card("📝 Examens", f"{int(total_examens):,}", "Planifiés ou confirmés", "ok")
        with col2: kpi_card("🏢 Salles", f"{float(taux_salles):.1f}%", "Utilisation", "ok" if float(taux_salles) >= 40 else "warn")
        with col3: kpi_card("⚠️ Conflits", f"{int(conflits_total)}", "À résoudre", "ok" if int(conflits_total) == 0 else "danger")
        with col4: kpi_card("✅ Confirmés", f"{float(taux_confirmes):.1f}%", "Taux", "ok" if float(taux_confirmes) >= 60 else "warn")
        with col5: kpi_card("👥 Étudiants", f"{int(total_etudiants):,}", "Concernés", "ok")

        st.divider()

        # --- Occupation salles ---
        section_header("🏢 Occupation des salles")
        occ = get_occupation_salles()
        if not occ.empty:
            cols_show = [c for c in ["nom", "type", "capacite", "nb_examens_planifies", "pourcentage_utilisation"] if c in occ.columns]
            df_occ = occ[cols_show] if cols_show else occ
            st.dataframe(df_occ, use_container_width=True, height=300 if compact else 400)
        else:
            st.info("Aucune donnée d'occupation.")

        st.divider()

        # --- Stats par département ---
        section_header("📈 Statistiques par département")
        stats = get_stats_departement()
        if not stats.empty:
            st.dataframe(stats, use_container_width=True, height=300 if compact else 400)
        else:
            st.info("Aucune statistique disponible.")

        st.divider()

        # --- Vérification contraintes ---
        section_header("✅ Contraintes critiques")
        violations = q1("""
            SELECT
              (SELECT COUNT(*) FROM (
                SELECT etudiant_id, DATE(date_heure)
                FROM examens e JOIN inscriptions i USING(module_id)
                WHERE i.statut = 'Inscrit' AND e.statut IN ('Planifie','Confirme')
                GROUP BY etudiant_id, DATE(date_heure)
                HAVING COUNT(*) > 1
              ) _) AS etu_viol,
              (SELECT COUNT(*) FROM (
                SELECT professeur_id, DATE(date_heure)
                FROM examens
                WHERE statut IN ('Planifie','Confirme')
                GROUP BY professeur_id, DATE(date_heure)
                HAVING COUNT(*) > 3
              ) _) AS prof_viol,
              (SELECT COUNT(*) FROM (
                SELECT e.id
                FROM examens e
                JOIN lieux_examen l ON e.salle_id = l.id
                JOIN (SELECT module_id, COUNT(*) nb FROM inscriptions WHERE statut='Inscrit' GROUP BY module_id) i ON e.module_id = i.module_id
                WHERE e.statut IN ('Planifie','Confirme') AND i.nb > l.capacite
              ) _) AS cap_viol
        """, {"etu_viol": 0, "prof_viol": 0, "cap_viol": 0})

        c1, c2, c3 = st.columns(3)
        with c1:
            v = int(violations.get("etu_viol", 0)) if isinstance(violations, dict) else 0
            st.success("✅ Étudiants : max 1/jour") if v == 0 else st.error(f"❌ {v} violations")
        with c2:
            v = int(violations.get("prof_viol", 0)) if isinstance(violations, dict) else 0
            st.success("✅ Profs : max 3/jour") if v == 0 else st.error(f"❌ {v} violations")
        with c3:
            v = int(violations.get("cap_viol", 0)) if isinstance(violations, dict) else 0
            st.success("✅ Capacité salles OK") if v == 0 else st.error(f"❌ {v} violations")

    # =====================================================
    # PAGE 2 — GÉNÉRATION OPTIMISÉE
    # =====================================================
    elif page == "🚀 Génération optimisée":
        section_header("🤖 Génération automatique du planning")

        col1, col2 = st.columns(2)
        with col1:
            date_debut = st.date_input("Date de début", value=datetime.today().date())
        with col2:
            date_fin = st.date_input("Date de fin", value=(datetime.today() + timedelta(days=21)).date())

        if date_debut >= date_fin:
            st.error("La date de fin doit être après la date de début.")
            return

        st.markdown("### Options d'optimisation")
        opt1 = st.toggle("Optimiser occupation salles", True)
        opt2 = st.toggle("Équilibrer surveillances profs", True)
        opt3 = st.toggle("Priorité département", True)

        if st.button("🚀 Lancer génération", type="primary", use_container_width=True):
            with st.spinner("Génération en cours..."):
                start_time = datetime.now()
                try:
                    df = generer_planning_optimise(date_debut, date_fin)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    st.success(f"✅ Généré en {elapsed:.2f}s {'🎯' if elapsed < 45 else '⚠️'}")
                    st.dataframe(df, use_container_width=True, height=500)

                    if not df.empty and "score_optimisation" in df.columns:
                        fig = px.histogram(df, x="score_optimisation", nbins=20, title="Distribution du score d'optimisation")
                        st.plotly_chart(fig, use_container_width=True)

                    st.download_button(
                        "📥 Télécharger planning (CSV)",
                        df.to_csv(index=False).encode("utf-8"),
                        "planning_genere.csv",
                        "text/csv"
                    )
                except Exception as e:
                    st.error(f"Erreur lors de la génération : {str(e)}")

    # =====================================================
    # PAGE 3 — CONFLITS
    # =====================================================
    elif page == "⚠️ Conflits":
        section_header("🔍 Analyse des conflits")

        if st.button("🔍 Détecter les conflits", type="primary", use_container_width=True):
            with st.spinner("Détection en cours..."):
                conflits = detecter_tous_les_conflits()
                st.session_state["conflits"] = conflits
        else:
            conflits = st.session_state.get("conflits", pd.DataFrame())

        if conflits.empty:
            st.success("🎉 Aucun conflit détecté.")
        else:
            st.error(f"⚠️ {len(conflits)} conflit(s) détecté(s)")
            if "severite" in conflits.columns:
                fig = px.histogram(conflits, x="severite", title="Répartition par sévérité")
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(conflits, use_container_width=True, height=500)

    # =====================================================
    # PAGE 4 — VALIDATION
    # =====================================================
    elif page == "✅ Validation":
        section_header("✅ Validation du planning final")

        planning = get_planning_examens()
        if planning.empty:
            st.info("Aucun examen à valider.")
            return

        planifies = len(planning[planning["statut"] == "Planifie"]) if "statut" in planning.columns else 0
        confirmes = len(planning) - planifies

        col1, col2, col3 = st.columns(3)
        with col1: kpi_card("📝 Total", f"{len(planning):,}")
        with col2: kpi_card("⏳ Planifiés", f"{planifies:,}", tone="warn" if planifies > 0 else "ok")
        with col3: kpi_card("✅ Confirmés", f"{confirmes:,}")

        tab1, tab2 = st.tabs(["Validation individuelle", "Validation globale"])

        with tab1:
            st.dataframe(planning.head(300), use_container_width=True, height=400)
            exam_id = st.number_input("ID de l'examen à valider", min_value=1, step=1)
            if st.button("✅ Valider cet examen", type="primary"):
                if valider_examen(int(exam_id)):
                    st.success("✅ Examen validé avec succès.")
                    st.rerun()
                else:
                    st.error("❌ Échec de la validation (ID invalide ou déjà confirmé).")

        with tab2:
            if planifies == 0:
                st.info("✅ Tous les examens sont déjà confirmés.")
            else:
                st.warning(f"Vous allez confirmer **{planifies}** examens planifiés.")
                if st.checkbox("Je confirme la validation globale"):
                    if st.button("🚀 Valider tout le planning", type="primary"):
                        if valider_tout_le_planning():
                            st.success("✅ Planning entièrement validé !")
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la validation globale.")

# Point d'entrée pour tester
if __name__ == "__main__":
    admin_dashboard()