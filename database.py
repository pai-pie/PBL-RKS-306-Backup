import mysql.connector
import os
import time
from datetime import datetime

class Database:
    def __init__(self):
        self.db_config = {
            'host': os.environ.get('DATABASE_HOST', 'localhost'),
            'user': os.environ.get('DATABASE_USER', 'root'),
            'password': os.environ.get('DATABASE_PASSWORD', 'pulupulu'),
            'database': os.environ.get('DATABASE_NAME', 'db_konser'),
            'port': os.environ.get('DATABASE_PORT', '3306')
        }

    def get_connection(self):
        """Dapatkan koneksi database"""
        try:
            return mysql.connector.connect(**self.db_config)
        except mysql.connector.Error as err:
            print(f"Database connection error: {err}")
            return None

    def execute_query(self, query, params=None, fetch=False, fetch_one=False):
        """Eksekusi query dengan error handling"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None
                
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
            elif fetch_one:
                result = cursor.fetchone()
            else:
                conn.commit()
                result = cursor.lastrowid
            
            return result
            
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    # ==========================
    #   USER OPERATIONS
    # ==========================
    
    def get_user_by_email(self, email):
        return self.execute_query(
            "SELECT * FROM users WHERE email = %s", 
            (email,), 
            fetch_one=True
        )

    def get_user_by_id(self, user_id):
        return self.execute_query(
            "SELECT * FROM users WHERE id = %s", 
            (user_id,), 
            fetch_one=True
        )

    def create_user(self, username, email, password_hash, role='user'):
        return self.execute_query(
            "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (username, email, password_hash, role)
        )

    # ==========================
    #   EVENT OPERATIONS
    # ==========================
    
    def get_events_with_tickets(self):
        """Ambil events dengan data tickets"""
        events = self.execute_query(
            "SELECT * FROM events WHERE status IN ('Active', 'Upcoming') ORDER BY event_date ASC",
            fetch=True
        ) or []
        
        events_with_tickets = []
        for event in events:
            tickets = self.execute_query(
                """SELECT type_name, price, quota, sold, (quota - sold) as available 
                   FROM tickets WHERE event_id = %s ORDER BY price DESC""",
                (event['id'],), 
                fetch=True
            ) or []
            
            events_with_tickets.append({
                'id': event['id'],
                'name': event['name'],
                'location': event['location'],
                'event_date': event['event_date'],
                'status': event['status'],
                'tickets': tickets
            })
            
        return events_with_tickets

    def get_event_by_id(self, event_id):
        return self.execute_query(
            "SELECT * FROM events WHERE id = %s", 
            (event_id,), 
            fetch_one=True
        )

    def create_event(self, name, event_date, location, status):
        return self.execute_query(
            "INSERT INTO events (name, event_date, location, status) VALUES (%s, %s, %s, %s)",
            (name, event_date, location, status)
        )

    def update_event(self, event_id, name, event_date, location, status):
        return self.execute_query(
            "UPDATE events SET name=%s, event_date=%s, location=%s, status=%s WHERE id=%s",
            (name, event_date, location, status, event_id)
        )

    def delete_event(self, event_id):
        """Delete event dengan disable foreign key checks sementara"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print(f"🔍 Attempting to delete event {event_id}")
            
            # Nonaktifkan foreign key checks sementara
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # Delete semua data terkait
            cursor.execute("DELETE FROM orders WHERE event_id = %s", (event_id,))
            print(f"📦 Deleted {cursor.rowcount} orders")
            
            cursor.execute("DELETE FROM payments WHERE event_id = %s", (event_id,))
            print(f"💰 Deleted {cursor.rowcount} payments")
            
            cursor.execute("DELETE FROM tickets WHERE event_id = %s", (event_id,))
            print(f"🎫 Deleted {cursor.rowcount} tickets")
            
            # Delete event
            cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
            deleted_rows = cursor.rowcount
            print(f"🗑️ Deleted {deleted_rows} events")
            
            # Aktifkan kembali foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            
            conn.commit()
            print(f"🎉 Event {event_id} deleted successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting event {event_id}: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    # ==========================
    #   TICKET OPERATIONS  
    # ==========================
    
    def get_tickets_by_event(self, event_id):
        return self.execute_query(
            "SELECT *, (quota - sold) as available FROM tickets WHERE event_id = %s ORDER BY price ASC",
            (event_id,), 
            fetch=True
        )

    def get_ticket_by_id(self, ticket_id):
        return self.execute_query(
            "SELECT * FROM tickets WHERE id = %s", 
            (ticket_id,), 
            fetch_one=True
        )

    def get_ticket_with_event(self, ticket_id):
        return self.execute_query(
            """SELECT t.*, e.name as event_name 
               FROM tickets t JOIN events e ON t.event_id = e.id 
               WHERE t.id = %s""",
            (ticket_id,), 
            fetch_one=True
        )

    def create_ticket(self, event_id, type_name, price, quota, sold=0):
        return self.execute_query(
            "INSERT INTO tickets (event_id, type_name, price, quota, sold) VALUES (%s, %s, %s, %s, %s)",
            (event_id, type_name, price, quota, sold)
        )

    def update_ticket(self, ticket_id, type_name, price, quota):
        return self.execute_query(
            "UPDATE tickets SET type_name=%s, price=%s, quota=%s WHERE id=%s",
            (type_name, price, quota, ticket_id)
        )

    def delete_ticket(self, ticket_id):
        return self.execute_query(
            "DELETE FROM tickets WHERE id = %s", 
            (ticket_id,)
        )

    # ==========================
    #   PAYMENT & ORDER OPERATIONS
    # ==========================
    
    def process_checkout(self, user_id, event_id, tickets, username, email):
        """Process checkout dengan transaction"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return {'success': False, 'error': 'Database connection failed'}
                
            cursor = conn.cursor(dictionary=True)
            
            # Hitung total & validasi stok
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
                    return {'success': False, 'error': f'Ticket type {ticket_type} not found'}
                
                available = ticket['quota'] - ticket['sold']
                if quantity > available:
                    return {'success': False, 'error': f'Only {available} {ticket_type} tickets available'}
                
                total_amount += quantity * ticket['price']
                ticket_details.append(f"{ticket_type} x{quantity}")
                
                # Update ticket quota
                cursor.execute(
                    "UPDATE tickets SET sold = sold + %s WHERE event_id = %s AND type_name = %s",
                    (quantity, event_id, ticket_type)
                )
            
            # Generate VA Number
            va_number = f"88{user_id:06d}{int(time.time()) % 10000:04d}"
            
            # Create payment
            cursor.execute(
                """INSERT INTO payments 
                   (user_id, event_id, payment_method, va_number, amount, status, expires_at) 
                   VALUES (%s, %s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))""",
                (user_id, event_id, 'VA', va_number, total_amount, 'pending')
            )
            payment_id = cursor.lastrowid
            
            # Create order
            cursor.execute(
                """INSERT INTO orders 
                   (user_id, event_id, customer_name, customer_email, total_amount, payment_status, payment_id, ticket_details) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, event_id, username, email, total_amount, 'pending', payment_id, ', '.join(ticket_details))
            )
            
            conn.commit()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'va_number': va_number,
                'total_amount': total_amount
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Checkout processing error: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_payment_with_details(self, payment_id):
        return self.execute_query(
            """SELECT p.*, e.name as event_name, u.username 
               FROM payments p
               JOIN events e ON p.event_id = e.id
               JOIN users u ON p.user_id = u.id
               WHERE p.id = %s""",
            (payment_id,), 
            fetch_one=True
        )

    def mark_payment_as_paid(self, payment_id):
        """Mark payment as paid dengan transaction"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get payment details
            cursor.execute("""
                SELECT p.*, o.ticket_details, o.id as order_id 
                FROM payments p 
                LEFT JOIN orders o ON p.id = o.payment_id 
                WHERE p.id = %s
            """, (payment_id,))
            payment = cursor.fetchone()
            
            if not payment:
                return {'success': False, 'error': 'Payment not found'}
            
            if payment['status'] == 'paid':
                return {'success': False, 'error': 'Payment already completed'}
            
            # Update payment status
            cursor.execute("UPDATE payments SET status = 'paid' WHERE id = %s", (payment_id,))
            
            # Update order status
            if payment['order_id']:
                cursor.execute("UPDATE orders SET payment_status = 'paid' WHERE payment_id = %s", (payment_id,))
            
            conn.commit()
            return {'success': True}
            
        except Exception as e:
            if conn:
                conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    # ==========================
    #   ORDER OPERATIONS
    # ==========================
    
    def get_orders_by_user(self, user_id):
        return self.execute_query(
            """SELECT o.*, e.name as event_name, e.event_date, e.location
               FROM orders o 
               JOIN events e ON o.event_id = e.id 
               WHERE o.user_id = %s 
               ORDER BY o.created_at DESC""",
            (user_id,), 
            fetch=True
        )

    def get_all_orders(self):
        return self.execute_query(
            """SELECT o.*, e.name as event_name, u.username, e.event_date
               FROM orders o 
               JOIN events e ON o.event_id = e.id 
               JOIN users u ON o.user_id = u.id 
               ORDER BY o.created_at DESC""",
            fetch=True
        )

    # ==========================
    #   ADMIN DASHBOARD DATA
    # ==========================
    
    def get_admin_dashboard_data(self):
        """Ambil semua data untuk admin dashboard"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get events
            cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
            events = cursor.fetchall()
            
            # Get tickets with event names
            cursor.execute("""
                SELECT t.*, (t.quota - t.sold) as available, e.name as event_name
                FROM tickets t JOIN events e ON t.event_id = e.id
                ORDER BY e.name, t.price ASC
            """)
            all_tickets = cursor.fetchall()
            
            # Get users
            cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
            users = cursor.fetchall()
            
            # Get recent transactions
            cursor.execute("""
                SELECT p.*, e.name as event_name, u.username as customer_name,
                       o.ticket_details, p.created_at as transaction_date
                FROM payments p
                JOIN events e ON p.event_id = e.id
                JOIN users u ON p.user_id = u.id
                LEFT JOIN orders o ON p.id = o.payment_id
                ORDER BY p.created_at DESC LIMIT 10
            """)
            transactions = cursor.fetchall()
            
            # Get transaction stats
            cursor.execute("SELECT COUNT(*) as total FROM payments")
            total_transactions = cursor.fetchone()['total'] or 0
            
            cursor.execute("SELECT COUNT(*) as paid FROM payments WHERE status = 'paid'")
            paid_transactions = cursor.fetchone()['paid'] or 0
            
            cursor.execute("SELECT SUM(amount) as revenue FROM payments WHERE status = 'paid'")
            revenue_result = cursor.fetchone()
            revenue = revenue_result['revenue'] if revenue_result['revenue'] else 0
            
            return {
                'events': events or [],
                'all_tickets': all_tickets or [],
                'users': users or [],
                'transactions': transactions or [],
                'total_transactions': total_transactions,
                'paid_transactions': paid_transactions,
                'revenue': revenue
            }
            
        except Exception as e:
            print(f"Error getting admin dashboard data: {e}")
            return {
                'events': [],
                'all_tickets': [],
                'users': [],
                'transactions': [],
                'total_transactions': 0,
                'paid_transactions': 0,
                'revenue': 0
            }
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    # ==========================
    #   ADDITIONAL METHODS
    # ==========================
    
    def get_event_stats(self):
        """Get statistics for events"""
        return self.execute_query(
            """SELECT 
                   COUNT(*) as total_events,
                   SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_events,
                   SUM(CASE WHEN status = 'Upcoming' THEN 1 ELSE 0 END) as upcoming_events,
                   SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_events
               FROM events""",
            fetch_one=True
        )

    def get_user_stats(self):
        """Get statistics for users"""
        return self.execute_query(
            """SELECT 
                   COUNT(*) as total_users,
                   SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_users,
                   SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) as regular_users
               FROM users""",
            fetch_one=True
        )