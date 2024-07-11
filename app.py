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

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///devices.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

logging.basicConfig(level=logging.DEBUG)

GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', 'your_gmail@gmail.com')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', 'your_gmail_password')

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False)
    mac_address = db.Column(db.String(17), unique=True, nullable=False)
    ip_address = db.Column(db.String(15), nullable=False)

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
        app.logger.error(f"Error sending email: {str(e)}")
        return False

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['id']
        device = Device.query.filter_by(user_id=user_id).first()
        if device:
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['user_id'] = user_id
            
            if send_otp_email(device.email, otp):
                flash(f'OTP sent to your registered email: {device.email}')
                return redirect(url_for('verify_otp'))
            else:
                flash('Error sending OTP. Please try again.')
        else:
            flash('Invalid ID')

    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'otp' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_otp = request.form['otp']
        if user_otp == session['otp']:
            session.pop('otp', None)
            flash('Access granted')
            return redirect(url_for('login'))
        else:
            flash('OTP does not match. Access denied.')

    return render_template('verify_otp.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['id']
        email = request.form['email']
        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1])
        ip_address = request.remote_addr
        
        existing_device = Device.query.filter_by(user_id=user_id).first()
        if existing_device:
            flash('User ID already exists')
            return redirect(url_for('register'))
        
        new_device = Device(user_id=user_id, email=email, mac_address=mac_address, ip_address=ip_address)
        db.session.add(new_device)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.errorhandler(500)
def internal_error(error):
    app.logger.error('An error occurred', exc_info=True)
    return "An internal error occurred", 500

@app.errorhandler(404)
def not_found_error(error):
    return "Page not found", 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)