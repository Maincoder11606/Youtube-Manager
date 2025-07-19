# Python standard libraries
import json
import os
import sqlite3
import sys
# Third-party libraries
from flask import *
from flask_login import*
from oauthlib.oauth2 import WebApplicationClient
import requests
from flask import Flask, jsonify
import datetime
import random
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
# Internal imports
from user import User
from googleapiclient.discovery import build
from db import*
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from user import User  # Import the User class from your user.py file
import uuid

#from apscheduler.schedulers.background import BackgroundScheduler

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET =  os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
UPLOAD_FOLDER = 'UsersProfilePic/'  # Replace with your desired folder path

# Configure the Flask app to use the upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#with app.app_context():
#init_db()


#apscheduler to auto update user youtube analytics
#scheduler = BackgroundScheduler() 
#scheduler.start()
#celery

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.login_view = "login_regular"
login_manager.init_app(app)

# Naive database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# Registration route and view function
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        # Additional fields

        db = get_db()
        existing_user = db.execute(
            "SELECT * FROM user WHERE email = ?", (email,)
        ).fetchone()

        if existing_user:
            # User with the same email already exists
            flash_message = 'User with this email already exists.'
            return render_template('signup.html',flash_message=flash_message)
            

        # Hash the password
        password_hash = generate_password_hash(password, method='sha256')

        # Generate a unique user ID using uuid
        unique_id = str(uuid.uuid4())

        # Create a new user instance and store it in the database
        db.execute(
            "INSERT INTO user (id, name, email, profile_pic, password_hash, likes, views, subscribers, subscriber_name, subscriber_photo, subscription_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (unique_id, name, email, '', password_hash, 0, 0, 0, 0, 0, 0),
        )
        db.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login_regular'))

    return render_template('signup.html')




# Login route and view function
@app.route('/', methods=['GET', 'POST'])
def login_regular():
    flash_message = None  # Default value for flash_message

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE email = ?", (email,)
        ).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            # Successfully logged in
            flash('Login successful.', 'success')

            # Log in the user using their unique ID
            user_id = user['id']
            login_user(User.get(user_id))  # Use the User.get method to fetch the user by ID

            # Redirect to the '/index' route after successful login
            return redirect(url_for('index'))
        else:
            flash_message = 'Invalid email or password.'

    return render_template('signin.html', flash_message=flash_message)



@app.route("/index", methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        db = get_db()
        recent_subscribers = db.execute(
           "SELECT subscriber_name, subscribers, subscriber_photo, subscription_date FROM user "
            "WHERE subscriber_name != '' AND subscriber_photo != '' AND subscription_date IS NOT NULL "
            "ORDER BY subscription_date DESC LIMIT 10"
        ).fetchall()

        form = request.form  # Replace YourForm with the actual form class you have

        if request.method == 'POST':
            channel_id = form.get('channel_id')
            api_key = 'AIzaSyBcTZ5ad-mRU-i4K557mBNNur2xl2rjqlw'

            # Make the API request to the YouTube Data API v3
            url = f'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}'
            response = requests.get(url)
            data = response.json()

            if 'items' in data and len(data['items']) > 0:
                channel_info = data['items'][0]['statistics']
                subscribers = channel_info['subscriberCount']
                views = channel_info['viewCount']
                likes = channel_info.get('videoCount') #viewCount

                # Update the user's record in the database with the new values
               
            
                db.execute(
                        "UPDATE user SET likes = ?, views = ?, subscribers = ? WHERE id = ?",
                        (likes, views, subscribers, current_user.id)
                    )
                
                db.commit()

                # Fetch and store the subscriber's name, photo, and subscription date from the YouTube Data API response
                subscriber_info = get_subscriber_info(api_key, channel_id)
                channel_creation_date = get_channel_creation_date(api_key, channel_id)

                if subscriber_info:
                    subscriber_name = subscriber_info.get('title', "")
                    subscriber_photo = subscriber_info.get('thumbnails', {}).get('default', {}).get('url', "")
                    subscription_date = datetime.datetime.strptime(channel_creation_date, "%Y-%m-%dT%H:%M:%SZ")

                    # Update the user's record in the database with the new values
                    db.execute(
                        "UPDATE user SET subscriber_name = ?, subscriber_photo = ?, subscription_date = ? WHERE id = ?",
                        (subscriber_name, subscriber_photo, subscription_date, current_user.id)
                    )
                    db.commit()
                else:
                    flash(f'Subscriber data not available', 'error')
            else:
                flash(f'Invalid Channel ID', 'error')

            # Redirect back to the index route
            return redirect(url_for('index'))
        
         # Fetch the data for the chart from the database
        data = db.execute(
                "SELECT views, subscribers, likes FROM user WHERE id = ?",
                (current_user.id,)
            ).fetchone()
        data_dict = dict(data)

    # Make sure that data_dict has metric names as keys and values as values
        metric_names = ['views', 'likes', 'subscribers']
        formatted_data_dict = {metric: data_dict[metric] for metric in metric_names}
        # Convert the Plotly figure to HTML
        chart_html = generate_chart(formatted_data_dict)

        user = User.get(current_user.id)

        
        # Render the index.html template with the flashed messages
        return render_template(
            "index.html",
            user_name=current_user.name,
            user_profile_pic=current_user.profile_pic,
            subscribers=format_number(current_user.subscribers),
            views=format_number(current_user.views),
            likes=format_number(current_user.likes),
            recent_subscribers=recent_subscribers,
            form=form,
            chart_html=chart_html,
        )
    else:
        return render_template("signin.html")

@app.route("/searchChannel", methods=["GET","POST"])
@login_required
def searchChannel():
    if current_user.is_authenticated:
        user = User.get(current_user.id)
        
        # Get the channel name from the GET request
        channel_name = request.form.get("channel_name")

        if channel_name:
            # Call YouTube Data API to search for the channel by name
            api_key = 'AIzaSyBcTZ5ad-mRU-i4K557mBNNur2xl2rjqlw'
            url = f'https://www.googleapis.com/youtube/v3/search?key={api_key}&part=snippet&q={channel_name}&type=channel'
            response = requests.get(url)
            data = response.json()
            
            # Extract the channel ID from the first search result
            if 'items' in data and data['items']:
                channel_id = data['items'][0]['id']['channelId']
            else:
                channel_id = None

            # Render the index.html template and pass the channel ID
            return render_template("index.html", user=user, channel_id=channel_id)

    return render_template("index.html")

    
def generate_chart(data_dict):
   
   df = pd.DataFrame({'Metrics': data_dict.keys(), 'Count': data_dict.values()})

    # Create a bar chart using Plotly Express
   fig = px.bar(df, x='Metrics', y='Count', labels={'Metrics': 'Metrics', 'Count': 'Count'})

    # Convert the plot to HTML
   chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')


   return chart_html

def format_number(number):
    if number >= 10**9:
        return f"{number / 10**9:.1f}B"
    elif number >= 10**6:
        return f"{number / 10**6:.1f}M"
    elif number >= 10**3:
        return f"{number / 10**3:.1f}K"
    else:
        return str(number)
       
def get_subscriber_info(api_key, channel_id):
    url = f'https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={api_key}'
    response = requests.get(url)
    data = response.json()

    if 'items' in data and len(data['items']) > 0:
        return data['items'][0]['snippet']
    else:
        return None
    
def get_channel_creation_date(api_key, channel_id):
    url = f'https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={api_key}'
    response = requests.get(url)
    data = response.json()
    if 'items' in data and len(data['items']) > 0:
        channel_snippet = data['items'][0]['snippet']
        creation_date = channel_snippet.get('publishedAt', "")
        return creation_date
    return ""





# Login
def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@app.route("/login") #login
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )

    return redirect(request_uri)


# Login Callback
@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")

    result = "<p>code: " + code + "</p>"

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    result = result + "<p>token_response: " + token_response.text + "</p>"

    # return result

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        email = userinfo_response.json()["email"]
        profile_pic_url = userinfo_response.json()["picture"]
        name = userinfo_response.json()["given_name"]

        profile_pic_filename = f"{unique_id}.jpg"  # Change the extension as needed

    # Download and save the image to a folder on your server
        profile_pic_path = os.path.join("UsersProfilePic", profile_pic_filename)
        response = requests.get(profile_pic_url)
        with open(profile_pic_path, "wb") as f:
            f.write(response.content)

    # Set the profile_picture variable to the filename of the saved image
        profile_picture = profile_pic_filename
    else:
        return "User email not available or not verified by Google.", 400
    
    #create a new user in your db with the information provided by Google
    user = User(id_=unique_id,
                 name=name, 
                 email=email, 
                 profile_pic=profile_picture,
                 password_hash="",
                 likes=0,
                 views=0,
                 subscribers=0,
                subscriber_name=0,
                subscriber_photo=0,
                subscription_date=0,)
        
    
# If the user doesn't exist
    if not User.get(unique_id):
       
            User.create(unique_id,
                        name,
                        email,
                        profile_pic=profile_picture,
                        password_hash="",
                        likes=0,
                        views=0,
                        subscribers=0,
                        subscriber_name=0,
                        subscriber_photo=0,
                        subscription_date=0,
                        )
        
    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))
   




 
  



#def fetch_and_update_data():
    api_key = 'AIzaSyBcTZ5ad-mRU-i4K557mBNNur2xl2rjqlw' 
    # Your code to fetch data from the YouTube Data API and update the database goes here
    # For example:

    # Fetch data from the YouTube Data API for the given channel ID
    
    channel_id = 'your_channel_id'
    url = f'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}'
    response = requests.get(url)
    data = response.json()

    if 'items' in data and len(data['items']) > 0:
        channel_info = data['items'][0]['statistics']
        subscribers = channel_info['subscriberCount']
        views = channel_info['viewCount']
        total_likes = channel_info.get('likeCount')

        # Update the user's record in the database with the new values
        db = get_db()
        db.execute(
            "UPDATE user SET likes = ?, views = ?, subscribers = ? WHERE id = ?",
            (total_likes, views, subscribers, current_user.id)
        )
        db.commit()





# Logout
@app.route('/logout')
@login_required  # Use this decorator to ensure only logged-in users can access this route
def logout():
    logout_user()
    return redirect(url_for('login_regular'))

#youtube 
@app.route("/watch", methods=['GET', 'POST'])
@login_required
def watch():
    if current_user.is_authenticated:
        user = User.get(current_user.id)
        
        if request.method == 'POST':
            search_query = request.form.get('search_query')
            if search_query:
                # Call YouTube Data API to get search results
                api_key = 'AIzaSyBcTZ5ad-mRU-i4K557mBNNur2xl2rjqlw'
                url = f'https://www.googleapis.com/youtube/v3/search?key={api_key}&part=snippet&q={search_query}&type=video&maxResults=21'
                response = requests.get(url)
                data = response.json()

                # Extract relevant information from the API response
                videos = []
                for item in data['items']:
                    video_id = item['id']['videoId']
                    video_info = get_video_info(api_key, video_id)  # Function to get video details
                    if video_info:
                        video = {
                            'title': item['snippet']['title'],
                            'video_id': video_id,
                            'thumbnail': item['snippet']['thumbnails']['default']['url'],
                            'likes': video_info['likes'],
                            'views': video_info['views']
                        }
                        videos.append(video)
                record_search_history(current_user.id, search_query)
                search_result = f'Search result for: {search_query}'
                recommended_videos = get_recommended_videos(current_user.id, search_query)
                
                return render_template("watch.html",
                                       user=user,
                                       videos=videos,
                                       search_query=search_query, 
                                       search_result=search_result,
                                       recommended_videos=recommended_videos)
        
        search_result = "Search result for:"
        recommended_videos = get_recommended_videos(current_user.id, "")
        
        return render_template("watch.html",
                               user=user,
                               search_result=search_result,
                               recommended_videos=recommended_videos)

def get_video_info(api_key, video_id):
    url = f'https://www.googleapis.com/youtube/v3/videos?key={api_key}&part=statistics&id={video_id}'
    response = requests.get(url)
    data = response.json()
    
    if 'items' in data and len(data['items']) > 0:
        statistics = data['items'][0]['statistics']
        likes = format_number(int(statistics.get('likeCount', 0)))
        views = format_number(int(statistics.get('viewCount', 0)))
        return {'likes': likes, 'views': views}
    
    return None

def get_recommended_videos(user_id, search_query):
    db = get_db()
    history = db.execute(
        "SELECT DISTINCT search_query FROM search_history WHERE user_id = ? AND search_query != ?",
        (user_id, search_query)
    ).fetchall()
    
    recommended_videos = []
    api_key = 'AIzaSyBcTZ5ad-mRU-i4K557mBNNur2xl2rjqlw'
    
    for search_query in history:
        url = f'https://www.googleapis.com/youtube/v3/search?key={api_key}&part=snippet&q={search_query[0]}&type=video'
        response = requests.get(url)
        data = response.json()
        
        for item in data['items']:
            video_id = item['id']['videoId']
            video_info = get_video_info(api_key, video_id)
            recommended_video = {
                'title': item['snippet']['title'],
                'video_id': video_id,
                'thumbnail': item['snippet']['thumbnails']['default']['url'],
                'likes': video_info['likes'],
                'views': video_info['views']
            }
            recommended_videos.append(recommended_video)
    
    return recommended_videos


def check_search_history(user_id):
    db = get_db()
    history = db.execute(
        "SELECT COUNT(*) FROM search_history WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    
    return history[0] > 0  # Return True if there are records, otherwise False


@app.route("/profile_board", methods=['GET', 'POST'])
@login_required
def profile_board():
    if current_user.is_authenticated:
        # Fetch the user's data from the database using the current_user.id
        user = User.get(current_user.id)
        context = {
            'user': user,
            'format_number': format_number  # Pass the function to the context
        }

    # Render the profile.html template and pass the user's data to the template
        return render_template("profile.html",**context)

#this local access of profile pic    
@app.route('/profile_pic/<filename>')
def profile_pic(filename):
    return send_from_directory('UsersProfilePic', filename)

@app.route("/updateProfile", methods=['GET', 'POST'])
@login_required
def updateProfile():
    if current_user.is_authenticated:
        db = get_db()
        if request.method == "POST":
            # Get the form data
            new_username = request.form.get("name")
            new_email = request.form.get("email")
            new_password = request.form.get('password')  # Assuming you receive a plain text password
            new_profile_pic = request.files.get("profile_pic")

            # Hash the new password
            new_password_hash = generate_password_hash(new_password, method='sha256')

            # Update the user's profile information
            current_user.name = new_username
            current_user.email = new_email
            current_user.password_hash = new_password_hash  # Store the hashed password

            if new_profile_pic:
            # Handle profile picture upload (save the file and update the user's profile_pic field)
               filename = secure_filename(new_profile_pic.filename)
               new_profile_pic.save(os.path.join("UsersProfilePic", filename))
               current_user.profile_pic = filename

            # Commit changes to the database
            db.execute(
                "UPDATE user SET name = ?, email = ?, password_hash = ?, profile_pic = ? WHERE id = ?",
                (current_user.name, current_user.email, current_user.password_hash, current_user.profile_pic, current_user.id)
            )
            db.commit()

            # Redirect the user back to their profile page to see the changes
            return redirect(url_for("updateProfile"))

        # Render the updateProfile.html template if it's a GET request
        return render_template("updateProfile.html", user=current_user)


    # Render the updateProfile.html template if it's a GET request
    return render_template("updateProfile.html", user=current_user)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if current_user.is_authenticated:
        # Fetch the user's data from the database using the current_user.id
        user = User.get(current_user.id)
        context = {
            'user': user,
            'format_number': format_number,# Pass the function to the context
          
        }
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        user_experience = request.form["user_experience"]
        performance = request.form["performance"]
        content_quality = request.form["content_quality"]
        suggestions=request.form["suggestions"]

        # Construct the email message
        subject = f"Feedback from {name}"
        message = f"Name: {name}\nEmail: {email}\nUser Experience: {user_experience}\nPerformance: {performance}\nContent Quality: {content_quality}\nSuggestions: {suggestions}"
        # Configure your email settings
        smtp_server = "smtp.googlemail.com"
        smtp_port = 587
        smtp_username = "mainasara11606@gmail.com"
        smtp_password = "jtnlcdhepxvsdwnn"
        recipient_email = "maincoder11606@gmail.com"

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(smtp_username, recipient_email,msg.as_string())
            flash("Feedback sent successfully!", "success")
        except Exception as e:
            flash(f"Error sending feedback: {str(e)}", "error")

        return redirect("/feedback")

    return render_template("feedback.html",**context)

     
@app.route("/theme",methods=['GET', 'POST'])
@login_required
def theme():
    if current_user.is_authenticated:
        # Fetch the user's data from the database using the current_user.id
        user = User.get(current_user.id)
        context = {
            'user': user,
            'format_number': format_number,# Pass the function to the context
          
        }

    # Render the profile.html template and pass the user's data to the template
        return render_template("Theme.html",**context)      

if __name__ == "__main__":
     with app.app_context():
        app.run(ssl_context="adhoc", port=5001,debug=True)
