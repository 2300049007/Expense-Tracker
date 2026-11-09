
from flask import Blueprint, render_template, request, redirect, url_for, make_response, flash
from app.database import db, Expense, Income, Budget
import csv
from io import StringIO
from datetime import date, datetime
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import User

main = Blueprint("main", __name__)


# Home page
@main.route("/")
@login_required
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
    expense_query = Expense.query.filter_by(
        user_id=current_user.id
    )

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
    income_records = Income.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Income.date.desc(), Income.id.desc()
    ).all()

    # Calculate totals
    total_expenses = db.session.query(
        db.func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id
    ).scalar() or 0

    total_income = db.session.query(
        db.func.sum(Income.amount)
    ).filter(
        Income.user_id == current_user.id
    ).scalar() or 0

    total_balance = total_income - total_expenses
    total_savings = total_balance

    # Monthly expense chart
    monthly_data = db.session.query(
        db.func.substr(Expense.date, 6, 2).label("month_number"),
        db.func.sum(Expense.amount).label("total")
    ).filter(
        Expense.user_id == current_user.id
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
    ).filter(
        Expense.user_id == current_user.id
    ).group_by(Expense.category).all()

    category_labels = [
        row.category for row in category_data
    ]

    category_totals = [
        float(row.total or 0) for row in category_data
    ]

    # Biggest expense
    biggest_expense = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Expense.amount.desc()
    ).first()

    # Highest spending category
    top_category = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label("total")
    ).filter(
        Expense.user_id == current_user.id
    ).group_by(
        Expense.category
    ).order_by(
        db.desc("total")
    ).first()

    # Monthly budget
    budget_record = Budget.query.filter_by(
        month=current_month,
        user_id=current_user.id
    ).first()

    monthly_budget = budget_record.amount if budget_record else 0

    # This month's spending
    monthly_spending = db.session.query(
        db.func.sum(Expense.amount)
    ).filter(
        Expense.user_id == current_user.id,
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
            date=expense_date,
            user_id=current_user.id
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
            date=income_date,
            user_id=current_user.id
        )

        db.session.add(income)
        db.session.commit()

        return redirect(url_for("main.home"))

    except ValueError:
        return "Please enter a valid amount!", 400


# Delete expense
@main.route("/delete-expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first()

    if expense:
        db.session.delete(expense)
        db.session.commit()

    return redirect(url_for("main.home"))


# Delete income
@main.route("/delete-income/<int:income_id>", methods=["POST"])
def delete_income(income_id):

    income = Income.query.filter_by(
        id=income_id,
        user_id=current_user.id
    ).first()

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

    budget = Budget.query.filter_by(
        month=month,
        user_id=current_user.id
    ).first()

    if budget:
        budget.amount = amount
    else:
        budget = Budget(
            month=month,
            amount=amount,
            user_id=current_user.id
        )
        db.session.add(budget)

    db.session.commit()

    return redirect(url_for("main.home"))


# Export expenses to CSV
@main.route("/export-expenses")
def export_expenses():

    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(
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

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=current_user.id
    ).first()

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

# USER REGISTRATION

@main.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("Please fill in all fields!", "error")
            return redirect(url_for("main.register"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("main.register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters!", "error")
            return redirect(url_for("main.register"))

        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email)
        ).first()

        if existing_user:
            flash("Username or email already exists!", "error")
            return redirect(url_for("main.register"))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        flash("Registration successful!", "success")
        return redirect(url_for("main.home"))

    return render_template("register.html")


# USER LOGIN

@main.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("main.home"))

        flash("Invalid email or password!", "error")

    return render_template("login.html")


# USER LOGOUT

@main.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out!", "success")

    return redirect(url_for("main.login"))
