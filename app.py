from flask import Flask, render_template, request, redirect, url_for, session, flash
import os

app = Flask(__name__)

# 🔒 SECRET KEY otomatis berubah setiap restart → session lama langsung invalid
app.secret_key = os.urandom(24)

# Simpan user sementara (sementara dict, seharusnya database)
users = {}

# Kredensial admin tetap
ADMIN_EMAIL = "admin@guardiantix.com"
ADMIN_PASSWORD = "admin123"

# ==========================
#        HOMEPAGE
# ==========================
@app.route("/")
@app.route("/homepage")
def homepage():
    # Jika belum login → ke halaman login
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Jika login sebagai admin → arahkan ke admin panel
    if session.get("role") == "admin":
        return redirect(url_for("admin_panel"))
    
    # Jika login sebagai user → tampilkan homepage user
    if session.get("role") == "user":
        return render_template("user/homepage.html", username=session["username"])
    
    # Jika ada role aneh → hapus session
    session.clear()
    return redirect(url_for("login"))

# ==========================
#        REGISTER
# ==========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        # Cek apakah email sudah terdaftar
        if email in users:
            return render_template("user/register.html", error="Email sudah terdaftar!")

        # Simpan user baru
        users[email] = {"username": username, "password": password}

        flash("Registrasi berhasil! Silakan login.", "success")
        return redirect(url_for("login"))

    return render_template("user/register.html")

# ==========================
#          LOGIN
# ==========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["email"].strip()
        password = request.form["password"].strip()

        # 🔹 Login sebagai ADMIN
        if identifier.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
            session["username"] = "Admin"
            session["email"] = ADMIN_EMAIL
            session["role"] = "admin"
            flash("Berhasil login sebagai admin!", "success")
            return redirect(url_for("admin_panel"))

        # 🔹 Login sebagai USER (pakai email)
        if identifier in users and users[identifier]["password"] == password:
            session["username"] = users[identifier]["username"]
            session["email"] = identifier
            session["role"] = "user"
            flash(f"Selamat datang, {session['username']}!", "success")
            return redirect(url_for("homepage"))

        # 🔹 Login sebagai USER (pakai username)
        for email, data in users.items():
            if data["username"] == identifier and data["password"] == password:
                session["username"] = data["username"]
                session["email"] = email
                session["role"] = "user"
                flash(f"Selamat datang, {session['username']}!", "success")
                return redirect(url_for("homepage"))

        # Jika gagal login
        flash("Email/Username atau password salah!", "danger")
        return render_template("user/login.html")

    return render_template("user/login.html")

# ==========================
#          LOGOUT
# ==========================
@app.route("/logout")
def logout():
    session.clear()
    flash("Anda sudah logout.", "info")
    return redirect(url_for("login"))

# ==========================
#        ADMIN PANEL
# ==========================
@app.route("/admin")
def admin_panel():
    # Cek hanya admin yang bisa masuk
    if session.get("role") != "admin":
        flash("Anda tidak memiliki akses ke halaman admin!", "danger")
        return redirect(url_for("login"))
    return render_template("adminpanel.html")

# ==========================
#      HALAMAN USER
# ==========================
@app.route("/concert")
def concert():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/concert.html")

@app.route("/account")
def account():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template(
        "user/account.html",
        username=session["username"],
        email=session["email"]
    )

@app.route("/payment")
def payment():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/payment.html")

@app.route("/success")
def success():
    if "username" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/success.html")

# ==========================
#        MAIN APP
# ==========================
if __name__ == "__main__":
    app.run(debug=True)
