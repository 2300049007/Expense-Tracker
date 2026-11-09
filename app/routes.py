
from flask import Blueprint, render_template, request, redirect, url_for, make_response
from app.database import db, Expense, Income, Budget
import csv
from io import StringIO
from datetime import date, datetime

main = Blueprint("main", __name__)


# Home page
@main.route("/")
def home():

    current_month = date.today().strftime("%Y-%m")
    today_date = date.today().strftime("%d %B %Y")

    search = request.args.get("search", "").strip()
    category_filter = request.args.get("category", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    sort_order = request.args.get(
        "sort_order",
        request.args.get("sort", "newest")
    )

    # Get expenses
    expense_query = Expense.query

    if search:
        expense_query = expense_query.filter(
            Expense.title.ilike(f"%{search}%")
        )

    if category_filter:
        expense_query = expense_query.filter(
            Expense.category == category_filter
        )

    if date_from:
        expense_query = expense_query.filter(
            Expense.date >= date_from
        )

    if date_to:
        expense_query = expense_query.filter(
            Expense.date <= date_to
        )

    if sort_order == "oldest":
        expense_query = expense_query.order_by(
            Expense.date.asc(), Expense.id.asc()
        )
    elif sort_order == "amount_high":
        expense_query = expense_query.order_by(
            Expense.amount.desc()
        )
    elif sort_order == "amount_low":
        expense_query = expense_query.order_by(
            Expense.amount.asc()
        )
    else:
        expense_query = expense_query.order_by(
            Expense.date.desc(), Expense.id.desc()
        )

    expenses = expense_query.all()

    # Get income records
    income_records = Income.query.order_by(
        Income.date.desc(), Income.id.desc()
    ).all()

    # Calculate totals
    total_expenses = db.session.query(
        db.func.sum(Expense.amount)
    ).scalar() or 0

    total_income = db.session.query(
        db.func.sum(Income.amount)
    ).scalar() or 0

    total_balance = total_income - total_expenses
    total_savings = total_balance

    # Monthly expense chart
    monthly_data = db.session.query(
        db.func.substr(Expense.date, 6, 2).label("month_number"),
        db.func.sum(Expense.amount).label("total")
    ).group_by(
        "month_number"
    ).order_by("month_number").all()

    monthly_labels = [
        datetime.strptime(str(row.month_number), "%m").strftime("%B")
        for row in monthly_data
    ]

    monthly_totals = [
        float(row.total or 0)
        for row in monthly_data
    ]

    # Category chart
    category_data = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label("total")
    ).group_by(Expense.category).all()

    category_labels = [
        row.category for row in category_data
    ]

    category_totals = [
        float(row.total or 0) for row in category_data
    ]

    # Biggest expense
    biggest_expense = Expense.query.order_by(
        Expense.amount.desc()
    ).first()

    # Highest spending category
    top_category = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label("total")
    ).group_by(
        Expense.category
    ).order_by(
        db.desc("total")
    ).first()

    # Monthly budget
    budget_record = Budget.query.filter_by(
        month=current_month
    ).first()

    monthly_budget = budget_record.amount if budget_record else 0

    # This month's spending
    monthly_spending = db.session.query(
        db.func.sum(Expense.amount)
    ).filter(
        db.func.substr(Expense.date, 1, 7) == current_month
    ).scalar() or 0

    budget_remaining = monthly_budget - monthly_spending

    if monthly_budget > 0:
        budget_percentage = min(
            (monthly_spending / monthly_budget) * 100,
            100
        )
    else:
        budget_percentage = 0

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

        expense = Expense(
            title=title,
            amount=amount,
            category=category,
            date=expense_date
        )

        db.session.add(expense)
        db.session.commit()

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

        income = Income(
            title=title,
            amount=amount,
            date=income_date
        )

        db.session.add(income)
        db.session.commit()

        return redirect(url_for("main.home"))

    except ValueError:
        return "Please enter a valid amount!", 400


# Delete expense
@main.route("/delete-expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    expense = db.session.get(Expense, expense_id)

    if expense:
        db.session.delete(expense)
        db.session.commit()

    return redirect(url_for("main.home"))


# Delete income
@main.route("/delete-income/<int:income_id>", methods=["POST"])
def delete_income(income_id):

    income = db.session.get(Income, income_id)

    if income:
        db.session.delete(income)
        db.session.commit()

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

    budget = Budget.query.filter_by(month=month).first()

    if budget:
        budget.amount = amount
    else:
        budget = Budget(month=month, amount=amount)
        db.session.add(budget)

    db.session.commit()

    return redirect(url_for("main.home"))


# Export expenses to CSV
@main.route("/export-expenses")
def export_expenses():

    expenses = Expense.query.order_by(
        Expense.date.desc()
    ).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Title", "Amount", "Category", "Date"])

    for expense in expenses:
        writer.writerow([
            expense.title,
            expense.amount,
            expense.category,
            expense.date
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

    expense = db.session.get(Expense, expense_id)

    if expense is None:
        return "Expense not found", 404

    if request.method == "POST":

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

        except ValueError:
            return "Please enter a valid amount!", 400

        expense.title = title
        expense.amount = amount
        expense.category = category
        expense.date = expense_date

        db.session.commit()

        return redirect(url_for("main.home"))

    return render_template(
        "edit_expense.html",
        expense=expense
    )
