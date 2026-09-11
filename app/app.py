import os
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import db

BASE_DIR = Path(__file__).parent


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me"),
        DATABASE=str(BASE_DIR / "instance" / "gestion_projet.db"),
        ENABLE_VULN_DEMO=os.environ.get("ENABLE_VULN_DEMO") == "1",
    )
    Path(app.instance_path).mkdir(exist_ok=True)

    db.init_app(app)

    @app.before_request
    def load_logged_in_user():
        g.user = charger_utilisateur(session.get("user_id"))

    @app.context_processor
    def inject_vuln_flag():
        return {"vuln_demo_enabled": app.config["ENABLE_VULN_DEMO"]}

    register_routes(app)

    if app.config["ENABLE_VULN_DEMO"]:
        from demo_vulnerable import bp as vuln_bp

        app.register_blueprint(vuln_bp)

    return app


def role_de(conn, id_emp):
    """Un employe est manager s'il dirige au moins un projet ou un departement.

    Cette information n'est pas stockee dans Utilisateur : elle se deduit des
    cles etrangeres Projet.mgrProj et Departement.mgrEmp, seule source de verite.
    """
    row = conn.execute(
        """
        SELECT EXISTS(SELECT 1 FROM Projet      WHERE mgrProj = :id)
            OR EXISTS(SELECT 1 FROM Departement WHERE mgrEmp  = :id) AS est_manager
        """,
        {"id": id_emp},
    ).fetchone()
    return "manager" if row["est_manager"] else "employe"


def charger_utilisateur(user_id):
    """Relit le compte et ses droits a chaque requete plutot que de les figer
    dans la session : un changement de manager en base prend effet immediatement.
    """
    if user_id is None:
        return None
    conn = db.get_db()
    row = conn.execute(
        """
        SELECT u.idUtilisateur, u.username, u.idEmp, e.nomEmp
        FROM Utilisateur u JOIN Employe e ON e.idEmp = u.idEmp
        WHERE u.idUtilisateur = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        session.clear()
        return None
    return {
        "id": row["idUtilisateur"],
        "username": row["username"],
        "idEmp": row["idEmp"],
        "nomEmp": row["nomEmp"],
        "role": role_de(conn, row["idEmp"]),
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def manager_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        if g.user["role"] != "manager":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("dashboard") if g.user else url_for("login"))

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            conn = db.get_db()
            row = conn.execute(
                "SELECT idUtilisateur, motDePasseHash FROM Utilisateur WHERE username = ?",
                (username,),
            ).fetchone()

            # Le mot de passe n'est jamais stocke ni compare en clair : on
            # rejoue le hachage sur la saisie et on compare les empreintes.
            if row is None or not check_password_hash(row["motDePasseHash"], password):
                flash("Identifiants invalides.")
            else:
                session.clear()
                session["user_id"] = row["idUtilisateur"]
                return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        conn = db.get_db()
        nb_projets = conn.execute("SELECT COUNT(*) AS n FROM Projet").fetchone()["n"]
        nb_employes = conn.execute("SELECT COUNT(*) AS n FROM Employe").fetchone()["n"]
        return render_template("dashboard.html", nb_projets=nb_projets, nb_employes=nb_employes)

    @app.route("/projects")
    @login_required
    def projects():
        conn = db.get_db()
        rows = conn.execute(
            """
            SELECT p.nomProj, p.budget, p.dateDebut, m.nomEmp AS mgrNom, m.idEmp AS mgrId
            FROM Projet p JOIN Employe m ON m.idEmp = p.mgrProj
            ORDER BY p.nomProj
            """
        ).fetchall()
        return render_template("projects.html", projects=rows)

    @app.route("/projects/<nom_proj>")
    @login_required
    def project_detail(nom_proj):
        conn = db.get_db()
        projet = conn.execute(
            """
            SELECT p.nomProj, p.budget, p.dateDebut, m.nomEmp AS mgrNom, m.idEmp AS mgrId
            FROM Projet p JOIN Employe m ON m.idEmp = p.mgrProj
            WHERE p.nomProj = ?
            """,
            (nom_proj,),
        ).fetchone()
        if projet is None:
            abort(404)

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

        # Un manager voit tout ; un employe ne voit que sa propre evaluation,
        # jamais le salaire ni l'evaluation de ses collegues.
        return render_template(
            "project_detail.html",
            projet=projet,
            assignments=assignments,
            can_see_all=g.user["role"] == "manager",
            current_id_emp=g.user["idEmp"],
        )

    @app.route("/employees")
    @manager_required
    def employees():
        conn = db.get_db()
        rows = conn.execute(
            """
            SELECT e.idEmp, e.nomEmp, e.salEmp, e.deptEmp, m.nomEmp AS mgrNom
            FROM Employe e
            JOIN Departement d ON d.deptEmp = e.deptEmp
            LEFT JOIN Employe m ON m.idEmp = d.mgrEmp
            ORDER BY e.nomEmp
            """
        ).fetchall()
        return render_template("employees.html", employees=rows)

    @app.route("/employees/<id_emp>")
    @login_required
    def employee_detail(id_emp):
        if g.user["role"] != "manager" and g.user["idEmp"] != id_emp:
            abort(403)
        conn = db.get_db()
        emp = conn.execute(
            """
            SELECT e.idEmp, e.nomEmp, e.salEmp, e.deptEmp, m.nomEmp AS mgrNom
            FROM Employe e
            JOIN Departement d ON d.deptEmp = e.deptEmp
            LEFT JOIN Employe m ON m.idEmp = d.mgrEmp
            WHERE e.idEmp = ?
            """,
            (id_emp,),
        ).fetchone()
        if emp is None:
            abort(404)
        assignments = conn.execute(
            "SELECT nomProj, heures, evalEmp FROM PerformanceEmp WHERE idEmp = ? ORDER BY nomProj",
            (id_emp,),
        ).fetchall()
        return render_template("employee_detail.html", emp=emp, assignments=assignments)

    @app.route("/recherche")
    @login_required
    def recherche():
        q = request.args.get("q", "")
        conn = db.get_db()
        results = []
        if q:
            results = conn.execute(
                "SELECT idEmp, nomEmp FROM Employe WHERE nomEmp LIKE ? ORDER BY nomEmp",
                (f"%{q}%",),
            ).fetchall()
        return render_template("recherche.html", q=q, results=results)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
