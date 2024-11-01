from flask import Flask, request, jsonify, render_template, send_file
import json
import os
from datetime import datetime, timedelta
from linkedin_api import Linkedin
from requests.cookies import RequestsCookieJar

app = Flask(__name__)

# Function to load cookies from a dictionary


def load_cookies_from_dict(cookie_dict):
    jar = RequestsCookieJar()
    for key, value in cookie_dict.items():
        jar.set(key, value)
    return jar

# Function to check if cached data is valid


def is_cache_valid(username):
    try:
        with open(f"data/{username}.json", "r") as f:
            data = json.load(f)
            timestamp = datetime.fromisoformat(data['timestamp'])
            return datetime.now() - timestamp < timedelta(minutes=60)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return False

# Function to save data to cache


def save_to_cache(username, data):
    data['timestamp'] = datetime.now().isoformat()
    os.makedirs('data', exist_ok=True)
    with open(f"data/{username}.json", "w") as f:
        json.dump(data, f)

# Function to load data from cache


def load_from_cache(username):
    with open(f"data/{username}.json", "r") as f:
        return json.load(f)

# Function to fetch LinkedIn profile data


def fetch_profile_data(username, use_cache):
    if use_cache and is_cache_valid(username):
        return load_from_cache(username)

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

        save_to_cache(username, data)
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
        return send_file(f"data/{username}.json", as_attachment=True)
    elif action == 'web-view':
        return render_template('web_view.html', data=data)
    else:
        return jsonify({"error": "Invalid action"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
