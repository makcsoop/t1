from data.db_session import global_init
from data.users import *

from data import db_session

import datetime

db_session.global_init('db/base.db')

db_sess = db_session.create_session()

users = [["admin", "1234", "makc.rosvlo@gmail.com", "Arz_solo_guitar"], ["user", "1234", "makc.soop@gmail.com", "arz_solo_guitar"]]

for i in users:
    od = User()
    od.login = i[0]
    od.password = i[1]
    od.email = i[2]
    od.tg_name = i[3]

    db_sess.add(od)
    db_sess.commit()

db_sess.close()


