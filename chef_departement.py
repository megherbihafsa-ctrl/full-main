# chef_departement.py
# ✅ Version finale — Identique au style de Pasted_Text_1768700972728.txt
# ✅ Compatible avec ta BDD : statuts SANS ACCENT ('Planifie', 'Confirme')
# ✅ Gère RealDictRow + NoneType + erreurs de formatage

def render_department_head_dashboard():
    import streamlit as st
    import pandas as pd
    import plotly.express as px
    from datetime import datetime, date

    from connection import execute_query

    # ----------------------------
    # Configuration de la page
    # ----------------------------
    st.set_page_config(
        page_title="Chef Département",
        page_icon="🏫",
        layout="wide"
    )

    # ----------------------------
    # Helper sécurisé pour requêtes scalaires
    # ----------------------------
    def q1(sql: str, default=0):
        rows = execute_query(sql)
        if not rows:
            return default
        row = rows[0]
        if hasattr(row, 'keys') and len(row) > 0:
            value = list(row.values())[0]
        elif hasattr(row, '__getitem__') and len(row) > 0:
            value = row[0]
        else:
            value = row
        return default if value is None else value

    # ----------------------------
    # CSS personnalisé (identique à admin_examens.py)
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
    # Vérification session
    # ----------------------------
    if 'user' not in st.session_state or st.session_state.user.get('role') != 'chef_departement':
        st.error("🔒 Accès réservé aux chefs de département")
        return

    chef_id = st.session_state.user.get('linked_id', 1)

    # Récupérer le département
    dept_info = q1(f"""
        SELECT d.id, d.nom, d.code
        FROM chef_departement cd
        JOIN departements d ON cd.departement_id = d.id
        WHERE cd.professeur_id = {chef_id} AND cd.is_actif = TRUE
    """, {"id": 1, "nom": "Inconnu", "code": "???"})

    if isinstance(dept_info, dict):
        dept_id = dept_info.get('id', 1)
        dept_nom = dept_info.get('nom', 'Inconnu')
        dept_code = dept_info.get('code', '???')
    else:
        dept_id = 1
        dept_nom = "Inconnu"
        dept_code = "???"

    # ----------------------------
    # Header
    # ----------------------------
    st.markdown(f"""
    <div class="card" style="padding:18px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <h3 style="margin:0;font-weight:700;">👔 Chef de Département - {dept_nom}</h3>
          <p style="margin:0;color:var(--muted);font-size:0.95rem;">Validation par département • Statistiques • Conflits</p>
        </div>
        <div>
          <span class="badge ok">PostgreSQL</span>
          <span class="badge ok">Streamlit</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ----------------------------
    # Sidebar Navigation
    # ----------------------------
    st.sidebar.markdown("## 🧭 Navigation")
    page = st.sidebar.radio(
        "",
        [
            "📊 Statistiques Département",
            "📚 Examens par Formation",
            "⚠️ Conflits Département",
            "✅ Validation Département"
        ],
        index=0
    )

    st.sidebar.markdown("---")
    compact = st.sidebar.toggle("Mode compact", value=False)

    # =====================================================
    # PAGE 1 — STATISTIQUES DÉPARTEMENT
    # =====================================================
    if page == "📊 Statistiques Département":
        section_header(f"📈 Statistiques du Département {dept_nom}")

        col1, col2, col3, col4 = st.columns(4)

        nb_formations = q1(f"SELECT COUNT(*) FROM formations WHERE departement_id = {dept_id} AND is_active = TRUE", 0)
        nb_etudiants = q1(f"SELECT COUNT(*) FROM etudiants e JOIN formations f ON e.formation_id = f.id WHERE f.departement_id = {dept_id} AND e.statut = 'Actif'", 0)
        nb_professeurs = q1(f"SELECT COUNT(*) FROM professeurs WHERE departement_id = {dept_id} AND is_active = TRUE", 0)
        nb_examens = q1(f"SELECT COUNT(*) FROM examens ex JOIN modules m ON ex.module_id = m.id JOIN formations f ON m.formation_id = f.id WHERE f.departement_id = {dept_id} AND ex.statut IN ('Planifie', 'Confirme')", 0)

        with col1: kpi_card("🎓 Formations", f"{int(nb_formations):,}", "", "ok")
        with col2: kpi_card("👨‍🎓 Étudiants", f"{int(nb_etudiants):,}", "", "ok")
        with col3: kpi_card("👨‍🏫 Professeurs", f"{int(nb_professeurs):,}", "", "ok")
        with col4: kpi_card("📅 Examens", f"{int(nb_examens):,}", "Planifiés/Confirmés", "ok")

        st.divider()

        # Statistiques par formation
        section_header("📚 Par Formation")
        stats_query = f"""
            SELECT 
                f.code,
                f.nom,
                f.niveau,
                COUNT(DISTINCT m.id) as nb_modules,
                COUNT(DISTINCT e.id) as nb_etudiants,
                COUNT(DISTINCT ex.id) as nb_examens_planifies,
                COUNT(DISTINCT ex.id) FILTER (WHERE ex.statut = 'Confirme') as nb_examens_confirmes
            FROM formations f
            LEFT JOIN modules m ON f.id = m.formation_id
            LEFT JOIN etudiants e ON f.id = e.formation_id AND e.statut = 'Actif'
            LEFT JOIN examens ex ON m.id = ex.module_id AND ex.statut IN ('Planifie', 'Confirme')
            WHERE f.departement_id = {dept_id} AND f.is_active = TRUE
            GROUP BY f.id, f.code, f.nom, f.niveau
            ORDER BY f.nom
        """
        stats_rows = execute_query(stats_query)
        if stats_rows:
            df = pd.DataFrame(stats_rows)
            st.dataframe(df, use_container_width=True, height=300 if compact else 400)
        else:
            st.info("Aucune formation trouvée.")

    # =====================================================
    # PAGE 2 — EXAMENS PAR FORMATION
    # =====================================================
    elif page == "📚 Examens par Formation":
        section_header(f"📚 Examens par Formation - {dept_nom}")

        formations = execute_query(f"""
            SELECT id, nom, code FROM formations
            WHERE departement_id = {dept_id} AND is_active = TRUE
            ORDER BY nom
        """)

        if not formations:
            st.warning("Aucune formation active.")
            return

        formation_map = {f"{f['code']} - {f['nom']}": f['id'] for f in formations}
        selected = st.selectbox("Formation", list(formation_map.keys()))
        formation_id = formation_map[selected]

        col1, col2 = st.columns(2)
        with col1: date_debut = st.date_input("Début", value=date.today())
        with col2: date_fin = st.date_input("Fin", value=date.today() + pd.Timedelta(days=30))

        examens = execute_query(f"""
            SELECT
                ex.id,
                m.nom as module_nom,
                ex.date_heure,
                ex.duree_minutes,
                ex.statut,
                l.nom as salle,
                p.nom || ' ' || p.prenom as professeur
            FROM examens ex
            JOIN modules m ON ex.module_id = m.id
            JOIN lieux_examen l ON ex.salle_id = l.id
            JOIN professeurs p ON ex.professeur_id = p.id
            WHERE m.formation_id = {formation_id}
            AND ex.date_heure BETWEEN '{date_debut}' AND '{date_fin}'
            AND ex.statut IN ('Planifie', 'Confirme')
            ORDER BY ex.date_heure
        """)

        if examens:
            df = pd.DataFrame(examens)
            st.dataframe(df, use_container_width=True, height=400)
            planifies = len([e for e in examens if e['statut'] == 'Planifie'])
            confirmes = len([e for e in examens if e['statut'] == 'Confirme'])
            st.metric("Examens planifiés", planifies)
            st.metric("Examens confirmés", confirmes)
        else:
            st.info("Aucun examen dans cette période.")

    # =====================================================
    # PAGE 3 — CONFLITS
    # =====================================================
    elif page == "⚠️ Conflits Département":
        section_header(f"⚠️ Conflits - {dept_nom}")

        if st.button("🔍 Détecter les conflits", type="primary"):
            conflits = execute_query(f"""
                -- Conflits étudiants
                SELECT 'Étudiant >1 examen/jour' as type_conflit,
                       'CRITIQUE' as severite,
                       i.etudiant_id,
                       DATE(e.date_heure) as jour,
                       COUNT(*) as nb_examens
                FROM inscriptions i
                JOIN examens e ON i.module_id = e.module_id
                JOIN modules m ON e.module_id = m.id
                JOIN formations f ON m.formation_id = f.id
                WHERE f.departement_id = {dept_id}
                AND e.statut IN ('Planifie', 'Confirme')
                GROUP BY i.etudiant_id, DATE(e.date_heure)
                HAVING COUNT(*) > 1
                
                UNION ALL
                
                -- Conflits professeurs
                SELECT 'Professeur >3 examens/jour' as type_conflit,
                       'CRITIQUE' as severite,
                       e.professeur_id,
                       DATE(e.date_heure) as jour,
                       COUNT(*) as nb_examens
                FROM examens e
                JOIN modules m ON e.module_id = m.id
                JOIN formations f ON m.formation_id = f.id
                WHERE f.departement_id = {dept_id}
                AND e.statut IN ('Planifie', 'Confirme')
                GROUP BY e.professeur_id, DATE(e.date_heure)
                HAVING COUNT(*) > 3
            """)

            if conflits:
                st.error(f"⚠️ {len(conflits)} conflit(s) détecté(s)")
                df = pd.DataFrame(conflits)
                st.dataframe(df, use_container_width=True)
            else:
                st.success("✅ Aucun conflit détecté !")

    # =====================================================
    # PAGE 4 — VALIDATION
    # =====================================================
    elif page == "✅ Validation Département":
        section_header(f"✅ Validation - {dept_nom}")

        col1, col2 = st.columns(2)
        with col1: date_debut = st.date_input("Début", value=date.today(), key="v1")
        with col2: date_fin = st.date_input("Fin", value=date.today() + pd.Timedelta(days=30), key="v2")

        examens = execute_query(f"""
            SELECT ex.id, m.nom as module, ex.date_heure, ex.statut
            FROM examens ex
            JOIN modules m ON ex.module_id = m.id
            JOIN formations f ON m.formation_id = f.id
            WHERE f.departement_id = {dept_id}
            AND ex.date_heure BETWEEN '{date_debut}' AND '{date_fin}'
            AND ex.statut = 'Planifie'
            ORDER BY ex.date_heure
        """)

        if not examens:
            st.success("✅ Tous les examens sont déjà confirmés !")
            return

        st.dataframe(pd.DataFrame(examens), use_container_width=True)

        if st.button("✅ Valider tous les examens", type="primary"):
            if st.checkbox("Je confirme la validation de tous les examens planifiés"):
                ids = [e['id'] for e in examens]
                placeholders = ','.join(['%s'] * len(ids))
                query = f"UPDATE examens SET statut = 'Confirme' WHERE id IN ({placeholders})"
                result = execute_query(query, tuple(ids), fetch=False)
                if result:
                    st.success(f"✅ {result} examen(s) validé(s) !")
                    st.rerun()