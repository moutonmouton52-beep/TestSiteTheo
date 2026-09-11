"""Peuple la base avec les donnees de l'enonce (Exercice 2) + comptes de demo.

Les managers (Dupont, Jones, Holmes, Lupin) sont enregistres comme des employes
a part entiere : l'instance de l'enonce ne donne que leurs noms, on leur attribue
donc un idEmp (E2xx) et un salaire pour pouvoir les referencer par cle etrangere.

Reexecutable librement : recree les tables a chaque lancement.
Usage : python seed.py
"""
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "instance" / "gestion_projet.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

# Comptes de demo : mot de passe en clair ici, hashe avant insertion dans
# Utilisateur (la table UtilisateurDemoVulnerable les garde en clair a dessein).
COMPTES = [
    ("dupont", "dupont123", "E200"),
    ("holmes", "holmes123", "E202"),
    ("durand", "durand123", "E101"),
    ("adam", "adam123", "E105"),
    ("rivera", "rivera123", "E110"),
]


def seed():
    DB_PATH.parent.mkdir(exist_ok=True)

    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    db.execute("PRAGMA foreign_keys = ON")

    # 1. Departements sans manager : Employe n'existe pas encore.
    db.executemany(
        "INSERT INTO Departement (deptEmp, mgrEmp) VALUES (?, NULL)",
        [("10",), ("12",)],
    )

    # 2. Employes, managers compris.
    db.executemany(
        "INSERT INTO Employe (idEmp, nomEmp, salEmp, deptEmp) VALUES (?, ?, ?, ?)",
        [
            ("E101", "Durand", 45000, "10"),
            ("E105", "Adam", 43000, "12"),
            ("E110", "Rivera", 41000, "10"),
            ("E200", "Dupont", 60000, "10"),
            ("E201", "Jones", 62000, "12"),
            ("E202", "Holmes", 58000, "10"),
            ("E203", "Lupin", 57000, "12"),
        ],
    )

    # 3. On peut maintenant rattacher chaque departement a son manager.
    db.executemany(
        "UPDATE Departement SET mgrEmp = ? WHERE deptEmp = ?",
        [("E202", "10"), ("E203", "12")],
    )

    db.executemany(
        "INSERT INTO Projet (nomProj, mgrProj, budget, dateDebut) VALUES (?, ?, ?, ?)",
        [
            ("ILO", "E200", 100000, "2011-11-15"),
            ("MAXI", "E201", 200000, "2012-01-03"),
        ],
    )

    db.executemany(
        "INSERT INTO PerformanceEmp (nomProj, idEmp, heures, evalEmp) VALUES (?, ?, ?, ?)",
        [
            ("ILO", "E101", 25, 9),
            ("ILO", "E105", 39, None),
            ("ILO", "E110", 10, 8),
            ("MAXI", "E110", 29, None),
        ],
    )

    db.executemany(
        "INSERT INTO Utilisateur (username, motDePasseHash, idEmp) VALUES (?, ?, ?)",
        [(u, generate_password_hash(p), id_emp) for u, p, id_emp in COMPTES],
    )

    # Les memes comptes stockes en clair, pour la comparaison pedagogique.
    db.executemany(
        "INSERT INTO UtilisateurDemoVulnerable (username, motDePasse) VALUES (?, ?)",
        [(u, p) for u, p, _ in COMPTES],
    )

    db.commit()
    db.close()

    print(f"Base initialisee et peuplee : {DB_PATH}")
    print("Comptes (mot de passe hashe dans Utilisateur) :")
    print("  dupont / dupont123  -> E200, manager du projet ILO")
    print("  holmes / holmes123  -> E202, manager du departement 10")
    print("  durand / durand123  -> E101")
    print("  adam   / adam123    -> E105")
    print("  rivera / rivera123  -> E110")


if __name__ == "__main__":
    seed()
