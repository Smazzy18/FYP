import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
import uuid
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import certifi
import ssl

app = Flask(__name__)

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# MongoDB configuration
mongo_uri = os.environ.get('MONGODB_URI', 'mongodb+srv://jonathan09748:W3hfCGztVaOjcw3h@fyp2cluster.wjspyde.mongodb.net/devicedb?retryWrites=true&w=majority&appName=FYP2Cluster')
app.config['MONGO_URI'] = mongo_uri
logger.debug(f"MongoDB URI: {mongo_uri}")

# Create a MongoDB client with SSL configuration
mongo = PyMongo(app, tlsCAFile=certifi.where())

# Other configurations
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '122382989200018AEF922')
GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', 'jonathan097869@gmail.com')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', 'cype xwru nytj xsmm')

def check_database_status():
    try:
        # The ismaster command is cheap and does not require auth.
        mongo.db.command('ismaster')
        logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")

def insert_mock_data():
    # Clear existing data
    mongo.db.devices.delete_many({})
    mongo.db.attendance.delete_many({})

    # Insert mock data for devices
    devices = [
        {
            "user_id": "STU001",
            "email": "student1@example.com",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "ip_address": "192.168.1.100"
        },
        {
            "user_id": "STU002",
            "email": "student2@example.com",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "ip_address": "192.168.1.101"
        },
        {
            "user_id": "STU003",
            "email": "student3@example.com",
            "mac_address": "11:22:33:44:55:66",
            "ip_address": "192.168.1.102"
        },
        {
            "user_id": "STU001",
            "email": "student1@example.com",
            "mac_address": "77:88:99:AA:BB:CC",
            "ip_address": "192.168.1.103"
        }
    ]

    # Insert mock data for attendance
    attendances = [
        {
            "user_id": "STU001",
            "check_in_time": datetime(2024, 3, 10, 9, 0, 0)
        },
        {
            "user_id": "STU002",
            "check_in_time": datetime(2024, 3, 10, 9, 5, 0)
        },
        {
            "user_id": "STU003",
            "check_in_time": datetime(2024, 3, 10, 8, 55, 0)
        },
        {
            "user_id": "STU001",
            "check_in_time": datetime(2024, 3, 11, 9, 2, 0)
        },
        {
            "user_id": "STU002",
            "check_in_time": datetime(2024, 3, 11, 9, 10, 0)
        }
    ]

    # Insert data into MongoDB
    mongo.db.devices.insert_many(devices)
    mongo.db.attendance.insert_many(attendances)

    logger.info("Mock data inserted successfully.")

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
        device = mongo.db.devices.find_one({'user_id': user_id})
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
    device = mongo.db.devices.find_one({'user_id': user_id})

    if request.method == 'GET':
        if device['ip_address'] == request.remote_addr:
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            if send_otp_email(device['email'], otp):
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
        
        existing_device = mongo.db.devices.find_one({'mac_address': mac_address})
        if existing_device:
            flash("Device has already been registered", "error")
            return redirect(url_for('register'))
        
        existing_devices = list(mongo.db.devices.find({'user_id': user_id}))
        if len(existing_devices) >= 2:
            flash("Device limit reached. You can only register up to two devices per ID.", "error")
            return redirect(url_for('register'))
        
        if len(existing_devices) == 1 and existing_devices[0]['email'] != email:
            flash("Email must match the email used for your first device.", "error")
            return redirect(url_for('register'))
        
        try:
            mongo.db.devices.insert_one({
                'user_id': user_id,
                'email': email,
                'mac_address': mac_address,
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
    device = mongo.db.devices.find_one({'user_id': user_id})
    
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for('login'))
    
    today = datetime.utcnow().date()
    existing_attendance = mongo.db.attendance.find_one({
        'user_id': user_id,
        'check_in_time': {'$gte': today, '$lt': today + timedelta(days=1)}
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

def create_app():
    with app.app_context():
        check_database_status()
        # Check if data already exists in both collections
        if mongo.db.devices.count_documents({}) == 0 or mongo.db.attendance.count_documents({}) == 0:
            insert_mock_data()
            logger.info("Mock data inserted.")
        else:
            logger.info("Existing data found. Skipping mock data insertion.")
    return app

if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))