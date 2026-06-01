# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 18:37:28 2026

@author: Manoj5.Mishra
"""

from database import engine
from models import Programme, Project, Task
from database import Base

Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully")