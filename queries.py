"""
Toutes les requêtes SQL organisées par module et optimisées
VERSION CORRIGÉE - Problèmes d'authentification résolus
"""
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime, date
from connection import execute_query, load_dataframe


class ExamQueries:
    """Requêtes liées aux examens"""
    
    @staticmethod
    def get_student_exams(student_id: int, start_date: date = None, end_date: date = None) -> List[Dict]:
        """
        Récupère les examens d'un étudiant
        Note : statut avec accents ('Planifié', 'Confirmé') pour correspondre à la base
        """
        query = """
        SELECT 
            e.id,
            e.uuid,
            m.code as module_code,
            m.nom as module_nom,
            f.nom as formation_nom,
            d.nom as departement_nom,
            CONCAT(p.nom, ' ', p.prenom) as professeur_nom,
            l.nom as salle_nom,
            l.type as salle_type,
            l.batiment,
            l.capacite,
            e.date_heure,
            e.duree_minutes,
            e.date_heure + (e.duree_minutes || ' minutes')::INTERVAL as date_fin,
            e.type_examen,
            e.statut,
            COUNT(i.etudiant_id) as nb_etudiants_inscrits,
            ROUND((COUNT(i.etudiant_id)::DECIMAL / l.capacite) * 100, 2) as taux_occupation
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        JOIN departements d ON f.departement_id = d.id
        JOIN professeurs p ON e.professeur_id = p.id
        JOIN lieux_examen l ON e.salle_id = l.id
        JOIN inscriptions i ON e.module_id = i.module_id AND i.statut = 'Inscrit'
        WHERE i.etudiant_id = %s
            AND e.statut IN ('Planifié', 'Confirmé')
            AND (%s IS NULL OR e.date_heure >= %s)
            AND (%s IS NULL OR e.date_heure <= %s)
        GROUP BY e.id, e.uuid, m.code, m.nom, f.nom, d.nom, p.nom, p.prenom, 
                 l.nom, l.type, l.batiment, l.capacite, e.date_heure, 
                 e.duree_minutes, e.type_examen, e.statut
        ORDER BY e.date_heure
        """
        return execute_query(query, (student_id, start_date, start_date, end_date, end_date)) or []
    
    @staticmethod
    def get_professor_exams(professor_id: int, days_ahead: int = 30) -> pd.DataFrame:
        """
        Récupère les examens d'un professeur pour les prochains jours
        """
        query = """
            SELECT 
                e.id,
                m.nom as module_nom,
                f.nom as formation_nom,
                l.nom as salle_nom,
                l.capacite,
                e.date_heure,
                e.duree_minutes,
                e.date_heure + (e.duree_minutes || ' minutes')::INTERVAL as date_fin,
                e.type_examen,
                e.statut,
                COUNT(i.etudiant_id) as nb_etudiants,
                ROUND((COUNT(i.etudiant_id)::DECIMAL / l.capacite) * 100, 2) as taux_occupation
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            JOIN formations f ON m.formation_id = f.id
            JOIN lieux_examen l ON e.salle_id = l.id
            LEFT JOIN inscriptions i ON e.module_id = i.module_id AND i.statut = 'Inscrit'
            WHERE e.professeur_id = %s
                AND e.date_heure BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + %s * INTERVAL '1 day'
                AND e.statut IN ('Planifié', 'Confirmé')
            GROUP BY e.id, m.nom, f.nom, l.nom, l.capacite, e.date_heure, 
                     e.duree_minutes, e.type_examen, e.statut
            ORDER BY e.date_heure
        """
        result = execute_query(query, (professor_id, days_ahead))
        if result:
            df = pd.DataFrame(result)
            if not df.empty and 'date_heure' in df.columns:
                df['date_heure'] = pd.to_datetime(df['date_heure'])
                if 'date_fin' in df.columns:
                    df['date_fin'] = pd.to_datetime(df['date_fin'])
            return df
        return pd.DataFrame()
    
    @staticmethod
    def get_department_exams(department_id: int, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Récupère tous les examens d'un département pour une période
        """
        query = """
            SELECT 
                e.id,
                e.uuid,
                m.code as module_code,
                m.nom as module_nom,
                f.code as formation_code,
                f.nom as formation_nom,
                CONCAT(p.nom, ' ', p.prenom) as professeur_nom,
                p.grade,
                l.nom as salle_nom,
                l.type as salle_type,
                l.capacite,
                e.date_heure,
                e.duree_minutes,
                e.date_heure + (e.duree_minutes || ' minutes')::INTERVAL as date_fin,
                e.type_examen,
                e.statut,
                COUNT(DISTINCT i.etudiant_id) as nb_etudiants_inscrits,
                ROUND((COUNT(DISTINCT i.etudiant_id)::DECIMAL / l.capacite) * 100, 2) as taux_occupation
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            JOIN formations f ON m.formation_id = f.id
            JOIN professeurs p ON e.professeur_id = p.id
            JOIN lieux_examen l ON e.salle_id = l.id
            LEFT JOIN inscriptions i ON e.module_id = i.module_id AND i.statut = 'Inscrit'
            WHERE f.departement_id = %s
                AND e.date_heure >= %s
                AND e.date_heure <= %s
                AND e.statut IN ('Planifié', 'Confirmé')
            GROUP BY e.id, e.uuid, m.code, m.nom, f.code, f.nom, p.nom, p.prenom, 
                     p.grade, l.nom, l.type, l.capacite, e.date_heure, 
                     e.duree_minutes, e.type_examen, e.statut
            ORDER BY e.date_heure, f.nom
        """
        result = load_dataframe(query, (department_id, start_date, end_date))
        return result if not result.empty else pd.DataFrame()
    
    @staticmethod
    def get_professor_stats(professor_id: int) -> Dict[str, Any]:
        """
        Récupère les statistiques du professeur
        """
        query = """
            SELECT 
                CONCAT(p.nom, ' ', p.prenom) as nom_complet,
                p.grade,
                p.specialite,
                d.nom as departement,
                (SELECT COUNT(*) FROM modules WHERE responsable_id = p.id) as modules_responsables,
                (SELECT COUNT(*) FROM examens WHERE professeur_id = p.id AND statut IN ('Planifié', 'Confirmé') AND date_heure > CURRENT_TIMESTAMP) as examens_a_venir,
                (SELECT COUNT(*) FROM examens WHERE professeur_id = p.id AND statut = 'Terminé') as examens_termines
            FROM professeurs p
            JOIN departements d ON p.departement_id = d.id
            WHERE p.id = %s
        """
        result = execute_query(query, (professor_id,))
        return result[0] if result else {}
    
    @staticmethod
    def get_professor_modules(professor_id: int) -> pd.DataFrame:
        """
        Récupère les modules du professeur
        """
        query = """
            SELECT 
                m.id,
                m.code,
                m.nom,
                m.credits,
                m.semestre,
                f.nom as formation_nom
            FROM modules m
            JOIN formations f ON m.formation_id = f.id
            WHERE m.responsable_id = %s
            ORDER BY m.semestre, m.code
        """
        result = execute_query(query, (professor_id,))
        return pd.DataFrame(result) if result else pd.DataFrame()


class AnalyticsQueries:
    """Requêtes analytiques pour le dashboard"""
    
    @staticmethod
    def get_department_stats(department_id: int) -> Dict[str, Any]:
        """
        Récupère les statistiques complètes d'un département
        """
        query = """
            SELECT 
                nb_formations,
                nb_etudiants,
                nb_professeurs,
                nb_modules,
                nb_examens_planifies,
                nb_examens_termines,
                capacite_moyenne_salles,
                dernier_examen,
                premier_examen
            FROM v_stats_departement
            WHERE departement_id = %s
        """
        result = execute_query(query, (department_id,))
        return result[0] if result else {}
    
    @staticmethod
    def get_conflicts_report(department_id: int) -> pd.DataFrame:
        """
        Génère un rapport détaillé des conflits pour un département
        Note: La fonction detecter_conflits() retourne tous les conflits.
        Pour filtrer par département, on vérifie si le département est mentionné dans les détails.
        """
        # Récupérer tous les conflits puis filtrer manuellement par département
        query = """
            SELECT 
                type_conflit,
                details,
                severite,
                COUNT(*) as nombre
            FROM detecter_conflits()
            GROUP BY type_conflit, details, severite
            ORDER BY 
                CASE severite 
                    WHEN 'CRITIQUE' THEN 1
                    WHEN 'ÉLEVÉ' THEN 2
                    WHEN 'MOYEN' THEN 3
                    ELSE 4
                END,
                nombre DESC
        """
        result = load_dataframe(query)
        if not result.empty and department_id and 'details' in result.columns:
            # Filtrer par département si spécifié (recherche dans les détails)
            try:
                dept_query = """
                    SELECT nom FROM departements WHERE id = %s
                """
                dept_result = execute_query(dept_query, (department_id,))
                if dept_result:
                    dept_nom = dept_result[0].get('nom', '')
                    if dept_nom:
                        # Filtrer les lignes qui mentionnent le département dans les détails
                        result = result[result['details'].astype(str).str.contains(dept_nom, case=False, na=False)]
            except Exception:
                # Si erreur lors du filtrage, retourner tous les conflits
                pass
        return result if not result.empty else pd.DataFrame()
    
    @staticmethod
    def get_resource_utilization(start_date: date, end_date: date) -> pd.DataFrame:
        """
        Analyse l'utilisation des ressources (salles, professeurs)
        """
        query = """
            SELECT 
                l.nom as salle_nom,
                l.type as salle_type,
                l.capacite,
                COUNT(e.id) as nb_examens,
                SUM(e.duree_minutes) as total_minutes,
                COALESCE(ROUND(AVG(
                    (SELECT COUNT(DISTINCT i.etudiant_id) 
                     FROM inscriptions i 
                     WHERE i.module_id = e.module_id AND i.statut = 'Inscrit')::DECIMAL / l.capacite * 100
                ), 2), 0) as taux_occupation_moyen,
                ROUND(COUNT(e.id) * 100.0 / 
                    NULLIF((SELECT COUNT(*) FROM examens 
                     WHERE date_heure BETWEEN %s AND %s 
                     AND statut IN ('Planifié', 'Confirmé')), 0), 2) as pourcentage_utilisation
            FROM lieux_examen l
            LEFT JOIN examens e ON l.id = e.salle_id 
                AND e.date_heure BETWEEN %s AND %s
                AND e.statut IN ('Planifié', 'Confirmé')
            GROUP BY l.id, l.nom, l.type, l.capacite
            ORDER BY pourcentage_utilisation DESC NULLS LAST
        """
        result = load_dataframe(query, (start_date, end_date, start_date, end_date))
        return result if not result.empty else pd.DataFrame()
    
    @staticmethod
    def get_student_load_analysis(department_id: int) -> pd.DataFrame:
        """
        Analyse la charge des étudiants (examens par jour)
        """
        query = """
            SELECT 
                DATE(e.date_heure) as jour,
                COUNT(DISTINCT e.id) as nb_examens,
                COUNT(DISTINCT i.etudiant_id) as nb_etudiants_convoques,
                ROUND(AVG(
                    (SELECT COUNT(*) 
                     FROM inscriptions i2 
                     WHERE i2.module_id = e.module_id 
                     AND i2.statut = 'Inscrit')
                ), 2) as moyenne_etudiants_par_examen,
                CASE 
                    WHEN COUNT(DISTINCT i.etudiant_id) > 1000 THEN 'Surcharge'
                    WHEN COUNT(DISTINCT i.etudiant_id) > 500 THEN 'Charge élevée'
                    ELSE 'Charge normale'
                END as niveau_charge
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            JOIN formations f ON m.formation_id = f.id
            JOIN inscriptions i ON e.module_id = i.module_id AND i.statut = 'Inscrit'
            WHERE f.departement_id = %s
                AND e.date_heure >= CURRENT_DATE
                AND e.statut IN ('Planifié', 'Confirmé')
            GROUP BY DATE(e.date_heure)
            ORDER BY jour
        """
        result = load_dataframe(query, (department_id,))
        return result if not result.empty else pd.DataFrame()


class OptimizationQueries:
    """Requêtes pour l'optimisation automatique"""
    
    @staticmethod
    def generate_optimized_schedule(start_date: date, end_date: date, department_id: int = None) -> pd.DataFrame:
        """
        Génère un planning optimisé en utilisant la fonction PL/pgSQL
        """
        if department_id:
            query = """
                SELECT * FROM generer_planning_optimise(%s, %s) gpo
                WHERE EXISTS (
                    SELECT 1 FROM modules m
                    JOIN formations f ON m.formation_id = f.id
                    WHERE m.id = gpo.module_id
                    AND f.departement_id = %s
                )
                ORDER BY score_optimisation DESC
            """
            params = (start_date, end_date, department_id)
        else:
            query = "SELECT * FROM generer_planning_optimise(%s, %s) ORDER BY score_optimisation DESC"
            params = (start_date, end_date)
        
        result = load_dataframe(query, params)
        return result if not result.empty else pd.DataFrame()
    
   
    
    @staticmethod
    def detect_all_conflicts() -> pd.DataFrame:
        """
        Détecte tous les conflits dans le planning actuel
        VERSION CORRIGÉE - Retourne toujours un DataFrame
        """
        try:
            query = """
                SELECT * FROM detecter_conflits() 
                ORDER BY 
                    CASE severite 
                        WHEN 'CRITIQUE' THEN 1
                        WHEN 'ÉLEVÉ' THEN 2
                        WHEN 'MOYEN' THEN 3
                        ELSE 4
                    END
            """
            result = load_dataframe(query)
            
            # Assurer que nous retournons toujours un DataFrame
            if result is None:
                return pd.DataFrame()
            elif isinstance(result, pd.DataFrame):
                return result
            else:
                # Si c'est une liste ou autre chose, convertir en DataFrame
                return pd.DataFrame(result)
                
        except Exception as e:
            print(f"Erreur dans detect_all_conflicts: {e}")
            # Retourner un DataFrame vide au lieu d'un dict
            return pd.DataFrame()
    @staticmethod
    def get_available_resources(date_filter: date) -> Dict[str, List]:
        """
        Récupère les ressources disponibles pour une date donnée
        """
        # Salles disponibles
        rooms_query = """
            SELECT l.id, l.nom, l.type, l.capacite
            FROM lieux_examen l
            WHERE l.is_disponible = TRUE
            AND NOT EXISTS (
                SELECT 1 FROM examens e
                WHERE e.salle_id = l.id
                AND DATE(e.date_heure) = %s
                AND e.statut IN ('Planifié', 'Confirmé')
            )
            ORDER BY l.capacite DESC
        """
        
        # Professeurs disponibles
        profs_query = """
            SELECT p.id, CONCAT(p.nom, ' ', p.prenom) as nom, p.grade, p.specialite
            FROM professeurs p
            WHERE p.is_active = TRUE
            AND (
                SELECT COUNT(*)
                FROM examens e
                WHERE e.professeur_id = p.id
                AND DATE(e.date_heure) = %s
            ) < 3
            ORDER BY p.nom
        """
        
        rooms = execute_query(rooms_query, (date_filter,)) or []
        profs = execute_query(profs_query, (date_filter,)) or []
        
        return {
            'salles_disponibles': rooms,
            'professeurs_disponibles': profs
        }


class UserQueries:
    """Requêtes liées aux utilisateurs et authentification"""
    
    @staticmethod
    def authenticate_user(username: str, password_hash: str) -> Optional[Dict]:
        """
        Authentifie un utilisateur et récupère ses informations
        VERSION SIMPLIFIÉE POUR LE DÉVELOPPEMENT
        Note: Cette fonction n'est pas utilisée actuellement.
        L'authentification se fait via auth.login() dans auth.py
        """
        try:
            query = """
                SELECT 
                    u.id,
                    u.username,
                    u.role,
                    u.linked_id,
                    u.email,
                    CASE u.role
                        WHEN 'etudiant' THEN (SELECT CONCAT(nom, ' ', prenom) FROM etudiants WHERE id = u.linked_id LIMIT 1)
                        WHEN 'professeur' THEN (SELECT CONCAT(nom, ' ', prenom) FROM professeurs WHERE id = u.linked_id LIMIT 1)
                        WHEN 'chef_departement' THEN (
                            SELECT CONCAT(p.nom, ' ', p.prenom) 
                            FROM chef_departement cd
                            JOIN professeurs p ON cd.professeur_id = p.id
                            WHERE cd.id = u.linked_id
                            LIMIT 1
                        )
                        ELSE u.username
                    END as display_name
                FROM users u
                WHERE u.username = %s 
                    AND u.is_active = TRUE
            """
            
            result = execute_query(query, (username,))
            
            if result:
                user = result[0]
                # Pour le développement: ignorer la vérification du mot de passe
                return user
            
            return None
        except Exception as e:
            print(f"Erreur dans authenticate_user: {e}")
            return None
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        """
        Récupère un utilisateur par son nom d'utilisateur
        """
        query = """
            SELECT 
                id,
                username,
                role,
                linked_id,
                email,
                is_active
            FROM users
            WHERE username = %s
        """
        result = execute_query(query, (username,))
        return result[0] if result else None
    
    @staticmethod
    def get_user_dashboard_data(user_role: str, linked_id: int) -> Dict[str, Any]:
        """
        Récupère les données spécifiques pour le dashboard de chaque rôle
        """
        data = {}
        
        if user_role == 'etudiant':
            query = """
                SELECT 
                    e.matricule,
                    CONCAT(e.nom, ' ', e.prenom) as nom_complet,
                    f.nom as formation,
                    d.nom as departement,
                    e.annee_inscription as promo,
                    COUNT(DISTINCT i.module_id) as modules_inscrits,
                    COUNT(DISTINCT ex.id) as examens_a_venir
                FROM etudiants e
                JOIN formations f ON e.formation_id = f.id
                JOIN departements d ON f.departement_id = d.id
                LEFT JOIN inscriptions i ON e.id = i.etudiant_id AND i.statut = 'Inscrit'
                LEFT JOIN examens ex ON i.module_id = ex.module_id 
                    AND ex.date_heure > CURRENT_TIMESTAMP
                    AND ex.statut IN ('Planifié', 'Confirmé')
                WHERE e.id = %s
                GROUP BY e.id, f.nom, d.nom
            """
            result = execute_query(query, (linked_id,))
            if result:
                data.update(result[0])
        
        elif user_role == 'professeur':
            query = """
                SELECT 
                    p.matricule,
                    CONCAT(p.nom, ' ', p.prenom) as nom_complet,
                    d.nom as departement,
                    p.grade,
                    p.specialite,
                    COUNT(DISTINCT ex.id) as examens_a_surveiller,
                    COUNT(DISTINCT m.id) as modules_responsables
                FROM professeurs p
                JOIN departements d ON p.departement_id = d.id
                LEFT JOIN examens ex ON p.id = ex.professeur_id 
                    AND ex.date_heure > CURRENT_TIMESTAMP
                    AND ex.statut IN ('Planifié', 'Confirmé')
                LEFT JOIN modules m ON p.id = m.responsable_id
                WHERE p.id = %s
                GROUP BY p.id, d.nom
            """
            result = execute_query(query, (linked_id,))
            if result:
                data.update(result[0])
        
        elif user_role == 'chef_departement':
            query = """
                SELECT 
                    cd.date_nomination,
                    cd.date_fin_mandat,
                    CONCAT(p.nom, ' ', p.prenom) as nom_complet,
                    d.nom as departement,
                    d.code as departement_code,
                    (SELECT COUNT(*) FROM formations WHERE departement_id = d.id) as nb_formations,
                    (SELECT COUNT(*) FROM etudiants e 
                     JOIN formations f ON e.formation_id = f.id 
                     WHERE f.departement_id = d.id AND e.statut = 'Actif') as nb_etudiants,
                    (SELECT COUNT(*) FROM professeurs WHERE departement_id = d.id AND is_active = TRUE) as nb_professeurs
                FROM chef_departement cd
                JOIN professeurs p ON cd.professeur_id = p.id
                JOIN departements d ON cd.departement_id = d.id
                WHERE cd.id = %s AND cd.is_actif = TRUE
            """
            result = execute_query(query, (linked_id,))
            if result:
                data.update(result[0])
        
        elif user_role == 'admin_examens' or user_role == 'vice_doyen':
            data.update({
                'nom_complet': 'Administrateur Système',
                'departement': 'Administration Centrale',
                'role_display': 'Administrateur' if user_role == 'admin_examens' else 'Vice-Doyen'
            })
        
        return data
    
    @staticmethod
    def get_password_hash(username: str) -> Optional[str]:
        """
        Récupère le hash du mot de passe
        """
        query = "SELECT password_hash FROM users WHERE username = %s"
        result = execute_query(query, (username,))
        return result[0]['password_hash'] if result else None
    
    @staticmethod
    def get_test_users() -> List[Dict]:
        """
        Récupère la liste des utilisateurs de test pour le développement
        """
        query = """
            SELECT username, role, email, is_active
            FROM users 
            WHERE username LIKE 'test.%' OR username IN ('admin', 'vice.doyen')
            ORDER BY role
        """
        return execute_query(query) or []
    
    @staticmethod
    def get_professor_details(professor_id: int) -> Dict[str, Any]:
        """
        Récupère tous les détails d'un professeur
        """
        query = """
            SELECT 
                p.*,
                d.nom as departement_nom,
                d.code as departement_code,
                (SELECT COUNT(*) FROM modules WHERE responsable_id = p.id) as nb_modules_responsables,
                (SELECT COUNT(*) FROM examens WHERE professeur_id = p.id AND date_heure > CURRENT_TIMESTAMP AND statut IN ('Planifié', 'Confirmé')) as nb_examens_a_venir,
                (SELECT COUNT(*) FROM examens WHERE professeur_id = p.id AND statut = 'Terminé') as nb_examens_termines,
                (SELECT COALESCE(SUM(duree_minutes), 0) FROM examens WHERE professeur_id = p.id AND date_heure >= CURRENT_DATE - INTERVAL '30 days') as minutes_30j,
                (SELECT COALESCE(SUM(nb_etudiants), 0) FROM (
                    SELECT COUNT(DISTINCT i.etudiant_id) as nb_etudiants
                    FROM examens e
                    LEFT JOIN inscriptions i ON e.module_id = i.module_id
                    WHERE e.professeur_id = p.id
                    GROUP BY e.id
                ) as subquery) as total_etudiants
            FROM professeurs p
            JOIN departements d ON p.departement_id = d.id
            WHERE p.id = %s
        """
        result = execute_query(query, (professor_id,))
        return result[0] if result else {}
    
    @staticmethod
    def get_notifications(user_id: int, user_role: str, limit: int = 10) -> List[Dict]:
        """
        Récupère les notifications de l'utilisateur
        """
        try:
            query = """
                SELECT 
                    id,
                    type_notification,
                    titre,
                    contenu,
                    is_lu,
                    created_at,
                    priority
                FROM notifications
                WHERE user_id = %s OR user_role = %s
                ORDER BY priority DESC, created_at DESC
                LIMIT %s
            """
            return execute_query(query, (user_id, user_role, limit)) or []
        except Exception as e:
            print(f"Erreur dans get_notifications: {e}")
            return []
    
    @staticmethod
    def mark_notification_as_read(notification_id: int) -> int:
        """
        Marque une notification comme lue
        """
        try:
            query = "UPDATE notifications SET is_lu = TRUE WHERE id = %s"
            return execute_query(query, (notification_id,), fetch=False)
        except Exception as e:
            print(f"Erreur dans mark_notification_as_read: {e}")
            return 0
    
    @staticmethod
    def add_notification(user_id: int, user_role: str, type_notif: str, 
                        titre: str, contenu: str, priority: int = 1) -> List:
        """
        Ajoute une nouvelle notification
        """
        try:
            query = """
                INSERT INTO notifications 
                (user_id, user_role, type_notification, titre, contenu, priority)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            return execute_query(query, (user_id, user_role, type_notif, 
                                       titre, contenu, priority), fetch=True)
        except Exception as e:
            print(f"Erreur dans add_notification: {e}")
            return []
    
    @staticmethod
    def get_unread_notifications_count(user_id: int, user_role: str) -> int:
        """
        Compte les notifications non lues
        """
        try:
            query = """
                SELECT COUNT(*) as count
                FROM notifications
                WHERE (user_id = %s OR user_role = %s)
                    AND is_lu = FALSE
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """
            result = execute_query(query, (user_id, user_role))
            return result[0]['count'] if result else 0
        except Exception as e:
            print(f"Erreur dans get_unread_notifications_count: {e}")
            return 0
    
    @staticmethod
    def get_professor_availability(professor_id: int, start_date: date, end_date: date) -> List[Dict]:
        """
        Récupère les indisponibilités d'un professeur
        """
        try:
            query = """
                SELECT 
                    id,
                    date_debut,
                    date_fin,
                    motif,
                    details
                FROM indisponibilites_professeurs
                WHERE professeur_id = %s
                    AND ((date_debut BETWEEN %s AND %s)
                    OR (date_fin BETWEEN %s AND %s)
                    OR (date_debut <= %s AND date_fin >= %s))
                ORDER BY date_debut
            """
            return execute_query(query, (
                professor_id, start_date, end_date, 
                start_date, end_date, start_date, end_date
            )) or []
        except Exception as e:
            print(f"Erreur dans get_professor_availability: {e}")
            return []


def get_recent_audit_logs(limit: int = 50) -> List[Dict]:
    """
    Récupère les logs d'audit récents
    """
    query = """
    SELECT 
        id,
        table_name,
        record_id,
        action,
        changed_by,
        TO_CHAR(changed_at, 'DD/MM/YYYY HH24:MI:SS') as date_heure,
        ip_address
    FROM audit_log 
    ORDER BY changed_at DESC
    LIMIT %s
    """
    return execute_query(query, (limit,))


def get_audit_stats(start_date: date = None, end_date: date = None) -> List[Dict]:
    """
    Récupère les statistiques d'audit
    """
    query = """
    SELECT 
        table_name,
        action,
        COUNT(*) as count,
        MAX(changed_at) as last_date
    FROM audit_log 
    WHERE (%s IS NULL OR changed_at >= %s)
      AND (%s IS NULL OR changed_at <= %s)
    GROUP BY table_name, action
    ORDER BY count DESC
    """
    return execute_query(query, (start_date, start_date, end_date, end_date))


# Fonctions standalone pour compatibilité avec les imports
def get_occupation_salles() -> pd.DataFrame:
    """
    Récupère l'occupation des salles et amphis
    Utilise la vue v_occupation_salles de la BDD
    """
    query = """
        SELECT 
            nom,
            type,
            capacite,
            nb_examens_planifies as nb_examens,
            taux_occupation_moyen
        FROM v_occupation_salles
        ORDER BY taux_occupation_moyen DESC
    """
    result = execute_query(query)
    if result:
        df = pd.DataFrame(result)
        return df
    return pd.DataFrame()


def get_stats_departement() -> pd.DataFrame:
    """
    Récupère les statistiques par département
    Utilise la vue v_stats_departement de la BDD
    """
    query = """
        SELECT 
            departement_id as id,
            departement_nom as nom,
            nb_formations,
            nb_examens_planifies,
            nb_etudiants,
            nb_professeurs
        FROM v_stats_departement
        ORDER BY departement_nom
    """
    result = execute_query(query)
    if result:
        df = pd.DataFrame(result)
        return df
    return pd.DataFrame()


def generer_planning_optimise(date_debut: date, date_fin: date) -> pd.DataFrame:
    """
    Génère un planning optimisé en utilisant la fonction PL/pgSQL
    """
    return OptimizationQueries.generate_optimized_schedule(date_debut, date_fin)


def detecter_tous_les_conflits() -> pd.DataFrame:
    """
    Détecte tous les conflits dans le planning actuel
    """
    return OptimizationQueries.detect_all_conflicts()


def get_planning_examens() -> pd.DataFrame:
    """
    Récupère le planning complet des examens
    Utilise la vue v_planning_examens de la BDD
    """
    query = """
        SELECT 
            id,
            uuid,
            module_code,
            module_nom,
            formation_nom,
            departement_nom,
            professeur_nom,
            salle_nom,
            salle_type,
            capacite,
            date_heure,
            duree_minutes,
            type_examen,
            statut,
            etudiants_inscrits as nb_etudiants_inscrits
        FROM v_planning_examens
        WHERE statut IN ('Planifié', 'Confirmé')
        ORDER BY date_heure
    """
    result = execute_query(query)
    if result:
        df = pd.DataFrame(result)
        if not df.empty and 'date_heure' in df.columns:
            df['date_heure'] = pd.to_datetime(df['date_heure'])
        return df
    return pd.DataFrame()


def valider_examen(examen_id: int) -> bool:
    """
    Valide un examen (passe le statut à 'Confirmé')
    """
    try:
        query = """
            UPDATE examens 
            SET statut = 'Confirmé'
            WHERE id = %s AND statut = 'Planifié'
            RETURNING id
        """
        result = execute_query(query, (examen_id,), fetch=True)
        return len(result) > 0 if result else False
    except Exception as e:
        print(f"Erreur dans valider_examen: {e}")
        return False


def valider_tout_le_planning() -> bool:
    """
    Valide tout le planning (passe tous les examens planifiés à 'Confirmé')
    """
    try:
        query = """
            UPDATE examens 
            SET statut = 'Confirmé'
            WHERE statut = 'Planifié'
        """
        result = execute_query(query, fetch=False)
        return result > 0
    except Exception as e:
        print(f"Erreur dans valider_tout_le_planning: {e}")
        return False


def add_unavailability(prof_id: int, date_debut: datetime, 
                      date_fin: datetime, motif: str, details: str = None):
    """
    Ajoute une indisponibilité
    """
    try:
        query = """
            INSERT INTO indisponibilites_professeurs 
            (professeur_id, date_debut, date_fin, motif, details)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        return execute_query(query, (prof_id, date_debut, date_fin, 
                                   motif, details), fetch=True)
    except Exception as e:
        print(f"Erreur dans add_unavailability: {e}")
        return []


def delete_unavailability(unavailability_id: int):
    """
    Supprime une indisponibilité
    """
    try:
        query = "DELETE FROM indisponibilites_professeurs WHERE id = %s RETURNING id"
        return execute_query(query, (unavailability_id,), fetch=True)
    except Exception as e:
        print(f"Erreur dans delete_unavailability: {e}")
        return []