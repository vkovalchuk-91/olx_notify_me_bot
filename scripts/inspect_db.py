import sqlite3
import sys

db = sys.argv[1] if len(sys.argv) > 1 else 'django_olx_notify.db'
conn = sqlite3.connect(db)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY 1")]
print('tables:', tables)
for table in tables:
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info({table})')]
    print(table, cols)
