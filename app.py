from flask import Flask, render_template, request, redirect, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "foodapp_secure_key_2026"


# ===============================
# DATABASE CONNECTION
# ===============================
def get_db():
    return sqlite3.connect("database.db", check_same_thread=False)


# ===============================
# CREATE TABLES + AUTO SEED
# ===============================
def create_tables():
    conn = get_db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    INSERT OR IGNORE INTO users(id,username,password,role)
    VALUES (1,'admin','admin123','admin')
    """)

    cur.execute("""
    INSERT OR IGNORE INTO users(id,username,password,role)
    VALUES (2,'user','123','user')
    """)

    # MENU
    cur.execute("""
    CREATE TABLE IF NOT EXISTS menu(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT UNIQUE,
        price INTEGER,
        image TEXT
    )
    """)

    cur.execute("""
    INSERT OR IGNORE INTO menu(id,item,price,image)
    VALUES
    (1,'Pizza',250,'pizza.jpg'),
    (2,'Burger',120,'burger.jpg'),
    (3,'Pasta',180,'pasta.jpg'),
    (4,'Chocolate Cake',150,'cake.jpg'),
    (5,'Sandwich',90,'sandwich.jpg')
    """)

    # ORDERS ✅ FIXED
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        item TEXT,
        qty INTEGER,
        address TEXT,
        payment_mode TEXT,
        payment_status TEXT,
        status TEXT DEFAULT 'Preparing'
    )
    """)

    conn.commit()
    conn.close()


create_tables()


# ===============================
# HOME
# ===============================
@app.route("/")
def home():
    return render_template("home.html")


# ===============================
# LOGIN
# ===============================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = username
            session["role"] = user[3]
            session["cart"] = []

            if user[3] == "admin":
                return redirect("/admin")

            return redirect("/dashboard")

        flash("Invalid Username or Password!")

    return render_template("login.html")


# ===============================
# DASHBOARD
# ===============================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


# ===============================
# MENU
# ===============================
@app.route("/menu")
def menu():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM menu")
    items = cur.fetchall()
    conn.close()

    return render_template("menu.html", items=items)


# ===============================
# ADD TO CART
# ===============================
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():

    if "user" not in session:
        return redirect("/login")

    item = request.form["item"]
    price = int(request.form["price"])
    qty = int(request.form["qty"])

    cart = session.get("cart", [])

    for c in cart:
        if c["item"] == item:
            c["qty"] += qty
            session["cart"] = cart
            flash("🛒 Quantity updated!")
            return redirect("/menu")

    cart.append({
        "item": item,
        "price": price,
        "qty": qty
    })

    session["cart"] = cart
    flash("🛒 Added to cart!")
    return redirect("/menu")


# ===============================
# CART
# ===============================
@app.route("/cart")
def cart():
    if "user" not in session:
        return redirect("/login")

    cart = session.get("cart", [])
    total = sum(i["price"] * i["qty"] for i in cart)
    return render_template("cart.html", cart=cart, total=total)


# ===============================
# CHECKOUT
# ===============================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    if "user" not in session:
        return redirect("/login")

    cart = session.get("cart", [])

    if not cart:
        flash("Your cart is empty!")
        return redirect("/menu")

    if request.method == "POST":
        session["address"] = request.form["address"]
        session["payment_mode"] = request.form["payment"]

        # ✅ COD → directly place order
        if session["payment_mode"] == "COD":
            return redirect("/place_order")

        # ✅ ONLINE → go to fake payment page
        return redirect("/payment")

    total = sum(i["price"] * i["qty"] for i in cart)
    return render_template("checkout.html", cart=cart, total=total)


# ===============================
# PAYMENT (FAKE)
# ===============================
@app.route("/payment", methods=["GET", "POST"])
def payment():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        return redirect("/place_order")

    total = sum(i["price"] * i["qty"] for i in session.get("cart", []))
    return render_template("payment.html", total=total)


# ===============================
# PLACE ORDER
# ===============================
@app.route("/place_order")
def place_order():

    if "user" not in session:
        return redirect("/login")

    cart = session.get("cart", [])
    address = session.get("address")
    payment_mode = session.get("payment_mode")

    payment_status = "Pending" if payment_mode == "COD" else "Paid"

    conn = get_db()
    cur = conn.cursor()

    for item in cart:
        cur.execute("""
            INSERT INTO orders(
                username,item,qty,address,
                payment_mode,payment_status,status
            )
            VALUES(?,?,?,?,?,?,?)
        """, (
            session["user"],
            item["item"],
            item["qty"],
            address,
            payment_mode,
            payment_status,
            "Preparing"
        ))

    conn.commit()
    conn.close()

    session["cart"] = []
    flash("🎉 Order placed successfully!")
    return redirect("/orders")


# ===============================
# ORDER HISTORY
# ===============================
@app.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM orders WHERE username=? ORDER BY id DESC",
        (session["user"],)
    )
    data = cur.fetchall()
    conn.close()

    return render_template("orders.html", orders=data)


# ===============================
# ADMIN PANEL
# ===============================
@app.route("/admin")
def admin():

    if "user" not in session or session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Preparing'")
    preparing = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status='Delivered'")
    delivered = cur.fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        orders=orders,
        total_orders=total_orders,
        total_users=total_users,
        preparing=preparing,
        delivered=delivered
    )


# ===============================
# UPDATE STATUS
# ===============================
@app.route("/update_status", methods=["POST"])
def update_status():

    if "user" not in session or session.get("role") != "admin":
        return redirect("/login")

    order_id = request.form["order_id"]
    status = request.form["status"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

    return redirect("/admin")


# ===============================
# LOGOUT
# ===============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
