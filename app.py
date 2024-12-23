from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, render_template_string, current_app
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
from extensions import db, login_manager, mail
from flask_mail import Message
from models import User, Service, Booking, Contact, Referral, Feedback, LoyaltyPoints
import random
import string
from openai import OpenAI
from swarm import Agent, Swarm
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from contextlib import contextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
from flask_migrate import Migrate
from tools.custom_tool import check_availability, calculate_estimate, send_confirmation_email

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the .env file
env_path = os.path.join(current_dir, '.env')
# Load the .env file
load_dotenv(dotenv_path=env_path)

print("OPENAI_API_KEY:", os.getenv('OPENAI_API_KEY'))

print("Current directory:", current_dir)
print("Env file path:", env_path)
print("Env file exists:", os.path.exists(env_path))
print("Env file contents:")
with open(env_path, 'r') as f:
    print(f.read())

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
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

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

    def send_email(to, subject, body):
        """Send an email using the configured mail server."""
        sender_email = current_app.config['MAIL_USERNAME']
        sender_password = current_app.config['MAIL_PASSWORD']
        mail_server = current_app.config['MAIL_SERVER']
        mail_port = current_app.config['MAIL_PORT']

        print(f"Attempting to send email from {sender_email} to {to}")
        
        if not sender_email or not sender_password:
            return json.dumps({"status": "error", "message": "Email credentials not found in configuration"})

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(mail_server, mail_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(message)
            return json.dumps({"status": "success", "message": "Email sent successfully!"})
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(error_message)
            return json.dumps({"status": "error", "message": error_message})

    # Initialize the scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()

    def book_service(service, email, date, time):
        """Book a service and save it to the database."""
        try:
            with app.app_context():
                new_booking = Booking(service=service, email=email, date=date, time=time)
                db.session.add(new_booking)
                db.session.commit()
                
                # Add loyalty points
                user = User.query.filter_by(email=email).first()
                if user:
                    loyalty_points = LoyaltyPoints.query.filter_by(user_id=user.id).first()
                    if not loyalty_points:
                        loyalty_points = LoyaltyPoints(user_id=user.id)
                    loyalty_points.points += 100  # Add 100 points for each booking
                    loyalty_points.last_updated = datetime.utcnow()
                    db.session.add(loyalty_points)
                    db.session.commit()
                
                # Send confirmation email
                confirmation_result = send_confirmation_email(email, [service], date, time)
                
                return f"Service '{service}' booked for {date} at {time}. {confirmation_result}"
        except Exception as e:
            with app.app_context():
                db.session.rollback()
            return f"Error booking service: {str(e)}"

    def send_confirmation_email(email, services, date, time):
        try:
            subject = "Your Booking Confirmation - Marquise's Services"
            
            # Personalized HTML email template
            html_content = render_template('email_templates/booking_confirmation.html', 
                                           services=services, date=date, time=time)
            
            msg = Message(subject, recipients=[email], html=html_content)
            mail.send(msg)
            
            # Schedule follow-up emails
            schedule_follow_up_emails(email, services, date, time)
            
            return f"Confirmation email sent to {email} for services on {date} at {time}."
        except Exception as e:
            print(f"Failed to send email: {str(e)}")  # Log the error
            return "Booking confirmed. You'll receive a confirmation email shortly."

    def schedule_follow_up_emails(email, services, date, time):
        # Schedule reminder email 1 day before the service
        reminder_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)
        scheduler.add_job(send_reminder_email, 'date', run_date=reminder_date, args=[email, services, date, time])
        
        # Schedule feedback request email 1 day after the service
        feedback_date = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
        scheduler.add_job(send_feedback_request, 'date', run_date=feedback_date, args=[email, services])

    def send_reminder_email(email, services, date, time):
        subject = "Your Marquise's Services Appointment Tomorrow"
        html_content = render_template('email_templates/reminder_email.html', 
                                       services=services, date=date, time=time)
        msg = Message(subject, recipients=[email], html=html_content)
        mail.send(msg)

    def send_feedback_request(email, services):
        subject = "How was your Marquise's Services experience?"
        feedback_url = url_for('feedback', _external=True)
        html_content = render_template('email_templates/feedback_request.html', 
                                       services=services, feedback_url=feedback_url)
        msg = Message(subject, recipients=[email], html=html_content)
        mail.send(msg)

    booking_agent = Agent(
        name="Marquise's Elite Booking Specialist",
        instructions="""
        You are an elite booking specialist for Marquise's Services, providing world-class customer service comparable to Fortune 500 companies. Your goal is to assist customers in booking appointments for moving, cleaning, or handyman services with utmost professionalism and attention to detail.

        Follow these steps:
        1. Greet the customer warmly and ask how you can assist them today.
        2. If they're interested in booking, ask which service they need (moving, cleaning, or handyman).
        3. Ask for their preferred date.
        4. Ask for their preferred time.
        5. Collect their email address for booking confirmation and follow-up communications.
        6. Summarize the booking details and confirm if everything is correct.
        7. Use the book_service function to finalize the booking.
        8. After booking, inform the customer about the confirmation email they'll receive.
        9. Ask if there's anything else you can assist them with, such as special requests or additional information about the service.

        Throughout the conversation:
        - Maintain a polite, professional, and friendly demeanor.
        - Use the customer's name if provided.
        - Offer personalized suggestions based on the service they're booking.
        - Address any concerns or questions promptly and thoroughly.
        - Highlight the unique benefits of choosing Marquise's Services.
        - If appropriate, mention any current promotions or loyalty programs.

        Remember the entire conversation history and use it to provide context-aware, personalized responses. Your goal is to make each customer feel valued and excited about their upcoming service.
        """,
        functions=[book_service, send_confirmation_email],
        model="gpt-4o-mini"
    )

    general_chat_agent = Agent(
        name="General Chat Agent",
        instructions="""
        You are a friendly and knowledgeable customer service agent for Marquise's Services.
        Your role is to answer general questions about our services, pricing, and policies.
        If a customer expresses interest in booking a service, politely transfer them to the Booking Agent.
        Always maintain a helpful and professional demeanor.
        Remember the entire conversation history and use it to provide context-aware responses.
        """,
        functions=[],
        model="gpt-4o-mini"
    )

    swarm_client = Swarm()

    def process_streaming_response(response):
        content = ""
        for chunk in response:
            if isinstance(chunk, dict):
                if "content" in chunk and chunk["content"] is not None:
                    content += chunk["content"]
                    yield json.dumps({"response": chunk["content"]}) + "\n"
                
                if "function_call" in chunk and chunk["function_call"] is not None:
                    function_call = chunk["function_call"]
                    if isinstance(function_call, dict) and "name" in function_call:
                        name = function_call["name"]
                        arguments = json.loads(function_call.get("arguments", "{}"))
                        try:
                            if name == "book_service":
                                result = book_service(**arguments)
                            elif name == "send_confirmation_email":
                                result = send_confirmation_email(**arguments)
                            else:
                                result = f"Unknown function: {name}"
                            yield json.dumps({"response": f"Function called: {name}\n{result}\n"}) + "\n"
                        except Exception as e:
                            error_message = f"An error occurred, but your booking is confirmed. You'll receive a confirmation email shortly."
                            print(f"Error in {name}: {str(e)}")  # Log the error
                            yield json.dumps({"response": error_message}) + "\n"
    
        if content:
            yield json.dumps({"response": content}) + "\n"

    @app.route('/chat', methods=['GET', 'POST'])
    def chat():
        if request.method == 'POST':
            user_message = request.json['message']
            chat_history = request.json.get('history', [])
            
            # Determine which agent to use based on the conversation context
            if any("book" in message['content'].lower() for message in chat_history):
                current_agent = booking_agent
            else:
                current_agent = general_chat_agent
            
            # Add the new user message to the chat history
            chat_history.append({"role": "user", "content": user_message})
            
            try:
                response = swarm_client.run(
                    agent=current_agent,
                    messages=chat_history,
                    stream=True
                )
                
                return app.response_class(process_streaming_response(response), content_type='application/json')
            except Exception as e:
                app.logger.error(f"Error in chat processing: {str(e)}")
                return jsonify({"error": "An error occurred while processing your request."}), 500
        
        return render_template('chat.html')

    @app.route('/feedback', methods=['GET', 'POST'])
    def feedback():
        if request.method == 'POST':
            data = request.form
            new_feedback = Feedback(
                user_id=current_user.id if current_user.is_authenticated else None,
                service_id=data.get('service_id'),
                rating=data.get('rating'),
                comment=data.get('comment')
            )
            db.session.add(new_feedback)
            db.session.commit()
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('index'))
        
        return render_template('feedback.html')

    return app

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

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///new_bookings.db')

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_services()
    app.run(host='0.0.0.0', port=5001, debug=True)
