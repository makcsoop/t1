from flask import Flask, request, session, render_template, redirect, url_for
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
from wtforms.validators import DataRequired, Email

from typing import Dict, Any, Optional, Tuple
import time
import socket
from urllib.parse import urlparse
import ssl


class ResourceAvailabilityChecker:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        
    def check_resource(self, url: str) -> Dict[str, Any]:
        """
        Полная проверка доступности ресурса
        """
        result = {
            'url': url,
            'timestamp': datetime.datetime.now().isoformat(),
            'is_available': False,
            'status_code': None,
            'response_time': None,
            'content_available': False,
            'ssl_valid': None,
            'ssl_days_remaining': None,
            'error': None
        }
        
        try:
            # Проверка SSL сертификата
            ssl_result = self.check_ssl_certificate(url)
            result.update(ssl_result)
            
            # HTTP/HTTPS запрос
            http_result = self.make_http_request(url)
            result.update(http_result)
            
            # Проверка контента (базовая)
            if http_result['status_code'] == 200:
                content_result = self.check_content_availability(url)
                result.update(content_result)
            
            result['is_available'] = (result['status_code'] == 200 and 
                                    result['content_available'] and 
                                    result['ssl_valid'])
            
        except Exception as e:
            result['error'] = str(e)
            
        return result

    def make_http_request(self, url: str) -> Dict[str, Any]:
        """
        Выполняет HTTP/HTTPS запрос и анализирует ответ
        """
        result = {
            'status_code': None,
            'response_time': None,
            'headers': None
        }
        
        try:
            start_time = time.time()
            response = self.session.get(
                url, 
                timeout=self.timeout,
                allow_redirects=True,
                headers={
                    'User-Agent': 'AvailabilityChecker/1.0'
                }
            )
            end_time = time.time()
            
            result['status_code'] = response.status_code
            result['response_time'] = round((end_time - start_time) * 1000, 2)  # мс
            result['headers'] = dict(response.headers)
            
        except requests.exceptions.RequestException as e:
            result['error'] = f"HTTP request failed: {str(e)}"
            
        return result

    def check_ssl_certificate(self, url: str) -> Dict[str, Any]:
        """
        Проверяет SSL сертификат
        """
        result = {
            'ssl_valid': False,
            'ssl_days_remaining': None,
            'ssl_issuer': None,
            'ssl_subject': None
        }
        
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme != 'https':
                result['ssl_valid'] = True  # HTTP не требует SSL
                return result
            
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Проверяем срок действия
                    not_after = cert['notAfter']
                    expire_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                    days_remaining = (expire_date - datetime.now()).days
                    
                    result['ssl_valid'] = days_remaining > 0
                    result['ssl_days_remaining'] = days_remaining
                    result['ssl_issuer'] = dict(x[0] for x in cert['issuer'])
                    result['ssl_subject'] = dict(x[0] for x in cert['subject'])
                    
        except Exception as e:
            result['error'] = f"SSL check failed: {str(e)}"
            
        return result

    def check_content_availability(self, url: str) -> Dict[str, Any]:
        """
        Проверяет доступность контента (базовая проверка)
        """
        result = {
            'content_available': False,
            'content_length': 0,
            'content_type': None
        }
        
        try:
            response = self.session.get(
                url, 
                timeout=self.timeout,
                stream=True  # Не загружать все содержимое
            )
            
            if response.status_code == 200:
                result['content_available'] = True
                result['content_length'] = int(response.headers.get('content-length', 0))
                result['content_type'] = response.headers.get('content-type')
                
        except Exception as e:
            result['error'] = f"Content check failed: {str(e)}"
            
        return result

    def check_multiple_resources(self, urls: list) -> Dict[str, Dict[str, Any]]:
        """
        Проверяет несколько ресурсов одновременно
        """
        results = {}
        for url in urls:
            results[url] = self.check_resource(url)
        return results


class LoginForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    tg_name = StringField('TG', validators=[DataRequired()])
    login = StringField('Логин', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_repeat = PasswordField('Повторите пароль', validators=[DataRequired()])
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


@app.route('/authorization', methods=["GET", "POST"])
def login_form():
    if in_user(session.get("login")):
        return redirect(url_for('dashboard'))
    session['login'] = ''
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
                                   message="Неверный пароль!!!")
        login = form.login.data
        session['login'] = login

        return redirect('/dashboard')
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/registration', methods=["GET", "POST"])
def register_form():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        login_cur = db_sess.query(User).filter(User.login == form.login.data).first()
        if login_cur:
            return render_template('registration.html', title='Авторизация',
                                   form=form,
                                   message="Такой пользователь уже существует")
        if(len(form.password.data) < 8):
            return render_template('registration.html', title='Авторизация',
                                   form=form,
                                   message="Пароль должен содержать не менее 8 символов")
        if(str(form.password.data) != str(form.password_repeat.data)):
            print(str(form.password.data), str(form.password_repeat.data))
            return render_template('registration.html', title='Авторизация',
                                   form=form,
                                   message="Пароль не совпадают")
        user = User()
        user.login = form.login.data
        user.email = form.email.data
        user.tg_name = form.tg_name.data
        user.password = form.password.data
        db_sess.add(user)
        db_sess.commit()

        return redirect('/')
    return render_template('registration.html', title='Регистрация', form=form)
    

@app.route('/dashboard')
def dashboard():
    if not in_user(session.get("login")):
        return render_template("access_denied.html")
    return render_template("dashboard.html")

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/authorization')


@app.route('/checking', methods=['POST'])
def checking():
    return render_template("checkSiteDashboard.html")


def format_results(results: Dict[str, Any]) -> str:
    """
    Форматирует результаты проверки в читаемый вид
    """
    output = []
    output.append(f"Проверка ресурса: {results['url']}")
    output.append(f"Время проверки: {results['timestamp']}")
    output.append(f"Доступен: {'✅' if results['is_available'] else '❌'}")
    
    if results['status_code'] is not None:
        output.append(f"HTTP статус: {results['status_code']}")
    
    if results['response_time'] is not None:
        output.append(f"Время ответа: {results['response_time']} мс")
    
    if results['ssl_valid'] is not None:
        status = "✅ Valid" if results['ssl_valid'] else "❌ Invalid"
        output.append(f"SSL сертификат: {status}")
        if results['ssl_days_remaining'] is not None:
            output.append(f"Дней до истечения: {results['ssl_days_remaining']}")
    
    output.append(f"Контент доступен: {'✅' if results['content_available'] else '❌'}")
    
    if results['error']:
        output.append(f"Ошибка: {results['error']}")
    
    return "\n".join(output)
    
if __name__ == '__main__':
    app.debug = True
    app.run(port=8001, host='127.0.0.1')
    #checker = ResourceAvailabilityChecker(timeout=15)

# Проверка одного ресурса
    #result = checker.check_resource("https://github.com/")
    #print(format_results(result))
