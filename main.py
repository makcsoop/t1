from flask import Flask, request, session, render_template
from scripts import *
import sqlalchemy
import requests
import urllib.request
from flask_login import LoginManager, login_user
from data import db_session
from data.users import User
from data.db_session import global_init, SqlAlchemyBase
import datetime


# яндекс ключ к картам  f9727fb1-f338-4780-b4c4-d639d0a62107
#http://localhost:8000/registration?login=user1&name=max&password=1234&password2=12&email=max@gmail.com

#http://localhost:8000/authorization?login=user&password=1234

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)

db_session.global_init('db/base.db')

@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)

db_sess = db_session.create_session()

@app.route('/', methods=['GET'])
def main():
    return render_template("main.html")

@app.route('/authorization', methods=['GET'])
def authorization():
    return render_template("login.html")


@app.route('/dasd', methods=['GET'])
def login():
    session['login'] = ''
    session['role'] = 0
    session['id'] = -1
    args = request.args
    login = args.get('login')
    password = args.get('password')
    #db_sess = db_session.create_session()
    login_cur = db_sess.query(User).filter(User.login == str(login), User.activity == 1).first()
    if len(login) and len(password):
        login_cur = db_sess.query(User).filter(User.login == login, User.password == password).first()
        if login_cur:
            ID = get_id(login)
            session['id'] = ID
            session['login'] = login
            return {"flag": 1}
        else:
            return {"flag": 2}
    else:
        return {"flag": 0}
    

    

if __name__ == '__main__':
    app.debug = True
    app.run(port=8000, host='127.0.0.1')
