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

    # ================= USERS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # ⭐ AUTO ADMIN
    cur.execute("""
    INSERT OR IGNORE INTO users(id,username,password,role)
    VALUES (1,'admin','admin123','admin')
    """)

    # ⭐ AUTO NORMAL USER (NEW)
    cur.execute("""
    INSERT OR IGNORE INTO users(id,username,password,role)
    VALUES (2,'user','123','user')
    """)

    # ================= MENU =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS menu(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT UNIQUE,
        price INTEGER,
        image TEXT
    )
    """)

    # ⭐ AUTO FOOD INSERT WITH IMAGES
    cur.execute("""
    INSERT OR IGNORE INTO menu(id,item,price,image)
    VALUES
    (1,'Pizza',250,'pizza.jpg'),
    (2,'Burger',120,'burger.jpg'),
    (3,'Pasta',180,'pasta.jpg'),
    (4,'Chocolate Cake',150,'cake.jpg'),
    (5,'Sandwich',90,'sandwich.jpg')
    """)

    # ================= ORDERS =================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        item TEXT,
        qty INTEGER,
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

            # ADMIN → Admin Panel
            if user[3] == "admin":
                return redirect("/admin")

            # USER → Dashboard
            return redirect("/dashboard")

        else:
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
# PLACE ORDER
# ===============================

@app.route("/order", methods=["POST"])
def order():

    if "user" not in session:
        return redirect("/login")

    item = request.form["item"]
    qty = request.form["qty"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders(username,item,qty,status)
        VALUES(?,?,?,?)
    """, (session["user"], item, qty, "Preparing"))

    conn.commit()
    conn.close()

    flash("✅ Order placed successfully!")

    return redirect("/menu")


# ===============================
# ORDER HISTORY
# ===============================

@app.route("/orders")
def orders():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM orders
        WHERE username=?
        ORDER BY id DESC
    """, (session["user"],))

    user_orders = cur.fetchall()

    conn.close()

    return render_template("orders.html", orders=user_orders)


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

    # Stats
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
# UPDATE ORDER STATUS
# ===============================

@app.route("/update_status", methods=["POST"])
def update_status():

    if "user" not in session or session.get("role") != "admin":
        return redirect("/login")

    order_id = request.form["order_id"]
    status = request.form["status"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE orders SET status=? WHERE id=?",
        (status, order_id)
    )

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
# RUN APP
# ===============================

if __name__ == "__main__":
    app.run(debug=True)
