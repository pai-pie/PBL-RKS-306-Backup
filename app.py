from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import mysql.connector
from functools import wraps
from datetime import datetime
import time

app = Flask(__name__)

# 🔒 SECRET KEY
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# ==========================
#   KONFIGURASI DATABASE
# ==========================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pulupulu', 
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
        
        # Ambil events
        cursor.execute("SELECT * FROM events WHERE status IN ('Active', 'Upcoming') ORDER BY event_date ASC")
        events = cursor.fetchall()
        
        # Untuk setiap event, ambil data ticketsnya
        events_with_tickets = []
        for event in events:
            cursor.execute("""
                SELECT type_name, price, quota, sold, (quota - sold) as available 
                FROM tickets 
                WHERE event_id = %s
                ORDER BY price DESC
            """, (event['id'],))
            tickets = cursor.fetchall()
            
            events_with_tickets.append({
                'id': event['id'],
                'name': event['name'],
                'location': event['location'],
                'event_date': event['event_date'],
                'status': event['status'],
                'tickets': tickets  # Tambahkan data tickets
            })
            
        events = events_with_tickets
        
    except mysql.connector.Error as err:
        print(f"Error fetching homepage events: {err}")
        events = []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template("user/homepage.html", username=session.get("username", "Pengguna"), events=events)

# ==========================
#   API ROUTES
# ==========================
@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    conn = None
    try:
        data = request.get_json()
        event_id = data['event_id']
        tickets = data['tickets']
        user_id = session['user_id']
        
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Database connection failed'}, 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Hitung total amount & validasi stok
        total_amount = 0
        ticket_details = []
        
        for ticket_type, quantity in tickets.items():
            if quantity <= 0:
                continue
                
            cursor.execute(
                "SELECT id, quota, sold, price FROM tickets WHERE event_id = %s AND type_name = %s",
                (event_id, ticket_type)
            )
            ticket = cursor.fetchone()
            
            if not ticket:
                return {'success': False, 'error': f'Ticket type {ticket_type} not found'}, 400
            
            available = ticket['quota'] - ticket['sold']
            if quantity > available:
                return {'success': False, 'error': f'Only {available} {ticket_type} tickets available'}, 400
            
            total_amount += quantity * ticket['price']
            ticket_details.append(f"{ticket_type} x{quantity}")
            
            # ⚠️⚠️⚠️ INI YANG PERLU DITAMBAH! ⚠️⚠️⚠️
            # UPDATE TICKET QUOTA DI SINI!
            cursor.execute(
                "UPDATE tickets SET sold = sold + %s WHERE event_id = %s AND type_name = %s",
                (quantity, event_id, ticket_type)
            )
        
        # Generate VA Number
        va_number = f"88{user_id:06d}{int(time.time()) % 10000:04d}"
        
        # Create payment record
        cursor.execute(
            """INSERT INTO payments 
               (user_id, event_id, payment_method, va_number, amount, status, expires_at) 
               VALUES (%s, %s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))""",
            (user_id, event_id, 'VA', va_number, total_amount, 'pending')
        )
        payment_id = cursor.lastrowid
        
        # Create order record
        cursor.execute(
            """INSERT INTO orders 
               (user_id, event_id, customer_name, customer_email, total_amount, payment_status, payment_id, ticket_details) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, event_id, session['username'], session['email'], total_amount, 'pending', payment_id, ', '.join(ticket_details))
        )
        
        conn.commit()  # ⚠️ JANGAN LUPA COMMIT!
        
        return {
            'success': True, 
            'message': 'Payment created! Please complete payment via VA',
            'payment_id': payment_id,
            'va_number': va_number,
            'amount': total_amount,
            'redirect_url': f'/payment/{payment_id}'
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Checkout error: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}, 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/payment/<int:payment_id>")
@login_required
def payment_page(payment_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT p.*, e.name as event_name, u.username 
            FROM payments p
            JOIN events e ON p.event_id = e.id
            JOIN users u ON p.user_id = u.id
            WHERE p.id = %s
        """, (payment_id,))
        payment = cursor.fetchone()
        
        if not payment:
            flash("Payment not found!", "danger")
            return redirect(url_for('homepage'))
            
        return render_template("user/payment.html", payment=payment)
        
    except Exception as e:
        print(f"Payment page error: {e}")
        return redirect(url_for('homepage'))
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

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
        
        # Ambil data tickets
        query_tickets = """
            SELECT t.*, (t.quota - t.sold) as available, e.name as event_name
            FROM tickets t
            JOIN events e ON t.event_id = e.id
            ORDER BY e.name, t.price ASC
        """
        cursor.execute(query_tickets)
        all_tickets = cursor.fetchall()

        # Ambil data users
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        
        # === TAMBAHAN: Ambil data transactions ===
        cursor.execute("""
            SELECT 
                p.*,
                e.name as event_name,
                u.username as customer_name,
                o.ticket_details,
                p.created_at as transaction_date
            FROM payments p
            JOIN events e ON p.event_id = e.id
            JOIN users u ON p.user_id = u.id
            LEFT JOIN orders o ON p.id = o.payment_id
            ORDER BY p.created_at DESC
            LIMIT 10  -- Tampilkan 10 transaksi terbaru
        """)
        transactions = cursor.fetchall()
        
        # Statistics
        cursor.execute("SELECT COUNT(*) as total FROM payments")
        total_transactions = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as paid FROM payments WHERE status = 'paid'")
        paid_transactions = cursor.fetchone()['paid']
        
        cursor.execute("SELECT SUM(amount) as revenue FROM payments WHERE status = 'paid'")
        revenue = cursor.fetchone()['revenue'] or 0

    except mysql.connector.Error as err:
        print(f"Admin panel error: {err}")
        events = []
        all_tickets = []
        users = []
        transactions = []
        total_transactions = 0
        paid_transactions = 0
        revenue = 0
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    # Kirim SEMUA data ke template (TAMBAH 4 VARIABLE BARU)
    return render_template("adminpanel.html", 
                         events=events, 
                         all_tickets=all_tickets, 
                         users=users,
                         transactions=transactions,           # BARU
                         total_transactions=total_transactions, # BARU
                         paid_transactions=paid_transactions,   # BARU
                         revenue=revenue)    
                   # BARU
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

#

# --- Quick Add Ticket (from admin panel) ---
@app.route("/admin/tickets/quick-add", methods=["POST"])
@admin_required
def add_ticket_quick():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tickets (event_id, type_name, price, quota, sold) VALUES (%s, %s, %s, %s, %s)",
            (request.form['event_id'], request.form['type_name'], request.form['price'], request.form['quota'], 0)
        )
        conn.commit()
        flash("🎫 Ticket added successfully!", "success")
    except mysql.connector.Error as err:
        flash("❌ Error adding ticket.", "danger")
        print(f"Quick add ticket error: {err}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('admin_panel'))

@app.route("/admin/mark_paid/<int:payment_id>", methods=["POST"])
@admin_required
def mark_paid(payment_id):
    """Mark payment as paid and update ticket quota"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get payment details
        cursor.execute("""
            SELECT p.*, o.ticket_details, o.id as order_id 
            FROM payments p 
            LEFT JOIN orders o ON p.id = o.payment_id 
            WHERE p.id = %s
        """, (payment_id,))
        payment = cursor.fetchone()
        
        if not payment:
            flash("Payment not found!", "danger")
            return redirect(url_for('admin_panel'))
        
        if payment['status'] == 'paid':
            flash("Payment already completed!", "warning")
            return redirect(url_for('admin_panel'))
        
        # 2. Update payment status
        cursor.execute("UPDATE payments SET status = 'paid' WHERE id = %s", (payment_id,))
        
        # 3. Update order status
        if payment['order_id']:
            cursor.execute("UPDATE orders SET payment_status = 'paid' WHERE payment_id = %s", (payment_id,))
        
        # 4. UPDATE TICKET QUOTA - INI YANG PENTING!
        # Parse ticket details dari order (contoh: "VIP x1")
        ticket_details = payment.get('ticket_details', '')
        if 'VIP' in ticket_details:
            cursor.execute("""
                UPDATE tickets 
                SET sold = sold + 1, available = quota - (sold + 1) 
                WHERE event_id = %s AND type_name = 'VIP'
            """, (payment['event_id'],))
        
        conn.commit()
        flash("✅ Payment marked as paid! Ticket quota updated.", "success")
        
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
        print(f"Mark paid error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
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

