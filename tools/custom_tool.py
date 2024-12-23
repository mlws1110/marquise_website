from functools import wraps
from extensions import db, mail
from models import Availability, Service, Booking
from flask_mail import Message
from datetime import datetime
from flask import render_template, current_app

def tool(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return {"result": result}
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
def send_confirmation_email(email: str, services: list, date: str, time: str) -> str:
    subject = "Booking Confirmation - Marquise's Services"
    
    # HTML email template
    html_content = render_template('email_templates/booking_confirmation.html', 
                                   services=services, date=date, time=time)
    
    msg = Message(subject, recipients=[email], html=html_content)
    mail.send(msg)
    
    return f"Confirmation email sent to {email} for services on {date} at {time}."

send_confirmation_email.schema = {
    "type": "function",
    "function": {
        "name": "send_confirmation_email",
        "description": "Send a confirmation email for a booking",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "services": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "date": {"type": "string"},
                "time": {"type": "string"}
            },
            "required": ["email", "services", "date", "time"]
        }
    }
}
