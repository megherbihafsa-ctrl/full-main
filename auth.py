# auth.py - Version Française
import streamlit as st
import hashlib
from connection import execute_query

def verifier_mot_de_passe(mot_de_passe_saisi: str, hash_stocke: str) -> bool:
    """
    Vérifier le mot de passe contre le hash stocké en base
    """
    if not hash_stocke or not mot_de_passe_saisi:
        return False
    
    # Méthode utilisée dans la base : $2a$12$ + 22 caractères MD5 + 31 caractères MD5
    if hash_stocke.startswith('$2a$12$'):
        md5hex = hashlib.md5(mot_de_passe_saisi.encode("utf-8")).hexdigest()
        hash_genere = "$2a$12$" + md5hex[:22] + md5hex[:31]
        return hash_stocke == hash_genere
    
    return False

def authentifier_utilisateur(username: str, password: str):
    """
    Authentification de l'utilisateur
    """
    username = (username or "").strip().lower()
    
    # Liste des utilisateurs de test (en cas de problème base)
    users_test = {
        "admin": {"password": "admin123", "role": "admin_examens", "id": 1},
        "test.etudiant": {"password": "test123", "role": "etudiant", "id": 1},
        "test.professeur": {"password": "test123", "role": "professeur", "id": 1},
        "test.chef": {"password": "test123", "role": "chef_departement", "id": 1},
        "vice.doyen": {"password": "doyen123", "role": "vice_doyen", "id": 1}
    }
    
    # Essayer d'abord avec la base de données
    try:
        sql = """
            SELECT id, username, password_hash, role, linked_id, is_active
            FROM users
            WHERE LOWER(username) = LOWER(%s)
            LIMIT 1
        """
        
        resultats = execute_query(sql, (username,))
        
        if resultats:
            user = resultats[0]
            
            # Vérifier compte actif
            if not user.get("is_active", True):
                return None
            
            # Vérifier mot de passe
            hash_stocke = user.get("password_hash", "")
            if verifier_mot_de_passe(password, hash_stocke):
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                    "linked_id": user["linked_id"],
                    "nom_affiche": user["username"].split('.')[0].title()
                }
    except Exception as e:
        st.warning(f"⚠️ Base de données : {e}. Utilisation mode test.")
    
    # Fallback : mode test (si base inaccessible)
    if username in users_test and users_test[username]["password"] == password:
        return {
            "id": 1,
            "username": username,
            "role": users_test[username]["role"],
            "linked_id": 1,
            "nom_affiche": username.split('.')[0].title()
        }
    
    return None

def afficher_formulaire_connexion():
    """
    Afficher le formulaire de connexion
    """
    st.markdown("""
    <style>
    .card-connexion {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 40px;
        color: white;
        max-width: 520px;
        margin: 50px auto;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    .titre-connexion {
        font-size: 32px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }
    .sous-titre {
        text-align: center;
        opacity: 0.8;
        margin-bottom: 30px;
    }
    .stTextInput input, .stTextInput input:focus {
        background: rgba(255,255,255,0.1);
        color: white;
        border: 1px solid rgba(255,255,255,0.3);
    }
    .stTextInput input::placeholder {
        color: rgba(255,255,255,0.6);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="card-connexion">', unsafe_allow_html=True)
    
   
def login(username: str, password: str):
    username = (username or "").strip()

    # ⚠️ Si la table users n'existe pas, execute_query renvoie []
    sql = """
        SELECT id, username, password_hash, role, linked_id, is_active
        FROM users
        WHERE username = %s
        LIMIT 1
    """
    rows = execute_query(sql, (username,))
    if not rows:
        return None

    u = rows[0]
    if not u.get("is_active", False):
        return None

    
    return {
        "id": u["id"],
        "username": u["username"],
        "role": u["role"],
        "linked_id": u["linked_id"],
        "display_name": u["username"],
    } 
def render_login_form():
    st.markdown(
        """
<div class="card fadeUp" style="max-width:520px; margin: 24px auto; text-align:center;">
  <div class="h-title">🔐 Connexion</div>
  <div class="h-sub">Accès selon le rôle (admin, vice-doyen, chef, etc.)</div>
</div>
""",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("👤 Nom d'utilisateur", placeholder="admin, vice.doyen, test.chef ...")
        with col2:
            password = st.text_input("🔒 Mot de passe", type="password", placeholder="admin123, doyen123 ...")

        submitted = st.form_submit_button("Se connecter", use_container_width=True, type="primary")

    if submitted:
        user_data = login(username, password)
        if user_data:
            st.session_state.authenticated = True
            st.session_state.user = user_data
            st.session_state.role = user_data["role"]
            st.success(f"✅ Connecté: {user_data['username']} ({user_data['role']})")
            st.rerun()
        else:
            st.error("❌ Identifiants incorrects, compte désactivé, ou DB non chargée.")
            st.info("⚠️ Vérifie que la table users existe dans exam_platform et que tu as bien exécuté bdd.sql.")