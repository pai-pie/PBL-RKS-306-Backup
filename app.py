from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import mysql.connector
from functools import wraps
from datetime import datetime

app = Flask(__name__)

# 🔒 SECRET KEY
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# ==========================
#   KONFIGURASI DATABASE
# ==========================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Quantum_drift14', 
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
    conn = None
    try:
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
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                ("System Admin", admin_email, password_hash, "admin")
            )
            conn.commit()
            print("Admin user created successfully.")
    except mysql.connector.Error as err:
        print(f"Failed to create admin user: {err}")
    finally:
        if conn and conn.is_connected():
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

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM events WHERE status IN ('Active', 'Upcoming') ORDER BY event_date ASC")
        events = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error fetching homepage events: {err}")
        events = []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template("user/homepage.html", username=session.get("username", "Pengguna"), events=events)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                flash("Database connection error.", "danger")
                return render_template("user/register.html")

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered!", "error")
                return render_template("user/register.html")

            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as err:
            flash("An error occurred during registration.", "danger")
            print(f"Registration error: {err}")
            return render_template("user/register.html")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
            
    return render_template("user/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        
        conn = None
        try:
            conn = get_db_connection()
            if not conn:
                flash("Database connection error.", "danger")
                return render_template("user/login.html")

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["email"] = email
                session["role"] = user["role"]
                flash(f"Welcome back, {user['username']}!", "success")
                
                return redirect(url_for("admin_panel")) if user["role"] == 'admin' else redirect(url_for("homepage"))
            else:
                flash("Invalid email or password!", "danger")
        except mysql.connector.Error as err:
            flash("An error occurred during login.", "danger")
            print(f"Login error: {err}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    return render_template("user/login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# =======================================================
#   ROUTES - ADMIN PANEL (EVENTS & TICKETS & USERS MANAGEMENT)
# =======================================================

@app.route("/admin")
@admin_required
def admin_panel():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Ambil data events
        cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
        events = cursor.fetchall()
        
        # Ambil data overview tickets
        query_tickets = """
            SELECT 
                t.id, t.type_name, t.price, t.quota, t.sold, (t.quota - t.sold) as available,
                e.name as event_name
            FROM tickets t
            JOIN events e ON t.event_id = e.id
            ORDER BY e.name, t.price ASC
        """
        cursor.execute(query_tickets)
        all_tickets = cursor.fetchall()

        # (REVISI) Ambil semua data pengguna
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Admin panel error: {err}")
        events = []
        all_tickets = []
        users = [] # (REVISI)
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    # (REVISI) Kirim TIGA variabel ke template
    return render_template("adminpanel.html", events=events, all_tickets=all_tickets, users=users)

# --- Event CRUD ---
@app.route("/admin/events/add", methods=["GET", "POST"])
@admin_required
def add_event():
    if request.method == "POST":
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (name, event_date, location, status) VALUES (%s, %s, %s, %s)",
                (request.form['name'], request.form['event_date'], request.form['location'], request.form['status'])
            )
            conn.commit()
            flash("Event added successfully!", "success")
        except mysql.connector.Error as err:
            flash("Error adding event.", "danger")
            print(f"Add event error: {err}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
        return redirect(url_for('admin_panel'))
    return render_template("add_event.html")

@app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])
@admin_required
def edit_event(event_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == "POST":
            cursor.execute(
                "UPDATE events SET name=%s, event_date=%s, location=%s, status=%s WHERE id=%s",
                (request.form['name'], request.form['event_date'], request.form['location'], request.form['status'], event_id)
            )
            conn.commit()
            flash("Event updated successfully!", "success")
            return redirect(url_for('admin_panel'))

        cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            flash("Event not found!", "danger")
            return redirect(url_for('admin_panel'))
            
        if isinstance(event.get('event_date'), datetime):
            event['event_date'] = event['event_date'].strftime('%Y-%m-%d')
        return render_template("edit_event.html", event=event)
    except mysql.connector.Error as err:
        flash("Error managing event.", "danger")
        print(f"Edit event error: {err}")
        return redirect(url_for('admin_panel'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
        conn.commit()
        flash("Event and all associated tickets have been deleted.", "success")
    except mysql.connector.Error as err:
        flash("Error deleting event.", "danger")
        print(f"Delete event error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('admin_panel'))

# --- Ticket CRUD per Event ---
@app.route("/admin/events/<int:event_id>/tickets")
@admin_required
def manage_tickets(event_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        event = cursor.fetchone()
        cursor.execute("SELECT *, (quota - sold) as available FROM tickets WHERE event_id = %s ORDER BY price ASC", (event_id,))
        tickets = cursor.fetchall()

        if not event:
            flash("Event not found!", "danger")
            return redirect(url_for('admin_panel'))

        return render_template("manage_tickets.html", event=event, tickets=tickets)
    except mysql.connector.Error as err:
        flash("Error loading tickets.", "danger")
        print(f"Manage tickets error: {err}")
        return redirect(url_for('admin_panel'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/admin/events/<int:event_id>/tickets/add", methods=["GET", "POST"])
@admin_required
def add_ticket(event_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            cursor.execute(
                "INSERT INTO tickets (event_id, type_name, price, quota) VALUES (%s, %s, %s, %s)",
                (event_id, request.form['type_name'], request.form['price'], request.form['quota'])
            )
            conn.commit()
            flash("Ticket type added successfully!", "success")
            return redirect(url_for('manage_tickets', event_id=event_id))

        cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            flash("Event not found!", "danger")
            return redirect(url_for('admin_panel'))

        return render_template("add_ticket.html", event=event)
    except mysql.connector.Error as err:
        flash("Error adding ticket.", "danger")
        print(f"Add ticket error: {err}")
        return redirect(url_for('manage_tickets', event_id=event_id))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route("/admin/tickets/edit/<int:ticket_id>", methods=["GET", "POST"])
@admin_required
def edit_ticket(ticket_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT event_id FROM tickets WHERE id = %s", (ticket_id,))
        ticket_data = cursor.fetchone()
        event_id = ticket_data['event_id'] if ticket_data else None

        if request.method == "POST":
            cursor.execute(
                "UPDATE tickets SET type_name=%s, price=%s, quota=%s WHERE id=%s",
                (request.form['type_name'], request.form['price'], request.form['quota'], ticket_id)
            )
            conn.commit()
            flash("Ticket type updated successfully!", "success")
            return redirect(url_for('manage_tickets', event_id=event_id))

        cursor.execute("SELECT t.*, e.name as event_name FROM tickets t JOIN events e ON t.event_id = e.id WHERE t.id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            flash("Ticket type not found!", "danger")
            return redirect(url_for('admin_panel'))
            
        return render_template("edit_ticket.html", ticket=ticket)
    except mysql.connector.Error as err:
        flash("Error editing ticket.", "danger")
        print(f"Edit ticket error: {err}")
        return redirect(url_for('admin_panel'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route("/admin/tickets/delete/<int:ticket_id>", methods=["POST"])
@admin_required
def delete_ticket(ticket_id):
    conn = None
    event_id = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT event_id FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        event_id = ticket['event_id'] if ticket else None
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conn.commit()
        flash("Ticket type deleted.", "success")
    except mysql.connector.Error as err:
        flash("Error deleting ticket.", "danger")
        print(f"Delete ticket error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return redirect(url_for('manage_tickets', event_id=event_id)) if event_id else redirect(url_for('admin_panel'))

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
    conn = None
    user = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Account page error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    join_date_str = "N/A"
    if user and user.get("created_at"):
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

