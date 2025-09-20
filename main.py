from flask import Flask, request, session, render_template, redirect
from scripts import *
import sqlalchemy
import requests
import urllib.request
from flask_login import LoginManager, login_user
from data import db_session
from data.users import User
from data.db_session import global_init, SqlAlchemyBase
import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField, TextAreaField, FileField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    patronymic = StringField('Отечество')
    login = StringField('Логин', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_repeat = PasswordField('Повторите пароль', validators=[DataRequired()])
    rules = BooleanField('Соглашение пользователя')
    submit = SubmitField('Зарегистрироваться')


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

# @app.route('/authorization', methods=['GET'])
# def authorization():
#     return render_template("login.html")


@app.route('/authorization', methods=["GET", "POST"])
def login_form():
    session['login'] = ''
    session['role'] = 0
    form = LoginForm()
    if form.validate_on_submit():
        login_cur = db_sess.query(User).filter(User.login == str(form.login.data)).first()
        if not login_cur:
            return render_template('login.html', title='Авторизация',
                                   form=form,
                                   message="Такого пользователя не существует")
        elif login_cur.password != form.password.data:
            return render_template('login.html', title='Авторизация',
                                   form=form,
                                   message="Неверный пароль")
        login = form.login.data
        session['login'] = login

        return redirect('/')
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/registration', methods=["GET", "POST"])
def register_form():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        login_cur = db_sess.query(User).filter(User.login == form.login.data).first()
        if login_cur:
            return render_template('register_new.html', title='Авторизация',
                                   form=form,
                                   message="Такой пользователь уже существует")
        user = User()
        user.name = form.name.data
        user.surname = form.surname.data
        user.patronymic = form.patronymic.data
        user.login = form.login.data
        user.email = form.email.data
        user.password = form.password.data
        user.level = 1
        db_sess.add(user)
        db_sess.commit()

        return redirect('/')
    return render_template('register_new.html', title='Авторизация', form=form)
    
@app.route('/dashbord', methods=['GET'])
def dashboard():
    return render_template("dashbord.html")

if __name__ == '__main__':
    app.debug = True
    app.run(port=8000, host='127.0.0.1')
