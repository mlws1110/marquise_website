from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, render_template_string
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
from extensions import db, login_manager, mail
from flask_mail import Message
from models import User, Service, Booking, Contact, Referral
import random
import string

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///new_bookings.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@marquisesservices.com')

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/services')
    def services():
        return render_template('services.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/testimonials')
    def testimonials():
        return render_template('testimonials.html')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            message = request.form['message']
            new_contact = Contact(name=name, email=email, message=message)
            db.session.add(new_contact)
            db.session.commit()
            flash('Your message has been sent!', 'success')
            return redirect(url_for('contact'))
        return render_template('contact.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            remember = True if request.form.get('remember') else False
            
            user = User.query.filter_by(email=email).first()
            
            if user and check_password_hash(user.password, password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Please check your login details and try again.', 'danger')
        
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('register'))

            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                flash('Username or email already exists', 'danger')
                return redirect(url_for('register'))

            new_user = User(username=username, email=email)
            new_user.password = generate_password_hash(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/profile')
    @login_required
    def profile():
        bookings = Booking.query.filter_by(user_id=current_user.id).all()
        return render_template('profile.html', bookings=bookings)

    @app.route('/booking', methods=['GET', 'POST'])
    def booking():
        services = Service.query.all()
        if request.method == 'POST':
            service_ids = request.form.getlist('services')
            email = request.form['email']
            date = request.form['date']
            time = request.form['custom-time']
            duration = request.form['duration']
            
            for service_id in service_ids:
                service = Service.query.get(service_id)
                new_booking = Booking(service=service.name, email=email, date=date, time=time)
                # Only set user_id if the user is logged in
                if current_user.is_authenticated:
                    new_booking.user_id = current_user.id
                db.session.add(new_booking)
            
            db.session.commit()
            
            try:
                send_confirmation_email(email, [Service.query.get(id).name for id in service_ids], date, time)
                flash('Booking successful! A confirmation email has been sent.', 'success')
            except Exception as e:
                app.logger.error(f"Failed to send email: {str(e)}")
                flash('Booking successful! Please check your email for confirmation details.', 'success')
            
            return redirect(url_for('confirmation'))
        user_email = current_user.email if current_user.is_authenticated else ''
        return render_template('booking.html', services=services, user_email=user_email)

    @app.route('/confirmation')
    def confirmation():
        return render_template('confirmation.html')

    @app.route('/faq')
    def faq():
        faqs = [
            {
                'question': 'What areas do you serve?',
                'answer': 'We currently serve the greater metropolitan area and surrounding suburbs.'
            },
            {
                'question': 'How do I schedule a service?',
                'answer': 'You can easily schedule a service through our online booking system or by calling our customer service line.'
            },
            {
                'question': 'What is your cancellation policy?',
                'answer': 'We offer free cancellation up to 24 hours before your scheduled service.'
            },
            # Add more FAQs as needed
        ]
        return render_template('faq.html', faqs=faqs)

    @app.route('/gallery')
    def gallery():
        gallery_images = [
            {'src': 'images/job1.jpg', 'alt': 'Moving Service Example', 'category': 'Moving'},
            {'src': 'images/job2.jpg', 'alt': 'Cleaning Service Example', 'category': 'Cleaning'},
            {'src': 'images/job3.jpg', 'alt': 'Handyman Service Example', 'category': 'Handyman'},
            # Add more images here
        ]
        return render_template('gallery.html', gallery_images=gallery_images)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
        user_referrals = Referral.query.filter_by(referrer_id=current_user.id).all()
        return render_template('dashboard.html', bookings=user_bookings, referrals=user_referrals)

    @app.route('/check_availability', methods=['POST'])
    def check_availability():
        service = request.form['service']
        date = request.form['date']
        time = request.form['time']
        # Implement your availability checking logic here
        # This is a placeholder response
        available = True
        return jsonify({'available': available})

    return app

def send_confirmation_email(email, services, date, time):
    subject = "Booking Confirmation - Marquise's Services"
    
    # HTML email template
    html_content = render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Booking Confirmation</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
            .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; }
            .header { background-color: #4A90E2; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; }
            .footer { background-color: #333; color: #fff; padding: 20px; text-align: center; font-size: 12px; }
            h1 { margin: 0; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .btn { display: inline-block; padding: 10px 20px; background-color: #4A90E2; color: white; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Booking Confirmation</h1>
            </div>
            <div class="content">
                <p>Dear Valued Customer,</p>
                <p>Thank you for choosing Marquise's Services. We're pleased to confirm your booking with the following details:</p>
                <table>
                    <tr>
                        <th>Service(s)</th>
                        <td>{{ ', '.join(services) }}</td>
                    </tr>
                    <tr>
                        <th>Date</th>
                        <td>{{ date }}</td>
                    </tr>
                    <tr>
                        <th>Time</th>
                        <td>{{ time }}</td>
                    </tr>
                </table>
                <p>Our team is committed to providing you with exceptional service. Here's what you can expect:</p>
                <ul>
                    <li>A courtesy call 24 hours before your appointment</li>
                    <li>Punctual arrival of our professional team</li>
                    <li>High-quality service tailored to your needs</li>
                </ul>
                <p>If you need to make any changes to your booking or have any questions, please don't hesitate to contact us:</p>
                <p>
                    Phone: (555) 123-4567<br>
                    Email: support@marquisesservices.com
                </p>
            </div>
            <div class="footer">
                <p>&copy; 2023 Marquise's Services. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    ''', services=services, date=date, time=time)
    
    msg = Message(subject, recipients=[email], html=html_content)
    mail.send(msg)

def create_sample_services():
    if Service.query.count() == 0:
        services = [
            Service(name="Moving", description="Professional moving services", price_per_hour=50.0, duration=4, image="moving.jpg"),
            Service(name="Cleaning", description="Thorough cleaning services", price_per_hour=30.0, duration=3, image="cleaning.jpg"),
            Service(name="Handyman", description="Skilled handyman services", price_per_hour=40.0, duration=2, image="handyman.jpg"),
        ]
        db.session.add_all(services)
        db.session.commit()
        print("Sample services added successfully!")

app = create_app()

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_services()
    app.run(host='0.0.0.0', port=5000, debug=True)