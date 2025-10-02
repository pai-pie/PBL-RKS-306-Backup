from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "supersecret"

# Simpan user sementara (harusnya database, tapi ini contoh simple)
users = {}

# --- HOMEPAGE ---
@app.route("/")
@app.route("/homepage")
def homepage():
    if "username" in session:
        return render_template("user/homepage.html")  
    return redirect(url_for("login"))

# --- REGISTER ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        # Cek apakah email sudah terdaftar
        if email in users:
            return render_template("user/register.html", error="Email sudah terdaftar!")

        # Simpan user baru
        users[email] = {"username": username, "password": password}

        # Auto login setelah daftar
        session["username"] = username
        return redirect(url_for("homepage"))

    return render_template("user/register.html")

# --- LOGIN ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email not in users or users[email]["password"] != password:
            return render_template("user/login.html", error="Email atau password salah!")

        session["username"] = users[email]["username"]
        return redirect(url_for("homepage"))

    return render_template("user/login.html")


# --- LOGOUT ---
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# --- CONCERT (contoh) ---
@app.route("/concert")
def concert():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/concert.html")

@app.route("/account")
def account():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template(
        "user/account.html",
        username=session["username"],
        email=session.get("email", "unknown")
    )


@app.route("/payment")
def payment():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/payment.html")

@app.route("/success")
def success():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("user/success.html")
    
if __name__ == "__main__":
    app.run(debug=True)
