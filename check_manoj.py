# -*- coding: utf-8 -*-
"""
Created on Fri Apr 17 15:34:17 2026

@author: Manoj5.Mishra
"""


import sqlite3

conn = sqlite3.connect("iptt.db")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM task_execution")
print(cur.fetchone())

conn.close()
