-- ============================================
-- PARTIE 1: RESET COMPLET DE LA BASE
-- ============================================

-- 1. إعادة تعيين Schema كامل
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- 2. تفعيل الامتدادات
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 3. منح الصلاحيات
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- ============================================
-- PARTIE 2: CREATION DES TABLES
-- ============================================

-- Table 1: departements
CREATE TABLE departements (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: formations
CREATE TABLE formations (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(150) NOT NULL,
    departement_id INT NOT NULL REFERENCES departements(id) ON DELETE CASCADE,
    niveau VARCHAR(20) CHECK (niveau IN ('Licence', 'Master', 'Doctorat')),
    nb_modules INT DEFAULT 0,
    annee_academique INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT fk_formation_departement FOREIGN KEY (departement_id) 
        REFERENCES departements(id) ON DELETE CASCADE
);

-- Table 3: modules
CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(200) NOT NULL,
    credits INT NOT NULL CHECK (credits BETWEEN 1 AND 12),
    formation_id INT NOT NULL REFERENCES formations(id) ON DELETE CASCADE,
    semestre INT CHECK (semestre BETWEEN 1 AND 6),
    volume_horaire INT,
    pre_requis_id INT REFERENCES modules(id),
    responsable_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_module_formation FOREIGN KEY (formation_id) 
        REFERENCES formations(id) ON DELETE CASCADE,
    CONSTRAINT fk_module_pre_requis FOREIGN KEY (pre_requis_id) 
        REFERENCES modules(id) ON DELETE SET NULL
);

-- Table 4: etudiants
CREATE TABLE etudiants (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    date_naissance DATE,
    email_univ VARCHAR(150) UNIQUE,
    formation_id INT NOT NULL REFERENCES formations(id) ON DELETE CASCADE,
    annee_inscription INT NOT NULL,
    statut VARCHAR(20) DEFAULT 'Actif' CHECK (statut IN ('Actif', 'Inactif', 'Diplome', 'Abandon')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_etudiant_formation FOREIGN KEY (formation_id) 
        REFERENCES formations(id) ON DELETE CASCADE
);

-- Table 5: professeurs
CREATE TABLE professeurs (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    grade VARCHAR(50),
    departement_id INT NOT NULL REFERENCES departements(id) ON DELETE CASCADE,
    specialite VARCHAR(200),
    email VARCHAR(150) UNIQUE,
    telephone VARCHAR(20),
    heures_min INT DEFAULT 48,
    heures_max INT DEFAULT 192,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_professeur_departement FOREIGN KEY (departement_id) 
        REFERENCES departements(id) ON DELETE CASCADE
);

-- Table 6: lieux_examen
CREATE TABLE lieux_examen (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    capacite INT NOT NULL CHECK (capacite > 0),
    type VARCHAR(30) NOT NULL CHECK (type IN ('Amphitheatre', 'Salle de cours', 'Laboratoire', 'Salle specialisee')),
    batiment VARCHAR(50),
    etage INT,
    equipements TEXT[],
    is_disponible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 7: inscriptions
CREATE TABLE inscriptions (
    id SERIAL PRIMARY KEY,
    etudiant_id INT NOT NULL REFERENCES etudiants(id) ON DELETE CASCADE,
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    annee_academique INT NOT NULL,
    session VARCHAR(10) CHECK (session IN ('Principale', 'Rattrapage')),
    note NUMERIC(4,2) CHECK (note BETWEEN 0 AND 20),
    statut VARCHAR(20) DEFAULT 'Inscrit' CHECK (statut IN ('Inscrit', 'Valide', 'Echoue', 'Abandonne')),
    date_inscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification TIMESTAMP,
    UNIQUE(etudiant_id, module_id, annee_academique, session),
    CONSTRAINT fk_inscription_etudiant FOREIGN KEY (etudiant_id) 
        REFERENCES etudiants(id) ON DELETE CASCADE,
    CONSTRAINT fk_inscription_module FOREIGN KEY (module_id) 
        REFERENCES modules(id) ON DELETE CASCADE
);

-- Table 8: examens
CREATE TABLE examens (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4(),
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    professeur_id INT NOT NULL REFERENCES professeurs(id) ON DELETE CASCADE,
    salle_id INT NOT NULL REFERENCES lieux_examen(id) ON DELETE CASCADE,
    date_heure TIMESTAMP NOT NULL,
    duree_minutes INT NOT NULL CHECK (duree_minutes BETWEEN 60 AND 240),
    type_examen VARCHAR(30) DEFAULT 'Final' CHECK (type_examen IN ('Final', 'Partiel', 'Rattrapage', 'Controle')),
    statut VARCHAR(20) DEFAULT 'Planifie' CHECK (statut IN ('Planifie', 'Confirme', 'Annule', 'Termine')),
    max_etudiants INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INT,
    notes TEXT,
    CONSTRAINT fk_examen_module FOREIGN KEY (module_id) 
        REFERENCES modules(id) ON DELETE CASCADE,
    CONSTRAINT fk_examen_professeur FOREIGN KEY (professeur_id) 
        REFERENCES professeurs(id) ON DELETE CASCADE,
    CONSTRAINT fk_examen_salle FOREIGN KEY (salle_id) 
        REFERENCES lieux_examen(id) ON DELETE CASCADE,
    CONSTRAINT unique_salle_temps UNIQUE(salle_id, date_heure)
);

-- Table 9: chef_departement
CREATE TABLE chef_departement (
    id SERIAL PRIMARY KEY,
    professeur_id INT NOT NULL UNIQUE REFERENCES professeurs(id) ON DELETE CASCADE,
    departement_id INT NOT NULL UNIQUE REFERENCES departements(id) ON DELETE CASCADE,
    date_nomination DATE NOT NULL,
    date_fin_mandat DATE,
    is_actif BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chef_professeur FOREIGN KEY (professeur_id) 
        REFERENCES professeurs(id) ON DELETE CASCADE,
    CONSTRAINT fk_chef_departement FOREIGN KEY (departement_id) 
        REFERENCES departements(id) ON DELETE CASCADE
);

-- Table 10: users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(150) UNIQUE,
    role VARCHAR(30) NOT NULL CHECK (role IN ('etudiant', 'professeur', 'chef_departement', 'admin_examens', 'vice_doyen')),
    linked_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    failed_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_linked UNIQUE(role, linked_id)
);

-- Table 11: audit_log
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INT NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by INT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- ============================================
-- PARTIE 3: INDEX BASIQUES
-- ============================================

-- Index pour departements
CREATE INDEX idx_departements_nom ON departements USING gin(nom gin_trgm_ops);

-- Index pour formations
CREATE INDEX idx_formations_dept ON formations(departement_id, annee_academique);
CREATE INDEX idx_formations_niveau ON formations(niveau, is_active);

-- Index pour modules
CREATE INDEX idx_modules_formation ON modules(formation_id);
CREATE INDEX idx_modules_semestre ON modules(semestre, formation_id);

-- Index pour etudiants
CREATE INDEX idx_etudiants_formation ON etudiants(formation_id, annee_inscription);
CREATE INDEX idx_etudiants_matricule ON etudiants(matricule);

-- Index pour professeurs
CREATE INDEX idx_professeurs_dept ON professeurs(departement_id, is_active);
CREATE INDEX idx_professeurs_matricule ON professeurs(matricule);

-- Index pour lieux_examen
CREATE INDEX idx_lieux_disponibles ON lieux_examen(id, capacite) WHERE is_disponible = TRUE;
CREATE INDEX idx_lieux_capacite ON lieux_examen(capacite, type);

-- Index pour inscriptions
CREATE INDEX idx_inscriptions_etudiant ON inscriptions(etudiant_id, annee_academique);
CREATE INDEX idx_inscriptions_module ON inscriptions(module_id, annee_academique);
CREATE INDEX idx_inscriptions_statut ON inscriptions(statut, annee_academique);

-- Index pour examens
CREATE INDEX idx_examens_date ON examens(date_heure DESC);
CREATE INDEX idx_examens_module ON examens(module_id);
CREATE INDEX idx_examens_professeur ON examens(professeur_id);
CREATE INDEX idx_examens_salle ON examens(salle_id);
CREATE INDEX idx_examens_statut ON examens(statut) WHERE statut IN ('Planifie', 'Confirme');

-- Index pour users
CREATE INDEX idx_users_role ON users(role, is_active);
CREATE INDEX idx_users_username ON users(username);

-- Index pour audit_log
CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_changed_at ON audit_log(changed_at DESC);

-- ============================================
-- PARTIE 4: TRIGGERS
-- ============================================

-- Trigger pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_etudiants_updated_at
BEFORE UPDATE ON etudiants
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_update_examens_updated_at
BEFORE UPDATE ON examens
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_update_lieux_updated_at
BEFORE UPDATE ON lieux_examen
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- ============================================
-- PARTIE 5: DONNEES DE TEST
-- ============================================

-- 1. إدخال الأقسام
INSERT INTO departements (code, nom) VALUES
('INFO', 'Informatique'),
('MATH', 'Mathematiques'),
('PHYS', 'Physique'),
('CHIM', 'Chimie'),
('BIO', 'Biologie'),
('GEOL', 'Geologie'),
('ECO', 'Sciences Economiques');

-- 2. إدخال التكوينات (5 لكل قسم)
INSERT INTO formations (code, nom, departement_id, niveau, nb_modules, annee_academique, is_active)
SELECT 
    d.code || '-F' || LPAD(i::text, 3, '0'),
    CASE i % 2 
        WHEN 0 THEN 'Licence ' || d.nom || ' S' || i
        ELSE 'Master ' || d.nom || ' S' || i
    END,
    d.id,
    CASE i % 2 WHEN 0 THEN 'Licence' ELSE 'Master' END,
    6 + (i % 4),
    2025,
    TRUE
FROM departements d
CROSS JOIN generate_series(1, 5) i;

-- 3. إدخال الأساتذة (10 لكل قسم)
INSERT INTO professeurs (matricule, nom, prenom, grade, departement_id, specialite, email, telephone, is_active)
SELECT 
    'PROF-' || LPAD(ROW_NUMBER() OVER ()::text, 6, '0'),
    'Nom' || s,
    'Prenom' || s,
    CASE (s % 4)
        WHEN 0 THEN 'Professeur'
        WHEN 1 THEN 'Maitre Conferences'
        WHEN 2 THEN 'Charge Cours'
        ELSE 'Assistant'
    END,
    ((s - 1) % 7) + 1,
    'Specialite ' || s,
    'prof' || s || '@univ.dz',
    '05' || LPAD((s % 1000000)::text, 8, '0'),
    TRUE
FROM generate_series(1, 70) s;

-- 4. إدخال الوحدات (4 لكل تكوين)
INSERT INTO modules (code, nom, credits, formation_id, semestre, volume_horaire)
SELECT 
    'MOD-' || LPAD(ROW_NUMBER() OVER ()::text, 6, '0'),
    'Module ' || f.code || '-M' || m,
    3 + ((ROW_NUMBER() OVER ()) % 6),
    f.id,
    1 + ((ROW_NUMBER() OVER ()) % 6),
    30 + ((ROW_NUMBER() OVER ()) % 30)
FROM formations f
CROSS JOIN generate_series(1, 4) m;

-- 5. إدخال الطلبة (500 طالب)
INSERT INTO etudiants (matricule, nom, prenom, email_univ, formation_id, annee_inscription, statut, date_naissance)
SELECT 
    'ETU-' || LPAD(s::text, 6, '0'),
    'Etudiant' || s,
    'Prenom' || s,
    'etu' || s || '@univ.dz',
    (s % (SELECT COUNT(*) FROM formations)) + 1,
    2022 + (s % 4),
    CASE (s % 10)
        WHEN 0 THEN 'Inactif'
        WHEN 1 THEN 'Diplome'
        ELSE 'Actif'
    END,
    DATE '2000-01-01' + (s % 3000)
FROM generate_series(1, 500) s;

-- 6. إدخال قاعات الامتحان
INSERT INTO lieux_examen (code, nom, capacite, type, batiment, equipements, is_disponible) VALUES
('AMPHI-A', 'Amphitheatre A', 400, 'Amphitheatre', 'Batiment Central', ARRAY['Video', 'Son'], TRUE),
('AMPHI-B', 'Amphitheatre B', 350, 'Amphitheatre', 'Batiment Central', ARRAY['Video'], TRUE),
('SAL-101', 'Salle 101', 20, 'Salle de cours', 'Batiment A', ARRAY['Tableau'], TRUE),
('SAL-102', 'Salle 102', 20, 'Salle de cours', 'Batiment A', ARRAY['Tableau'], TRUE),
('SAL-201', 'Salle 201', 20, 'Salle de cours', 'Batiment B', ARRAY['Tableau'], TRUE),
('SAL-202', 'Salle 202', 20, 'Salle de cours', 'Batiment B', ARRAY['Tableau', 'Video'], TRUE),
('LAB-INFO1', 'Lab Informatique 1', 30, 'Laboratoire', 'Batiment Info', ARRAY['PC', 'Reseau'], TRUE),
('LAB-INFO2', 'Lab Informatique 2', 30, 'Laboratoire', 'Batiment Info', ARRAY['PC', 'Reseau'], TRUE);

-- 7. إدخال التسجيلات (2000 تسجيل)
INSERT INTO inscriptions (etudiant_id, module_id, annee_academique, session, statut, note)
SELECT 
    e.id,
    m.id,
    2025,
    'Principale',
    CASE 
        WHEN RANDOM() < 0.7 THEN 'Inscrit'
        WHEN RANDOM() < 0.8 THEN 'Valide'
        ELSE 'Echoue'
    END,
    CASE 
        WHEN RANDOM() < 0.7 THEN 10 + (RANDOM() * 10)
        ELSE NULL
    END
FROM etudiants e
CROSS JOIN modules m
WHERE e.statut = 'Actif'
  AND m.formation_id = e.formation_id
  AND RANDOM() < 0.4
LIMIT 2000;
-- الخطوة 1: حذف الامتحانات الحالية
DELETE FROM examens;

-- الخطوة 2: إدخال امتحانات جديدة - VERSION ULTRA SIMPLE
DO $$
DECLARE
    module_record RECORD;
    prof_id INT;
    salle_id INT;
    exam_date TIMESTAMP := TIMESTAMP '2025-01-15 08:00:00';
    counter INT := 0;
BEGIN
    FOR module_record IN (
        SELECT m.id, f.departement_id
        FROM modules m
        JOIN formations f ON m.formation_id = f.id
        WHERE EXISTS (SELECT 1 FROM inscriptions WHERE module_id = m.id AND statut = 'Inscrit')
        ORDER BY RANDOM()
        LIMIT 100
    ) LOOP
        -- اختيار أستاذ عشوائي من نفس القسم
        SELECT id INTO prof_id
        FROM professeurs 
        WHERE departement_id = module_record.departement_id 
        ORDER BY RANDOM() 
        LIMIT 1;
        
        -- اختيار قاعة بالتناوب (8 قاعات)
        SELECT id INTO salle_id
        FROM lieux_examen 
        ORDER BY id 
        LIMIT 1 OFFSET (counter % 8);
        
        -- إدخال الامتحان
        INSERT INTO examens (module_id, professeur_id, salle_id, date_heure, duree_minutes, type_examen, statut)
        VALUES (
            module_record.id,
            prof_id,
            salle_id,
            exam_date + ((counter / 8) || ' days')::INTERVAL + (((counter % 8) * 90) || ' minutes')::INTERVAL,
            90,
            CASE (counter % 3)
                WHEN 0 THEN 'Final'
                WHEN 1 THEN 'Partiel'
                ELSE 'Controle'
            END,
            CASE (counter % 4)
                WHEN 0 THEN 'Planifie'
                WHEN 1 THEN 'Confirme'
                WHEN 2 THEN 'Termine'
                ELSE 'Annule'
            END
        );
        
        counter := counter + 1;
    END LOOP;
END $$;

-- حذف وإعادة إدخال رؤساء الأقسام
DELETE FROM chef_departement;

DO $$
DECLARE
    dept RECORD;
    prof_id INT;
BEGIN
    FOR dept IN SELECT id FROM departements ORDER BY id LOOP
        -- اختيار أستاذ عشوائي من القسم
        SELECT id INTO prof_id
        FROM professeurs 
        WHERE departement_id = dept.id 
        AND grade IN ('Professeur', 'Maitre Conferences')
        ORDER BY RANDOM() 
        LIMIT 1;
        
        -- إذا وجد أستاذ، أدخله كرئيس قسم
        IF prof_id IS NOT NULL THEN
            INSERT INTO chef_departement (professeur_id, departement_id, date_nomination, date_fin_mandat, is_actif)
            VALUES (prof_id, dept.id, '2024-09-01', '2027-08-31', TRUE);
        END IF;
    END LOOP;
END $$;
-- 10. دالة لكلمات المرور
CREATE OR REPLACE FUNCTION generate_simple_bcrypt(password TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN '$2a$12$' || SUBSTR(MD5(password), 1, 22) || SUBSTR(MD5(password), 23, 31);
END;
$$ LANGUAGE plpgsql;

-- 11. إدخال المستخدمين
INSERT INTO users (username, password_hash, role, linked_id, email, is_active) VALUES
('test.etudiant', generate_simple_bcrypt('test123'), 'etudiant', 1, 'test.etudiant@univ.dz', TRUE),
('test.professeur', generate_simple_bcrypt('test123'), 'professeur', 1, 'test.professeur@univ.dz', TRUE),
('test.chef', generate_simple_bcrypt('test123'), 'chef_departement', 1, 'test.chef@univ.dz', TRUE),
('admin', generate_simple_bcrypt('admin123'), 'admin_examens', 1, 'admin@univ.dz', TRUE),
('vice.doyen', generate_simple_bcrypt('doyen123'), 'vice_doyen', 1, 'vice.doyen@univ.dz', TRUE);



-- ============================================
-- TABLE audit_log
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INT NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by INT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- Indexes pour audit_log
CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON audit_log(changed_at DESC);

-- ============================================
-- FONCTION GÉNÉRIQUE POUR TOUS LES TRIGGERS
-- ============================================
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id INT;
    v_ip_address VARCHAR(45);
BEGIN
    -- Récupérer l'ID utilisateur depuis la session
    BEGIN
        v_user_id := current_setting('app.user_id', TRUE)::INT;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;
    
    -- Récupérer l'adresse IP
    BEGIN
        v_ip_address := inet_client_addr()::VARCHAR;
    EXCEPTION WHEN OTHERS THEN
        v_ip_address := NULL;
    END;
    
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, changed_by, ip_address)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD)::jsonb, v_user_id, v_ip_address);
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        -- Ne pas enregistrer si seuls les champs updated_at ou created_at ont changé
        IF (OLD.* IS DISTINCT FROM NEW.*) AND 
           (NEW.updated_at IS NULL OR OLD.updated_at IS NULL OR 
            EXTRACT(EPOCH FROM (NEW.updated_at - OLD.updated_at)) > 1) THEN
            INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by, ip_address)
            VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', 
                    row_to_json(OLD)::jsonb, 
                    row_to_json(NEW)::jsonb, 
                    v_user_id, v_ip_address);
        END IF;
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO audit_log (table_name, record_id, action, new_values, changed_by, ip_address)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW)::jsonb, v_user_id, v_ip_address);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS POUR TOUTES LES TABLES IMPORTANTES
-- ============================================

-- Trigger pour examens
DROP TRIGGER IF EXISTS trg_audit_examens ON examens;
CREATE TRIGGER trg_audit_examens
AFTER INSERT OR UPDATE OR DELETE ON examens
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour etudiants
DROP TRIGGER IF EXISTS trg_audit_etudiants ON etudiants;
CREATE TRIGGER trg_audit_etudiants
AFTER INSERT OR UPDATE OR DELETE ON etudiants
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour professeurs
DROP TRIGGER IF EXISTS trg_audit_professeurs ON professeurs;
CREATE TRIGGER trg_audit_professeurs
AFTER INSERT OR UPDATE OR DELETE ON professeurs
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour inscriptions
DROP TRIGGER IF EXISTS trg_audit_inscriptions ON inscriptions;
CREATE TRIGGER trg_audit_inscriptions
AFTER INSERT OR UPDATE OR DELETE ON inscriptions
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour modules
DROP TRIGGER IF EXISTS trg_audit_modules ON modules;
CREATE TRIGGER trg_audit_modules
AFTER INSERT OR UPDATE OR DELETE ON modules
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour formations
DROP TRIGGER IF EXISTS trg_audit_formations ON formations;
CREATE TRIGGER trg_audit_formations
AFTER INSERT OR UPDATE OR DELETE ON formations
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour lieux_examen
DROP TRIGGER IF EXISTS trg_audit_lieux ON lieux_examen;
CREATE TRIGGER trg_audit_lieux
AFTER INSERT OR UPDATE OR DELETE ON lieux_examen
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour chef_departement
DROP TRIGGER IF EXISTS trg_audit_chef ON chef_departement;
CREATE TRIGGER trg_audit_chef
AFTER INSERT OR UPDATE OR DELETE ON chef_departement
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Trigger pour users (avec exclusion des changements de session)
CREATE OR REPLACE FUNCTION audit_users_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id INT;
    v_ip_address VARCHAR(45);
BEGIN
    -- Ne pas enregistrer les changements de last_login ou failed_attempts
    IF (TG_OP = 'UPDATE') AND 
       (OLD.last_login IS NOT DISTINCT FROM NEW.last_login OR 
        OLD.failed_attempts IS NOT DISTINCT FROM NEW.failed_attempts) THEN
        RETURN NEW;
    END IF;
    
    RETURN audit_trigger_function();
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_users ON users;
CREATE TRIGGER trg_audit_users
AFTER INSERT OR UPDATE OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION audit_users_trigger_function();
-- ============================================
-- FONCTIONS UTILES POUR AUDIT_LOG
-- ============================================

-- Fonction pour définir l'utilisateur courant dans la session
CREATE OR REPLACE FUNCTION set_current_user(user_id INT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.user_id', user_id::TEXT, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Fonction pour nettoyer les anciens logs (garder 90 jours)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM audit_log 
    WHERE changed_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
    RETURNING COUNT(*) INTO deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour obtenir les statistiques d'audit
CREATE OR REPLACE FUNCTION get_audit_statistics(
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
)
RETURNS TABLE (
    table_name VARCHAR,
    action_type VARCHAR,
    operation_count BIGINT,
    last_operation TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        al.table_name,
        al.action,
        COUNT(*) as operation_count,
        MAX(al.changed_at) as last_operation
    FROM audit_log al
    WHERE (p_start_date IS NULL OR al.changed_at >= p_start_date)
      AND (p_end_date IS NULL OR al.changed_at <= p_end_date)
    GROUP BY al.table_name, al.action
    ORDER BY operation_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour rechercher dans audit_log
CREATE OR REPLACE FUNCTION search_audit_log(
    p_table_name VARCHAR DEFAULT NULL,
    p_record_id INT DEFAULT NULL,
    p_action VARCHAR DEFAULT NULL,
    p_user_id INT DEFAULT NULL,
    p_limit INT DEFAULT 100
)
RETURNS TABLE (
    id BIGINT,
    table_name VARCHAR,
    record_id INT,
    action VARCHAR,
    changed_by INT,
    changed_at TIMESTAMP,
    ip_address VARCHAR,
    old_data JSONB,
    new_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        al.id,
        al.table_name,
        al.record_id,
        al.action,
        al.changed_by,
        al.changed_at,
        al.ip_address,
        al.old_values,
        al.new_values
    FROM audit_log al
    WHERE (p_table_name IS NULL OR al.table_name = p_table_name)
      AND (p_record_id IS NULL OR al.record_id = p_record_id)
      AND (p_action IS NULL OR al.action = p_action)
      AND (p_user_id IS NULL OR al.changed_by = p_user_id)
    ORDER BY al.changed_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
-- ============================================
-- VUES POUR AUDIT_LOG
-- ============================================

-- Vue pour l'activité récente
CREATE OR REPLACE VIEW v_audit_recent_activity AS
SELECT 
    al.id,
    al.table_name as table_cible,
    al.record_id as id_cible,
    CASE al.action
        WHEN 'INSERT' THEN '🟢 Ajout'
        WHEN 'UPDATE' THEN '🔵 Modification'
        WHEN 'DELETE' THEN '🔴 Suppression'
    END as operation,
    COALESCE(u.username, 'Système') as utilisateur,
    al.changed_at as date_operation,
    al.ip_address,
    CASE 
        WHEN al.old_values IS NOT NULL THEN TRUE
        ELSE FALSE
    END as a_anciennes_valeurs,
    CASE 
        WHEN al.new_values IS NOT NULL THEN TRUE
        ELSE FALSE
    END as a_nouvelles_valeurs
FROM audit_log al
LEFT JOIN users u ON al.changed_by = u.id
ORDER BY al.changed_at DESC;

-- Vue pour les statistiques quotidiennes
CREATE OR REPLACE VIEW v_audit_daily_stats AS
SELECT 
    DATE(al.changed_at) as jour,
    al.table_name,
    al.action,
    COUNT(*) as nombre_operations,
    COUNT(DISTINCT al.changed_by) as nombre_utilisateurs
FROM audit_log al
GROUP BY DATE(al.changed_at), al.table_name, al.action
ORDER BY jour DESC, nombre_operations DESC;

-- Vue pour les utilisateurs les plus actifs
CREATE OR REPLACE VIEW v_audit_top_users AS
SELECT 
    COALESCE(u.username, 'ID:' || al.changed_by::TEXT) as utilisateur,
    COUNT(*) as total_operations,
    COUNT(DISTINCT al.table_name) as tables_modifiees,
    MIN(al.changed_at) as premiere_operation,
    MAX(al.changed_at) as derniere_operation,
    STRING_AGG(DISTINCT al.action, ', ' ORDER BY al.action) as types_operations
FROM audit_log al
LEFT JOIN users u ON al.changed_by = u.id
GROUP BY al.changed_by, u.username
ORDER BY total_operations DESC;
-- ============================================
-- DONNÉES DE TEST POUR AUDIT_LOG
-- ============================================
-- ============================================
-- DONNÉES DE TEST POUR AUDIT_LOG (CORRIGÉ)
-- ============================================

-- Simulation d'activité sur les dernières 7 jours
INSERT INTO audit_log (table_name, record_id, action, changed_by, ip_address, changed_at)
SELECT 
    CASE (n % 7)
        WHEN 0 THEN 'etudiants'
        WHEN 1 THEN 'professeurs'
        WHEN 2 THEN 'examens'
        WHEN 3 THEN 'modules'
        WHEN 4 THEN 'inscriptions'
        WHEN 5 THEN 'formations'
        WHEN 6 THEN 'lieux_examen'
    END as table_name,
    (n * 10) + 1 as record_id,
    CASE (n % 3)
        WHEN 0 THEN 'INSERT'
        WHEN 1 THEN 'UPDATE'
        WHEN 2 THEN 'DELETE'
    END as action,
    (n % 5) + 1 as changed_by,  -- CORRECTION: retirer CASE inutile
    '192.168.1.' || (n % 255) as ip_address,
    CURRENT_TIMESTAMP - (n % 7 || ' days')::INTERVAL - ((n % 24) || ' hours')::INTERVAL as changed_at
FROM generate_series(1, 50) n;
-- الكود النهائي البسيط والمضمون
TRUNCATE audit_log RESTART IDENTITY;

INSERT INTO audit_log (table_name, record_id, action, changed_by, ip_address, changed_at) VALUES
('etudiants', 100, 'INSERT', 1, '192.168.1.10', NOW()),
('examens', 50, 'UPDATE', 2, '192.168.1.20', NOW() - INTERVAL '30 minutes'),
('professeurs', 30, 'DELETE', 3, '192.168.1.30', NOW() - INTERVAL '1 hour');

SELECT '✅ Audit log prêt!' as status, COUNT(*) as total FROM audit_log;

-- التحقق من وجود audit_log
SELECT * FROM audit_log LIMIT 5;

-- التحقق من الـ Triggers
SELECT 
    trigger_name,
    event_manipulation,
    event_object_table
FROM information_schema.triggers 
WHERE trigger_schema = 'public'
ORDER BY event_object_table;
-- التحقق من الـ Triggers
SELECT 
    trigger_name,
    event_manipulation,
    event_object_table
FROM information_schema.triggers 
WHERE trigger_schema = 'public'
ORDER BY event_object_table;


-- ============================================
-- PARTIE 7: TABLES MANQUANTES POUR L'INTERFACE
-- ============================================

-- Table pour les indisponibilités des professeurs
CREATE TABLE IF NOT EXISTS indisponibilites_professeurs (
    id SERIAL PRIMARY KEY,
    professeur_id INT NOT NULL REFERENCES professeurs(id) ON DELETE CASCADE,
    date_debut TIMESTAMP NOT NULL,
    date_fin TIMESTAMP NOT NULL,
    motif VARCHAR(100),
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_dates CHECK (date_fin > date_debut)
);

-- Table pour les conflits détectés
CREATE TABLE IF NOT EXISTS conflits_examens (
    id SERIAL PRIMARY KEY,
    type_conflit VARCHAR(50),
    description TEXT,
    severite VARCHAR(20) CHECK (severite IN ('CRITIQUE', 'ÉLEVÉ', 'MOYEN', 'FAIBLE')),
    date_detection TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    statut VARCHAR(20) DEFAULT 'Non résolu' CHECK (statut IN ('Non résolu', 'En cours', 'Résolu')),
    examens_impliques JSONB,
    suggestions TEXT,
    resolved_by INT REFERENCES users(id),
    resolved_at TIMESTAMP,
    notes TEXT
);

-- Table pour les notifications (corrigée)
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT,
    user_role VARCHAR(30),
    type_notification VARCHAR(50),
    titre VARCHAR(200),
    contenu TEXT,
    is_lu BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    priority INT DEFAULT 1 CHECK (priority BETWEEN 1 AND 3)
);
-- ============================================
-- PARTIE 6: VERIFICATION FINALE
-- ============================================

-- التحقق من عدد الجداول
SELECT 'Nombre de tables' as info, COUNT(*) as valeur 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- التحقق من إدخال البيانات
SELECT 'departements' as table_name, COUNT(*) as count FROM departements
UNION ALL SELECT 'formations', COUNT(*) FROM formations
UNION ALL SELECT 'modules', COUNT(*) FROM modules
UNION ALL SELECT 'etudiants', COUNT(*) FROM etudiants
UNION ALL SELECT 'professeurs', COUNT(*) FROM professeurs
UNION ALL SELECT 'lieux_examen', COUNT(*) FROM lieux_examen
UNION ALL SELECT 'inscriptions', COUNT(*) FROM inscriptions
UNION ALL SELECT 'examens', COUNT(*) FROM examens
UNION ALL SELECT 'chef_departement', COUNT(*) FROM chef_departement
UNION ALL SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'Logs audit: ' , COUNT(*) FROM audit_log
UNION ALL SELECT 'indisponibilites_professeurs', COUNT(*) FROM indisponibilites_professeurs
UNION ALL SELECT 'conflits_examens', COUNT(*) FROM conflits_examens
UNION ALL SELECT 'notifications', COUNT(*) FROM notifications;
-- ============================================
-- PARTIE 8: FONCTIONS PL/PGSQL POUR L'INTERFACE
-- ============================================

-- Fonction pour détecter les conflits
CREATE OR REPLACE FUNCTION detecter_conflits()
RETURNS TABLE(
    type_conflit VARCHAR(50),
    details TEXT,
    severite VARCHAR(20)
) AS $$
BEGIN
    -- Conflit étudiant: >1 examen/jour
    RETURN QUERY
    SELECT 
        'Étudiant >1 examen/jour' as type_conflit,
        'Étudiant ID: ' || i.etudiant_id || ' a ' || COUNT(DISTINCT e.id) || ' examens le ' || DATE(e.date_heure) as details,
        'CRITIQUE' as severite
    FROM inscriptions i
    JOIN examens e ON i.module_id = e.module_id
    WHERE e.statut IN ('Planifie', 'Confirme')
    GROUP BY i.etudiant_id, DATE(e.date_heure)
    HAVING COUNT(DISTINCT e.id) > 1;
    
    -- Conflit professeur: >3 examens/jour
    RETURN QUERY
    SELECT 
        'Professeur >3 examens/jour' as type_conflit,
        'Professeur ID: ' || e.professeur_id || ' a ' || COUNT(*) || ' examens le ' || DATE(e.date_heure) as details,
        'CRITIQUE' as severite
    FROM examens e
    WHERE e.statut IN ('Planifie', 'Confirme')
    GROUP BY e.professeur_id, DATE(e.date_heure)
    HAVING COUNT(*) > 3;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour générer planning optimisé
CREATE OR REPLACE FUNCTION generer_planning_optimise(
    p_date_debut DATE,
    p_date_fin DATE
)
RETURNS TABLE(
    module_id INT,
    module_nom VARCHAR,
    salle_id INT,
    salle_nom VARCHAR,
    professeur_id INT,
    professeur_nom VARCHAR,
    date_heure TIMESTAMP,
    duree_minutes INT,
    score_optimisation DECIMAL(5,2),
    capacite_utilisee DECIMAL(5,2)
) AS $$
DECLARE
    v_counter INT := 0;
BEGIN
    -- Données simulées pour le développement
    RETURN QUERY
    SELECT 
        m.id as module_id,
        m.nom as module_nom,
        l.id as salle_id,
        l.nom as salle_nom,
        p.id as professeur_id,
        p.nom || ' ' || p.prenom as professeur_nom,
        p_date_debut + (v_counter * INTERVAL '1 day') + INTERVAL '9 hours' as date_heure,
        120 as duree_minutes,
        85.5 as score_optimisation,
        75.0 as capacite_utilisee
    FROM modules m
    JOIN lieux_examen l ON l.id = 1
    JOIN professeurs p ON p.id = 1
    WHERE m.id IN (1, 2, 3, 4, 5)
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Vue pour les statistiques du département
CREATE OR REPLACE VIEW v_stats_departement AS
SELECT 
    d.id as departement_id,
    d.nom as departement_nom,
    (SELECT COUNT(*) FROM formations f WHERE f.departement_id = d.id) as nb_formations,
    (SELECT COUNT(*) FROM etudiants e 
     JOIN formations f ON e.formation_id = f.id 
     WHERE f.departement_id = d.id AND e.statut = 'Actif') as nb_etudiants,
    (SELECT COUNT(*) FROM professeurs p WHERE p.departement_id = d.id AND p.is_active = TRUE) as nb_professeurs,
    (SELECT COUNT(*) FROM modules m 
     JOIN formations f ON m.formation_id = f.id 
     WHERE f.departement_id = d.id) as nb_modules,
    (SELECT COUNT(*) FROM examens e 
     JOIN modules m ON e.module_id = m.id 
     JOIN formations f ON m.formation_id = f.id 
     WHERE f.departement_id = d.id AND e.statut IN ('Planifie', 'Confirme')) as nb_examens_planifies,
    (SELECT COUNT(*) FROM examens e 
     JOIN modules m ON e.module_id = m.id 
     JOIN formations f ON m.formation_id = f.id 
     WHERE f.departement_id = d.id AND e.statut = 'Termine') as nb_examens_termines,
    (SELECT AVG(capacite) FROM lieux_examen WHERE is_disponible = TRUE) as capacite_moyenne_salles,
    (SELECT MAX(date_heure) FROM examens e 
     JOIN modules m ON e.module_id = m.id 
     JOIN formations f ON m.formation_id = f.id 
     WHERE f.departement_id = d.id) as dernier_examen,
    (SELECT MIN(date_heure) FROM examens e 
     JOIN modules m ON e.module_id = m.id 
     JOIN formations f ON m.formation_id = f.id 
     WHERE f.departement_id = d.id AND e.date_heure > CURRENT_TIMESTAMP) as premier_examen
FROM departements d;
-- 1. أضف الحقل updated_at إذا كان مفقوداً
ALTER TABLE examens 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 2. أضف created_by إذا كان مفقوداً
ALTER TABLE examens 
ADD COLUMN IF NOT EXISTS created_by INT;

-- 3. أضف updated_by إذا كان مفقوداً
ALTER TABLE examens 
ADD COLUMN IF NOT EXISTS updated_by INT;
-- 4. صحح الدالة لتعمل بدون updated_at إذا لم يكن موجوداً
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id INT;
    v_ip_address VARCHAR(45);
BEGIN
    -- Récupérer l'ID utilisateur depuis la session
    BEGIN
        v_user_id := current_setting('app.user_id', TRUE)::INT;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;
    
    -- Récupérer l'adresse IP
    BEGIN
        v_ip_address := inet_client_addr()::VARCHAR;
    EXCEPTION WHEN OTHERS THEN
        v_ip_address := NULL;
    END;
    
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, changed_by, ip_address)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD)::jsonb, v_user_id, v_ip_address);
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        -- Version simplifiée sans vérification updated_at
        IF (OLD.* IS DISTINCT FROM NEW.*) THEN
            INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by, ip_address)
            VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', 
                    row_to_json(OLD)::jsonb, 
                    row_to_json(NEW)::jsonb, 
                    v_user_id, v_ip_address);
        END IF;
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO audit_log (table_name, record_id, action, new_values, changed_by, ip_address)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW)::jsonb, v_user_id, v_ip_address);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
-- ============================================
-- PARTIE 9 CORRIGÉE: DONNÉES POUR TEST ETUDIANT
-- ============================================

-- 1. تأكد أن الطالب 1 نشط (تخطي إذا كان بالفعل Actif)
UPDATE etudiants SET statut = 'Actif' WHERE id = 1 AND statut != 'Actif';

-- 2. احذف تسجيلات الطالب 1 القديمة وأعد التسجيل
DELETE FROM inscriptions WHERE etudiant_id = 1;

INSERT INTO inscriptions (etudiant_id, module_id, annee_academique, session, statut) VALUES
(1, 1, 2025, 'Principale', 'Inscrit'),
(1, 2, 2025, 'Principale', 'Inscrit'),
(1, 3, 2025, 'Principale', 'Inscrit'),
(1, 4, 2025, 'Principale', 'Inscrit'),
(1, 5, 2025, 'Principale', 'Inscrit');

-- 3. أنشئ امتحانات جديدة (لا تحذف القديمة إذا كنت تريد الاحتفاظ بها)
-- فقط أضف امتحانات جديدة دون حذف القديمة
INSERT INTO examens (module_id, professeur_id, salle_id, date_heure, duree_minutes, type_examen, statut) VALUES
-- امتحانات مستقبلية
(1, 1, 1, CURRENT_TIMESTAMP + INTERVAL '1 day' + INTERVAL '9 hours', 120, 'Final', 'Planifie'),
(2, 2, 2, CURRENT_TIMESTAMP + INTERVAL '2 days' + INTERVAL '14 hours', 90, 'Partiel', 'Planifie'),
(3, 3, 3, CURRENT_TIMESTAMP + INTERVAL '3 days' + INTERVAL '10 hours', 180, 'Final', 'Confirme'),
(4, 4, 4, CURRENT_TIMESTAMP + INTERVAL '7 days' + INTERVAL '8 hours', 120, 'Controle', 'Planifie'),
(5, 5, 5, CURRENT_TIMESTAMP + INTERVAL '10 days' + INTERVAL '13 hours', 90, 'Partiel', 'Planifie');

-- 4. أضف إشعارات (تخطي إذا كانت موجودة)
INSERT INTO notifications (user_id, user_role, type_notification, titre, contenu, priority)
SELECT 1, 'etudiant', 'Rappel', 'Examen Algorithmique dans 24h', 'N''oubliez pas votre carte d''étudiant', 1
WHERE NOT EXISTS (SELECT 1 FROM notifications WHERE titre = 'Examen Algorithmique dans 24h' AND user_id = 1);

INSERT INTO notifications (user_id, user_role, type_notification, titre, contenu, priority)
SELECT 1, 'etudiant', 'Information', 'Changement de salle', 'L''examen de BDD est déplacé en Amphi B', 2
WHERE NOT EXISTS (SELECT 1 FROM notifications WHERE titre = 'Changement de salle' AND user_id = 1);

-- 5. تحديث أسماء الوحدات (تطبيق فقط إذا كانت مختلفة)
UPDATE modules SET nom = 'Algorithmique Avancée' WHERE id = 1 AND nom != 'Algorithmique Avancée';
UPDATE modules SET nom = 'Bases de Données' WHERE id = 2 AND nom != 'Bases de Données';
UPDATE modules SET nom = 'Machine Learning' WHERE id = 3 AND nom != 'Machine Learning';
UPDATE modules SET nom = 'Analyse Mathématique' WHERE id = 4 AND nom != 'Analyse Mathématique';
UPDATE modules SET nom = 'Physique Quantique' WHERE id = 5 AND nom != 'Physique Quantique';

-- 6. التحقق النهائي
SELECT '✅ PARTIE 9 terminée avec succès!' as resultat;
SELECT '👤 Étudiant 1:' as info, nom || ' ' || prenom as valeur FROM etudiants WHERE id = 1
UNION ALL
SELECT '📚 Modules inscrits:', COUNT(*)::text FROM inscriptions WHERE etudiant_id = 1
UNION ALL
SELECT '📅 Examens à venir:', COUNT(*)::text FROM examens e 
JOIN inscriptions i ON e.module_id = i.module_id 
WHERE i.etudiant_id = 1 AND e.statut IN ('Planifie', 'Confirme') AND e.date_heure > CURRENT_TIMESTAMP;
-- Script SQL pour créer des données de test pour les professeurs

-- 1. Ajouter des examens futurs pour le professeur 1
INSERT INTO examens (module_id, professeur_id, salle_id, date_heure, duree_minutes, type_examen, statut)
SELECT 
    m.id,
    1, -- Professeur ID
    CASE 
        WHEN m.id % 8 = 0 THEN 1
        WHEN m.id % 8 = 1 THEN 2
        WHEN m.id % 8 = 2 THEN 3
        WHEN m.id % 8 = 3 THEN 4
        WHEN m.id % 8 = 4 THEN 5
        WHEN m.id % 8 = 5 THEN 6
        WHEN m.id % 8 = 6 THEN 7
        ELSE 8
    END as salle_id,
    CURRENT_TIMESTAMP + (ROW_NUMBER() OVER (ORDER BY m.id) || ' days')::INTERVAL + 
        CASE 
            WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 3 = 0 THEN INTERVAL '9 hours'
            WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 3 = 1 THEN INTERVAL '14 hours'
            ELSE INTERVAL '16 hours'
        END as date_heure,
    CASE 
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 4 = 0 THEN 90
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 4 = 1 THEN 120
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 4 = 2 THEN 180
        ELSE 150
    END as duree_minutes,
    CASE 
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 3 = 0 THEN 'Final'
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 3 = 1 THEN 'Partiel'
        ELSE 'Controle'
    END as type_examen,
    CASE 
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 5 = 0 THEN 'Planifie'
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 5 = 1 THEN 'Confirme'
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 5 = 2 THEN 'Termine'
        WHEN ROW_NUMBER() OVER (ORDER BY m.id) % 5 = 3 THEN 'Annule'
        ELSE 'Planifie'
    END as statut
FROM modules m
WHERE EXISTS (
    SELECT 1 FROM inscriptions i 
    WHERE i.module_id = m.id AND i.statut = 'Inscrit'
)
LIMIT 20;

-- 2. Mettre à jour des modules pour que le professeur 1 soit responsable
UPDATE modules 
SET responsable_id = 1
WHERE id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10);

-- 3. Ajouter des indisponibilités
INSERT INTO indisponibilites_professeurs (professeur_id, date_debut, date_fin, motif, details)
VALUES 
(1, CURRENT_TIMESTAMP + INTERVAL '5 days', CURRENT_TIMESTAMP + INTERVAL '7 days', 'Congé', 'Congé annuel'),
(1, CURRENT_TIMESTAMP + INTERVAL '15 days' + INTERVAL '9 hours', CURRENT_TIMESTAMP + INTERVAL '15 days' + INTERVAL '12 hours', 'Réunion', 'Réunion départementale'),
(1, CURRENT_TIMESTAMP + INTERVAL '20 days', CURRENT_TIMESTAMP + INTERVAL '22 days', 'Mission', 'Mission scientifique');

-- 4. Ajouter des notifications
INSERT INTO notifications (user_id, user_role, type_notification, titre, contenu, priority)
VALUES 
(1, 'professeur', 'Rappel', 'Examen dans 2 jours', 'Vous avez un examen de Algorithmique Avancée dans 2 jours', 2),
(1, 'professeur', 'Changement', 'Changement de salle', 'L''examen de BDD est déplacé en Amphi B', 3),
(1, 'professeur', 'Information', 'Nouveau module', 'Vous êtes maintenant responsable du module Machine Learning', 1),
(1, 'professeur', 'Alerte', 'Surcharge détectée', 'Vous avez 4 examens le 25/01/2025', 3);

-- 5. Vérification
SELECT '✅ Données de test créées avec succès!' as status;
SELECT '👨‍🏫 Professeur 1:' as info, nom || ' ' || prenom as valeur FROM professeurs WHERE id = 1;
SELECT '📅 Examens planifiés:' as info, COUNT(*) as valeur FROM examens WHERE professeur_id = 1 AND statut IN ('Planifie', 'Confirme') AND date_heure > CURRENT_TIMESTAMP;
SELECT '📚 Modules responsables:' as info, COUNT(*) as valeur FROM modules WHERE responsable_id = 1;
-- Ajouter cette table si elle n'existe pas
CREATE TABLE IF NOT EXISTS demandes_modification_examens (
    id SERIAL PRIMARY KEY,
    etudiant_id INT NOT NULL REFERENCES etudiants(id) ON DELETE CASCADE,
    examen_id INT NOT NULL REFERENCES examens(id) ON DELETE CASCADE,
    type_demande VARCHAR(50) NOT NULL CHECK (type_demande IN ('REPORT', 'CHANGEMENT_SALLE', 'AUTRE')),
    date_demande TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    motif TEXT NOT NULL,
    date_souhaitee TIMESTAMP,
    salle_souhaitee INT REFERENCES lieux_examen(id),
    statut VARCHAR(20) DEFAULT 'EN_ATTENTE' CHECK (statut IN ('EN_ATTENTE', 'ACCEPTEE', 'REFUSEE', 'TRAITEE')),
    reponse_administration TEXT,
    date_reponse TIMESTAMP,
    traite_par INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(etudiant_id, examen_id, type_demande) -- Une demande par type par examen
);

-- Index pour optimiser les recherches
CREATE INDEX IF NOT EXISTS idx_demandes_etudiant ON demandes_modification_examens(etudiant_id, statut);
CREATE INDEX IF NOT EXISTS idx_demandes_examen ON demandes_modification_examens(examen_id);
CREATE INDEX IF NOT EXISTS idx_demandes_statut ON demandes_modification_examens(statut, date_demande DESC);

-- Trigger pour updated_at
CREATE TRIGGER trg_update_demandes_updated_at
BEFORE UPDATE ON demandes_modification_examens
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Table pour les substitutions/remplacements
CREATE TABLE IF NOT EXISTS substitutions_remplacement (
    id SERIAL PRIMARY KEY,
    professeur_origine_id INT NOT NULL REFERENCES professeurs(id) ON DELETE CASCADE,
    professeur_remplacant_id INT REFERENCES professeurs(id) ON DELETE SET NULL,
    examen_id INT NOT NULL REFERENCES examens(id) ON DELETE CASCADE,
    motif TEXT NOT NULL,
    motif_refus TEXT,
    statut VARCHAR(20) DEFAULT 'EN_ATTENTE' CHECK (statut IN ('EN_ATTENTE', 'ACCEPTE', 'REFUSE', 'ANNULE')),
    date_demande TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_traitement TIMESTAMP,
    traite_par INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(examen_id, professeur_origine_id) -- Une demande par examen par professeur
);

-- Table pour les préférences des professeurs
CREATE TABLE IF NOT EXISTS preferences_professeurs (
    id SERIAL PRIMARY KEY,
    professeur_id INT UNIQUE NOT NULL REFERENCES professeurs(id) ON DELETE CASCADE,
    max_examens_jour INT DEFAULT 3 CHECK (max_examens_jour BETWEEN 1 AND 5),
    heure_debut_pref TIME DEFAULT '08:30',
    heure_fin_pref TIME DEFAULT '17:30',
    pause_minimale INT DEFAULT 60 CHECK (pause_minimale BETWEEN 15 AND 180),
    batiments_preferes TEXT[],
    types_salles_preferes TEXT[],
    capacite_minimale INT DEFAULT 30,
    notifications_email BOOLEAN DEFAULT TRUE,
    notifications_sms BOOLEAN DEFAULT FALSE,
    rappel_examen_heures INT DEFAULT 24 CHECK (rappel_examen_heures BETWEEN 1 AND 48),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table pour les présences aux examens (feuilles d'émargement)
CREATE TABLE IF NOT EXISTS presences_examens (
    id SERIAL PRIMARY KEY,
    examen_id INT NOT NULL REFERENCES examens(id) ON DELETE CASCADE,
    etudiant_id INT NOT NULL REFERENCES etudiants(id) ON DELETE CASCADE,
    present BOOLEAN DEFAULT FALSE,
    heure_arrivee TIMESTAMP,
    heure_depart TIMESTAMP,
    observations TEXT,
    valide_par INT REFERENCES professeurs(id),
    valide_le TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(examen_id, etudiant_id)
);

-- Index pour optimiser
CREATE INDEX IF NOT EXISTS idx_substitutions_prof ON substitutions_remplacement(professeur_origine_id, statut);
CREATE INDEX IF NOT EXISTS idx_substitutions_examen ON substitutions_remplacement(examen_id);
CREATE INDEX IF NOT EXISTS idx_presences_examen ON presences_examens(examen_id, etudiant_id);
CREATE INDEX IF NOT EXISTS idx_preferences_prof ON preferences_professeurs(professeur_id);



-- ============================================
-- دوال SQL لدعم الخوارزمية
-- ============================================

-- دالة لتحميل البيانات بسرعة
CREATE OR REPLACE FUNCTION load_optimization_data(
    p_start_date TIMESTAMP,
    p_end_date TIMESTAMP,
    p_department_id INT DEFAULT NULL
)
RETURNS TABLE (
    module_id INT,
    module_code VARCHAR,
    module_name VARCHAR,
    credits INT,
    formation_id INT,
    formation_name VARCHAR,
    departement_id INT,
    professor_id INT,
    student_count BIGINT,
    student_ids INT[],
    duration_minutes INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.code,
        m.nom,
        m.credits,
        m.formation_id,
        f.nom,
        f.departement_id,
        COALESCE(m.responsable_id, 
            (SELECT id FROM professeurs 
             WHERE departement_id = f.departement_id 
             LIMIT 1)),
        COUNT(DISTINCT i.etudiant_id)::BIGINT,
        ARRAY_AGG(DISTINCT i.etudiant_id),
        CASE 
            WHEN m.credits >= 6 THEN 180
            WHEN m.credits >= 4 THEN 120
            ELSE 90
        END
    FROM modules m
    JOIN formations f ON m.formation_id = f.id
    JOIN inscriptions i ON m.id = i.module_id
    WHERE i.statut = 'Inscrit'
        AND i.annee_academique = EXTRACT(YEAR FROM CURRENT_DATE)
        AND NOT EXISTS (
            SELECT 1 FROM examens e 
            WHERE e.module_id = m.id 
            AND e.date_heure BETWEEN p_start_date AND p_end_date
        )
        AND (p_department_id IS NULL OR f.departement_id = p_department_id)
    GROUP BY m.id, m.code, m.nom, m.credits, m.formation_id, 
             f.nom, f.departement_id, m.responsable_id;
END;
$$ LANGUAGE plpgsql;

-- دالة للتحقق السريع من التعارضات
CREATE OR REPLACE FUNCTION quick_conflict_check(
    p_student_ids INT[],
    p_professor_id INT,
    p_room_id INT,
    p_exam_date TIMESTAMP,
    p_duration_minutes INT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_has_conflict BOOLEAN := FALSE;
BEGIN
    -- 1. التحقق من تعارض الطلاب
    SELECT EXISTS(
        SELECT 1 FROM examens e
        JOIN inscriptions i ON e.module_id = i.module_id
        WHERE i.etudiant_id = ANY(p_student_ids)
            AND DATE(e.date_heure) = DATE(p_exam_date)
            AND e.statut IN ('Planifie', 'Confirme')
    ) INTO v_has_conflict;
    
    IF v_has_conflict THEN
        RETURN TRUE;
    END IF;
    
    -- 2. التحقق من تعارض الأستاذ
    SELECT EXISTS(
        SELECT 1 FROM examens e
        WHERE e.professeur_id = p_professor_id
            AND DATE(e.date_heure) = DATE(p_exam_date)
            AND e.statut IN ('Planifie', 'Confirme')
        GROUP BY DATE(e.date_heure)
        HAVING COUNT(*) >= 3
    ) INTO v_has_conflict;
    
    IF v_has_conflict THEN
        RETURN TRUE;
    END IF;
    
    -- 3. التحقق من تعارض القاعة
    SELECT EXISTS(
        SELECT 1 FROM examens e
        WHERE e.salle_id = p_room_id
            AND e.date_heure < p_exam_date + (p_duration_minutes || ' minutes')::INTERVAL
            AND e.date_heure + (e.duree_minutes || ' minutes')::INTERVAL > p_exam_date
            AND e.statut IN ('Planifie', 'Confirme')
    ) INTO v_has_conflict;
    
    RETURN v_has_conflict;
END;
$$ LANGUAGE plpgsql;

-- دالة لحساب درجة الأولوية للامتحان
CREATE OR REPLACE FUNCTION calculate_exam_priority(
    p_student_count INT,
    p_credits INT,
    p_formation_name VARCHAR
)
RETURNS DECIMAL(5,2) AS $$
DECLARE
    v_score DECIMAL(5,2) := 0;
BEGIN
    -- 1. عدد الطلاب (40%)
    v_score := v_score + (p_student_count::DECIMAL / 100) * 40;
    
    -- 2. عدد الاعتمادات (30%)
    v_score := v_score + (p_credits::DECIMAL / 12) * 30;
    
    -- 3. تعقيد المادة (20%)
    IF p_credits >= 6 THEN
        v_score := v_score + 20;
    ELSIF p_credits >= 4 THEN
        v_score := v_score + 15;
    ELSE
        v_score := v_score + 10;
    END IF;
    
    -- 4. قسم المادة (10%)
    IF p_formation_name LIKE '%INFO%' THEN
        v_score := v_score + 10;
    END IF;
    
    RETURN v_score;
END;
$$ LANGUAGE plpgsql;

-- دالة لحفظ الجدول المحسن
CREATE OR REPLACE FUNCTION save_optimized_schedule(
    p_schedule JSONB
)
RETURNS INTEGER AS $$
DECLARE
    v_exam_record RECORD;
    v_inserted_count INTEGER := 0;
BEGIN
    -- تحويل JSON إلى سجلات وإدراجها
    FOR v_exam_record IN 
        SELECT * FROM jsonb_to_recordset(p_schedule) AS x(
            module_id INT,
            professor_id INT,
            room_id INT,
            exam_time TIMESTAMP,
            duration_minutes INT,
            student_count INT
        )
    LOOP
        INSERT INTO examens (
            module_id,
            professeur_id,
            salle_id,
            date_heure,
            duree_minutes,
            type_examen,
            statut,
            max_etudiants,
            created_at
        ) VALUES (
            v_exam_record.module_id,
            v_exam_record.professor_id,
            v_exam_record.room_id,
            v_exam_record.exam_time,
            v_exam_record.duration_minutes,
            'Final',
            'Planifie',
            v_exam_record.student_count,
            CURRENT_TIMESTAMP
        );
        
        v_inserted_count := v_inserted_count + 1;
    END LOOP;
    
    RETURN v_inserted_count;
END;
$$ LANGUAGE plpgsql;
-- 1. Mettre à jour tous les statuts pour enlever les accents
UPDATE examens SET statut = 'Planifie' WHERE statut = 'Planifié';
UPDATE examens SET statut = 'Confirme' WHERE statut = 'Confirmé';
UPDATE examens SET statut = 'Termine' WHERE statut = 'Terminé';

-- 2. Corriger les contraintes CHECK
ALTER TABLE examens 
DROP CONSTRAINT IF EXISTS examens_statut_check;

ALTER TABLE examens 
ADD CONSTRAINT examens_statut_check 
CHECK (statut IN ('Planifie', 'Confirme', 'Annule', 'Termine'));

-- 3. Même chose pour les inscriptions
UPDATE inscriptions SET statut = 'Inscrit' WHERE statut = 'Inscrit' OR statut = 'Inscrit';
UPDATE inscriptions SET statut = 'Valide' WHERE statut = 'Validé';
UPDATE inscriptions SET statut = 'Echoue' WHERE statut = 'Échoué';

ALTER TABLE inscriptions 
DROP CONSTRAINT IF EXISTS inscriptions_statut_check;

ALTER TABLE inscriptions 
ADD CONSTRAINT inscriptions_statut_check 
CHECK (statut IN ('Inscrit', 'Valide', 'Echoue', 'Abandonne'));

-- Vue 1 : Planning des examens
CREATE OR REPLACE VIEW v_planning_examens AS
SELECT 
    e.id,
    e.uuid,
    m.code as module_code,
    m.nom as module_nom,
    f.nom as formation_nom,
    d.nom as departement_nom,
    p.nom || ' ' || p.prenom as professeur_nom,
    l.nom as salle_nom,
    l.type as salle_type,
    l.capacite,
    e.date_heure,
    e.duree_minutes,
    e.type_examen,
    e.statut,
    COUNT(DISTINCT i.etudiant_id) as etudiants_inscrits
FROM examens e
JOIN modules m ON e.module_id = m.id
JOIN formations f ON m.formation_id = f.id
JOIN departements d ON f.departement_id = d.id
JOIN professeurs p ON e.professeur_id = p.id
JOIN lieux_examen l ON e.salle_id = l.id
LEFT JOIN inscriptions i ON e.module_id = i.module_id 
    AND i.statut = 'Inscrit'
GROUP BY e.id, e.uuid, m.code, m.nom, f.nom, d.nom, 
         p.nom, p.prenom, l.nom, l.type, l.capacite, 
         e.date_heure, e.duree_minutes, e.type_examen, e.statut;

-- Vue 2 : Occupation des salles
CREATE OR REPLACE VIEW v_occupation_salles AS
SELECT 
    l.id,
    l.nom,
    l.type,
    l.capacite,
    COUNT(e.id) as nb_examens_planifies,
    COALESCE(AVG(
        (SELECT COUNT(*) 
         FROM inscriptions i 
         WHERE i.module_id = e.module_id 
         AND i.statut = 'Inscrit')::FLOAT / l.capacite * 100
    ), 0) as taux_occupation_moyen
FROM lieux_examen l
LEFT JOIN examens e ON l.id = e.salle_id 
    AND e.statut IN ('Planifie', 'Confirme')
    AND e.date_heure >= CURRENT_DATE
GROUP BY l.id, l.nom, l.type, l.capacite;

-- Index essentiels
CREATE INDEX IF NOT EXISTS idx_examens_date_statut 
ON examens(date_heure, statut);

CREATE INDEX IF NOT EXISTS idx_inscriptions_module_statut 
ON inscriptions(module_id, statut);

CREATE INDEX IF NOT EXISTS idx_etudiants_formation 
ON etudiants(formation_id, statut);

-- Index pour les conflits
CREATE INDEX IF NOT EXISTS idx_examens_prof_date 
ON examens(professeur_id, date_heure);

CREATE INDEX IF NOT EXISTS idx_inscriptions_etudiant_module 
ON inscriptions(etudiant_id, module_id);

-- Supprimer l'ancienne fonction
DROP FUNCTION IF EXISTS detecter_conflits();

-- Recréer avec les bons types
CREATE OR REPLACE FUNCTION detecter_conflits()
RETURNS TABLE(
    type_conflit VARCHAR(50),
    details TEXT,
    severite VARCHAR(20)
) AS $$
BEGIN
    -- Conflit étudiant: >1 examen/jour
    RETURN QUERY
    SELECT 
        'Étudiant >1 examen/jour'::VARCHAR(50) as type_conflit,
        ('Étudiant ID: ' || i.etudiant_id || ' a ' || COUNT(DISTINCT e.id) || ' examens le ' || DATE(e.date_heure))::TEXT as details,
        'CRITIQUE'::VARCHAR(20) as severite
    FROM inscriptions i
    JOIN examens e ON i.module_id = e.module_id
    WHERE e.statut IN ('Planifie', 'Confirme')
    GROUP BY i.etudiant_id, DATE(e.date_heure)
    HAVING COUNT(DISTINCT e.id) > 1;
    
    -- Conflit professeur: >3 examens/jour
    RETURN QUERY
    SELECT 
        'Professeur >3 examens/jour'::VARCHAR(50) as type_conflit,
        ('Professeur ID: ' || e.professeur_id || ' a ' || COUNT(*) || ' examens le ' || DATE(e.date_heure))::TEXT as details,
        'CRITIQUE'::VARCHAR(20) as severite
    FROM examens e
    WHERE e.statut IN ('Planifie', 'Confirme')
    GROUP BY e.professeur_id, DATE(e.date_heure)
    HAVING COUNT(*) > 3;
    
    -- Conflit salle: chevauchement
    RETURN QUERY
    SELECT 
        'Chevauchement salle'::VARCHAR(50) as type_conflit,
        ('Salle ID: ' || e1.salle_id || ' - Examens ' || e1.id || ' et ' || e2.id || ' se chevauchent')::TEXT as details,
        'ÉLEVÉ'::VARCHAR(20) as severite
    FROM examens e1
    JOIN examens e2 ON e1.salle_id = e2.salle_id
    WHERE e1.id < e2.id
        AND e1.statut IN ('Planifie', 'Confirme')
        AND e2.statut IN ('Planifie', 'Confirme')
        AND e1.date_heure < e2.date_heure + (e2.duree_minutes || ' minutes')::INTERVAL
        AND e2.date_heure < e1.date_heure + (e1.duree_minutes || ' minutes')::INTERVAL;
    
    -- Conflit capacité: trop d'étudiants
    RETURN QUERY
    SELECT 
        'Dépassement capacité'::VARCHAR(50) as type_conflit,
        ('Examen ID: ' || e.id || ' - ' || COUNT(i.etudiant_id) || ' étudiants pour ' || l.capacite || ' places')::TEXT as details,
        'MOYEN'::VARCHAR(20) as severite
    FROM examens e
    JOIN lieux_examen l ON e.salle_id = l.id
    JOIN inscriptions i ON e.module_id = i.module_id
    WHERE e.statut IN ('Planifie', 'Confirme')
        AND i.statut = 'Inscrit'
    GROUP BY e.id, l.capacite
    HAVING COUNT(i.etudiant_id) > l.capacite;
END;
$$ LANGUAGE plpgsql;
-- Version simplifiée pour test
DROP FUNCTION IF EXISTS generer_planning_optimise(date, date);

CREATE OR REPLACE FUNCTION generer_planning_optimise(
    p_date_debut DATE,
    p_date_fin DATE
)
RETURNS TABLE(
    module_id INT,
    module_nom VARCHAR,
    module_code VARCHAR,
    formation_nom VARCHAR,
    salle_id INT,
    salle_nom VARCHAR,
    salle_capacite INT,
    professeur_id INT,
    professeur_nom VARCHAR,
    date_heure TIMESTAMP,
    duree_minutes INT,
    nb_etudiants INT,
    score_optimisation DECIMAL(5,2),
    capacite_utilisee DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id::INT,
        m.nom::VARCHAR,
        m.code::VARCHAR,
        f.nom::VARCHAR,
        l.id::INT,
        l.nom::VARCHAR,
        l.capacite::INT,
        p.id::INT,
        (p.nom || ' ' || p.prenom)::VARCHAR,
        (p_date_debut + (ROW_NUMBER() OVER () * INTERVAL '1 day') + INTERVAL '8 hours')::TIMESTAMP,
        120::INT,
        COUNT(i.etudiant_id)::INT,
        75.50::DECIMAL(5,2),
        ROUND((COUNT(i.etudiant_id)::DECIMAL / l.capacite) * 100, 2)::DECIMAL(5,2)
    FROM modules m
    JOIN formations f ON m.formation_id = f.id
    JOIN inscriptions i ON m.id = i.module_id AND i.statut = 'Inscrit'
    CROSS JOIN lieux_examen l
    CROSS JOIN professeurs p
    WHERE l.is_disponible = TRUE
        AND p.is_active = TRUE
        AND l.id = (SELECT id FROM lieux_examen WHERE is_disponible = TRUE ORDER BY capacite DESC LIMIT 1)
        AND p.id = (SELECT id FROM professeurs WHERE is_active = TRUE AND departement_id = f.departement_id LIMIT 1)
        AND NOT EXISTS (
            SELECT 1 FROM examens e 
            WHERE e.module_id = m.id 
            AND e.date_heure BETWEEN p_date_debut AND p_date_fin
        )
    GROUP BY m.id, m.nom, m.code, f.nom, l.id, l.nom, l.capacite, p.id, p.nom, p.prenom
    HAVING COUNT(i.etudiant_id) > 0
    ORDER BY COUNT(i.etudiant_id) DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;