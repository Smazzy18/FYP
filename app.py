import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import uuid
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import inspect
from datetime import datetime

app = Flask(__name__)

# Database configuration
if 'DATABASE_URL' in os.environ:
    # Running on Render, use PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
else:
    # Local development, use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///devices.db'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '122382989200018AEF922')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
logger.debug("Attempting to connect to the database...")

GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', 'jonathan097869@gmail.com')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', 'cype xwru nytj xsmm')

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    mac_address = db.Column(db.String(17), nullable=False)
    ip_address = db.Column(db.String(15), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('device.user_id'), nullable=False)
    check_in_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

def check_database_status():
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info(f"Database connection successful. Tables: {tables}")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")

def send_otp_email(to_email, otp):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = "Your OTP for Login"
    
    body = f"Your OTP is: {otp}"
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(GMAIL_ADDRESS, to_email, text)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

@app.route('/', methods=['GET', 'POST'])
def login():
    check_database_status()
    if request.method == 'POST':
        user_id = request.form['id']
        device = Device.query.filter_by(user_id=user_id).first()
        if device:
            session['user_id'] = user_id
            return redirect(url_for('verify_otp'))
        else:
            flash("Invalid ID. Please register the device first.", "error")

    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    check_database_status()
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    device = Device.query.filter_by(user_id=user_id).first()

    if request.method == 'GET':
        if device.ip_address == request.remote_addr:
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            if send_otp_email(device.email, otp):
                flash("OTP sent to your email. Please verify.", "success")
            else:
                flash("Error sending OTP. Please try again.", "error")
        else:
            flash("Access denied. IP address does not match.", "error")
            return redirect(url_for('login'))

    if request.method == 'POST':
        user_otp = request.form['otp']
        if user_otp == session.get('otp'):
            session.pop('otp', None)
            flash("Access granted. Welcome!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("OTP does not match. Access denied.", "error")

    return render_template('verify_otp.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    check_database_status()
    if request.method == 'POST':
        user_id = request.form['id']
        email = request.form['email']
        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
        ip_address = request.remote_addr
        
        existing_device = Device.query.filter_by(mac_address=mac_address).first()
        if existing_device:
            flash("Device already registered", "error")
            return redirect(url_for('register'))
        
        existing_devices = Device.query.filter_by(user_id=user_id).all()
        if len(existing_devices) >= 2:
            flash("Device limit has been reached.", "error")
        else:
            try:
                new_device = Device(user_id=user_id, email=email, mac_address=mac_address, ip_address=ip_address)
                db.session.add(new_device)
                db.session.commit()
                flash("Device registered successfully.", "success")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error during registration: {str(e)}")
                flash("An error occurred during registration. Please try again.", "error")
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    device = Device.query.filter_by(user_id=user_id).first()
    
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', user_id=user_id, email=device.email)

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    device = Device.query.filter_by(user_id=user_id).first()
    
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for('login'))
    
    # Check if attendance already marked for today
    today = datetime.utcnow().date()
    existing_attendance = Attendance.query.filter(
        Attendance.user_id == user_id,
        db.func.date(Attendance.check_in_time) == today
    ).first()
    
    if existing_attendance:
        flash("Attendance already marked for today.", "info")
    else:
        new_attendance = Attendance(user_id=user_id)
        db.session.add(new_attendance)
        db.session.commit()
        flash("Attendance marked successfully.", "success")
    
    return redirect(url_for('dashboard'))

@app.route('/attendance_history')
def attendance_history():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    attendances = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.check_in_time.desc()).all()
    
    return render_template('attendance_history.html', attendances=attendances)

@app.errorhandler(500)
def internal_error(error):
    logger.error('An error occurred', exc_info=True)
    flash("An internal error occurred. Please try again later.", "error")
    return render_template('error.html'), 500

@app.errorhandler(404)
def not_found_error(error):
    flash("Page not found.", "error")
    return render_template('error.html'), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)