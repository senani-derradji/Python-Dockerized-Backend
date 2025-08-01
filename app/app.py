from flask import Flask, render_template, request, redirect, session, url_for
import pymysql, redis, os
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
# MariaDB Configuration
db = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "user"),
    password=os.getenv("DB_PASSWORD", "password"),
    database=os.getenv("DB_NAME", "flask_db"),
    connect_timeout=5 )
# Redis Configuration
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    decode_responses=True )
# Create users table if not exists
with db.cursor() as cursor:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password VARCHAR(100)
        )
    """)
    db.commit()
@app.route("/")
def index():
    if "username" in session:
        return f"<h2>Welcome, {session['username']}!</h2><a href='/logout'>Logout</a>"
    return redirect("/login")
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with db.cursor() as cursor:
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
                db.commit()
                return redirect("/login")
            except pymysql.err.IntegrityError:
                return "Username already exists."
    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # check in redis first
        cached = redis_client.get(f"user:{username}")
        if cached and cached == password:
            session["username"] = username
            return redirect("/")
        # check in DB
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            user = cursor.fetchone()
        if user:
            redis_client.set(f"user:{username}", password)
            session["username"] = username
            return redirect("/")
        else:
            return "Invalid credentials."
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

