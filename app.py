from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import uuid
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///devices.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Gmail configuration for sending OTPs
GMAIL_ADDRESS = os.environ.get('GMAIL_ADDRESS', 'jonathan097869@gmail.com')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', 'ndnb dzjc jqpw zawu')

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
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
        print(f"Error sending email: {str(e)}")
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
            flash('Access denied: User ID not found')

    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'otp' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_otp = request.form['otp']
        if user_otp == session['otp']:
            session.pop('otp', None)
            session.pop('user_id', None)
            flash('Access granted')
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
        
        existing_devices = Device.query.filter_by(user_id=user_id).all()
        
        if not existing_devices:
            new_device = Device(user_id=user_id, email=email, mac_address=mac_address, ip_address=ip_address)
            db.session.add(new_device)
            db.session.commit()
            flash('First device registered successfully.')
        elif len(existing_devices) == 1:
            if existing_devices[0].email == email:
                new_device = Device(user_id=user_id, email=email, mac_address=mac_address, ip_address=ip_address)
                db.session.add(new_device)
                db.session.commit()
                flash('Second device registered successfully.')
            else:
                flash('Email does not match registered device.')
        else:
            flash('Maximum devices already registered for this ID.')
        
        return redirect(url_for('register'))
    
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)