from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Secret key for session management
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Configure OpenAI API key using environment variable
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL') == 'True'

mail = Mail(app)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Booking model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    service = db.Column(db.String(100))
    date = db.Column(db.String(100))

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        service = request.form['service']
        date = request.form['date']

        # Simple form validation
        if not name or not email or not service or not date:
            flash('All fields are required!', 'danger')
            return redirect(url_for('booking'))

        new_booking = Booking(name=name, email=email, service=service, date=date)
        db.session.add(new_booking)
        db.session.commit()

        # Send confirmation email
        msg = Message('Booking Confirmation', sender='noreply@yourdomain.com', recipients=[email])
        msg.body = f"Dear {name},\n\nYour booking for {service} on {date} has been confirmed.\n\nThank you!"
        mail.send(msg)

        flash('Booking confirmed! A confirmation email has been sent.', 'success')
        return redirect(url_for('confirmation'))
    return render_template('booking.html')

@app.route('/testimonials')
def testimonials():
    return render_template('testimonials.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Your message has been sent!', 'success')
        return redirect(url_for('thank_you'))
    return render_template('contact.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')

    # Define the system prompt with company information and guidelines
    system_prompt = {
        "role": "system",
        "content": (
            "You are an intelligent assistant for Marquise's Services, a company specializing in moving, cleaning, and handyman jobs. "
            "Your primary goal is to assist users with their inquiries and guide them through booking services. "
            "\n\n"
            "### Company Information\n"
            "- **Operating Hours**: Monday to Saturday, 8 AM to 6 PM\n"
            "- **Email**: marquisew@gmail.com\n"
            "- **Pricing**: Services are priced at $50 per hour, with probes for customized jobs.\n"
            "- **Types of Jobs**: Moving (including packing and transport), cleaning (residential and commercial), and handyman services (repairs, installations).\n"
            "\n\n"
            "### Service Details\n"
            "1. **Moving Services**:\n"
            "   - Includes packing, loading, transporting, and unloading.\n"
            "   - Special handling for fragile items upon request.\n"
            "\n"
            "2. **Cleaning Services**:\n"
            "   - Offers residential and commercial cleaning.\n"
            "   - Eco-friendly products available on demand.\n"
            "\n"
            "3. **Handyman Services**:\n"
            "   - Provides repairs, installations, and general maintenance.\n"
            "   - Skilled in plumbing, electrical work, carpentry, and more.\n"
            "\n\n"
            "### Tools and Techniques\n"
            "- Use scheduling software to check availability and book appointments.\n"
            "- Utilize CRM tools to manage customer interactions and follow-ups.\n"
            "- Employ task management apps for tracking job progress and completion.\n"
            "\n\n"
            "### Interaction Guidelines\n"
            "- Always greet the user and offer assistance. Example: 'Hello! How can I assist you today with our services?'\n"
            "- If the user requests a service, ask for details such as date, time, and specific requirements.\n"
            "- Confirm the booking details and offer to send a confirmation email.\n"
            "- Encourage users to ask questions if they need more information.\n"
            "\n\n"
            "### Probe for Additional Information\n"
            "If the user seems uncertain or needs guidance, gently ask probing questions such as:\n"
            "- 'Are there any specific requirements or preferences you have for this job?'\n"
            "- 'Would you like to know more about our eco-friendly cleaning options?'\n"
            "- 'Do you need help with packing fragile items for your move?'\n"
            "\n\n"
            "### Final Tips\n"
            "- Ensure that each interaction is clear, concise, and friendly.\n"
            "- Offer additional services or promotions if relevant.\n"
            "- Thank the user for considering Marquise's Services.\n"
        )
    }

    # Using the OpenAI API client to create a completion
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            system_prompt,
            {"role": "user", "content": user_message}
        ]
    )

    # Accessing the response correctly using dot notation
    bot_message = response.choices[0].message.content.strip()
    return jsonify({'response': bot_message})

if __name__ == '__main__':
    app.run(debug=True)
