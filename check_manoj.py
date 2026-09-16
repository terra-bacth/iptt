# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

import sqlite3

conn = sqlite3.connect("iptt.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM task_execution")
print(cur.fetchone())

conn.close()