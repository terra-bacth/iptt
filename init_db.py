# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from database import engine
from models import Programme, Project, Task
from database import Base

Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully")