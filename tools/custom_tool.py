from functools import wraps
from extensions import db
from models import Availability, Service, Booking
from flask_mail import Message
from datetime import datetime
from flask import render_template, current_app

def tool(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@tool
def check_availability(service_name: str, date: str) -> str:
    service = Service.query.filter_by(name=service_name).first()
    if not service:
        return f"Service {service_name} not found."

    date_obj = datetime.strptime(date, "%Y-%m-%d")
    bookings = Booking.query.filter_by(service=service_name, date=date).count()
    if bookings >= 3:  # Assuming a maximum of 3 bookings per day per service
        return f"No available slots for {service_name} on {date}."
    
    return f"Available slots for {service_name} on {date}."

@tool
def calculate_estimate(service_name: str, hours: int) -> str:
    service = Service.query.filter_by(name=service_name).first()
    if not service:
        return f"Service {service_name} not found."

    cost = hours * service.price_per_hour
    return f"The estimated cost for {hours} hours of {service.name} is ${cost}."

@tool
def send_confirmation_email(name: str, email: str, service: str, date: str, time: str) -> str:
    subject = "Booking Confirmation - Marquise's Services"
    
    # Render the email template
    email_body = render_template('email_templates/booking_confirmation.html', 
                                 name=name, 
                                 service=service, 
                                 date=date, 
                                 time=time)
    
    sender = current_app.config['MAIL_DEFAULT_SENDER']
    msg = Message(subject, 
                  sender=sender,
                  recipients=[email])
    msg.html = email_body
    
    try:
        current_app.extensions['mail'].send(msg)
        return f"Confirmation email sent to {email}."
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return f"Failed to send confirmation email to {email}. Please contact support."
