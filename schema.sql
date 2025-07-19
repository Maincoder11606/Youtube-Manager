
-- DROP TABLE user; if added new column
-- Create the user table with the necessary columns
CREATE TABLE user(
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    profile_pic TEXT NOT NULL,
    password_hash TEXT,
    likes INTEGER NOT NULL,
    views INTEGER NOT NULL,
    subscribers INTEGER NOT NULL,
    subscriber_name TEXT NOT NULL,  
    subscriber_photo TEXT NOT NULL,     
    subscription_date DATE 
);



-- user search history based on searching
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    search_query TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
);
