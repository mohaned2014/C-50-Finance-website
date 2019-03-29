from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    #get user cash
    users = db.execute("SELECT * FROM users WHERE id = :user_id",user_id=session["user_id"])
    current_cash = float(users[0]["cash"])

    totalcash =0
    #get user stocks from database
    stocks= db.execute("SELECT * FROM portfolio WHERE id = :user_id GROUP BY stock_name",user_id=session["user_id"])
    for stock_name in stocks:
        symbol =stock_name["stock_name"]
        shares = float(stock_name["shares"])
        mystocknow = lookup(symbol)
        if mystocknow == None:
            continue
        else:
            total = shares * mystocknow["price"]
            totalcash = totalcash +total
            #
            db.execute("UPDATE portfolio SET current_price = :price ,total=:total WHERE id=:id AND stock_name=:symbol",
                        price=mystocknow["price"],
                        total=total, id=session["user_id"], symbol=symbol)


    #updated database
    updated_db =db.execute("SELECT * FROM portfolio WHERE id = :user_id",user_id=session["user_id"] )
    #total cash(in bank and stocks)
    totalcash =totalcash+current_cash
    #finished return template
    return render_template("index.html",mycurrentmoney=usd(current_cash),mytotalmoney=usd(totalcash),stocks =updated_db)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    #if user used post
    if request.method =="POST":
        #get stock information
        result1 =lookup(request.form.get("buy"))
        #ensure correct stock
        if result1 ==None or not request.form.get("buy") or not request.form.get("shares"):
            return apology("Empty or Not Found")

        else:
            #get number of shares in int
            shares = int(request.form.get("shares"))
            #ensure user input number in shares
            if shares <= 0:
                return apology("please enter a positive numbers")
            #get price of stotch
            else:
                priceof1stock = float(result1["price"])
                #get cash from database
                cash = db.execute("SELECT cash FROM users WHERE id = :user_id"
                , user_id=session["user_id"])
                #convert cash into int
                cash = int(cash[0]['cash'])
                #ensure there is enough money
                if cash >= shares * priceof1stock :
                    # Select user shares of that symbol
                    user_shares = db.execute("SELECT shares FROM portfolio WHERE id = :id AND stock_name=:symbol",
                    id=session["user_id"], symbol=result1["symbol"])
                    #insert into history
                    db.execute("INSERT INTO history (id,stock_name,shares,current_price) VALUES (:user_id ,:stock_name,:shares,:current_price)"
                        ,user_id=session["user_id"] ,stock_name =result1["symbol"],
                        shares =request.form.get("shares"),current_price =usd(priceof1stock))

                    #if user has no shares of that stock
                    if not user_shares:
                        db.execute("INSERT INTO portfolio (id,stock_name,shares,current_price,total) VALUES (:user_id ,:stock_name,:shares,:current_price,:total)"
                        ,user_id=session["user_id"] ,stock_name =result1["symbol"],
                        shares =request.form.get("shares"),current_price =usd(priceof1stock),total=shares *priceof1stock)

                    #if user already have this stock
                    else:
                        shares_total = user_shares[0]["shares"] + shares
                        db.execute("UPDATE portfolio SET shares=:shares WHERE id=:id AND stock_name=:symbol",
                        shares=shares_total, id=session["user_id"],
                        symbol=result1["symbol"])

                    db.execute("UPDATE users SET cash=cash -:total WHERE id = :user_id"
                    ,total = shares * priceof1stock,user_id=session["user_id"])
                    return redirect(url_for("index"))

                else:
                    return apology("You don't have enough cash")

    else:
        return render_template("buy.html")

    """Buy shares of stock."""

@app.route("/history")
@login_required
def history():
    #get data from database
    historytable = db.execute("SELECT * FROM history WHERE id =:user_id",user_id=session["user_id"])
    #FORM TABLE IN HTML
    for history in historytable :
        symbol = history["stock_name"]
        shares = history["shares"]
        price = history["current_price"]
        date = history["time"]
    return render_template("history.html",stocks =historytable)


    """Show history of transactions."""
    return apology("TODO")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    #if user reached throw post
    if request.method == "GET":
        return render_template("quote.html")
    if request.method == "POST":
        result =lookup(request.form.get("stock"))
        if result ==None or not request.form.get("stock") :
            return apology("Empty or Not Found")
        else :
            return render_template("quoed.html",name=result["name"],symbol=result["symbol"],price=result["price"])



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    #if user reached throw post
    if request.method == "POST":
    # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

            # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")


        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username not exist
        if len(rows) == 1:
            return apology("username exists already")

        #secure password
        hash = pwd_context.hash(request.form.get("password"))
        #ensure password match
        if request.form["password"] != request.form["password1"]:
            return apology("password doesn't match")
        #insert into database
        db.execute("INSERT INTO users (username,hash) VALUES (:username, :password)"
        , username = request.form["username"] , password=hash)

        #auto login
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        session["user_id"] = rows[0]["id"]
        return redirect(url_for("index"))



    #if user used get
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
    # ensure username was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol")

            # ensure password was submitted
        elif not request.form.get("shares"):
            return apology("must provide number")

        sellprice =lookup(request.form.get("symbol"))
        priceof1stock=sellprice["price"]
        shereinput=int(request.form.get("shares"))
         # query database for the stock we want to sell
        sell = db.execute("SELECT * FROM portfolio WHERE id = :user_id AND stock_name =:stock_name"
        , user_id=session["user_id"],stock_name=sellprice["symbol"])
        #sell more than owend
        #if we don't have it
        if len(sell) == 0 or sell[0]["shares"] < shereinput :
            return apology("you don't have this stock")
        else:
            #insert into history
            db.execute("INSERT INTO history (id,stock_name,shares,current_price) VALUES (:user_id ,:stock_name,:shares,:current_price)"
            ,user_id=session["user_id"] ,stock_name =sellprice["symbol"],
            shares =shereinput* - 1,current_price =usd(priceof1stock))
             #####
            total_shares = sell[0]["shares"] - shereinput
            db.execute("UPDATE portfolio SET shares=:shares WHERE id=:id AND stock_name=:symbol",
            shares=total_shares, id=session["user_id"],symbol=sell[0]["stock_name"])

            sellprice = sellprice["price"]
            db.execute("UPDATE users SET cash=cash +:x WHERE id = :user_id"
            ,x = shereinput * sellprice,user_id=session["user_id"])
            return redirect(url_for("index"))
    else:
        return render_template("sell.html")