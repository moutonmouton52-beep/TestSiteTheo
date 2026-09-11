"""
!!! DEMO PEDAGOGIQUE - A NE JAMAIS EXPOSER PUBLIQUEMENT !!!

Ce module illustre plusieurs mauvaises pratiques, a comparer avec leur
equivalent securise dans app.py :

  - /demo-vulnerable/recherche        <-> /recherche          (injection SQL)
  - /demo-vulnerable/login            <-> /login               (mot de passe en clair + injection SQL)
  - /demo-vulnerable/mots-de-passe    <-> /login               (stockage en clair vs hachage)
  - /demo-vulnerable/projects/<nom>   <-> /projects/<nom>      (absence de controle d'acces)

Ce blueprint n'est enregistre par app.py QUE si la variable d'environnement
ENABLE_VULN_DEMO=1 est positionnee. Sans elle, ces routes n'existent pas (404).

Les comptes affiches sont ceux de la demo, sans valeur en dehors de ce TD.
"""
import sqlite3

from flask import Blueprint, current_app, g, render_template, request

bp = Blueprint("demo_vulnerable", __name__, url_prefix="/demo-vulnerable")


def get_raw_db():
    if "vuln_db" not in g:
        g.vuln_db = sqlite3.connect(current_app.config["DATABASE"])
        g.vuln_db.row_factory = sqlite3.Row
    return g.vuln_db


@bp.teardown_app_request
def close_raw_db(exc):
    conn = g.pop("vuln_db", None)
    if conn is not None:
        conn.close()


@bp.route("/")
def index():
    return render_template("demo_vulnerable/index.html")


@bp.route("/recherche")
def recherche():
    """FAILLE : la valeur saisie est concatenee directement dans la requete SQL.
    Comparer avec /recherche (requete parametree).
    Essayer par exemple : q = x' OR '1'='1' --  (avec l'espace final)
    """
    q = request.args.get("q", "")
    conn = get_raw_db()
    sql = "SELECT idEmp, nomEmp FROM Employe WHERE nomEmp LIKE '%" + q + "%'"
    results = []
    error = None
    if q:
        try:
            results = conn.execute(sql).fetchall()
        except sqlite3.Error as e:
            error = str(e)
    return render_template(
        "demo_vulnerable/recherche.html", q=q, results=results, sql=sql, error=error
    )


@bp.route("/login", methods=("GET", "POST"))
def login():
    """FAILLES : mot de passe compare en clair + requete SQL concatenee.
    Comparer avec /login (hachage + requete parametree).
    Essayer : utilisateur = admin' OR '1'='1' --  (avec l'espace final), mot de passe = n'importe quoi.
    """
    result = None
    sql = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_raw_db()
        sql = (
            "SELECT * FROM UtilisateurDemoVulnerable WHERE username = '"
            + username
            + "' AND motDePasse = '"
            + password
            + "'"
        )
        try:
            row = conn.execute(sql).fetchone()
            result = (
                f"Connexion reussie en tant que '{row['username']}'"
                if row
                else "Echec de connexion."
            )
        except sqlite3.Error as e:
            result = f"Erreur SQL : {e}"
    return render_template("demo_vulnerable/login.html", result=result, sql=sql)


@bp.route("/mots-de-passe")
def mots_de_passe():
    """Ce que lit un attaquant qui met la main sur la base, selon le stockage.

    A gauche : les mots de passe en clair, exploitables immediatement (et
    reutilisables sur les autres services de la personne). A droite : des
    empreintes salees, qu'il faut casser une par une.
    """
    conn = get_raw_db()
    en_clair = conn.execute(
        "SELECT username, motDePasse FROM UtilisateurDemoVulnerable ORDER BY username"
    ).fetchall()
    haches = conn.execute(
        "SELECT username, motDePasseHash FROM Utilisateur ORDER BY username"
    ).fetchall()
    return render_template(
        "demo_vulnerable/mots_de_passe.html", en_clair=en_clair, haches=haches
    )


@bp.route("/projects/<nom_proj>")
def project_detail(nom_proj):
    """FAILLE : aucune verification de session ni de role. Toute personne
    connaissant l'URL voit salaires et evaluations, sans etre authentifiee.
    Comparer avec /projects/<nom_proj>, qui exige une connexion et filtre les
    colonnes sensibles selon le role.
    """
    conn = get_raw_db()
    projet = conn.execute(
        """
        SELECT p.nomProj, p.budget, p.dateDebut, m.nomEmp AS mgrNom
        FROM Projet p JOIN Employe m ON m.idEmp = p.mgrProj
        WHERE p.nomProj = ?
        """,
        (nom_proj,),
    ).fetchone()
    assignments = []
    if projet is not None:
        assignments = conn.execute(
            """
            SELECT e.idEmp, e.nomEmp, e.salEmp, p.heures, p.evalEmp
            FROM PerformanceEmp p
            JOIN Employe e ON e.idEmp = p.idEmp
            WHERE p.nomProj = ?
            ORDER BY e.nomEmp
            """,
            (nom_proj,),
        ).fetchall()
    return render_template(
        "demo_vulnerable/project_detail.html",
        projet=projet,
        assignments=assignments,
        nom_proj=nom_proj,
    )
