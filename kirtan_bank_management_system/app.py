from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from functools import wraps
import sqlite3
import secrets
import string
import io
import csv
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY_IN_PRODUCTION"
BASE_DIR = Path(__file__).parent
DB = BASE_DIR / "bank.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            email TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_after REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def now():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def generate_account_no():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        number = "KT" + "".join(secrets.choice(alphabet) for _ in range(8))
        with get_db() as db:
            if not db.execute("SELECT 1 FROM accounts WHERE account_no=?", (number,)).fetchone():
                return number


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "account_no" not in session:
            return jsonify({"error": "Please login first."}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    pin = str(data.get("pin", "")).strip()

    try:
        age = int(data.get("age", 0))
    except (TypeError, ValueError):
        age = 0

    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400
    if age < 18:
        return jsonify({"error": "Account holder must be at least 18 years old."}), 400
    if not (pin.isdigit() and len(pin) == 4):
        return jsonify({"error": "PIN must contain exactly 4 digits."}), 400

    account_no = generate_account_no()

    try:
        with get_db() as db:
            db.execute(
                """INSERT INTO accounts
                (account_no, name, age, email, pin_hash, balance, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)""",
                (account_no, name, age, email, generate_password_hash(pin), now())
            )
    except sqlite3.IntegrityError:
        return jsonify({"error": "Could not create account. Please try again."}), 500

    return jsonify({
        "message": "Account created successfully.",
        "account_no": account_no
    }), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    account_no = str(data.get("account_no", "")).strip().upper()
    pin = str(data.get("pin", "")).strip()

    with get_db() as db:
        account = db.execute(
            "SELECT * FROM accounts WHERE account_no=?", (account_no,)
        ).fetchone()

    if not account or not check_password_hash(account["pin_hash"], pin):
        return jsonify({"error": "Account number or PIN is incorrect."}), 401

    session["account_no"] = account_no
    return jsonify({"message": "Login successful."})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


def current_account():
    with get_db() as db:
        return db.execute(
            "SELECT id, account_no, name, age, email, balance, created_at FROM accounts WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()


@app.get("/api/me")
@login_required
def me():
    account = current_account()
    if not account:
        session.clear()
        return jsonify({"error": "Account not found."}), 404
    return jsonify(dict(account))


@app.post("/api/deposit")
@login_required
def deposit():
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0 or amount > 100000:
        return jsonify({"error": "Deposit must be between ₹1 and ₹100,000."}), 400

    with get_db() as db:
        account = db.execute(
            "SELECT balance FROM accounts WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()
        new_balance = account["balance"] + amount

        db.execute(
            "UPDATE accounts SET balance=? WHERE account_no=?",
            (new_balance, session["account_no"])
        )
        db.execute(
            """INSERT INTO transactions
            (account_no, type, amount, balance_after, created_at)
            VALUES (?, 'DEPOSIT', ?, ?, ?)""",
            (session["account_no"], amount, new_balance, now())
        )

    return jsonify({"message": "Money deposited successfully.", "balance": new_balance})


@app.post("/api/withdraw")
@login_required
def withdraw():
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0

    if amount <= 0 or amount > 100000:
        return jsonify({"error": "Withdrawal must be between ₹1 and ₹100,000."}), 400

    with get_db() as db:
        account = db.execute(
            "SELECT balance FROM accounts WHERE account_no=?",
            (session["account_no"],)
        ).fetchone()

        if account["balance"] < amount:
            return jsonify({"error": "Insufficient balance."}), 400

        new_balance = account["balance"] - amount

        db.execute(
            "UPDATE accounts SET balance=? WHERE account_no=?",
            (new_balance, session["account_no"])
        )
        db.execute(
            """INSERT INTO transactions
            (account_no, type, amount, balance_after, created_at)
            VALUES (?, 'WITHDRAW', ?, ?, ?)""",
            (session["account_no"], amount, new_balance, now())
        )

    return jsonify({"message": "Money withdrawn successfully.", "balance": new_balance})


@app.put("/api/profile")
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()

    if not name or not email:
        return jsonify({"error": "Name and email cannot be empty."}), 400

    with get_db() as db:
        db.execute(
            "UPDATE accounts SET name=?, email=? WHERE account_no=?",
            (name, email, session["account_no"])
        )

    return jsonify({"message": "Profile updated successfully."})


@app.delete("/api/account")
@login_required
def delete_account():
    account = current_account()
    if account["balance"] != 0:
        return jsonify({"error": "Account must have ₹0 balance before deletion."}), 400

    with get_db() as db:
        db.execute("DELETE FROM transactions WHERE account_no=?", (session["account_no"],))
        db.execute("DELETE FROM accounts WHERE account_no=?", (session["account_no"],))

    session.clear()
    return jsonify({"message": "Account deleted successfully."})


@app.get("/api/transactions")
@login_required
def transactions():
    with get_db() as db:
        rows = db.execute(
            """SELECT type, amount, balance_after, created_at
               FROM transactions WHERE account_no=?
               ORDER BY id DESC LIMIT 100""",
            (session["account_no"],)
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.get("/api/statement")
@login_required
def statement():
    with get_db() as db:
        rows = db.execute(
            """SELECT type, amount, balance_after, created_at
               FROM transactions WHERE account_no=?
               ORDER BY id DESC""",
            (session["account_no"],)
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type", "Amount", "Balance After", "Date"])
    for row in rows:
        writer.writerow([row["type"], row["amount"], row["balance_after"], row["created_at"]])

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{session['account_no']}_statement.csv"
    )


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
