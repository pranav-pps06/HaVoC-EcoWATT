from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import sqlite3
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import atexit
from datetime import datetime, timedelta
from functools import wraps
from simulation_service import simulator
import os
import re

# Configure SQLite to handle datetime properly
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("DATETIME", lambda s: datetime.fromisoformat(s.decode('utf-8')))

app = Flask(__name__)
app.secret_key = 'your-super-secret-key-change-this-in-production'  # Change this to a secure secret key

# Database configuration
DATABASE = 'havoc_ecowatt.db'

# Email configuration (update with your SMTP settings)
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'your-email@gmail.com',  # Update with your email
    'password': 'your-app-password',   # Update with your app password
    'from_name': 'HaVoC-EcoWATT'
}

def get_db_connection():
    """Get database connection with row factory and datetime parsing"""
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return salt + password_hash.hex()

def verify_password(password, hashed):
    """Verify password against hash"""
    salt = hashed[:32]
    stored_password = hashed[32:]
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return password_hash.hex() == stored_password

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    return True, "Valid password"

def send_email(to_email, subject, body, is_html=False):
    """Send email using SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{EMAIL_CONFIG['from_name']} <{EMAIL_CONFIG['email']}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        text = msg.as_string()
        server.sendmail(EMAIL_CONFIG['email'], to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_database():
    """Initialize the database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            phone VARCHAR(20),
            address TEXT,
            city VARCHAR(50),
            state VARCHAR(50),
            zip_code VARCHAR(10),
            is_active BOOLEAN DEFAULT 1,
            email_verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP
        )
    ''')
    
    # Create password reset tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create user sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token VARCHAR(255) UNIQUE NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create email verification tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create user preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            theme VARCHAR(20) DEFAULT 'light',
            notifications_enabled BOOLEAN DEFAULT 1,
            email_notifications BOOLEAN DEFAULT 1,
            energy_goal DECIMAL(10,2) DEFAULT 0,
            cost_goal DECIMAL(10,2) DEFAULT 0,
            carbon_goal DECIMAL(10,2) DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'INR',
            timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database tables initialized successfully")

# Initialize database and start simulation
def startup():
    init_database()
    simulator.start()
    print("Application started with IoT simulation")

# Stop simulation when app shuts down
def cleanup():
    simulator.stop()

atexit.register(cleanup)

# ============= ROUTE HANDLERS =============

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

# ============= AUTHENTICATION ROUTES =============

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    remember_me = request.form.get('remember_me') == 'on'
    
    print(f"Login attempt - Username: {username}, Password length: {len(password)}")
    
    if not username or not password:
        flash('Please enter both username and password.', 'error')
        return render_template('login.html')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get user by username or email
        cursor.execute('''
            SELECT id, password, failed_login_attempts, locked_until, email, first_name, last_name, is_active
            FROM users 
            WHERE (username = ? OR email = ?) AND is_active = 1
        ''', (username, username))
        
        user = cursor.fetchone()
        print(f"User found: {user is not None}")
        
        if not user:
            flash('Invalid username or password.', 'error')
            conn.close()
            return render_template('login.html')
        
        # Check if account is locked
        if user['locked_until']:
            try:
                locked_until = user['locked_until']
                if isinstance(locked_until, str):
                    locked_until = datetime.fromisoformat(locked_until)
                if datetime.now() < locked_until:
                    flash('Account is temporarily locked due to multiple failed login attempts. Please try again later.', 'error')
                    conn.close()
                    return render_template('login.html')
            except (ValueError, TypeError):
                # Clear invalid locked_until value
                cursor.execute('UPDATE users SET locked_until = NULL WHERE id = ?', (user['id'],))
        
        # Verify password
        password_valid = verify_password(password, user['password'])
        print(f"Password valid: {password_valid}")
        
        if password_valid:
            # Successful login
            session['user_id'] = user['id']
            session['username'] = username
            session['user_email'] = user['email']
            first_name = user['first_name'] or ''
            last_name = user['last_name'] or ''
            session['user_name'] = f"{first_name} {last_name}".strip() or username
            
            print(f"Session created for user ID: {user['id']}")
            
            # Reset failed login attempts
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = 0, locked_until = NULL, last_login = ?
                WHERE id = ?
            ''', (datetime.now(), user['id']))
            
            # Create session record
            session_token = secrets.token_urlsafe(32)
            session['session_token'] = session_token
            expires_at = datetime.now() + timedelta(days=30 if remember_me else 1)
            
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user['id'], session_token, request.remote_addr or 'unknown', 
                  str(request.user_agent) if request.user_agent else 'unknown', expires_at))
            
            conn.commit()
            conn.close()
            
            print(f"Redirecting to dashboard for user: {session['user_name']}")
            flash(f'Welcome back, {session["user_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            # Failed login
            failed_attempts = (user['failed_login_attempts'] or 0) + 1
            locked_until = None
            
            # Lock account after 5 failed attempts
            if failed_attempts >= 5:
                locked_until = datetime.now() + timedelta(minutes=30)
                flash('Account locked due to multiple failed login attempts. Please try again in 30 minutes.', 'error')
            else:
                flash(f'Invalid username or password. {5 - failed_attempts} attempts remaining.', 'error')
            
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = ?, locked_until = ?
                WHERE id = ?
            ''', (failed_attempts, locked_until, user['id']))
            
            conn.commit()
            conn.close()
            
            return render_template('login.html')
            
    except Exception as e:
        print(f"Login error: {e}")
        flash('An error occurred during login. Please try again.', 'error')
        if conn:
            conn.close()
        return render_template('login.html')

@app.route("/newuser", methods=['GET', 'POST'])
def newuser():
    if request.method == 'GET':
        return render_template('newuser.html')
    
    # Get form data
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    zip_code = request.form.get('zip_code', '').strip()
    terms_accepted = request.form.get('terms') == 'on'
    
    # Validation
    errors = []
    
    if not username or len(username) < 3:
        errors.append('Username must be at least 3 characters long.')
    
    if not validate_email(email):
        errors.append('Please enter a valid email address.')
    
    if not password:
        errors.append('Password is required.')
    else:
        is_valid, message = validate_password(password)
        if not is_valid:
            errors.append(message)
    
    if password != confirm_password:
        errors.append('Passwords do not match.')
    
    if not first_name:
        errors.append('First name is required.')
    
    if not terms_accepted:
        errors.append('You must accept the Terms of Service and Privacy Policy.')
    
    if errors:
        for error in errors:
            flash(error, 'error')
        return render_template('newuser.html')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if username or email already exists
    cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
    if cursor.fetchone():
        flash('Username or email already exists. Please choose a different one.', 'error')
        conn.close()
        return render_template('newuser.html')
    
    try:
        # Create new user
        hashed_password = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, email, password, first_name, last_name, phone, address, city, state, zip_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, hashed_password, first_name, last_name, phone, address, city, state, zip_code))
        
        user_id = cursor.lastrowid
        
        # Create user preferences
        cursor.execute('''
            INSERT INTO user_preferences (user_id)
            VALUES (?)
        ''', (user_id,))
        
        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=24)
        
        cursor.execute('''
            INSERT INTO email_verification_tokens (user_id, token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, verification_token, expires_at))
        
        conn.commit()
        
        # Send verification email
        verification_link = url_for('verify_email', token=verification_token, _external=True)
        email_body = f"""
        Welcome to HaVoC-EcoWATT!
        
        Thank you for registering with us. Please click the link below to verify your email address:
        
        {verification_link}
        
        This link will expire in 24 hours.
        
        If you didn't create an account with us, please ignore this email.
        
        Best regards,
        The HaVoC-EcoWATT Team
        """
        
        if send_email(email, 'Verify Your Email - HaVoC-EcoWATT', email_body):
            flash('Account created successfully! Please check your email to verify your account.', 'success')
        else:
            flash('Account created successfully! However, we could not send the verification email. Please contact support.', 'warning')
        
        conn.close()
        return redirect(url_for('login'))
        
    except Exception as e:
        conn.rollback()
        conn.close()
        flash('An error occurred while creating your account. Please try again.', 'error')
        return render_template('newuser.html')

@app.route("/forgotpassword", methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'GET':
        return render_template('forgotpassword.html')
    
    email = request.form.get('email', '').strip().lower()
    
    if not validate_email(email):
        flash('Please enter a valid email address.', 'error')
        return render_template('forgotpassword.html')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if email exists
    cursor.execute('SELECT id, username, first_name FROM users WHERE email = ? AND is_active = 1', (email,))
    user = cursor.fetchone()
    
    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        
        cursor.execute('''
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (?, ?, ?)
        ''', (user['id'], reset_token, expires_at))
        
        conn.commit()
        
        # Send reset email
        reset_link = url_for('reset_password', token=reset_token, _external=True)
        email_body = f"""
        Hello {user['first_name'] or user['username']},
        
        You have requested to reset your password for HaVoC-EcoWATT.
        
        Please click the link below to reset your password:
        
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you didn't request this password reset, please ignore this email and your password will remain unchanged.
        
        Best regards,
        The HaVoC-EcoWATT Team
        """
        
        if send_email(email, 'Reset Your Password - HaVoC-EcoWATT', email_body):
            flash('Password reset instructions have been sent to your email address.', 'success')
        else:
            flash('Unable to send reset email. Please try again later.', 'error')
    else:
        # Don't reveal if email exists or not for security
        flash('If an account with that email exists, password reset instructions have been sent.', 'info')
    
    conn.close()
    return render_template('forgotpassword.html')

@app.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify token
    cursor.execute('''
        SELECT prt.id, prt.user_id, u.username, u.email
        FROM password_reset_tokens prt
        JOIN users u ON prt.user_id = u.id
        WHERE prt.token = ? AND prt.expires_at > ? AND prt.used = 0
    ''', (token, datetime.now()))
    
    token_data = cursor.fetchone()
    
    if not token_data:
        flash('Invalid or expired password reset link.', 'error')
        conn.close()
        return redirect(url_for('forgotpassword'))
    
    if request.method == 'GET':
        conn.close()
        return render_template('reset_password.html', token=token)
    
    # Handle password reset
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not password:
        flash('Password is required.', 'error')
        conn.close()
        return render_template('reset_password.html', token=token)
    
    is_valid, message = validate_password(password)
    if not is_valid:
        flash(message, 'error')
        conn.close()
        return render_template('reset_password.html', token=token)
    
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        conn.close()
        return render_template('reset_password.html', token=token)
    
    try:
        # Update password
        hashed_password = hash_password(password)
        cursor.execute('''
            UPDATE users 
            SET password = ?, failed_login_attempts = 0, locked_until = NULL
            WHERE id = ?
        ''', (hashed_password, token_data['user_id']))
        
        # Mark token as used
        cursor.execute('''
            UPDATE password_reset_tokens 
            SET used = 1 
            WHERE id = ?
        ''', (token_data['id'],))
        
        # Invalidate all user sessions
        cursor.execute('''
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE user_id = ?
        ''', (token_data['user_id'],))
        
        conn.commit()
        conn.close()
        
        flash('Your password has been reset successfully. Please log in with your new password.', 'success')
        return redirect(url_for('login'))
        
    except Exception as e:
        conn.rollback()
        conn.close()
        flash('An error occurred while resetting your password. Please try again.', 'error')
        return render_template('reset_password.html', token=token)

@app.route("/verify-email/<token>")
def verify_email(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify token
    cursor.execute('''
        SELECT evt.id, evt.user_id, u.username, u.email
        FROM email_verification_tokens evt
        JOIN users u ON evt.user_id = u.id
        WHERE evt.token = ? AND evt.expires_at > ? AND evt.used = 0
    ''', (token, datetime.now()))
    
    token_data = cursor.fetchone()
    
    if not token_data:
        flash('Invalid or expired email verification link.', 'error')
        conn.close()
        return redirect(url_for('login'))
    
    try:
        # Mark email as verified
        cursor.execute('''
            UPDATE users 
            SET email_verified = 1 
            WHERE id = ?
        ''', (token_data['user_id'],))
        
        # Mark token as used
        cursor.execute('''
            UPDATE email_verification_tokens 
            SET used = 1 
            WHERE id = ?
        ''', (token_data['id'],))
        
        conn.commit()
        conn.close()
        
        flash('Your email has been verified successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    except Exception as e:
        conn.rollback()
        conn.close()
        flash('An error occurred while verifying your email. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route("/logout")
def logout():
    if 'user_id' in session:
        # Invalidate session in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE user_id = ?
        ''', (session['user_id'],))
        conn.commit()
        conn.close()
    
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

# ============= DASHBOARD ROUTES =============

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route("/appliances")
@login_required
def appliances():
    return render_template('appliances.html')

@app.route("/analytics")
@login_required
def analytics():
    return render_template('analytics.html')

@app.route("/scheduling")
@login_required
def scheduling():
    return render_template('scheduling.html')

@app.route("/reports")
@login_required
def reports():
    return render_template('reports.html')

@app.route("/settings")
@login_required
def settings():
    return render_template('settings.html')

# ============= API ROUTES =============

@app.route('/api/user/profile')
@login_required
def get_user_profile():
    """Get user profile information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.username, u.email, u.first_name, u.last_name, u.phone, 
               u.address, u.city, u.state, u.zip_code, u.created_at, u.last_login,
               up.theme, up.notifications_enabled, up.email_notifications, 
               up.energy_goal, up.cost_goal, up.carbon_goal, up.currency, up.timezone
        FROM users u
        LEFT JOIN user_preferences up ON u.id = up.user_id
        WHERE u.id = ?
    ''', (session['user_id'],))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'success': True,
            'user': dict(user)
        })
    else:
        return jsonify({'success': False, 'error': 'User not found'}), 404

@app.route('/api/user/profile', methods=['POST'])
@login_required
def update_user_profile():
    """Update user profile information"""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update user basic info
        cursor.execute('''
            UPDATE users 
            SET first_name = ?, last_name = ?, phone = ?, address = ?, city = ?, state = ?, zip_code = ?
            WHERE id = ?
        ''', (
            data.get('first_name'), data.get('last_name'), data.get('phone'),
            data.get('address'), data.get('city'), data.get('state'), data.get('zip_code'),
            session['user_id']
        ))
        
        # Update preferences
        cursor.execute('''
            UPDATE user_preferences 
            SET theme = ?, notifications_enabled = ?, email_notifications = ?, 
                energy_goal = ?, cost_goal = ?, carbon_goal = ?, currency = ?, timezone = ?,
                updated_at = ?
            WHERE user_id = ?
        ''', (
            data.get('theme'), data.get('notifications_enabled'), data.get('email_notifications'),
            data.get('energy_goal'), data.get('cost_goal'), data.get('carbon_goal'),
            data.get('currency'), data.get('timezone'), datetime.now(),
            session['user_id']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/appliances/<int:user_id>')
@login_required
def get_user_appliances(user_id):
    """Get all appliances for a specific user"""
    # Ensure user can only access their own data
    if user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT a.*, 
               ad.is_on, ad.temperature, ad.power_consumption, ad.timestamp
        FROM appliances a
        LEFT JOIN appliance_data ad ON a.id = ad.appliance_id
        WHERE a.user_id = ? AND a.is_active = 1
        AND (ad.id IS NULL OR ad.id = (
            SELECT MAX(id) FROM appliance_data 
            WHERE appliance_id = a.id
        ))
        ORDER BY a.name
    ''', (user_id,))
    
    appliances = []
    for row in cursor.fetchall():
        appliances.append({
            'id': row['id'],
            'name': row['name'],
            'type': row['type'],
            'power_rating': row['power_rating'],
            'is_on': row['is_on'] if row['is_on'] is not None else False,
            'temperature': row['temperature'],
            'power_consumption': row['power_consumption'] if row['power_consumption'] is not None else 0,
            'last_updated': row['timestamp']
        })
    
    conn.close()
    return jsonify(appliances)

@app.route('/api/dashboard-data/<int:user_id>')
@login_required
def get_dashboard_data(user_id):
    """Get comprehensive dashboard data for a user"""
    # Ensure user can only access their own data
    if user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get latest appliance data
    cursor.execute('''
        SELECT a.id, a.name, a.type,
               ad.is_on, ad.temperature, ad.power_consumption
        FROM appliances a
        LEFT JOIN appliance_data ad ON a.id = ad.appliance_id
        WHERE a.user_id = ? AND a.is_active = 1
        AND (ad.id IS NULL OR ad.id = (
            SELECT MAX(id) FROM appliance_data 
            WHERE appliance_id = a.id
        ))
    ''', (user_id,))
    
    appliances = [dict(row) for row in cursor.fetchall()]
    
    # Calculate total power consumption
    total_power = sum(app.get('power_consumption', 0) for app in appliances)
    
    # Count active appliances
    active_count = sum(1 for app in appliances if app.get('is_on'))
    
    # Get hourly usage for the last 24 hours
    cursor.execute('''
        SELECT strftime('%H', timestamp) as hour,
               AVG(power_consumption) as avg_power
        FROM appliance_data
        WHERE user_id = ? 
        AND timestamp >= datetime('now', '-24 hours')
        GROUP BY strftime('%H', timestamp)
        ORDER BY hour
    ''', (user_id,))
    
    hourly_usage = [dict(row) for row in cursor.fetchall()]
    
    # Get daily usage for the last 7 days
    cursor.execute('''
        SELECT DATE(timestamp) as date,
               SUM(power_consumption) / 1000.0 as daily_kwh
        FROM appliance_data
        WHERE user_id = ? 
        AND timestamp >= datetime('now', '-7 days')
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (user_id,))
    
    daily_usage = [dict(row) for row in cursor.fetchall()]
    
    # Get monthly cost estimate (simplified calculation)
    cursor.execute('''
        SELECT AVG(power_consumption) as avg_power
        FROM appliance_data
        WHERE user_id = ? 
        AND timestamp >= datetime('now', '-30 days')
    ''', (user_id,))
    
    avg_power_result = cursor.fetchone()
    avg_power = avg_power_result['avg_power'] if avg_power_result['avg_power'] else 0
    
    # Calculate estimated monthly cost (avg_power * 24 hours * 30 days * rate per kWh)
    estimated_monthly_cost = (avg_power * 24 * 30 / 1000) * 5.8  # 5.8 INR per kWh
    
    conn.close()
    
    return jsonify({
        'appliances': appliances,
        'total_power': round(total_power, 2),
        'active_count': active_count,
        'total_count': len(appliances),
        'hourly_usage': hourly_usage,
        'daily_usage': daily_usage,
        'estimated_monthly_cost': round(estimated_monthly_cost, 2),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/add-appliance', methods=['POST'])
@login_required
def add_appliance():
    """Add a new appliance for a user"""
    data = request.json
    user_id = session['user_id']  # Use session user ID for security
    name = data.get('name')
    appliance_type = data.get('type')
    power_rating = data.get('power_rating', 0)
    
    if not all([name, appliance_type]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate appliance type
    valid_types = ['air_conditioner', 'refrigerator', 'washing_machine', 'water_heater', 
                   'television', 'microwave', 'dishwasher']
    if appliance_type not in valid_types:
        return jsonify({'error': 'Invalid appliance type'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO appliances (user_id, name, type, power_rating)
            VALUES (?, ?, ?, ?)
        ''', (user_id, name, appliance_type, power_rating))
        
        appliance_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'appliance_id': appliance_id,
            'message': f'Appliance "{name}" added successfully'
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appliance/<int:appliance_id>', methods=['DELETE'])
@login_required
def delete_appliance(appliance_id):
    """Delete an appliance"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify appliance belongs to current user
    cursor.execute('''
        SELECT id FROM appliances 
        WHERE id = ? AND user_id = ?
    ''', (appliance_id, session['user_id']))
    
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Appliance not found or unauthorized'}), 404
    
    try:
        # Soft delete appliance
        cursor.execute('''
            UPDATE appliances 
            SET is_active = 0 
            WHERE id = ?
        ''', (appliance_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Appliance deleted successfully'
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/appliance/<int:appliance_id>', methods=['PUT'])
@login_required
def update_appliance(appliance_id):
    """Update an appliance"""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify appliance belongs to current user
    cursor.execute('''
        SELECT id FROM appliances 
        WHERE id = ? AND user_id = ?
    ''', (appliance_id, session['user_id']))
    
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Appliance not found or unauthorized'}), 404
    
    try:
        cursor.execute('''
            UPDATE appliances 
            SET name = ?, power_rating = ?
            WHERE id = ?
        ''', (data.get('name'), data.get('power_rating'), appliance_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Appliance updated successfully'
        })
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/energy-usage/<int:user_id>')
@login_required
def get_energy_usage(user_id):
    """Get detailed energy usage analytics"""
    # Ensure user can only access their own data
    if user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    period = request.args.get('period', 'week')  # day, week, month
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if period == 'day':
        # Hourly data for today
        cursor.execute('''
            SELECT strftime('%H:00', timestamp) as time_label,
                   AVG(power_consumption) as avg_power,
                   COUNT(*) as data_points
            FROM appliance_data
            WHERE user_id = ? 
            AND DATE(timestamp) = DATE('now')
            GROUP BY strftime('%H', timestamp)
            ORDER BY time_label
        ''', (user_id,))
    elif period == 'week':
        # Daily data for this week
        cursor.execute('''
            SELECT strftime('%Y-%m-%d', timestamp) as time_label,
                   AVG(power_consumption) as avg_power,
                   COUNT(*) as data_points
            FROM appliance_data
            WHERE user_id = ? 
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY time_label
        ''', (user_id,))
    else:  # month
        # Daily data for this month
        cursor.execute('''
            SELECT strftime('%Y-%m-%d', timestamp) as time_label,
                   AVG(power_consumption) as avg_power,
                   COUNT(*) as data_points
            FROM appliance_data
            WHERE user_id = ? 
            AND timestamp >= datetime('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY time_label
        ''', (user_id,))
    
    usage_data = [dict(row) for row in cursor.fetchall()]
    
    # Get appliance-wise breakdown
    cursor.execute('''
        SELECT a.type, a.name,
               AVG(ad.power_consumption) as avg_power,
               SUM(CASE WHEN ad.is_on = 1 THEN 1 ELSE 0 END) as on_count,
               COUNT(*) as total_count
        FROM appliances a
        LEFT JOIN appliance_data ad ON a.id = ad.appliance_id
        WHERE a.user_id = ? AND a.is_active = 1
        AND ad.timestamp >= datetime('now', '-7 days')
        GROUP BY a.id, a.type, a.name
        ORDER BY avg_power DESC
    ''', (user_id,))
    
    appliance_breakdown = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'usage_data': usage_data,
        'appliance_breakdown': appliance_breakdown,
        'period': period
    })

@app.route('/api/simulation-stats')
@login_required
def get_simulation_stats():
    """Get overall simulation statistics"""
    stats = simulator.get_user_stats()
    return jsonify(stats)

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        return jsonify({'error': 'All fields are required'}), 400
    
    if new_password != confirm_password:
        return jsonify({'error': 'New passwords do not match'}), 400
    
    is_valid, message = validate_password(new_password)
    if not is_valid:
        return jsonify({'error': message}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current user password
    cursor.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    if not verify_password(current_password, user['password']):
        conn.close()
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    try:
        # Update password
        hashed_password = hash_password(new_password)
        cursor.execute('''
            UPDATE users 
            SET password = ?
            WHERE id = ?
        ''', (hashed_password, session['user_id']))
        
        # Invalidate all other sessions
        cursor.execute('''
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE user_id = ? AND session_token != ?
        ''', (session['user_id'], session.get('session_token', '')))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# ============= DATABASE INITIALIZATION =============

def init_db():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if users table exists and get its structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            # Check current columns
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add missing columns if needed
            expected_columns = [
                ('first_name', 'VARCHAR(50)'),
                ('last_name', 'VARCHAR(50)'),
                ('phone', 'VARCHAR(20)'),
                ('address', 'TEXT'),
                ('city', 'VARCHAR(50)'),
                ('state', 'VARCHAR(50)'),
                ('zip_code', 'VARCHAR(10)'),
                ('is_verified', 'BOOLEAN DEFAULT 0'),
                ('is_active', 'BOOLEAN DEFAULT 1'),
                ('failed_login_attempts', 'INTEGER DEFAULT 0'),
                ('locked_until', 'DATETIME'),
                ('last_login', 'DATETIME')
            ]
            
            for col_name, col_type in expected_columns:
                if col_name not in columns:
                    try:
                        cursor.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
                        print(f"Added column {col_name} to users table")
                    except Exception as e:
                        print(f"Could not add column {col_name}: {e}")
        else:
            # Create users table from scratch
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    first_name VARCHAR(50),
                    last_name VARCHAR(50),
                    phone VARCHAR(20),
                    address TEXT,
                    city VARCHAR(50),
                    state VARCHAR(50),
                    zip_code VARCHAR(10),
                    is_verified BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME
                )
            ''')
        
        # User preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                theme VARCHAR(10) DEFAULT 'light',
                notifications_enabled BOOLEAN DEFAULT 1,
                email_notifications BOOLEAN DEFAULT 1,
                energy_goal REAL DEFAULT 1000.0,
                cost_goal REAL DEFAULT 5000.0,
                carbon_goal REAL DEFAULT 500.0,
                currency VARCHAR(10) DEFAULT 'INR',
                timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Appliances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                type VARCHAR(50) NOT NULL,
                power_rating REAL DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Appliance data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appliance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                appliance_id INTEGER NOT NULL,
                is_on BOOLEAN DEFAULT 0,
                power_consumption REAL DEFAULT 0,
                temperature REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (appliance_id) REFERENCES appliances (id)
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Password reset tokens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Email verification tokens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appliance_data_user_id ON appliance_data (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appliance_data_timestamp ON appliance_data (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions (session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions (expires_at)')
        
        # Create demo users if they don't exist
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Create demo users
            demo_users = [
                ('demo1', 'demo1@havoc.com', 'Demo', 'User', '+91-9876543210'),
                ('demo2', 'demo2@havoc.com', 'Test', 'User', '+91-9876543211'),
                ('admin', 'admin@havoc.com', 'Admin', 'User', '+91-9876543212')
            ]
            
            demo_password = hash_password('Demo@123')
            
            for username, email, first_name, last_name, phone in demo_users:
                cursor.execute('''
                    INSERT INTO users (username, email, password, first_name, last_name, phone, is_verified)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (username, email, demo_password, first_name, last_name, phone))
                
                user_id = cursor.lastrowid
                
                # Create user preferences
                cursor.execute('''
                    INSERT INTO user_preferences (user_id)
                    VALUES (?)
                ''', (user_id,))
                
                # Create demo appliances
                demo_appliances = [
                    ('Air Conditioner', 'air_conditioner', 1500),
                    ('Refrigerator', 'refrigerator', 200),
                    ('Washing Machine', 'washing_machine', 2000),
                    ('Water Heater', 'water_heater', 1000),
                    ('Television', 'television', 150),
                    ('Microwave', 'microwave', 800)
                ]
                
                for name, app_type, power_rating in demo_appliances:
                    cursor.execute('''
                        INSERT INTO appliances (user_id, name, type, power_rating)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, name, app_type, power_rating))
        
        conn.commit()
        print("✅ Database initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        conn.rollback()
    finally:
        conn.close()

# ============= CLEANUP AND UTILITIES =============

def cleanup_expired_sessions():
    """Clean up expired sessions and tokens"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Clean up expired sessions
        cursor.execute('''
            UPDATE user_sessions 
            SET is_active = 0 
            WHERE expires_at < ?
        ''', (datetime.now(),))
        
        # Clean up expired password reset tokens
        cursor.execute('''
            DELETE FROM password_reset_tokens 
            WHERE expires_at < ?
        ''', (datetime.now(),))
        
        # Clean up expired email verification tokens
        cursor.execute('''
            DELETE FROM email_verification_tokens 
            WHERE expires_at < ?
        ''', (datetime.now(),))
        
        # Clean up old appliance data (keep last 30 days)
        cursor.execute('''
            DELETE FROM appliance_data 
            WHERE timestamp < datetime('now', '-30 days')
        ''', )
        
        conn.commit()
        print(f"Cleanup completed at {datetime.now()}")
        
    except Exception as e:
        print(f"Cleanup error: {e}")
        conn.rollback()
    finally:
        conn.close()

def schedule_cleanup():
    """Schedule periodic cleanup tasks"""
    import threading
    import time
    
    def cleanup_worker():
        while True:
            try:
                time.sleep(3600)  # Run every hour
                cleanup_expired_sessions()
            except Exception as e:
                print(f"Cleanup worker error: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()

def enhanced_startup():
    """Enhanced startup with all initializations"""
    try:
        print("🔧 Initializing HaVoC-EcoWATT Backend...")
        
        # Initialize database
        print("📂 Setting up database...")
        init_db()
        
        # Start the IoT simulation service
        print("🤖 Starting IoT simulation...")
        simulator.start()
        
        # Schedule cleanup tasks
        print("🧹 Setting up cleanup tasks...")
        schedule_cleanup()
        
        # Run initial cleanup
        cleanup_expired_sessions()
        
        print("✅ Startup completed successfully!")
        print("🚀 HaVoC-EcoWATT Backend Server Starting...")
        print("📊 IoT Simulation Service: ACTIVE")
        print("🔐 Authentication System: ENABLED") 
        print("📧 Email Service: CONFIGURED")
        print("🧹 Cleanup Tasks: SCHEDULED")
        print("=" * 50)
        print("🌐 Server will be available at:")
        print("   - Local: http://127.0.0.1:5000")
        print("   - Network: http://0.0.0.0:5000")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        print("Attempting to continue with basic setup...")
        try:
            init_db()
            simulator.start()
        except Exception as inner_e:
            print(f"❌ Critical startup failure: {inner_e}")

if __name__ == '__main__':
    # Enhanced startup sequence
    enhanced_startup()
    
    # Run Flask app with reloader disabled to prevent duplicate simulation
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        print("🔄 Cleanup completed")