from extensions import db
from flask_login import UserMixin
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    referral_code = db.Column(db.String(10), unique=True)
    bookings = db.relationship('Booking', backref='user', lazy='dynamic')
    is_admin = db.Column(db.Boolean, default=False)
    referrals = db.relationship('Referral', backref='referrer', lazy=True)

    def get_id(self):
        return str(self.id)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    service = db.Column(db.String(100))
    date = db.Column(db.String(100))
    time = db.Column(db.String(100))  # Add this line
    status = db.Column(db.String(50), default='Pending')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def get_modify_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'booking_id': self.id})

    @staticmethod
    def verify_modify_token(token, max_age=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=max_age)
            booking_id = data['booking_id']
        except:
            return None
        return Booking.query.get(booking_id)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    price_per_hour = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer)  # Duration in hours
    image = db.Column(db.String(100))  # Make sure this line is present

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    date = db.Column(db.Date)
    time_slot = db.Column(db.String(50))  # e.g., '09:00 AM - 12:00 PM'
    is_booked = db.Column(db.Boolean, default=False)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    message = db.Column(db.Text)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_email = db.Column(db.String(100), nullable=False)
    date_referred = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed, etc.

class LoyaltyPoints(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('loyalty_points', uselist=False))

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))
    service = db.relationship('Service', backref=db.backref('feedbacks', lazy=True))
