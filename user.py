# user.py

from flask_login import UserMixin
from db import*
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash





class User(UserMixin):

 
    def __init__(self, id_, name, email, profile_pic,password_hash="",likes=0, views=0, subscribers=0, subscriber_name=None, subscriber_photo=None, subscription_date=None):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_pic = profile_pic
        self.password_hash = password_hash
        self.likes = likes
        self.views = views
        self.subscribers = subscribers
        self.subscriber_name = subscriber_name
        self.subscriber_photo = subscriber_photo
        self.subscription_date = subscription_date


   
    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            return None

        user = User(
            id_=user[0],
            name=user[1],
            email=user[2],
            profile_pic=user[3],
            password_hash=user[4],
            likes=user[5],       # Assuming likes is the 5th column in the table
            views=user[6],       # Assuming views is the 6th column in the table
            subscribers=user[7], # Assuming subscribers is the 7th column in the table
            subscriber_name=user[8],     # Assuming subscriber_name is the 8th column in the table
            subscriber_photo=user[9],    # Assuming subscriber_photo is the 9th column in the table
            subscription_date=user[10],   # Assuming subscription_date is the 10th column in the table
        )
        return user

    @staticmethod
    def create(id_, name, email, profile_pic,password_hash, likes=0, views=0, subscribers=0, subscriber_name="", subscriber_photo="", subscription_date=None):
        db = get_db()
        password_hash = generate_password_hash(password_hash, method='sha256')
        db.execute(
            "INSERT INTO user (id, name, email, profile_pic,password_hash, likes, views, subscribers, subscriber_name, subscriber_photo, subscription_date) "
            "VALUES (?, ?, ?, ?,?, ?, ?, ?, ?, ?, ?)",
            (id_, name, email, profile_pic,password_hash, likes, views, subscribers, subscriber_name, subscriber_photo, subscription_date),
        )
        db.commit()
