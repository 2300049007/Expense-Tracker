
from flask import Blueprint, render_template, request, redirect, url_for, make_response
import sqlite3
import os
import csv
from io import StringIO
from datetime import date, datetime

main = Blueprint("main", __name__)

# Database location
DATABASE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "instance",
    "expenses.db"
)


# Connect to database
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# Home page
@main.route("/")
def home():

    current_month = date.today().strftime("%Y-%m")
    today_date = date.today().strftime("%d %B %Y")

    connection = get_db_connection()

    search = request.args.get("search", "").strip()
    category_filter = request.args.get("category", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Read sort_order, with sort as a fallback
    sort_order = request.args.get(
        "sort_order",
        request.args.get("sort", "newest")
    )

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    if sort_order == "oldest":
        query += " ORDER BY date ASC, id ASC"
    elif sort_order == "amount_high":
        query += " ORDER BY amount DESC"
    elif sort_order == "amount_low":
        query += " ORDER BY amount ASC"
    else:
        query += " ORDER BY date DESC, id DESC"

    expenses = connection.execute(query, params).fetchall()

    income_records = connection.execute(
        "SELECT * FROM income ORDER BY date DESC, id DESC"
    ).fetchall()

    total_expenses = connection.execute(
        "SELECT SUM(amount) FROM expenses"
    ).fetchone()[0]

    total_income = connection.execute(
        "SELECT SUM(amount) FROM income"
    ).fetchone()[0]

    # Get monthly expenses
    monthly_data = connection.execute("""
        SELECT
            strftime('%m', date) AS month_number,
            SUM(amount) AS total
        FROM expenses
        GROUP BY strftime('%m', date)
        ORDER BY month_number
    """).fetchall()

    # Convert month numbers into readable month names
    monthly_labels = [
        datetime.strptime(row["month_number"], "%m").strftime("%B")
        for row in monthly_data
    ]

    monthly_totals = [
        float(row["total"] or 0)
        for row in monthly_data
    ]

    # Get category-wise expenses
    category_data = connection.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        GROUP BY category
    """).fetchall()

    category_labels = [
        row["category"]
        for row in category_data
    ]

    category_totals = [
        float(row["total"] or 0)
        for row in category_data
    ]

    # Find the biggest expense
    biggest_expense = connection.execute("""
        SELECT title, amount, category, date
        FROM expenses
        ORDER BY amount DESC
        LIMIT 1
    """).fetchone()

    # Find the highest spending category
    top_category = connection.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """).fetchone()

    # Get this month's budget
    budget_record = connection.execute(
        "SELECT amount FROM budgets WHERE month = ?",
        (current_month,)
    ).fetchone()

    monthly_budget = budget_record["amount"] if budget_record else 0

    # Calculate this month's spending
    monthly_spending = connection.execute("""
        SELECT SUM(amount)
        FROM expenses
        WHERE strftime('%Y-%m', date) = ?
    """, (current_month,)).fetchone()[0]

    if monthly_spending is None:
        monthly_spending = 0

    budget_remaining = monthly_budget - monthly_spending

    if monthly_budget > 0:
        budget_percentage = min(
            (monthly_spending / monthly_budget) * 100,
            100
        )
    else:
        budget_percentage = 0

    connection.close()

    if total_expenses is None:
        total_expenses = 0

    if total_income is None:
        total_income = 0

    # Calculate remaining balance
    total_balance = total_income - total_expenses

    # Calculate savings
    total_savings = total_income - total_expenses

    return render_template(
        "index.html",
        expenses=expenses,
        income_records=income_records,
        total_expenses=total_expenses,
        total_income=total_income,
        total_balance=total_balance,
        total_savings=total_savings,
        monthly_labels=monthly_labels,
        monthly_totals=monthly_totals,
        category_labels=category_labels,
        category_totals=category_totals,
        search=search,
        category_filter=category_filter,
        date_from=date_from,
        date_to=date_to,
        sort_order=sort_order,
        current_month=current_month,
        monthly_budget=monthly_budget,
        monthly_spending=monthly_spending,
        budget_remaining=budget_remaining,
        budget_percentage=budget_percentage,
        biggest_expense=biggest_expense,
        top_category=top_category,
        today_date=today_date
    )


# Add expense
@main.route("/add-expense", methods=["POST"])
def add_expense():

    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    expense_date = request.form.get("date", "").strip()

    if not title or not amount or not category or not expense_date:
        return "Please fill in all fields!", 400

    try:
        amount = float(amount)

        if amount <= 0:
            return "Amount must be greater than zero!", 400

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO expenses (title, amount, category, date)
            VALUES (?, ?, ?, ?)
        """, (title, amount, category, expense_date))

        connection.commit()
        connection.close()

        return redirect(url_for("main.home"))

    except ValueError:
        return "Please enter a valid amount!", 400


# Add income
@main.route("/add-income", methods=["POST"])
def add_income():

    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "").strip()
    income_date = request.form.get("date", "").strip()

    if not title or not amount or not income_date:
        return "Please fill in all fields!", 400

    try:
        amount = float(amount)

        if amount <= 0:
            return "Amount must be greater than zero!", 400

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO income (title, amount, date)
            VALUES (?, ?, ?)
        """, (title, amount, income_date))

        connection.commit()
        connection.close()

        return redirect(url_for("main.home"))

    except ValueError:
        return "Please enter a valid amount!", 400


# Delete expense
@main.route("/delete-expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    connection = get_db_connection()

    connection.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("main.home"))


# Delete income
@main.route("/delete-income/<int:income_id>", methods=["POST"])
def delete_income(income_id):

    connection = get_db_connection()

    connection.execute(
        "DELETE FROM income WHERE id = ?",
        (income_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("main.home"))


# Set monthly budget
@main.route("/set-budget", methods=["POST"])
def set_budget():

    month = request.form.get("month", "").strip()
    amount = request.form.get("amount", "").strip()

    if not month:
        return "Please select a month!", 400

    try:
        datetime.strptime(month, "%Y-%m")
        amount = float(amount)

        if amount <= 0:
            return "Budget must be greater than zero!", 400

    except (ValueError, TypeError):
        return "Please enter a valid budget!", 400

    connection = get_db_connection()

    connection.execute("""
        INSERT INTO budgets (month, amount)
        VALUES (?, ?)
        ON CONFLICT(month)
        DO UPDATE SET amount = excluded.amount
    """, (month, amount))

    connection.commit()
    connection.close()

    return redirect(url_for("main.home"))


# Export expenses to CSV
@main.route("/export-expenses")
def export_expenses():

    connection = get_db_connection()

    expenses = connection.execute(
        """
        SELECT title, amount, category, date
        FROM expenses
        ORDER BY date DESC
        """
    ).fetchall()

    connection.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Title", "Amount", "Category", "Date"])

    for expense in expenses:
        writer.writerow([
            expense["title"],
            expense["amount"],
            expense["category"],
            expense["date"]
        ])

    response = make_response(output.getvalue())

    response.headers["Content-Disposition"] = (
        "attachment; filename=expenses.csv"
    )
    response.headers["Content-Type"] = "text/csv; charset=utf-8"

    return response


# Edit expense
@main.route("/edit-expense/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):

    connection = get_db_connection()

    expense = connection.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (expense_id,)
    ).fetchone()

    if expense is None:
        connection.close()
        return "Expense not found", 404

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        expense_date = request.form.get("date", "").strip()

        if not title or not amount or not category or not expense_date:
            connection.close()
            return "Please fill in all fields!", 400

        try:
            amount = float(amount)

            if amount <= 0:
                connection.close()
                return "Amount must be greater than zero!", 400

        except ValueError:
            connection.close()
            return "Please enter a valid amount!", 400

        connection.execute("""
            UPDATE expenses
            SET title = ?, amount = ?, category = ?, date = ?
            WHERE id = ?
        """, (title, amount, category, expense_date, expense_id))

        connection.commit()
        connection.close()

        return redirect(url_for("main.home"))

    connection.close()

    return render_template("edit_expense.html", expense=expense)
