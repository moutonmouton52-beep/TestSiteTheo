-- Les DROP se font sans contrainte : Departement et Employe se referencent
-- mutuellement (un departement a un manager, qui est lui-meme un employe).
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS UtilisateurDemoVulnerable;
DROP TABLE IF EXISTS Utilisateur;
DROP TABLE IF EXISTS PerformanceEmp;
DROP TABLE IF EXISTS Employe;
DROP TABLE IF EXISTS Projet;
DROP TABLE IF EXISTS Departement;

-- Un manager EST un employe : mgrEmp et mgrProj sont des cles etrangeres vers
-- Employe(idEmp), et non des noms. L'enonce precise que les noms des employes
-- et des managers ne sont pas uniques : un nom ne peut donc pas servir de cle.
CREATE TABLE Departement (
    deptEmp TEXT PRIMARY KEY,
    -- NULL autorise : un departement peut etre sans manager, et cela permet de
    -- rompre le cycle Departement <-> Employe au moment du chargement.
    mgrEmp  TEXT REFERENCES Employe(idEmp)
);

CREATE TABLE Employe (
    idEmp   TEXT PRIMARY KEY,
    nomEmp  TEXT NOT NULL,
    salEmp  INTEGER NOT NULL,
    deptEmp TEXT NOT NULL REFERENCES Departement(deptEmp)
);

CREATE TABLE Projet (
    nomProj   TEXT PRIMARY KEY,
    mgrProj   TEXT NOT NULL REFERENCES Employe(idEmp),
    budget    INTEGER NOT NULL,
    dateDebut TEXT NOT NULL
);

CREATE TABLE PerformanceEmp (
    nomProj TEXT NOT NULL REFERENCES Projet(nomProj),
    idEmp   TEXT NOT NULL REFERENCES Employe(idEmp),
    heures  INTEGER NOT NULL,
    evalEmp INTEGER,
    PRIMARY KEY (nomProj, idEmp)
);

-- Authentification (absente des dependances fonctionnelles d'origine, ajoutee
-- pour la demo). Chaque compte correspond a un employe ; le fait d'etre manager
-- n'est PAS stocke ici, il se deduit de la base (Projet.mgrProj / Departement.mgrEmp)
-- pour eviter de dupliquer une information deja presente.
CREATE TABLE Utilisateur (
    idUtilisateur  INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    motDePasseHash TEXT NOT NULL,
    idEmp          TEXT NOT NULL REFERENCES Employe(idEmp)
);

-- Table isolee utilisee UNIQUEMENT par la demo pedagogique (demo_vulnerable.py) :
-- les memes comptes, stockes en clair, pour montrer ce que lit un attaquant en
-- cas de fuite de la base. Le code de l'app ne s'authentifie jamais dessus.
CREATE TABLE UtilisateurDemoVulnerable (
    username   TEXT PRIMARY KEY,
    motDePasse TEXT NOT NULL
);
