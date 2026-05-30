import os
import sqlite3
from manage import app
from flask import current_app
from flask_migrate import upgrade

print('app database uri:', app.config['SQLALCHEMY_DATABASE_URI'])
print('db file exists before:', os.path.exists('schemepro.db'))
print('db file size before:', os.path.getsize('schemepro.db') if os.path.exists('schemepro.db') else 'n/a')

with app.app_context():
    print('migrate engine url:', current_app.extensions['migrate'].db.engine.url)
    try:
        upgrade()
        print('upgrade() completed')
    except Exception as exc:
        print('upgrade exception:', exc)

print('db file exists after:', os.path.exists('schemepro.db'))
print('db file size after:', os.path.getsize('schemepro.db') if os.path.exists('schemepro.db') else 'n/a')
conn = sqlite3.connect('schemepro.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables after upgrade:', cur.fetchall())
conn.close()
