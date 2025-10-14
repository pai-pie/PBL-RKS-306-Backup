from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import mysql.connector
from functools import wraps
from datetime import datetime # Diperlukan untuk konversi tanggal

app = Flask(__name__)

# 🔒 SECRET KEY
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# ==========================
#   KONFIGURASI DATABASE
# ==========================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'db_konser'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# ==========================
#   DECORATORS (PENGAMAN ROUTE)
# ==========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Access denied! You must be an admin to view this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ==========================
#   FUNGSI BANTUAN
# ==========================
def create_admin_user_if_not_exists():
    conn = get_db_connection()
    if not conn:
        print("Could not connect to database to verify admin user.")
        return

    cursor = conn.cursor(dictionary=True)
    
    admin_email = "admin@guardiantix.com"
    cursor.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
    admin_user = cursor.fetchone()

    if not admin_user:
        print(f"Admin user not found, creating one...")
        password_hash = generate_password_hash('admin123')
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                ("System Admin", admin_email, password_hash, "admin")
            )
            conn.commit()
            print("Admin user created successfully.")
        except mysql.connector.Error as err:
            print(f"Failed to create admin user: {err}")
    
    cursor.close()
    conn.close()

# Jalankan fungsi ini saat aplikasi dimulai
with app.app_context():
    create_admin_user_if_not_exists()


# ==========================
#   ROUTES - AUTENTIKASI
# ==========================
@app.route("/")
@app.route("/homepage")
@login_required
def homepage():
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

        conn = get_db_connection()
        if not conn:
            flash("Database connection error. Please try again later.", "danger")
            return render_template("user/register.html")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Email already registered!", "error")
            cursor.close()
            conn.close()
            return render_template("user/register.html")

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        flash("Registration successful! Please log in to continue.", "success")
        return redirect(url_for("login"))
        
    return render_template("user/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        
        conn = get_db_connection()
        if not conn:
            flash("Database connection error. Please try again later.", "danger")
            return render_template("user/login.html")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = email
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
            
            if user["role"] == 'admin':
                return redirect(url_for("admin_panel"))
            else:
                return redirect(url_for("homepage"))

        flash("Invalid email or password!", "danger")
        return render_template("user/login.html")

    return render_template("user/login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# =======================================================
#   ROUTES - ADMIN PANEL (EVENTS & TICKETS MANAGEMENT)
# =======================================================

@app.route("/admin")
@admin_required
def admin_panel():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Ambil semua event (kode yang sudah ada)
    cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
    events = cursor.fetchall()

    # (REVISI) Ambil semua tiket dari semua event untuk tampilan overview
    query = """
        SELECT 
            t.id, t.type_name, t.price, t.quota, t.sold, (t.quota - t.sold) as available,
            e.name as event_name
        FROM tickets t
        JOIN events e ON t.event_id = e.id
        ORDER BY e.name, t.price ASC
    """
    cursor.execute(query)
    all_tickets = cursor.fetchall()

    cursor.close()
    conn.close()
    
    # Kirim DUA variabel ke template: events dan all_tickets
    return render_template("adminpanel.html", events=events, all_tickets=all_tickets)

# --- Event CRUD ---
@app.route("/admin/events/add", methods=["GET", "POST"])
@admin_required
def add_event():
    if request.method == "POST":
        name = request.form['name']
        event_date = request.form['event_date']
        location = request.form['location']
        status = request.form['status']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (name, event_date, location, status) VALUES (%s, %s, %s, %s)",
            (name, event_date, location, status)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Event added successfully!", "success")
        return redirect(url_for('admin_panel'))
    return render_template("add_event.html")

@app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == "POST":
        name = request.form['name']
        event_date = request.form['event_date']
        location = request.form['location']
        status = request.form['status']
        
        cursor.execute(
            "UPDATE events SET name=%s, event_date=%s, location=%s, status=%s WHERE id=%s",
            (name, event_date, location, status, event_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Event updated successfully!", "success")
        return redirect(url_for('admin_panel'))

    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not event:
        flash("Event not found!", "danger")
        return redirect(url_for('admin_panel'))
        
    # Konversi date ke string format YYYY-MM-DD untuk input HTML
    if isinstance(event['event_date'], datetime):
        event['event_date'] = event['event_date'].strftime('%Y-%m-%d')
    return render_template("edit_event.html", event=event)

@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Event and all associated tickets have been deleted.", "success")
    return redirect(url_for('admin_panel'))

# --- Ticket CRUD per Event ---
@app.route("/admin/events/<int:event_id>/tickets")
@admin_required
def manage_tickets(event_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ambil info event untuk ditampilkan di judul
    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()

    # Ambil semua tiket untuk event ini
    cursor.execute("SELECT *, (quota - sold) as available FROM tickets WHERE event_id = %s ORDER BY price ASC", (event_id,))
    tickets = cursor.fetchall()

    cursor.close()
    conn.close()

    if not event:
        flash("Event not found!", "danger")
        return redirect(url_for('admin_panel'))

    return render_template("manage_tickets.html", event=event, tickets=tickets)

@app.route("/admin/events/<int:event_id>/tickets/add", methods=["GET", "POST"])
@admin_required
def add_ticket(event_id):
    if request.method == "POST":
        type_name = request.form['type_name']
        price = request.form['price']
        quota = request.form['quota']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tickets (event_id, type_name, price, quota) VALUES (%s, %s, %s, %s)",
            (event_id, type_name, price, quota)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Ticket type added successfully!", "success")
        return redirect(url_for('manage_tickets', event_id=event_id))

    # Ambil info event untuk ditampilkan di form
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not event:
        flash("Event not found!", "danger")
        return redirect(url_for('admin_panel'))

    return render_template("add_ticket.html", event=event)


@app.route("/admin/tickets/edit/<int:ticket_id>", methods=["GET", "POST"])
@admin_required
def edit_ticket(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        type_name = request.form['type_name']
        price = request.form['price']
        quota = request.form['quota']

        # Ambil event_id sebelum update
        cursor.execute("SELECT event_id FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        event_id = ticket['event_id'] if ticket else None

        cursor.execute(
            "UPDATE tickets SET type_name=%s, price=%s, quota=%s WHERE id=%s",
            (type_name, price, quota, ticket_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Ticket type updated successfully!", "success")
        
        if event_id:
            return redirect(url_for('manage_tickets', event_id=event_id))
        else:
            return redirect(url_for('admin_panel'))


    cursor.execute("SELECT t.*, e.name as event_name FROM tickets t JOIN events e ON t.event_id = e.id WHERE t.id = %s", (ticket_id,))
    ticket = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not ticket:
        flash("Ticket type not found!", "danger")
        return redirect(url_for('admin_panel'))
        
    return render_template("edit_ticket.html", ticket=ticket)

@app.route("/admin/tickets/delete/<int:ticket_id>", methods=["POST"])
@admin_required
def delete_ticket(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ambil event_id sebelum delete untuk redirect
    cursor.execute("SELECT event_id FROM tickets WHERE id = %s", (ticket_id,))
    ticket = cursor.fetchone()
    event_id = ticket['event_id'] if ticket else None

    cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Ticket type deleted.", "success")
    
    if event_id:
        return redirect(url_for('manage_tickets', event_id=event_id))
    else:
        return redirect(url_for('admin_panel'))

# ==========================
#   ROUTES - USER LAINNYA
# ==========================

@app.route("/concert")
@login_required
def concert():
    return render_template("user/concert.html")

@app.route("/account")
@login_required
def account():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    join_date_str = "N/A"
    if user and user.get("created_at"):
        # Pastikan created_at adalah objek datetime
        if isinstance(user["created_at"], datetime):
            join_date_str = user["created_at"].strftime('%B %d, %Y')

    return render_template(
        "user/account.html",
        username=user.get("username") if user else "N/A",
        email=user.get("email") if user else "N/A",
        join_date=join_date_str
    )

@app.route("/payment")
@login_required
def payment():
    return render_template("user/payment.html")

@app.route("/success")
@login_required
def success():
    return render_template("user/success.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

