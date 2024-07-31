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

@app.route('/', methods=['GET', 'POST'])
def login():
    check_database_status()
    if request.method == 'POST':
        user_id = request.form['id']
        device_id = request.form['device_id']
        device = mongo.db.devices.find_one({'user_id': user_id, 'device_id': device_id})
        if device:
            session['user_id'] = user_id
            return redirect(url_for('verify_otp'))
        else:
            flash("Invalid ID or unrecognized device. Please register the device first.", "error")

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
        device_id = request.form['device_id']
        ip_address = request.remote_addr
        
        # Check if this device ID is already registered
        existing_device = mongo.db.devices.find_one({'device_id': device_id})
        if existing_device:
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
                'ip_address': ip_address
            })
            flash("Device registered successfully.", "success")
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
    device_id = request.form['device_id']
    logger.debug(f"User ID: {user_id}")
    
    try:
        device = mongo.db.devices.find_one({'user_id': user_id, 'device_id': device_id})
        logger.debug(f"Device found: {device}")
    except Exception as e:
        logger.error(f"Error finding device: {str(e)}")
        flash("An error occurred. Please try again.", "error")
        return redirect(url_for('dashboard'))
    
    if not device:
        logger.warning("Device not found")
        flash("Unrecognized device.", "error")
        return redirect(url_for('dashboard'))
    
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
    return app

if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))