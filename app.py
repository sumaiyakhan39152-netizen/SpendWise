from flask import Flask, request, jsonify, session, send_from_directory
from pathlib import Path

from database import (
    create_tables,
    create_user,
    get_user_by_email,
    get_user_by_id,
    add_transaction,
    get_transactions,
    get_summary,
    save_budget,
    get_budget_summary,
    create_goal,
    get_goals,
    add_goal_savings
)

from auth import hash_password, verify_password, validate_user

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path="/static"
)

app.config["SECRET_KEY"] = "spendwise-local-development-key"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

create_tables()


# FRONTEND PAGES

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/login")
def login_page():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.route("/register")
def register_page():
    return send_from_directory(FRONTEND_DIR, "register.html")


@app.route("/dashboard")
def dashboard_page():
    return send_from_directory(FRONTEND_DIR, "dashboard.html")


@app.route("/budget")
def budget_page():
    return send_from_directory(FRONTEND_DIR, "budget.html")


@app.route("/transactions")
def transactions_page():
    return send_from_directory(FRONTEND_DIR, "transactions.html")


@app.route("/analytics")
def analytics_page():
    return send_from_directory(FRONTEND_DIR, "analytics.html")


@app.route("/goals")
def goals_page():
    return send_from_directory(FRONTEND_DIR, "goals.html")


# REGISTER API

@app.route("/api/register", methods=["POST"])
def register():
    try:
        data = request.get_json(silent=True) or {}

        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        valid, message = validate_user(name, email, password)

        if not valid:
            return jsonify({"error": message}), 400

        if get_user_by_email(email):
            return jsonify({"error": "Email already registered"}), 409

        create_user(name, email, hash_password(password))

        return jsonify({
            "message": "Account created successfully!"
        }), 201

    except Exception:
        app.logger.exception("Registration error")
        return jsonify({"error": "Registration failed"}), 500


# LOGIN API

@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.get_json(silent=True) or {}

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        user = get_user_by_email(email)

        if not user or not verify_password(password, user["password"]):
            return jsonify({"error": "Invalid email or password"}), 401

        session.clear()
        session["user_id"] = user["id"]

        return jsonify({
            "message": "Login successful!",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        })

    except Exception:
        app.logger.exception("Login error")
        return jsonify({"error": "Login failed"}), 500


# CURRENT USER API

@app.route("/api/me")
def current_user():
    if "user_id" not in session:
        return jsonify({"error": "Please login"}), 401

    user = get_user_by_id(session["user_id"])

    if not user:
        session.clear()
        return jsonify({"error": "User not found"}), 404

    return jsonify(dict(user))


# LOGOUT API

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


# TRANSACTIONS API

@app.route("/api/transactions", methods=["GET", "POST"])
def transactions():
    if "user_id" not in session:
        return jsonify({"error": "Please login"}), 401

    user_id = session["user_id"]

    if request.method == "GET":
        return jsonify(get_transactions(user_id))

    data = request.get_json(silent=True) or {}

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    if (
        data.get("type") not in ["income", "expense"]
        or amount <= 0
        or not data.get("category")
        or not data.get("date")
    ):
        return jsonify({"error": "Invalid transaction details"}), 400

    data["amount"] = amount
    add_transaction(user_id, data)

    return jsonify({
        "message": "Transaction added successfully!"
    }), 201


# DASHBOARD AND ANALYTICS SUMMARY API

@app.route("/api/summary")
def summary():
    if "user_id" not in session:
        return jsonify({"error": "Please login"}), 401

    return jsonify(get_summary(session["user_id"]))


# BUDGET API

@app.route("/api/budget", methods=["GET", "POST"])
def budget_api():
    if "user_id" not in session:
        return jsonify({"error": "Please login"}), 401

    user_id = session["user_id"]

    if request.method == "GET":
        month = request.args.get("month")

        if not month:
            return jsonify({"error": "Month is required"}), 400

        return jsonify(get_budget_summary(user_id, month))

    data = request.get_json(silent=True) or {}
    month = data.get("month", "")

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid budget amount"}), 400

    if len(month) != 7 or month[4:5] != "-" or amount <= 0:
        return jsonify({"error": "Enter a valid month and budget"}), 400

    save_budget(user_id, month, amount)

    return jsonify({
        "message": "Budget saved successfully!"
    }), 201


# GOALS API

@app.route("/api/goals", methods=["GET", "POST"])
def goals_api():
    if "user_id" not in session:
        return jsonify({"error": "Please login"}), 401

    user_id = session["user_id"]

    if request.method == "GET":
        return jsonify(get_goals(user_id))

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()

    try:
        target = float(data.get("target", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid target amount"}), 400

    if not title or target <= 0:
        return jsonify({"error": "Enter a goal name and valid target"}), 400

    create_goal(user_id, title, target)

    return jsonify({
        "message": "Goal created successfully!"
    }), 201


# ADD SAVINGS API

@app.route("/api/goals/<int:goal_id>/save", methods=["POST"])
def save_goal_amount(goal_id):
    if "user_id" not in session:
        return jsonify({"error": "Please login"}), 401

    data = request.get_json(silent=True) or {}

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    if amount <= 0:
        return jsonify({"error": "Enter a valid savings amount"}), 400

    updated = add_goal_savings(
        session["user_id"],
        goal_id,
        amount
    )

    if not updated:
        return jsonify({"error": "Goal not found"}), 404

    return jsonify({
        "message": "Savings added successfully!"
    })


# RUN SERVER

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
        use_reloader=False
    )