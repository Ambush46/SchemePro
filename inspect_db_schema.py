import sqlite3
import os
path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'schemepro.db'))
print('db exists:', os.path.exists(path))
print('db path:', path)
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables:', cur.fetchall())
for tbl in ['levels', 'subjects', 'payments', 'wallet_transactions']:
    print('\nTABLE', tbl)
    try:
        cur.execute(f"PRAGMA table_info({tbl})")
        for row in cur.fetchall():
            print(row)
    except Exception as e:
        print('ERR', e)
conn.close()
