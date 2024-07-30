import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import certifi

app = Flask(__name__)

# MongoDB configuration
app.config['MONGO_URI'] = os.environ.get('MONGODB_URI', 'mongodb+srv://jonathan09748:W3hfCGztVaOjcw3h@fyp2cluster.wjspyde.mongodb.net/devicedb?retryWrites=true&w=majority&appName=FYP2Cluster')
mongo = PyMongo(app, tlsCAFile=certifi.where())

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '122382989200018AEF922')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"MongoDB URI: {app.config['MONGO_URI']}")
logger.debug("Attempting to connect to the database...")

GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', 'jonathan097869@gmail.com')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', 'cype xwru nytj xsmm')

ALLOWED_IP = "192.168.68.100"

def check_database_status():
    try:
        mongo.db.command('ping')
        logger.info("Database connection successful.")
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

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    return request.remote_addr

@app.route('/', methods=['GET', 'POST'])
def login():
    check_database_status()
    if request.method == 'POST':
        user_id = request.form['id']
        device = mongo.db.devices.find_one({'user_id': user_id})
        if device:
            client_ip = get_client_ip()
            logger.debug(f"Client IP: {client_ip}")
            logger.debug(f"Allowed IP: {ALLOWED_IP}")
            
            if client_ip == ALLOWED_IP:
                session['user_id'] = user_id
                return redirect(url_for('verify_otp'))
            else:
                flash(f"Access denied. IP address not allowed: {client_ip}", "error")
                logger.warning(f"Login attempt from unauthorized IP: {client_ip}")
        else:
            flash("Invalid ID. Please register the device first.", "error")

    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    device = mongo.db.devices.find_one({'user_id': user_id})

    if request.method == 'GET':
        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        if send_otp_email(device['email'], otp):
            flash("OTP sent to your email. Please verify.", "success")
        else:
            flash("Error sending OTP. Please try again.", "error")

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
    if request.method == 'POST':
        user_id = request.form['id']
        email = request.form['email']
        ip_address = get_client_ip()
        
        existing_device = mongo.db.devices.find_one({'user_id': user_id})
        if existing_device:
            flash("User ID has already been registered", "error")
            return redirect(url_for('register'))
        
        try:
            mongo.db.devices.insert_one({
                'user_id': user_id,
                'email': email,
                'ip_address': ip_address
            })
            flash("Device registered successfully.", "success")
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            flash("An error occurred during registration. Please try again.", "error")
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    device = mongo.db.devices.find_one({'user_id': user_id})
    
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', user_id=user_id, email=device['email'])

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    existing_attendance = mongo.db.attendance.find_one({
        'user_id': user_id,
        'check_in_time': {'$gte': today, '$lt': tomorrow}
    })
    
    if existing_attendance:
        flash("Attendance already marked for today.", "info")
    else:
        mongo.db.attendance.insert_one({
            'user_id': user_id,
            'check_in_time': datetime.utcnow()
        })
        flash("Attendance marked successfully.", "success")
    
    return redirect(url_for('dashboard'))

@app.route('/attendance_history')
def attendance_history():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    attendances = list(mongo.db.attendance.find({'user_id': user_id}).sort('check_in_time', -1))
    
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))