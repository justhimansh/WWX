import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    user_his = db.execute("SELECT symbol, SUM(stocks) AS stocks, price FROM transactions WHERE user_id = ? GROUP BY symbol", user_id)

    user_money = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    #rounding cash
    real_cash = user_money[0]["cash"]
    cash = round(real_cash, 2)

    return render_template("index.html", data = user_his, cash = cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    else:
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        if not symbol:
            return apology("Please provide a stock symbol.")

        symbol = lookup(symbol.upper())

        if symbol == None:
            return apology("Please re-enter symbol")

        if shares < 0:
            return apology("Please enter a positive int")

        trans = shares * symbol["price"]

        user_id = session["user_id"]
        user_amount = db.execute("SELECT cash from users WHERE id = :id", id = user_id)
        user_money = user_amount[0]["cash"]

        if user_money < trans:
            return apology("You have insufficient funds")

        new_amount = user_money - trans

        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_amount, user_id)

        curr_date = datetime.datetime.now()

        db.execute("INSERT INTO transactions (user_id, symbol, stocks, price, date) VALUES (?, ?, ?, ?, ?)", user_id, symbol["symbol"], shares, symbol["price"], curr_date)

        flash("Stock has been purchased!")

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transaction_data = db.execute("SELECT * FROM transactions where user_id = :id", id=user_id)

    return render_template("history.html", transaction = transaction_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")

    else:
        stock = request.form.get("symbol")

        if not stock:
            return apology("Stock name is empty :(")

        stocksym = lookup(stock.upper())

        if stock == None:
            return apology("This stock doesn't currently exist in the database")

        return render_template("quoted.html", name = stocksym["name"], price = stocksym["price"], symbol = stocksym["symbol"])



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("Please input a username")

        if not password:
            return apology("Please input a password")

        if not confirmation:
            return apology("Please confirm your password")

        if password != confirmation:
            return apology("Please re-enter your password")

        if len(password) < 6:
            return apology("Please provide a longer password")

        if len(username) > 13:
            return apology("Please use a shorter username")

        encrypted = generate_password_hash(password)

        try:
            test = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, encrypted)
        except:
            return apology("The credentials already exist in the database")


        session["user_id"] = test

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        user_id = session["user_id"]

        user_sym = db.execute("SELECT symbol FROM transactions WHERE user_id = :id GROUP BY symbol HAVING SUM(stocks) > 0", id=user_id)
        return render_template("sell.html", symbols = [row["symbol"] for row in user_sym])

    else:
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        if not symbol:
            return apology("Please provide a stock symbol.")

        symbol = lookup(symbol.upper())

        if symbol == None:
            return apology("Please re-enter symbol")

        if shares < 0:
            return apology("Please enter a positive int")

        trans = shares * symbol["price"]

        user_id = session["user_id"]
        user_amount = db.execute("SELECT cash from users WHERE id = :id", id = user_id)
        user_money = user_amount[0]["cash"]

        new_amount = user_money + trans

        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_amount, user_id)

        curr_date = datetime.datetime.now()

        db.execute("INSERT INTO transactions (user_id, symbol, stocks, price, date) VALUES (?, ?, ?, ?, ?)", user_id, symbol["symbol"], (-1)*shares, symbol["price"], curr_date)

        flash("Sold!")

        return redirect("/")
