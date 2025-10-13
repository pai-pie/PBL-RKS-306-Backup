from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash # Masih berguna untuk hashing password
import os
import uuid 
# datetime, SQLAlchemy, dotenv, dan model DB dihapus

app = Flask(__name__)

# 🔒 SECRET KEY (PENTING untuk session dan flash)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# ==========================
#      DUMMY USER DATA (Hanya di memori RAM)
# ==========================
# Data ini HANYA ada di memori RAM dan akan hilang saat server dimatikan.
# Hash password 'admin123' untuk simulasi keamanan
DUMMY_USERS = {
    "admin@guardiantix.com": {
        "id": 1, 
        "username": "System Admin", 
        "role": "admin", 
        "password_hash": generate_password_hash('admin123')
    },
    "user@test.com": {
        "id": 2, 
        "username": "Guest User", 
        "role": "user", 
        "password_hash": generate_password_hash('user123')
    },
}

# Fungsi untuk mencari user dummy
def find_user_by_email(email):
    return DUMMY_USERS.get(email)

# ==========================
#      ROUTES
# ==========================

@app.route("/")
@app.route("/homepage")
def homepage():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if session.get("role") == "admin":
        return redirect(url_for("admin_panel"))
    
    return render_template("user/homepage.html", username=session.get("username", "Pengguna"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return render_template("user/register.html")

        # SIMULASI: Jika email sudah ada di dummy data
        if find_user_by_email(email):
             flash("Email already registered!", "error")
             return render_template("user/register.html")

        # DUMMY REGISTRASI BERHASIL (data disimpan sementara di DUMMY_USERS)
        new_id = str(uuid.uuid4())
        DUMMY_USERS[email] = {
            "id": new_id, 
            "username": username, 
            "role": "user", 
            "password_hash": generate_password_hash(password)
        }

        session["user_id"] = new_id
        session["username"] = username
        session["email"] = email
        session["role"] = "user"
        
        flash("Registration successful! Welcome!", "success")
        return redirect(url_for("homepage"))
        
    return render_template("user/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["email"].strip()
        password = request.form["password"].strip()
        
        # Cari user di DUMMY_USERS berdasarkan email
        user_attempt = find_user_by_email(identifier)

        # Cek Password menggunakan hash
        if user_attempt and check_password_hash(user_attempt["password_hash"], password):
            session["user_id"] = user_attempt["id"]
            session["username"] = user_attempt["username"]
            session["email"] = identifier
            session["role"] = user_attempt["role"]
            flash(f"Welcome back, {user_attempt['username']}!", "success")
            
            if user_attempt["role"] == 'admin':
                return redirect(url_for("admin_panel"))
            else:
                return redirect(url_for("homepage"))

        flash("Invalid email/username or password!", "danger")
        return render_template("user/login.html")

    return render_template("user/login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/admin")
def admin_panel():
    if session.get("role") != "admin":
        flash("Access denied! Admin only.", "danger")
        return redirect(url_for("login"))
    return render_template("adminpanel.html") 

# Routes user lainnya...
@app.route("/concert")
def concert():
    if "user_id" not in session:
        flash("Please login to view concerts.", "warning")
        return redirect(url_for("login"))
    return render_template("user/concert.html")

@app.route("/account")
def account():
    if "user_id" not in session:
        flash("Please login to view your account.", "warning")
        return redirect(url_for("login"))
    
    # Hanya menampilkan data dari session
    return render_template(
        "user/account.html",
        username=session.get("username"),
        email=session.get("email"),
        join_date="N/A (No Database)"
    )

@app.route("/payment")
def payment():
    if "user_id" not in session:
        flash("Please login to view payment options.", "warning")
        return redirect(url_for("login"))
    return render_template("user/payment.html")

@app.route("/success")
def success():
    if "user_id" not in session:
        flash("Please login to view success page.", "warning")
        return redirect(url_for("login"))
    return render_template("user/success.html")

if __name__ == "__main__":
    print("🚀 Server starting (NO DATABASE). Access on http://localhost:8000")
    print("👤 DUMMY Admin login: admin@guardiantix.com / admin123")
    app.run(host='0.0.0.0', port=5000, debug=True)
