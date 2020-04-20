'''Used to connect database of our application'''

# Every request pushes a new application context, wiping the old one,
# So g can be used to set flags per-request without change to code.

# Scope of g is per request (thread) and it will not retain the value in subsequent request

from flask import g
import sqlite3


def connect_db():
    sql = sqlite3.connect('C:/Users/HP/PycharmProjects/qa-app/questions.db')  # You can put whole route there

    # Row provides both index-based and case-insensitive name-based access to columns with almost no memory overhead.
    # Better than your own custom dictionary-based approach or even a db_row based solution.

    sql.row_factory = sqlite3.Row  # Returning an object that can also access columns by name
    return sql


def get_db():

    # 'Hasattr main task is to check if an object has the given named attribute and return true if present, else false.
    # Parameters obj: object whose which attribute has to be checked, key: Attribute which needs to be checked.

    if not hasattr(g, 'sqlite.db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db



#
