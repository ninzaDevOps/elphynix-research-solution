import hmac
import logging
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
import pymysql
from dotenv import load_dotenv
from flask import (
    Flask, g, jsonify, redirect, render_template, request, session, url_for,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()


def required_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if len(value) < 32 or value.upper().startswith("CHANGE_ME"):
        raise RuntimeError(
            f"{name} must be set to a random value of at least 32 characters. "
            "Copy .env.example to .env and configure it before starting the app."
        )
    return value


app = Flask(__name__)
app.config.update(
    SECRET_KEY=required_secret("FLASK_SECRET_KEY"),
    WTF_CSRF_TIME_LIMIT=3600,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)
csrf = CSRFProtect(app)

JWT_SECRET = required_secret("JWT_SECRET")
JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", "8"))
if not 1 <= JWT_EXP_HOURS <= 24:
    raise RuntimeError("JWT_EXP_HOURS must be between 1 and 24.")

DB = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "elphynix_app"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "elphynix_research"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
    "connect_timeout": 5,
    "read_timeout": 15,
    "write_timeout": 15,
}
if not DB["password"]:
    raise RuntimeError("DB_PASSWORD must be configured in the environment.")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("elphynix")


def db():
    return pymysql.connect(**DB)


def query(sql, args=(), one=False, commit=False):
    """Execute one parameterized SQL statement and always close the connection."""
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            if commit:
                conn.commit()
            if sql.lstrip().lower().startswith(("insert", "update", "delete")):
                return cur.lastrowid
            return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()


def token_for(value: str = "") -> str:
    # Cryptographically random callback token; not derived from the project identifier.
    return secrets.token_urlsafe(32)


def current_user():
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header:
        scheme, _, supplied = auth_header.partition(" ")
        if scheme.lower() == "bearer" and supplied:
            token = supplied.strip()
    token = token or session.get("jwt")
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user = query(
            "SELECT id, username, password, role, email, full_name, active "
            "FROM users WHERE username=%s AND active=1",
            (payload["username"],), one=True,
        )
        return user
    except (jwt.InvalidTokenError, KeyError, TypeError):
        return None
    except pymysql.MySQLError:
        logger.exception("Could not load the authenticated user")
        return None


def auth_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            if role and user["role"] != role:
                return jsonify({"error": "Forbidden"}), 403
            request.user = user
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def log_request(response):
    """Best-effort request logging; logging failure must not break the response."""
    if app.testing:
        return response
    if request.path.startswith("/static/") or request.path in ("/health/live",):
        return response
    try:
        user = current_user()
        query(
            """INSERT INTO request_log
               (request_id, method, endpoint, user_agent, ip_address, username,
                response_status, error_message, processing_time_ms, created_at,
                completed_at, is_successful)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),%s)""",
            (
                str(uuid.uuid4()), request.method, request.path,
                request.headers.get("User-Agent", "")[:1000],
                request.remote_addr,
                user["username"] if user else None,
                response.status_code,
                "Request failed" if response.status_code >= 400 else None,
                max(0, int((time.perf_counter() - getattr(g, "request_started", time.perf_counter())) * 1000)),
                200 <= response.status_code < 400,
            ),
            commit=True,
        )
    except Exception:
        logger.exception("Request logging failed")
    return response


@app.before_request
def start_request_timer():
    g.request_started = time.perf_counter()


@app.after_request
def after_request(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return log_request(response)


@app.get("/")
def home():
    return redirect(url_for("dashboard_page") if current_user() else url_for("login_page"))


@app.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")


@app.get("/dashboard")
def dashboard_page():
    user = current_user()
    if not user:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", user=user)


@app.get("/projects")
def projects_page():
    if not current_user():
        return redirect(url_for("login_page"))
    return render_template("projects.html")


@app.get("/analytics")
def analytics_page():
    if not current_user():
        return redirect(url_for("login_page"))
    return render_template("analytics.html")


@app.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    user = query(
        "SELECT id, username, password, role, active FROM users "
        "WHERE username=%s AND active=1",
        (username,), one=True,
    )
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "username": user["username"],
            "role": user["role"],
            "iat": now,
            "exp": now + timedelta(hours=JWT_EXP_HOURS),
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    session.clear()
    session["jwt"] = token
    return jsonify({"message": "Login successful", "role": user["role"], "username": user["username"]})


@app.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.put("/change-password")
@auth_required()
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("currentPassword") or ""
    new_password = data.get("newPassword") or ""
    if not check_password_hash(request.user["password"], current_password):
        return jsonify({"error": "Current password is incorrect"}), 400
    if len(new_password) < 12:
        return jsonify({"error": "New password must contain at least 12 characters"}), 400
    query(
        "UPDATE users SET password=%s WHERE id=%s",
        (generate_password_hash(new_password), request.user["id"]), commit=True,
    )
    session.clear()
    return jsonify({"message": "Password updated. Please log in again."})


@app.get("/health/live")
def health_live():
    # Liveness must not depend on RDS; the process can be alive while DB is unavailable.
    return jsonify({"status": "UP"})


@app.get("/health/ready")
def health_ready():
    try:
        query("SELECT 1", one=True)
        return jsonify({"status": "READY", "database": "UP"})
    except pymysql.MySQLError:
        logger.exception("Readiness check failed")
        return jsonify({"status": "NOT_READY", "database": "DOWN"}), 503


@app.get("/api/analytics/metrics")
@auth_required()
def metrics():
    rows = query("SELECT status, COUNT(*) AS total FROM survey_response GROUP BY status")
    counts = {row["status"]: row["total"] for row in rows}
    total = sum(counts.values())
    percent = lambda key: round(counts.get(key, 0) * 100 / total, 1) if total else 0
    return jsonify({
        "totalTraffics": {"value": total, "change": 0},
        "completePercent": {"value": percent("COMPLETE"), "change": 0},
        "terminatePercent": {"value": percent("TERMINATE"), "change": 0},
        "securityTerminatePercent": {"value": percent("SECURITYTERMINATE"), "change": 0},
        "quotaFullPercent": {"value": percent("QUOTAFULL"), "change": 0},
        "totalDropPercent": {"value": round((counts.get("TERMINATE", 0) + counts.get("SECURITYTERMINATE", 0) + counts.get("QUOTAFULL", 0)) * 100 / total, 1) if total else 0},
    })


@app.get("/api/analytics/traffic-chart")
@auth_required()
def traffic_chart():
    view = request.args.get("view", "day")
    if view == "month":
        sql = """SELECT DATE_FORMAT(start_time,'%%Y-%%m') AS label, COUNT(*) AS total
                 FROM survey_response
                 WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                 GROUP BY DATE_FORMAT(start_time,'%%Y-%%m') ORDER BY label"""
    else:
        sql = """SELECT DATE_FORMAT(start_time,'%%b %%d') AS label, COUNT(*) AS total
                 FROM survey_response
                 WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                 GROUP BY DATE(start_time) ORDER BY DATE(start_time)"""
    rows = query(sql)
    return jsonify({"labels": [r["label"] for r in rows], "data": [r["total"] for r in rows]})


@app.get("/api/analytics/markets")
@auth_required()
def markets():
    rows = query(
        "SELECT DISTINCT country FROM survey_response "
        "WHERE country IS NOT NULL AND country<>'' ORDER BY country"
    )
    return jsonify(["All"] + [row["country"] for row in rows])


@app.get("/projects/all")
@auth_required("ADMIN")
def projects_all():
    status = request.args.get("status", "ACTIVE").upper()
    base_sql = """SELECT p.*, CAST(p.ir AS DOUBLE) AS ir, CAST(p.cpi AS DOUBLE) AS cpi,
                          c.username AS client_username, c.company_name AS client_company
                   FROM project p LEFT JOIN client c ON c.id=p.client_id"""
    if status == "ALL":
        rows = query(base_sql + " ORDER BY p.created_at DESC")
    else:
        rows = query(base_sql + " WHERE p.status=%s ORDER BY p.created_at DESC", (status,))
    return jsonify(rows)


@app.post("/projects/create/project")
@auth_required("ADMIN")
def create_project():
    data = request.get_json(silent=True) or {}
    project_identifier = (data.get("projectIdentifier") or "").strip()
    client_username = (data.get("clientUsername") or "").strip()
    if not project_identifier or not client_username:
        return jsonify({"success": False, "message": "Project identifier and client username are required"}), 400
    if query("SELECT id FROM project WHERE project_identifier=%s", (project_identifier,), one=True):
        return jsonify({"success": False, "message": "Project identifier already exists"}), 409
    client = query("SELECT id FROM client WHERE username=%s AND is_shown='show'", (client_username,), one=True)
    if not client:
        return jsonify({"success": False, "message": "Client does not exist or is inactive"}), 404
    try:
        ir = float(data["ir"]) if data.get("ir") not in (None, "") else None
        loi = int(data["loi"]) if data.get("loi") not in (None, "") else None
        quota = int(data["quota"]) if data.get("quota") not in (None, "") else 0
        counts = int(data["counts"]) if data.get("counts") not in (None, "") else 0
        cpi = float(data["cpi"]) if data.get("cpi") not in (None, "") else None
        if quota < 0 or counts < 0 or (loi is not None and loi < 0) or (ir is not None and not 0 <= ir <= 100) or (cpi is not None and cpi < 0):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "IR must be 0-100; LOI, quota and counts must be non-negative integers; CPI must be non-negative"}), 400

    project_id = query(
        """INSERT INTO project
           (project_identifier, project_identifier_token, status, ir, loi, quota, counts, cpi, client_id, created_by)
           VALUES (%s,%s,'ACTIVE',%s,%s,%s,%s,%s,%s,%s)""",
        (project_identifier, token_for(), ir, loi, quota, counts, cpi, client["id"], request.user["id"]),
        commit=True,
    )
    query(
        "INSERT INTO security_terminate_flag(project_id, flag) VALUES(%s,%s)",
        (project_identifier, bool(data.get("securityTerminateFlag", False))), commit=True,
    )
    return jsonify({"success": True, "message": "Project created successfully", "projectId": project_id, "projectIdentifier": project_identifier, "projectToken": query("SELECT project_identifier_token FROM project WHERE id=%s", (project_id,), one=True)["project_identifier_token"]}), 201


@app.get("/admin/vendors/get/")
@auth_required("ADMIN")
def vendors():
    return jsonify(query(
        """SELECT id,username,email,company_name,complete,terminate,quotafull,
                  security_terminate AS securityTerminate,user_token,is_shown
           FROM users WHERE role='VENDOR' AND is_shown='show' ORDER BY id DESC"""
    ))


@app.post("/admin/vendors/create")
@auth_required("ADMIN")
def create_vendor():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    if not username or not email or len(password) < 12:
        return jsonify({"error": "Username and email are required; password must contain at least 12 characters"}), 400
    if query("SELECT id FROM users WHERE username=%s", (username,), one=True):
        return jsonify({"error": "Username exists"}), 409
    query(
        """INSERT INTO users
           (username,password,role,email,company_name,user_token,is_shown)
           VALUES(%s,%s,'VENDOR',%s,%s,%s,'show')""",
        (username, generate_password_hash(password), email, data.get("companyName", ""), uuid.uuid4().hex),
        commit=True,
    )
    return jsonify({"message": "Vendor created"}), 201


@app.get("/admin/clients/get/")
@auth_required("ADMIN")
def clients():
    return jsonify(query(
        """SELECT id,username,email,company_name,is_shown,created_at
           FROM client WHERE is_shown='show' ORDER BY id DESC"""
    ))


@app.post("/admin/create/client")
@auth_required("ADMIN")
def create_client():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    company_name = (data.get("companyName") or "").strip()
    supplied_token = (data.get("token") or "").strip()
    if not username or not email:
        return jsonify({"error": "Client username and email are required"}), 400
    if query("SELECT id FROM client WHERE username=%s OR token=%s", (username, supplied_token or "__not_supplied__"), one=True):
        return jsonify({"error": "Client username/token exists"}), 409
    query(
        "INSERT INTO client(username,email,company_name,token,is_shown) VALUES(%s,%s,%s,%s,'show')",
        (username, email, company_name, supplied_token or uuid.uuid4().hex), commit=True,
    )
    return jsonify({"message": "Client created"}), 201


@app.get("/survey/api/survey-responses/all")
@auth_required()
def survey_all():
    return jsonify(query("SELECT * FROM survey_response ORDER BY start_time DESC"))


@app.get("/survey/api/survey-responses/paged")
@auth_required()
def survey_paged():
    try:
        page = max(int(request.args.get("page", 0)), 0)
        size = min(max(int(request.args.get("size", 20)), 1), 200)
    except ValueError:
        return jsonify({"error": "page and size must be integers"}), 400
    offset = page * size
    total = query("SELECT COUNT(*) AS c FROM survey_response", one=True)["c"]
    rows = query("SELECT * FROM survey_response ORDER BY start_time DESC LIMIT %s OFFSET %s", (size, offset))
    return jsonify({"content": rows, "page": page, "size": size, "totalElements": total, "totalPages": (total + size - 1) // size})


def set_survey_status(status):
    respondent_id = request.args.get("uid") or request.args.get("UID")
    project_identifier = request.args.get("pid") or request.args.get("PID")
    if not respondent_id or not project_identifier:
        return render_template("survey-status.html", status="INVALID", message="PID and UID are required"), 400
    project = query(
        "SELECT project_identifier, project_identifier_token FROM project WHERE project_identifier=%s",
        (project_identifier,), one=True,
    )
    if not project:
        return render_template("survey-status.html", status="INVALID", message="Project was not found"), 404
    supplied_token = request.args.get("token") or request.args.get("TOKEN") or ""
    if not supplied_token or not hmac.compare_digest(supplied_token, project["project_identifier_token"]):
        return render_template("survey-status.html", status="INVALID", message="Invalid survey callback token"), 403
    existing = query(
        "SELECT id FROM survey_response WHERE project_id=%s AND u_id=%s",
        (project_identifier, respondent_id), one=True,
    )
    now = datetime.now()
    if existing:
        query(
            """UPDATE survey_response SET status=%s, end_time=%s,
                      vendor_username=COALESCE(%s,vendor_username)
               WHERE id=%s""",
            (status, now, request.args.get("vendor"), existing["id"]), commit=True,
        )
    else:
        query(
            """INSERT INTO survey_response
               (status,ip_address,start_time,end_time,country,project_id,u_id,vendor_username)
               VALUES(%s,%s,%s,%s,NULL,%s,%s,%s)""",
            (status, request.remote_addr, now, now, project_identifier, respondent_id, request.args.get("vendor")),
            commit=True,
        )
    return render_template("survey-status.html", status=status, message=f"Survey marked as {status}")


@app.get("/survey/complete")
def complete():
    return set_survey_status("COMPLETE")


@app.get("/survey/terminate")
def terminate():
    return set_survey_status("TERMINATE")


@app.get("/survey/quotafull")
def quotafull():
    return set_survey_status("QUOTAFULL")


@app.get("/survey/securityTerminate")
def security_terminate():
    return set_survey_status("SECURITYTERMINATE")


@app.get("/api/monitoring/failed-requests")
@auth_required("ADMIN")
def failed_requests():
    return jsonify(query("SELECT * FROM request_log WHERE is_successful=0 ORDER BY created_at DESC LIMIT 500"))


@app.get("/api/monitoring/dashboard")
@auth_required("ADMIN")
def monitoring_dashboard():
    total = query("SELECT COUNT(*) AS c FROM request_log", one=True)["c"]
    failed = query("SELECT COUNT(*) AS c FROM request_log WHERE is_successful=0", one=True)["c"]
    return jsonify({"totalRequests": total, "failedRequests": failed, "failureRate": round(failed * 100 / total, 2) if total else 0})


@app.errorhandler(HTTPException)
def handle_http_error(error):
    if request.path.startswith("/api/") or request.is_json:
        return jsonify({"error": error.description}), error.code
    return error


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.exception("Unhandled application exception")
    if request.path.startswith("/api/") or request.is_json:
        return jsonify({"error": "Internal server error"}), 500
    return render_template("survey-status.html", status="ERROR", message="An unexpected error occurred"), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
