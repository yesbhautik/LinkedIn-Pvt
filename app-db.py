from flask import Flask, request, jsonify, render_template, send_file
from sqlalchemy import create_engine, Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json
import os
from datetime import datetime, timedelta
from linkedin_api import Linkedin
from requests.cookies import RequestsCookieJar
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load environment variables
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

# Set up SQLAlchemy with connection pooling and SSL
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800
)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Define a model for storing LinkedIn profile data


class LinkedInProfile(Base):
    __tablename__ = 'linkedin_profiles'
    username = Column(String, primary_key=True)
    data = Column(JSON)
    timestamp = Column(DateTime)


Base.metadata.create_all(engine)

# Function to load cookies from a dictionary


def load_cookies_from_dict(cookie_dict):
    jar = RequestsCookieJar()
    for key, value in cookie_dict.items():
        jar.set(key, value)
    return jar

# Function to check if cached data is valid


def is_cache_valid(profile):
    return datetime.now() - profile.timestamp < timedelta(minutes=60)

# Function to save data to the database


def save_to_db(username, data):
    session = Session()
    profile = LinkedInProfile(
        username=username, data=data, timestamp=datetime.now())
    session.merge(profile)
    session.commit()
    session.close()

# Function to load data from the database


def load_from_db(username):
    session = Session()
    profile = session.query(LinkedInProfile).filter_by(
        username=username).first()
    session.close()
    return profile

# Function to fetch LinkedIn profile data


def fetch_profile_data(username, use_cache):
    profile = load_from_db(username)
    if use_cache and profile and is_cache_valid(profile):
        return profile.data

    # Load LinkedIn cookies
    try:
        with open("cookies.json", "r") as f:
            cookies_dict = json.load(f)
            cookies = load_cookies_from_dict(cookies_dict)
    except json.JSONDecodeError:
        return {"error": "Error loading cookies.json"}

    # Initialize LinkedIn API client
    try:
        linkedin = Linkedin(
            "dummy_username", "dummy_password", cookies=cookies)
    except Exception as e:
        return {"error": f"Error during LinkedIn authentication: {str(e)}"}

    # Fetch data
    try:
        profile = linkedin.get_profile(public_id=username)
        contact_info = linkedin.get_profile_contact_info(public_id=username)
        experiences = linkedin.get_profile_experiences(
            urn_id=profile['profile_id'])
        skills = linkedin.get_profile_skills(public_id=username)
        connections = linkedin.get_profile_connections(
            urn_id=profile['profile_id'])

        data = {
            "profile": profile,
            "contact_info": contact_info,
            "experiences": experiences,
            "skills": skills,
            "connections": connections
        }

        save_to_db(username, data)
        return data
    except Exception as e:
        return {"error": f"Error fetching data: {str(e)}"}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/fetchdata/<username>/<action>', methods=['GET'])
def handle_data(username, action):
    use_cache = request.args.get('cache', 'true').lower() == 'true'
    data = fetch_profile_data(username, use_cache)

    if "error" in data:
        return jsonify(data), 404

    if action == 'raw':
        return jsonify(data)
    elif action == 'download':
        # Temporarily write data to a file for download
        with open(f"{username}.json", "w") as f:
            json.dump(data, f)
        return send_file(f"{username}.json", as_attachment=True)
    elif action == 'web-view':
        return render_template('web_view.html', data=data)
    else:
        return jsonify({"error": "Invalid action"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
