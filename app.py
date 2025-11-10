from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
import time
from datetime import datetime

from database import Database
from models import User, Event, Ticket, Payment, Order
from auth import login_required, admin_required

class GuardianTixApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
        self.db = Database()
        
        self.setup_routes()
        self.create_admin_user()

    def setup_routes(self):
        """Setup semua routes aplikasi"""
        # Homepage & Auth
        self.app.route("/")(self.homepage)
        self.app.route("/homepage")(self.homepage)
        self.app.route("/register", methods=["GET", "POST"])(self.register)
        self.app.route("/login", methods=["GET", "POST"])(self.login)
        self.app.route("/logout")(self.logout)
        
        # User Routes
        self.app.route("/concert")(self.concert)
        self.app.route("/account")(self.account)
        self.app.route("/payment/<int:payment_id>")(self.payment_page)
        self.app.route("/success")(self.payment_success)  

        # API Routes
        self.app.route("/checkout", methods=["POST"])(self.checkout)
        
        # Admin Routes
        self.app.route("/admin")(self.admin_panel)
        self.app.route("/admin/events/add", methods=["GET", "POST"])(self.add_event)
        self.app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])(self.edit_event)
        self.app.route("/admin/events/delete/<int:event_id>", methods=["POST"])(self.delete_event)
        self.app.route("/admin/events/<int:event_id>/tickets")(self.manage_tickets)
        self.app.route("/admin/events/<int:event_id>/tickets/add", methods=["GET", "POST"])(self.add_ticket)
        self.app.route("/admin/tickets/edit/<int:ticket_id>", methods=["GET", "POST"])(self.edit_ticket)
        self.app.route("/admin/tickets/delete/<int:ticket_id>", methods=["POST"])(self.delete_ticket)
        self.app.route("/admin/tickets/quick-add", methods=["POST"])(self.add_ticket_quick)
        self.app.route("/admin/mark_paid/<int:payment_id>", methods=["POST"])(self.mark_paid)

        # ==========================
        #   API ROUTES BARU - TAMBAHKAN INI
        # ==========================
        self.app.route("/api/update_profile", methods=["POST"])(self.update_profile)
        self.app.route("/api/user_tickets")(self.api_user_tickets)
        self.app.route("/api/user_stats")(self.api_user_stats)
        self.app.route("/api/cancel_ticket/<int:ticket_id>", methods=["POST"])(self.cancel_ticket)
        self.app.route("/api/admin/update_user_role/<int:user_id>", methods=["POST"])(self.update_user_role)

    def create_admin_user(self):
        """Buat admin user jika belum ada"""
        admin_email = "admin@guardiantix.com"
        admin_user = self.db.get_user_by_email(admin_email)
        
        if not admin_user:
            password_hash = generate_password_hash('admin123')
            self.db.create_user("System Admin", admin_email, password_hash, "admin")
            print("Admin user created successfully.")

    # ==========================
    #   ROUTE HANDLERS - AUTH
    # ==========================
    
    @login_required
    def homepage(self):
        if session.get("role") == "admin":
            return redirect(url_for("admin_panel"))

        events_data = self.db.get_events_with_tickets()
        return render_template("user/homepage.html", 
                             username=session.get("username", "Pengguna"), 
                             events=events_data)

    def register(self):
        if request.method == "POST":
            username = request.form["username"].strip()
            email = request.form["email"].strip()
            password = request.form["password"].strip()
            
            existing_user = self.db.get_user_by_email(email)
            if existing_user:
                flash("Email already registered!", "error")
                return render_template("user/register.html")

            password_hash = generate_password_hash(password)
            if self.db.create_user(username, email, password_hash):
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for("login"))
            else:
                flash("An error occurred during registration.", "danger")
            
        return render_template("user/register.html")

    def login(self):
        if request.method == "POST":
            email = request.form["email"].strip()
            password = request.form["password"].strip()
            
            user = self.db.get_user_by_email(email)
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["email"] = user["email"]
                session["role"] = user["role"]
                flash(f"Welcome back, {user['username']}!", "success")
                
                if user["role"] == 'admin':
                    return redirect(url_for("admin_panel"))
                else:
                    return redirect(url_for("homepage"))
            else:
                flash("Invalid email or password!", "danger")
                
        return render_template("user/login.html")

    def logout(self):
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    # ==========================
    #   ROUTE HANDLERS - USER
    # ==========================
    
    @login_required
    def concert(self):
        return render_template("user/concert.html")

    @login_required
    def account(self):
        user = self.db.get_user_by_id(session['user_id'])
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

    @login_required
    def payment_page(self, payment_id):
        payment = self.db.get_payment_with_details(payment_id)
        if not payment:
            flash("Payment not found!", "danger")
            return redirect(url_for('homepage'))
            
        return render_template("user/payment.html", payment=payment)

    @login_required
    def payment_success(self):
        payment_method = request.args.get('method', 'Unknown')
        return render_template("user/success.html", 
                         payment_method=payment_method,
                         username=session.get("username", "User"))

    # ==========================
    #   ROUTE HANDLERS - API
    # ==========================
    
    @login_required
    def checkout(self):
        try:
            data = request.get_json()
            event_id = data['event_id']
            tickets = data['tickets']
            payment_method = data.get('payment_method', 'BCA')
            user_id = session['user_id']
        
            # Kirim payment_method ke database
            result = self.db.process_checkout(user_id, event_id, tickets, session['username'], session['email'], payment_method)
        
            if result['success']:
                return {
                    'success': True, 
                    'message': '🎫 Order confirmed! Please complete payment.',
                    'payment_id': result['payment_id'],
                    'va_number': result['va_number'],
                    'amount': result['total_amount'],
                    'redirect_url': f'/payment/{result["payment_id"]}'
                }
            else:
                return {'success': False, 'error': result['error']}, 400
            
        except Exception as e:
            print(f"❌ Checkout error: {str(e)}")
            return {'success': False, 'error': f'System error: {str(e)}'}, 500

    # ==========================
    #   API ROUTES BARU - TAMBAHKAN INI
    # ==========================
    
    @login_required
    def update_profile(self):
        """Update user profile data"""
        try:
            user_id = session['user_id']
            data = request.get_json()
            
            print(f"🎯 DEBUG update_profile called")
            print(f"🎯 User ID: {user_id}")
            print(f"🎯 Request data: {data}")
            
            # Validasi data wajib
            if not data.get('name') or not data.get('email'):
                print("❌ Missing name or email")
                return jsonify({
                    'success': False, 
                    'error': 'Name and email are required'
                }), 400
            
            # Cek jika email sudah dipakai oleh user lain
            existing_user = self.db.get_user_by_email(data.get('email'))
            print(f"🎯 Existing user check: {existing_user}")
            
            if existing_user and existing_user['id'] != user_id:
                print("❌ Email already used by another user")
                return jsonify({
                    'success': False, 
                    'error': 'Email already used by another account'
                }), 400
            
            # Update user data in database
            print("🎯 Calling database update...")
            result = self.db.update_user_profile(
                user_id,
                data.get('name'),
                data.get('email'),
                data.get('status', 'Regular Member')
            )
            
            print(f"🎯 Database update result: {result}")
            
            if result:
                # Update session data
                session['username'] = data.get('name')
                session['email'] = data.get('email')
                
                print("✅ Profile updated successfully")
                return jsonify({
                    'success': True, 
                    'message': 'Profile updated successfully!'
                })
            else:
                print("❌ Database update failed")
                return jsonify({
                    'success': False, 
                    'error': 'Failed to update profile in database'
                }), 400
                
        except Exception as e:
            print(f"❌ Profile update error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False, 
                'error': f'System error: {str(e)}'
            }), 500

    @login_required
    def api_user_tickets(self):
        """Get user tickets data"""
        try:
            user_id = session['user_id']
            tickets = self.db.get_user_tickets(user_id)
            
            return jsonify({
                'success': True,
                'tickets': tickets
            })
        except Exception as e:
            print(f"Tickets fetch error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch tickets'
            }), 500

    @login_required
    def api_user_stats(self):
        """Get user statistics"""
        try:
            user_id = session['user_id']
            stats = self.db.get_user_detailed_stats(user_id)
            
            return jsonify({
                'success': True,
                'stats': stats
            })
        except Exception as e:
            print(f"Stats fetch error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch user stats'
            }), 500

    @login_required
    def cancel_ticket(self, ticket_id):
        """Cancel user ticket"""
        try:
            user_id = session['user_id']
            result = self.db.cancel_user_ticket(user_id, ticket_id)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Ticket cancelled successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 400
                
        except Exception as e:
            print(f"Ticket cancellation error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to cancel ticket'
            }), 500

    @admin_required
    def update_user_role(self, user_id):
        """Update user role (admin function)"""
        try:
            data = request.get_json()
            new_role = data.get('role')
            
            if new_role not in ['user', 'admin']:
                return jsonify({'success': False, 'error': 'Invalid role'}), 400
            
            # Update role in database
            result = self.db.execute_query(
                "UPDATE users SET role = %s WHERE id = %s",
                (new_role, user_id)
            )
            
            if result:
                return jsonify({'success': True, 'message': 'User role updated'})
            else:
                return jsonify({'success': False, 'error': 'Failed to update role'}), 400
                
        except Exception as e:
            print(f"Role update error: {str(e)}")
            return jsonify({'success': False, 'error': 'System error'}), 500

    # ==========================
    #   ROUTE HANDLERS - ADMIN
    # ==========================
    
    @admin_required
    def admin_panel(self):
        data = self.db.get_admin_dashboard_data()
        return render_template("adminpanel.html", **data)

    @admin_required
    def add_event(self):
        if request.method == "POST":
            if self.db.create_event(
                request.form['name'],
                request.form['event_date'],
                request.form['location'],
                request.form['status']
            ):
                flash("Event added successfully!", "success")
            else:
                flash("Error adding event.", "danger")
            return redirect(url_for('admin_panel'))
        return render_template("add_event.html")

    @admin_required
    def edit_event(self, event_id):
        if request.method == "POST":
            if self.db.update_event(
                event_id,
                request.form['name'],
                request.form['event_date'],
                request.form['location'],
                request.form['status']
            ):
                flash("Event updated successfully!", "success")
            else:
                flash("Error updating event.", "danger")
            return redirect(url_for('admin_panel'))

        event = self.db.get_event_by_id(event_id)
        if not event:
            flash("Event not found!", "danger")
            return redirect(url_for('admin_panel'))
            
        if isinstance(event.get('event_date'), datetime):
            event['event_date'] = event['event_date'].strftime('%Y-%m-%d')
        return render_template("edit_event.html", event=event)

    @admin_required
    def delete_event(self, event_id):
        if self.db.delete_event(event_id):
            flash("Event and all associated tickets have been deleted.", "success")
        else:
            flash("Error deleting event.", "danger")
        return redirect(url_for('admin_panel'))

    @admin_required
    def manage_tickets(self, event_id):
        event = self.db.get_event_by_id(event_id)
        if not event:
            flash("Event not found!", "danger")
            return redirect(url_for('admin_panel'))

        tickets = self.db.get_tickets_by_event(event_id)
        return render_template("manage_tickets.html", event=event, tickets=tickets)

    @admin_required
    def add_ticket(self, event_id):
        if request.method == "POST":
            if self.db.create_ticket(
                event_id,
                request.form['type_name'],
                request.form['price'],
                request.form['quota']
            ):
                flash("Ticket type added successfully!", "success")
            else:
                flash("Error adding ticket.", "danger")
            return redirect(url_for('manage_tickets', event_id=event_id))

        event = self.db.get_event_by_id(event_id)
        if not event:
            flash("Event not found!", "danger")
            return redirect(url_for('admin_panel'))

        return render_template("add_ticket.html", event=event)

    @admin_required
    def edit_ticket(self, ticket_id):
        if request.method == "POST":
            if self.db.update_ticket(
                ticket_id,
                request.form['type_name'],
                request.form['price'],
                request.form['quota']
            ):
                flash("Ticket type updated successfully!", "success")
            else:
                flash("Error updating ticket.", "danger")
            
            ticket = self.db.get_ticket_by_id(ticket_id)
            return redirect(url_for('manage_tickets', event_id=ticket['event_id']))

        ticket = self.db.get_ticket_with_event(ticket_id)
        if not ticket:
            flash("Ticket type not found!", "danger")
            return redirect(url_for('admin_panel'))
            
        return render_template("edit_ticket.html", ticket=ticket)

    @admin_required
    def delete_ticket(self, ticket_id):
        ticket = self.db.get_ticket_by_id(ticket_id)
        event_id = ticket['event_id'] if ticket else None
        
        if self.db.delete_ticket(ticket_id):
            flash("Ticket type deleted.", "success")
        else:
            flash("Error deleting ticket.", "danger")
            
        return redirect(url_for('manage_tickets', event_id=event_id)) if event_id else redirect(url_for('admin_panel'))

    @admin_required
    def add_ticket_quick(self):
        if self.db.create_ticket(
            request.form['event_id'],
            request.form['type_name'],
            request.form['price'],
            request.form['quota']
        ):
            flash("🎫 Ticket added successfully!", "success")
        else:
            flash("❌ Error adding ticket.", "danger")
        return redirect(url_for('admin_panel'))

    @admin_required
    def mark_paid(self, payment_id):
        result = self.db.mark_payment_as_paid(payment_id)
        if result['success']:
            flash("✅ Payment marked as paid! Ticket quota updated.", "success")
        else:
            flash(f"❌ Error: {result['error']}", "danger")
        return redirect(url_for('admin_panel'))

    def run(self, host='0.0.0.0', port=5000, debug=True):
        self.app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    app_instance = GuardianTixApp()
    app_instance.run()