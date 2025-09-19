import sqlalchemy
from sqlalchemy import orm, ForeignKey
import datetime
from .db_session import SqlAlchemyBase

class TgUser(SqlAlchemyBase):
    __tablename__ = "tg_users"
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    tg_id = sqlalchemy.Column(sqlalchemy.String)
    tg_use = sqlalchemy.Column(sqlalchemy.String)
    role = sqlalchemy.Column(sqlalchemy.Integer)
    status = sqlalchemy.Column(sqlalchemy.Integer) # 0 - свободен, 1 - обрабатывает заказ, 2 - admin



class User(SqlAlchemyBase):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    login = sqlalchemy.Column(sqlalchemy.String)
    password = sqlalchemy.Column(sqlalchemy.String)
    name = sqlalchemy.Column(sqlalchemy.String)
    role = sqlalchemy.Column(sqlalchemy.Integer)


class Orders(SqlAlchemyBase):
    __tablename__ = 'orders'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    id_users = sqlalchemy.Column(sqlalchemy.Integer)
    data = sqlalchemy.Column(sqlalchemy.DateTime)
    relevant = sqlalchemy.Column(sqlalchemy.Integer)
    

class Product(SqlAlchemyBase):
    __tablename__ = 'product'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    id_orders = sqlalchemy.Column(sqlalchemy.Integer)
    count = sqlalchemy.Column(sqlalchemy.Integer)
    article = sqlalchemy.Column(sqlalchemy.String)
    name = sqlalchemy.Column(sqlalchemy.String)
    delivery_city = sqlalchemy.Column(sqlalchemy.Integer) ## город где будет получать

class HistoryBuy(SqlAlchemyBase):
    __tablename__ = 'history_buy'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    id_product = sqlalchemy.Column(sqlalchemy.Integer, ForeignKey("product.id"))
    count = sqlalchemy.Column(sqlalchemy.Integer)
    pick_point = sqlalchemy.Column(sqlalchemy.String) #пункт выдачи
    data = sqlalchemy.Column(sqlalchemy.DateTime)
    id_manager = sqlalchemy.Column(sqlalchemy.Integer)
    status = sqlalchemy.Column(sqlalchemy.Integer)



class TelephoneNumber(SqlAlchemyBase):
    __tablename__ = 'telephone_number'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    numbers = sqlalchemy.Column(sqlalchemy.String)
    country = sqlalchemy.Column(sqlalchemy.Integer)
    city = sqlalchemy.Column(sqlalchemy.Integer)
    status = sqlalchemy.Column(sqlalchemy.Integer)
    info = sqlalchemy.Column(sqlalchemy.Integer)


class Proxy(SqlAlchemyBase):
    __tablename__ = 'proxy'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    ip = sqlalchemy.Column(sqlalchemy.String)
    port = sqlalchemy.Column(sqlalchemy.String)
    username = sqlalchemy.Column(sqlalchemy.String)
    password = sqlalchemy.Column(sqlalchemy.String)
    country = sqlalchemy.Column(sqlalchemy.Integer)
    city = sqlalchemy.Column(sqlalchemy.Integer)
    status = sqlalchemy.Column(sqlalchemy.Integer)

class Info(SqlAlchemyBase):
    __tablename__ = 'info'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    count_orders = sqlalchemy.Column(sqlalchemy.Integer)
    last_session = sqlalchemy.Column(sqlalchemy.DateTime)
    last_country = sqlalchemy.Column(sqlalchemy.Integer)
    last_city = sqlalchemy.Column(sqlalchemy.Integer)


class Country(SqlAlchemyBase):
    __tablename__ = 'country'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    

class City(SqlAlchemyBase):
    __tablename__ = 'city'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String)

class OrderPickPoint(SqlAlchemyBase):
    __tablename__ = "order_pick_point"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    city = sqlalchemy.Column(sqlalchemy.String)
    address = sqlalchemy.Column(sqlalchemy.String)
    status = sqlalchemy.Column(sqlalchemy.Integer) #0 - свободно; 1 - курьер в пути; 2 - курьер забрал заказ
    tg_use = sqlalchemy.Column(sqlalchemy.String)
    tg_id = sqlalchemy.Column(sqlalchemy.String)

class Settings(SqlAlchemyBase):
    __tablename__ = "settings"
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    id_user = sqlalchemy.Column(sqlalchemy.Integer)
    proxifier = sqlalchemy.Column(sqlalchemy.String)
    pytesseract = sqlalchemy.Column(sqlalchemy.String)
    bluestacks = sqlalchemy.Column(sqlalchemy.String)
    adb = sqlalchemy.Column(sqlalchemy.String)



    









