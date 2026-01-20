"""
Gestion des demandes de modification d'examens pour les étudiants
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from queries import ExamQueries, UserQueries
from connection import execute_query

class StudentRequests:
    """Gestion des demandes étudiantes"""
    
    @staticmethod
    def detect_student_conflicts(student_id: int):
        """
        Détecte les conflits personnels de l'étudiant
        """
        try:
            query = """
            -- Conflit: Plus d'un examen le même jour
            SELECT 
                'Conflit horaire' as type_conflit,
                'Vous avez ' || COUNT(DISTINCT e.id) || ' examens le ' || DATE(e.date_heure) as details,
                'CRITIQUE' as severite,
                ARRAY_AGG(e.id) as examens_ids
            FROM inscriptions i
            JOIN examens e ON i.module_id = e.module_id
            WHERE i.etudiant_id = %s
                AND e.statut IN ('Planifie', 'Confirme')
            GROUP BY DATE(e.date_heure)
            HAVING COUNT(DISTINCT e.id) > 1
            
            UNION ALL
            
            -- Conflit: Pas assez de temps entre deux examens (< 2h)
            SELECT 
                'Intervalle trop court' as type_conflit,
                'Seulement ' || EXTRACT(HOUR FROM (e2.date_heure - e1.date_heure)) || 'h entre ' || 
                m1.nom || ' et ' || m2.nom as details,
                'ÉLEVÉ' as severite,
                ARRAY[e1.id, e2.id] as examens_ids
            FROM inscriptions i1
            JOIN examens e1 ON i1.module_id = e1.module_id
            JOIN modules m1 ON e1.module_id = m1.id
            JOIN inscriptions i2 ON i1.etudiant_id = i2.etudiant_id
            JOIN examens e2 ON i2.module_id = e2.module_id
            JOIN modules m2 ON e2.module_id = m2.id
            WHERE i1.etudiant_id = %s
                AND e1.id < e2.id
                AND e1.date_heure::date = e2.date_heure::date
                AND e2.date_heure - e1.date_heure BETWEEN INTERVAL '0 minutes' AND INTERVAL '120 minutes'
                AND e1.statut IN ('Planifie', 'Confirme')
                AND e2.statut IN ('Planifie', 'Confirme')
            """
            return execute_query(query, (student_id, student_id)) or []
        except Exception as e:
            print(f"Erreur détection conflits étudiant: {e}")
            return []
    
    @staticmethod
    def get_registered_modules(student_id: int):
        """
        Récupère uniquement les modules où l'étudiant est inscrit
        """
        query = """
        SELECT 
            m.id,
            m.code,
            m.nom,
            m.credits,
            m.semestre,
            f.nom as formation_nom,
            i.statut as statut_inscription,
            i.date_inscription
        FROM inscriptions i
        JOIN modules m ON i.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        WHERE i.etudiant_id = %s
            AND i.statut = 'Inscrit'
        ORDER BY m.semestre, m.code
        """
        return execute_query(query, (student_id,)) or []
    
    @staticmethod
    def create_modification_request(student_id: int, exam_id: int, 
                                   request_type: str, reason: str, 
                                   preferred_date: datetime = None, 
                                   preferred_room: int = None):
        """
        Crée une demande de modification d'examen
        Types: 'REPORT', 'CHANGEMENT_SALLE', 'AUTRE'
        """
        try:
            # Vérifier si l'étudiant est bien inscrit à cet examen
            check_query = """
            SELECT 1 FROM inscriptions i
            JOIN examens e ON i.module_id = e.module_id
            WHERE i.etudiant_id = %s AND e.id = %s AND i.statut = 'Inscrit'
            """
            check = ExamQueries.execute_query(check_query, (student_id, exam_id))
            
            if not check:
                return False, "Vous n'êtes pas inscrit à cet examen"
            
            # Insérer la demande
            insert_query = """
            INSERT INTO demandes_modification_examens 
            (etudiant_id, examen_id, type_demande, date_demande, motif, 
             date_souhaitee, salle_souhaitee, statut)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'EN_ATTENTE')
            RETURNING id
            """
            
            result = ExamQueries.execute_query(
                insert_query, 
                (student_id, exam_id, request_type, datetime.now(), reason,
                 preferred_date, preferred_room),
                fetch=True
            )
            
            # Ajouter une notification
            exam_query = "SELECT module_id FROM examens WHERE id = %s"
            exam = execute_query(exam_query, (exam_id,))
            if exam:
                UserQueries.add_notification(
                    user_id=student_id,
                    user_role='etudiant',
                    type_notif='demande_examen',
                    titre='Demande de modification envoyée',
                    contenu=f"Votre demande pour l'examen a été envoyée. Référence: DMD-{result[0]['id']}",
                    priority=2
                )
            
            return True, f"Demande créée avec succès (ID: {result[0]['id']})"
            
        except Exception as e:
            print(f"Erreur création demande: {e}")
            return False, "Erreur lors de la création de la demande"
    
    @staticmethod
    def get_student_requests(student_id: int):
        """
        Récupère les demandes de l'étudiant
        """
        query = """
        SELECT 
            dme.id,
            dme.type_demande,
            dme.date_demande,
            dme.motif,
            dme.statut,
            dme.date_souhaitee,
            dme.salle_souhaitee,
            dme.reponse_administration,
            dme.date_reponse,
            e.id as examen_id,
            m.nom as module_nom,
            e.date_heure as date_examen_originale,
            l.nom as salle_originale
        FROM demandes_modification_examens dme
        JOIN examens e ON dme.examen_id = e.id
        JOIN modules m ON e.module_id = m.id
        LEFT JOIN lieux_examen l ON e.salle_id = l.id
        WHERE dme.etudiant_id = %s
        ORDER BY dme.date_demande DESC
        """
        return execute_query(query, (student_id,)) or []
    
    @staticmethod
    def get_available_alternative_slots(student_id: int, exam_id: int):
        """
        Trouve des créneaux alternatifs pour un examen
        """
        try:
            # Récupérer l'examen original
            exam_query = """
            SELECT 
                e.date_heure,
                e.duree_minutes,
                e.module_id,
                m.formation_id
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            WHERE e.id = %s
            """
            exam = execute_query(exam_query, (exam_id,))
            
            if not exam:
                return []
            
            exam = exam[0]
            
            # Trouver des créneaux disponibles dans les 7 jours suivants
            query = """
            WITH examens_futurs AS (
                SELECT date_heure, duree_minutes
                FROM examens 
                WHERE statut IN ('Planifie', 'Confirme')
                    AND date_heure >= %s
                    AND date_heure <= %s + INTERVAL '7 days'
            ),
            creneaux AS (
                SELECT 
                    %s + (n || ' hours')::INTERVAL as debut_creneau,
                    %s + (n || ' hours')::INTERVAL + (%s || ' minutes')::INTERVAL as fin_creneau
                FROM generate_series(8, 18, 2) n  -- De 8h à 18h par pas de 2h
            ),
            salles_disponibles AS (
                SELECT l.id, l.nom, l.capacite
                FROM lieux_examen l
                WHERE l.is_disponible = TRUE
            )
            SELECT 
                c.debut_creneau,
                c.fin_creneau,
                sd.nom as salle_suggeree,
                sd.id as salle_id,
                sd.capacite,
                NOT EXISTS (
                    SELECT 1 FROM examens_futurs ef
                    WHERE NOT (ef.date_heure + (ef.duree_minutes || ' minutes')::INTERVAL <= c.debut_creneau
                           OR ef.date_heure >= c.fin_creneau)
                ) as creneau_libre
            FROM creneaux c
            CROSS JOIN salles_disponibles sd
            WHERE c.debut_creneau::time BETWEEN '08:00' AND '18:00'
                AND EXTRACT(DOW FROM c.debut_creneau) BETWEEN 1 AND 5  -- Lundi à Vendredi
            ORDER BY c.debut_creneau, sd.capacite DESC
            LIMIT 10
            """
            
            return execute_query(
                query, 
                (exam['date_heure'], exam['date_heure'], 
                 exam['date_heure'].date(), exam['date_heure'].date(),
                 exam['duree_minutes'])
            )
            
        except Exception as e:
            print(f"Erreur recherche créneaux: {e}")
            return []