from flask import Flask, request, jsonify, g
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME,JWT_SECRET_KEY

app = Flask(__name__)
app.config['MYSQL_HOST'] = DB_HOST
app.config['MYSQL_USER'] = DB_USER
app.config['MYSQL_PASSWORD'] = DB_PASSWORD
app.config['MYSQL_DB'] = DB_NAME
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY

mysql = MySQL(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


# User registration
@app.route('/register', methods=['POST'])
def register():
    username = request.json['username']
    password = request.json['password']
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
    mysql.connection.commit()
    cur.close()

    return jsonify(message='Registration successful'), 201


# User login
@app.route('/login', methods=['POST'])
def login():
    username = request.json['username']
    password = request.json['password']

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()

    if user and bcrypt.check_password_hash(user['password'], password):
        access_token = create_access_token(identity=user['id'])
        return jsonify(access_token=access_token), 200

    return jsonify(message='Invalid username or password'), 401


# Create a tweet
@app.route('/tweets', methods=['POST'])
@jwt_required()
def create_tweet():
    current_user_id = get_jwt_identity()
    content = request.json['content']

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO tweets (user_id, content) VALUES (%s, %s)", (current_user_id, content))
    mysql.connection.commit()
    cur.close()

    return jsonify(message='Tweet created successfully'), 201


# Get tweets from followed users
@app.route('/tweets', methods=['GET'])
@jwt_required()
def get_tweets():
    current_user_id = get_jwt_identity()

    cur = mysql.connection.cursor()
    cur.execute("SELECT t.content, u.username FROM tweets t "
                "INNER JOIN users u ON t.user_id = u.id "
                "WHERE t.user_id IN "
                "(SELECT followed_user_id FROM followers WHERE user_id = %s)", (current_user_id,))
    tweets = cur.fetchall()
    cur.close()

    return jsonify(tweets=tweets), 200


# Follow a user
@app.route('/follow', methods=['POST'])
@jwt_required()
def follow_user():
    current_user_id = get_jwt_identity()
    followed_user_id = request.json['followed_user_id']

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO followers (user_id, followed_user_id) VALUES (%s, %s)", (current_user_id, followed_user_id))
    mysql.connection.commit()
    cur.close()

    return jsonify(message='User followed successfully'), 201


# Unfollow a user
@app.route('/unfollow', methods=['POST'])
@jwt_required()
def unfollow_user():
    current_user_id = get_jwt_identity()
    followed_user_id = request.json['followed_user_id']

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM followers WHERE user_id = %s AND followed_user_id = %s", (current_user_id, followed_user_id))
    mysql.connection.commit()
    cur.close()

    return jsonify(message='User unfollowed successfully'), 200


# Search for tweets
@app.route('/tweets/search', methods=['GET'])
@jwt_required()
def search_tweets():
    current_user_id = get_jwt_identity()
    keyword = request.args.get('keyword')

    cur = mysql.connection.cursor()
    cur.execute("SELECT t.content, u.username FROM tweets t "
                "INNER JOIN users u ON t.user_id = u.id "
                "WHERE t.content LIKE %s", ('%' + keyword + '%',))
    tweets = cur.fetchall()
    cur.close()

    return jsonify(tweets=tweets), 200


# Pagination for tweets
@app.route('/tweets/page/<int:page>', methods=['GET'])
@jwt_required()
def get_tweets_paginated(page):
    current_user_id = get_jwt_identity()
    per_page = 10
    offset = (page - 1) * per_page

    cur = mysql.connection.cursor()
    cur.execute("SELECT t.content, u.username FROM tweets t "
                "INNER JOIN users u ON t.user_id = u.id "
                "WHERE t.user_id IN "
                "(SELECT followed_user_id FROM followers WHERE user_id = %s) "
                "ORDER BY t.created_at DESC LIMIT %s OFFSET %s", (current_user_id, per_page, offset))
    tweets = cur.fetchall()
    cur.close()

    return jsonify(tweets=tweets), 200


if __name__ == '__main__':
    app.run(debug=True)
