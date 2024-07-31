import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from flask_pymongo import PyMongo
from flask_fingerprint import Fingerprint
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import certifi
import hashlib
import uuid

app = Flask(__name__)
fingerprint = Fingerprint()
fingerprint.init_app(app)

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

# Define the allowed IP addresses
ALLOWED_IPS = os.environ.get('ALLOWED_IPS', '127.0.0.1,58.71.197.20,192.168.68.100,192.168.68.101,192.168.68.102,192.168.68.103').split(',')

def check_database_status():
    try:
        mongo.db.command('ping')
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
            "device_id": "hash1",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
        {
            "user_id": "STU002",
            "email": "student2@example.com",
            "device_id": "hash2",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "ip_address": "192.168.1.101",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        },
        {
            "user_id": "STU003",
            "email": "student3@example.com",
            "device_id": "hash3",
            "mac_address": "11:22:33:44:55:66",
            "ip_address": "192.168.1.102",
            "user_agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
        },
        {
            "user_id": "STU001",
            "email": "student1@example.com",
            "device_id": "hash4",
            "mac_address": "77:88:99:AA:BB:CC",
            "ip_address": "192.168.1.103",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1"
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

def get_mac_address():
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
        return mac
    except:
        return "Unknown"

def generate_device_id():
    user_agent = request.user_agent.string
    ip_address = request.remote_addr
    fp = fingerprint.get()
    device_info = f"{user_agent}|{ip_address}|{fp}"
    return hashlib.md5(device_info.encode()).hexdigest()

@app.route('/', methods=['GET', 'POST'])
def login():
    check_database_status()
    if request.method == 'POST':
        user_id = request.form['id']
        device = mongo.db.devices.find_one({'user_id': user_id})
        if device:
            device_id = request.cookies.get('device_id') or generate_device_id()
            mac_address = get_mac_address()
            
            logger.debug(f"Login attempt - User ID: {user_id}, Device ID: {device_id}, MAC: {mac_address}")
            logger.debug(f"Stored device - ID: {device['device_id']}, MAC: {device['mac_address']}")
            
            if device_id != device['device_id']:
                logger.warning(f"Device mismatch - User ID: {user_id}, Current ID: {device_id}, Stored ID: {device['device_id']}")
                flash("Device does not match ID.", "error")
                return render_template('login.html')
            
            # Check if the request is coming from Render
            x_forwarded_for = request.headers.get('X-Forwarded-For')
            if x_forwarded_for:
                # If it's coming from Render, use the first IP in X-Forwarded-For
                client_ip = x_forwarded_for.split(',')[0].strip()
            else:
                # If not, use the regular remote_addr
                client_ip = request.remote_addr
            
            logger.debug(f"Client IP: {client_ip}")
            logger.debug(f"Allowed IPs: {ALLOWED_IPS}")
            
            if client_ip in ALLOWED_IPS:
                session['user_id'] = user_id
                return redirect(url_for('verify_otp'))
            else:
                flash("Access denied. IP address not allowed.", "error")
                logger.warning(f"Login attempt from unauthorized IP: {client_ip}")
                return render_template('login.html')
        else:
            flash("Invalid ID. Please register the device first.", "error")

    response = make_response(render_template('login.html'))
    if 'device_id' not in request.cookies:
        response.set_cookie('device_id', generate_device_id(), max_age=30*24*60*60)  # 30 days
    return response

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    check_database_status()
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
    check_database_status()
    if request.method == 'POST':
        user_id = request.form['id']
        email = request.form['email']
        
        device_id = generate_device_id()
        mac_address = get_mac_address()
        
        logger.debug(f"Registering device - User ID: {user_id}, Email: {email}, Device ID: {device_id}, MAC: {mac_address}")
        
        # Check if this device ID is already registered
        existing_device = mongo.db.devices.find_one({'device_id': device_id})
        if existing_device:
            logger.warning(f"Attempt to register existing device - User ID: {user_id}, Device ID: {device_id}")
            flash("This device has already been registered", "error")
            return redirect(url_for('register'))
        
        # Check how many devices are registered with this user_id
        existing_devices = list(mongo.db.devices.find({'user_id': user_id}))
        if len(existing_devices) >= 2:
            flash("Device limit reached. You can only register up to two devices per ID.", "error")
            return redirect(url_for('register'))
        
        # If this is the second device, ensure the email matches the first device
        if len(existing_devices) == 1 and existing_devices[0]['email'] != email:
            flash("Email must match the email used for your first device.", "error")
            return redirect(url_for('register'))
        
        try:
            mongo.db.devices.insert_one({
                'user_id': user_id,
                'email': email,
                'device_id': device_id,
                'mac_address': mac_address,
                'ip_address': request.remote_addr,
                'user_agent': request.user_agent.string
            })
            flash("Device registered successfully.", "success")
            response = make_response(redirect(url_for('login')))
            response.set_cookie('device_id', device_id, max_age=30*24*60*60)  # 30 days
            return response
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            flash("An error occurred during registration. Please try again.", "error")
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    logger.debug(f"Session data: {session}")
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
    logger.debug("Entering mark_attendance function")
    check_database_status()
    if 'user_id' not in session:
        logger.warning("User not in session")
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    logger.debug(f"User ID: {user_id}")
    
    try:
        device = mongo.db.devices.find_one({'user_id': user_id})
        logger.debug(f"Device found: {device}")
    except Exception as e:
        logger.error(f"Error finding device: {str(e)}")
        flash("An error occurred. Please try again.", "error")
        return redirect(url_for('dashboard'))
    
    if not device:
        logger.warning("Device not found")
        flash("Device not found.", "error")
        return redirect(url_for('login'))
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    logger.debug(f"Today's date: {today}")
    
    try:
        existing_attendance = mongo.db.attendance.find_one({
            'user_id': user_id,
            'check_in_time': {'$gte': today, '$lt': tomorrow}
        })
        logger.debug(f"Existing attendance: {existing_attendance}")
    except Exception as e:
        logger.error(f"Error checking existing attendance: {str(e)}")
        flash("An error occurred. Please try again.", "error")
        return redirect(url_for('dashboard'))
    
    if existing_attendance:
        logger.info("Attendance already marked")
        flash("Attendance already marked for today.", "info")
    else:
        try:
            mongo.db.attendance.insert_one({
                'user_id': user_id,
                'check_in_time': datetime.utcnow()
            })
            logger.info("Attendance marked successfully")
            flash("Attendance marked successfully.", "success")
        except Exception as e:
            logger.error(f"Error marking attendance: {str(e)}")
            flash("An error occurred while marking attendance. Please try again.", "error")
    
    return redirect(url_for('dashboard'))
@app.route('/attendance_history')
def attendance_history():
    if 'user_id' not in session:
        flash("Please login first.", "error")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    attendances = list(mongo.db.attendance.find({'user_id': user_id}).sort('check_in_time', -1))
    
    return render_template('attendance_history.html', attendances=attendances)

@app.route('/check_device')
def check_device():
    device_id = request.cookies.get('device_id') or generate_device_id()
    mac_address = get_mac_address()
    return f"Device ID: {device_id}<br>MAC Address: {mac_address}"

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
        # Ensure collections exist
        if 'devices' not in mongo.db.list_collection_names():
            mongo.db.create_collection('devices')
        if 'attendance' not in mongo.db.list_collection_names():
            mongo.db.create_collection('attendance')
        # Check if data already exists in both collections
        if mongo.db.devices.count_documents({}) == 0 or mongo.db.attendance.count_documents({}) == 0:
            insert_mock_data()
            logger.info("Mock data inserted.")
        else:
            logger.info("Existing data found. Skipping mock data insertion.")
    return app

if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))