from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Service, Booking, Contact, Referral
from . import db, mail
from flask_mail import Message
import random
import string

main = Blueprint('main', __name__)

# Move all your existing route functions here
# For example:

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/services')
def services():
    return render_template('services.html')

# ... (move all other route functions here)

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

# ... (include all other helper functions here)