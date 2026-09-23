# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

import sqlite3

conn = sqlite3.connect("iptt.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM scope")
print("Scope rows:", cur.fetchone()[0])

cur.execute("SELECT node_id, circle, priority FROM scope LIMIT 5")
for row in cur.fetchall():
    print(row)

conn.close()