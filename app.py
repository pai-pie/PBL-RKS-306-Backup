from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)

# 🔒 SECRET KEY 
app.secret_key = os.urandom(24)

# ==========================
#       DATABASE SETUP (FIXED)
# ==========================

# FORCE menggunakan path yang absolut dan sama
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'guardiantix.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

print(f"📍 Database location: {DATABASE_PATH}")  # DEBUG

# ==========================
#       MODEL USER
# ==========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    phone = db.Column(db.String(20))
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# ==========================
#       DATABASE INITIALIZATION
# ==========================
with app.app_context():
    try:
        print("🔄 Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # DEBUG: Cek file database
        import os
        if os.path.exists('guardiantix.db'):
            size = os.path.getsize('guardiantix.db')
            print(f"📁 Database file: {os.path.abspath('guardiantix.db')}")
            print(f"📊 Database size: {size} bytes")
        else:
            print("❌ Database file not found!")
        
        # Buat admin user jika belum ada
        admin = User.query.filter_by(email='admin@guardiantix.com').first()
        if not admin:
            admin = User(
                username='System Admin',
                email='admin@guardiantix.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created!")
        
        # Test query
        users_count = User.query.count()
        print(f"📊 Total users in database: {users_count}")
        
        # DEBUG: Tampilkan semua user
        users = User.query.all()
        print("👥 Users in database:")
        for user in users:
            print(f"   - {user.id}: {user.username} ({user.email})")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

# ==========================
#        ROUTES
# ==========================

@app.route("/")
@app.route("/homepage")
def homepage():
    print(f"🏠 Homepage access - Session: {dict(session)}")  # DEBUG
    
    # Jika belum login → ke halaman login
    if "user_id" not in session:
        print("❌ No user_id in session - redirect to login")  # DEBUG
        return redirect(url_for("login"))
    
    # Jika login sebagai admin → arahkan ke admin panel
    if session.get("role") == "admin":
        print("🔧 Admin detected - redirect to admin panel")  # DEBUG
        return redirect(url_for("admin_panel"))
    
    # Jika login sebagai user → tampilkan homepage user
    if session.get("role") == "user":
        print(f"✅ User {session['username']} accessing homepage")  # DEBUG
        return render_template("user/homepage.html", username=session["username"])
    
    # Jika ada role aneh → hapus session
    print("🚫 Invalid role - clearing session")  # DEBUG
    session.clear()
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        print(f"🔰 Register attempt: {username} ({email})")  # DEBUG

        # Validasi confirm password
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            print("❌ Password mismatch")  # DEBUG
            return render_template("user/register.html")

        # Cek apakah email sudah terdaftar di DATABASE
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered!", "error")
            print(f"❌ Email already exists: {email}")  # DEBUG
            return render_template("user/register.html")

        # Buat user baru di DATABASE
        new_user = User(
            username=username,
            email=email,
            role='user'
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            print(f"✅ User saved to database - ID: {new_user.id}, Username: {new_user.username}")
            
            # VERIFIKASI: Cek lagi dari database
            verify_user = User.query.get(new_user.id)
            if verify_user:
                print(f"✅ Verification passed - User found in DB: {verify_user.username}")
            else:
                print("❌ VERIFICATION FAILED - User not found in DB after commit!")
            
            # AUTO LOGIN SETELAH REGISTER - SET SESSION
            session["user_id"] = new_user.id
            session["username"] = new_user.username
            session["email"] = new_user.email
            session["role"] = new_user.role
            
            print(f"✅ Session set - user_id: {session['user_id']}")
            flash("Registration successful! Welcome!", "success")
            return redirect(url_for("homepage"))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ DATABASE ERROR: {e}")
            flash("Registration failed! Please try again.", "error")
            return render_template("user/register.html")

    return render_template("user/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["email"].strip()
        password = request.form["password"].strip()
        
        print(f"🔐 Login attempt: {identifier}")

        # 🔹 Login sebagai ADMIN
        admin_user = User.query.filter_by(email='admin@guardiantix.com', role='admin').first()
        if admin_user and admin_user.check_password(password) and identifier.lower() == 'admin@guardiantix.com':
            print("✅ Admin login successful - redirecting to admin panel")
            session["user_id"] = admin_user.id
            session["username"] = admin_user.username
            session["email"] = admin_user.email
            session["role"] = admin_user.role
            flash("Welcome back, Admin!", "success")
            return redirect(url_for("admin_panel"))

        # 🔹 Login sebagai USER (by email)
        user_by_email = User.query.filter_by(email=identifier).first()
        if user_by_email and user_by_email.check_password(password):
            print("✅ User login by email successful - redirecting to homepage")
            session["user_id"] = user_by_email.id
            session["username"] = user_by_email.username
            session["email"] = user_by_email.email
            session["role"] = user_by_email.role
            flash(f"Welcome back, {user_by_email.username}!", "success")
            return redirect(url_for("homepage"))

        # 🔹 Login sebagai USER (by username)  
        user_by_username = User.query.filter_by(username=identifier).first()
        if user_by_username and user_by_username.check_password(password):
            print("✅ User login by username successful - redirecting to homepage")
            session["user_id"] = user_by_username.id
            session["username"] = user_by_username.username
            session["email"] = user_by_username.email
            session["role"] = user_by_username.role
            flash(f"Welcome back, {user_by_username.username}!", "success")
            return redirect(url_for("homepage"))

        print("❌ Login failed")
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
    if "user_id" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/concert.html")

@app.route("/account")
def account():
    if "user_id" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    
    user = User.query.get(session.get("user_id"))
    if user:
        return render_template(
            "user/account.html",
            username=user.username,
            email=user.email,
            join_date=user.join_date.strftime("%d %B %Y")
        )
    else:
        flash("User not found!", "error")
        return redirect(url_for("login"))

@app.route("/payment")
def payment():
    if "user_id" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/payment.html")

@app.route("/success")
def success():
    if "user_id" not in session or session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user/success.html")

if __name__ == "__main__":
    print("🚀 Server starting...")
    print("📊 Database: SQLite (local file)")
    print("👤 Admin login: admin@guardiantix.com / admin123")
    app.run(debug=True, port=5000)