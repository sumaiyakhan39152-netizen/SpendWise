import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("spendwise.db")


# DATABASE CONNECTION
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# CREATE DATABASE TABLES
def create_tables():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            UNIQUE(user_id, month),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            target REAL NOT NULL,
            saved REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# CREATE USER
def create_user(name, email, password):
    conn = get_connection()

    conn.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        (name, email, password)
    )

    conn.commit()
    conn.close()


# FIND USER BY EMAIL
def get_user_by_email(email):
    conn = get_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    conn.close()
    return user


# FIND USER BY ID
def get_user_by_id(user_id):
    conn = get_connection()

    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    conn.close()
    return user


# ADD TRANSACTION
def add_transaction(user_id, data):
    conn = get_connection()

    conn.execute("""
        INSERT INTO transactions
        (user_id, type, amount, category, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data["type"],
        data["amount"],
        data["category"],
        data.get("description", ""),
        data["date"]
    ))

    conn.commit()
    conn.close()


# GET TRANSACTIONS
def get_transactions(user_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT * FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
    """, (user_id,)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# DASHBOARD SUMMARY
def get_summary(user_id):
    conn = get_connection()

    row = conn.execute("""
        SELECT
            COALESCE(SUM(
                CASE WHEN type = 'income'
                THEN amount ELSE 0 END
            ), 0) AS income,

            COALESCE(SUM(
                CASE WHEN type = 'expense'
                THEN amount ELSE 0 END
            ), 0) AS expense

        FROM transactions
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    conn.close()

    income = row["income"]
    expense = row["expense"]

    return {
        "income": income,
        "expense": expense,
        "balance": income - expense
    }


# SAVE OR UPDATE MONTHLY BUDGET
def save_budget(user_id, month, amount):
    conn = get_connection()

    conn.execute("""
        INSERT INTO budgets (user_id, month, amount)
        VALUES (?, ?, ?)

        ON CONFLICT(user_id, month)
        DO UPDATE SET amount = excluded.amount
    """, (user_id, month, amount))

    conn.commit()
    conn.close()


# GET MONTHLY BUDGET SUMMARY
def get_budget_summary(user_id, month):
    conn = get_connection()

    budget_row = conn.execute("""
        SELECT amount
        FROM budgets
        WHERE user_id = ? AND month = ?
    """, (user_id, month)).fetchone()

    spent_row = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) AS spent
        FROM transactions
        WHERE user_id = ?
        AND type = 'expense'
        AND substr(date, 1, 7) = ?
    """, (user_id, month)).fetchone()

    conn.close()

    budget = budget_row["amount"] if budget_row else 0
    spent = spent_row["spent"]

    return {
        "budget": budget,
        "spent": spent,
        "remaining": budget - spent
    }
    
    # CREATE A SAVING GOAL
def create_goal(user_id, title, target):
    conn = get_connection()

    conn.execute("""
        INSERT INTO goals (user_id, title, target, saved)
        VALUES (?, ?, ?, 0)
    """, (user_id, title, target))

    conn.commit()
    conn.close()


# GET USER GOALS
def get_goals(user_id):
    conn = get_connection()

    rows = conn.execute("""
        SELECT id, title, target, saved
        FROM goals
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# ADD SAVINGS TO A GOAL
def add_goal_savings(user_id, goal_id, amount):
    conn = get_connection()

    result = conn.execute("""
        UPDATE goals
        SET saved = saved + ?
        WHERE id = ? AND user_id = ?
    """, (amount, goal_id, user_id))

    conn.commit()
    updated = result.rowcount
    conn.close()

    return updated > 0