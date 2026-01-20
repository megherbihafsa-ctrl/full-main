# vice_doyen.py
import streamlit as st
import pandas as pd

from ui_theme import section_header, kpi_card, hero_header
from connection import execute_query
from queries import (
    get_occupation_salles,
    get_stats_departement,
    detecter_tous_les_conflits,
    get_planning_examens,
    valider_tout_le_planning,
)

# -------- Helpers robustes ----------
def q_scalar(sql: str, params=None, key: str = None, default=0):
    rows = execute_query(sql, params or ())
    if not rows:
        return default
    row = rows[0] or {}
    if key is None:
        return list(row.values())[0] if row else default
    v = row.get(key, default)
    return default if v is None else v


def df_query(sql: str, params=None) -> pd.DataFrame:
    """Retourne un DataFrame (jamais plante)."""
    try:
        rows = execute_query(sql, params or ())
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_planning_examens_fallback() -> pd.DataFrame:
    """
    Fallback si get_planning_examens() renvoie vide.
    1) Essaie v_planning_examens
    2) Sinon lit directement examens + joins minimaux
    """
    # 1) Vue prête si elle existe
    df = df_query(
        """
        SELECT *
        FROM v_planning_examens
        WHERE statut IN ('Planifie','Confirme')
        ORDER BY date_heure DESC
        """
    )
    if df is not None and not df.empty:
        return df

    # 2) Requête directe
    df = df_query(
        """
        SELECT
            e.id AS examen_id,
            e.date_heure,
            e.duree_minutes,
            e.type_examen,
            e.statut,
            m.nom AS module,
            d.nom AS departement,
            (p.nom || ' ' || p.prenom) AS professeur,
            l.nom AS salle
        FROM examens e
        JOIN modules m ON m.id = e.module_id
        JOIN formations f ON f.id = m.formation_id
        JOIN departements d ON d.id = f.departement_id
        JOIN professeurs p ON p.id = e.professeur_id
        JOIN lieux_examen l ON l.id = e.salle_id
        WHERE e.statut IN ('Planifie','Confirme')
        ORDER BY e.date_heure DESC
        """
    )
    return df if df is not None else pd.DataFrame()


def vice_doyen_dashboard():
    hero_header(
        "🎓 Vice-Doyen / Doyen — Vue Stratégique",
        "KPIs • Occupation • Conflits • Validation finale (UI premium).",
        pills=["PostgreSQL", "Streamlit", "Analytics"],
    )

    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        page = st.radio(
            "",
            [
                "🏠 Vue Globale & KPIs",
                "📊 Conflits par sévérité",
                "⚠️ Analyse des conflits",
                "✅ Validation finale EDT",
            ],
        )
        st.markdown("---")
        compact = st.toggle("Mode compact", value=False)

    # =========================================================
    # PAGE 1 : KPIs
    # =========================================================
    if page == "🏠 Vue Globale & KPIs":
        section_header("📌 Indicateurs clés", "Suivi global du planning.")

        total_examens = q_scalar(
            "SELECT COUNT(*) FROM examens WHERE statut IN ('Planifie','Confirme')"
        ) or 0

        taux_salles = q_scalar(
            """
            SELECT ROUND(
                (SELECT COUNT(DISTINCT salle_id)
                 FROM examens
                 WHERE statut IN ('Planifie','Confirme')
                ) * 100.0 /
                NULLIF((SELECT COUNT(*) FROM lieux_examen WHERE is_disponible = TRUE),0),
                2
            )
            """
        ) or 0

        # si detecter_conflits() n'existe pas mais detecter_tous_les_conflits() oui,
        # laisse comme ça si ta DB a bien la fonction detecter_conflits()
        conflits = q_scalar("SELECT COUNT(*) FROM detecter_conflits()") or 0

        # ✅ CORRECTION ICI : COUNT() -> COUNT(*)
        # + on calcule sur les examens planifiés/confirmés uniquement (plus logique pour un taux)
        taux_confirmes = q_scalar(
            """
            SELECT ROUND(
                COUNT(*) FILTER (WHERE statut = 'Confirme') * 100.0
                / NULLIF(COUNT(*) FILTER (WHERE statut IN ('Planifie','Confirme')), 0),
                2
            ) AS taux_confirmes
            FROM examens
            """
        ) or 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("📝 Examens planifiés", int(total_examens), "Planifie / Confirme", "ok")
        with c2:
            kpi_card(
                "🏢 Utilisation salles",
                f"{float(taux_salles):.1f}%",
                "Occupation",
                "warn" if float(taux_salles) < 40 else "ok",
            )
        with c3:
            kpi_card("⚠️ Conflits", int(conflits), "Doit être à 0", "danger" if int(conflits) > 0 else "ok")
        with c4:
            kpi_card(
                "✅ Taux confirmés",
                f"{float(taux_confirmes):.1f}%",
                "Objectif ≥ 60%",
                "warn" if float(taux_confirmes) < 60 else "ok",
            )

        section_header("🏢 Occupation des salles", "Analyse de charge")
        occ = get_occupation_salles()
        if occ is None or occ.empty:
            st.info("Aucune donnée.")
        else:
            st.dataframe(occ, use_container_width=True, height=300 if not compact else 200)

        section_header("📈 Statistiques par département", "Vue académique")
        stats = get_stats_departement()
        if stats is None or stats.empty:
            st.info("Aucune statistique.")
        else:
            st.dataframe(stats, use_container_width=True, height=300 if not compact else 200)

    # =========================================================
    # PAGE 2 : Conflits par sévérité
    # =========================================================
    elif page == "📊 Conflits par sévérité":
        section_header("📊 Conflits par sévérité", "Priorisation")
        conflits_df = detecter_tous_les_conflits()

        if conflits_df is None or conflits_df.empty:
            st.success("🎉 Aucun conflit détecté.")
        else:
            st.dataframe(conflits_df, use_container_width=True)

    # =========================================================
    # PAGE 3 : Analyse détaillée
    # =========================================================
    elif page == "⚠️ Analyse des conflits":
        section_header("🔍 Analyse détaillée", "Détection complète")

        if st.button("🔍 Lancer l'analyse", type="primary"):
            conflits_df = detecter_tous_les_conflits()
            st.session_state["vd_conflits"] = conflits_df

        conflits_df = st.session_state.get("vd_conflits", pd.DataFrame())

        if conflits_df is None or conflits_df.empty:
            st.success("🎉 Aucun conflit détecté.")
        else:
            st.error(f"{len(conflits_df)} conflit(s) détecté(s)")
            st.dataframe(conflits_df, use_container_width=True)

    # =========================================================
    # PAGE 4 : VALIDATION FINALE
    # =========================================================
    elif page == "✅ Validation finale EDT":
        section_header("✅ Validation finale du planning", "Décision institutionnelle")

        conflits_val = int(q_scalar("SELECT COUNT(*) FROM detecter_conflits()") or 0)

        # 1) Essai via queries.py
        planning = get_planning_examens()
        if planning is None:
            planning = pd.DataFrame()

        # 2) Fallback si vide
        if planning.empty:
            planning = get_planning_examens_fallback()
            if not planning.empty:
                st.warning("ℹ️ Planning chargé via fallback (vérifie get_planning_examens() dans queries.py).")

        # 3) Si toujours vide => vrai vide en base
        if planning.empty:
            st.info("Aucun examen (Planifie/Confirme) trouvé en base pour la validation.")
            st.caption("Vérifie la table examens : statuts, dates, et la fonction get_planning_examens().")
            return

        # Statuts robustes
        if "statut" not in planning.columns:
            st.error("La colonne 'statut' est absente du planning (requête/vues à corriger).")
            st.dataframe(planning, use_container_width=True)
            return

        planifies = int((planning["statut"] == "Planifie").sum())
        confirmes = int((planning["statut"] == "Confirme").sum())

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("🧾 Total", len(planning), "", "ok")
        with c2:
            kpi_card("⏳ Planifiés", planifies, "À confirmer", "warn" if planifies > 0 else "ok")
        with c3:
            kpi_card("✅ Confirmés", confirmes, "Validés", "ok")

        st.dataframe(planning, use_container_width=True, height=400)

        # 🔴 REFUS DE VALIDATION
        if conflits_val > 0:
            st.error("⛔ Validation refusée : conflits détectés")
            st.caption(f"{conflits_val} conflit(s) doivent être corrigé(s) avant validation.")
            st.info("Retour à l'administration des examens pour correction.")
            return

        # 🟢 VALIDATION AUTORISÉE
        if planifies == 0:
            st.success("Tout est déjà confirmé ✅")
        else:
            confirm = st.checkbox("Je confirme la validation globale")
            if st.button("🚀 Valider tout", type="primary", disabled=not confirm):
                if valider_tout_le_planning():
                    st.success("Planning officiellement validé ✅")
                    st.rerun()
                else:
                    st.error("validation refusée")
