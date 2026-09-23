# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

# -*- coding: utf-8 -*-
"""
Scope Loader – Jio PSBC
"""

from database import SessionLocal
from models import Project, Scope

# -------------------------------------------------
# Scope Data for Jio PSBC
# -------------------------------------------------
# priority, circle, facility_name, node_id, num_servers
SCOPE_TABLE = [
    (1, "AP", "Hyderabad JDC", "AP4JPSBC01", 4),
    (1, "AP", "Vijayawada MCN", "AP7JPSBC01", 4),
    (1, "AP", "Vijayawada MCN", "AP7JPSBC02", 4),
    (1, "BH", "Patna GF SAG2", "BH6JPSBC01", 4),
    (1, "BH", "Patna GF SAG2", "BH6JPSBC02", 4),
    (1, "GJ", "Ahmedabad AG3", "GJ1JPSBC01", 4),
    (1, "GJ", "Ahmedabad SAG2", "GJ2JPSBC01", 4),
    (1, "HR", "Karnal MCN", "HR4JPSBC01", 4),
    (1, "KA", "Karnataka Peenya MCN", "KA4JPSBC01", 4),
    (1, "KA", "Karnataka Peenya MCN", "KA4JPSBC02", 4),
    (1, "MH", "Nagpur Mouda IDC 1", "MH2JPSBC01", 4),
    (1, "MP", "Indore MCN", "MP5JPSBC01", 4),
    (1, "RJ", "Udaipur MCN", "RJ4JPSBC01", 4),
    (1, "TN", "Madurai MCN", "TN5JPSBC01", 4),
    (1, "TN", "Madurai MCN", "TN5JPSBC02", 4),
    (1, "UPE", "Lucknow SAG2", "UPE2JPSBC01", 4),
    (1, "UPE", "Lucknow SAG2", "UPE2JPSBC02", 4),
    (1, "UPW", "Meerut MCN", "UPW4JPSBC01", 4),
    (1, "UPW", "Meerut MCN", "UPW4JPSBC02", 4),
    (1, "WB", "Berhampur MCN", "WB5JPSBC01", 4),
    (1, "WB", "Kharagpur MCN", "WB4JPSBC01", 4),

    (2, "AS", "Guwahati SAG2", "AS1JPSBC01", 4),
    (2, "DL", "Lawrence Road MCN", "DL3JPSBC01", 4),
    (2, "DL", "Noida AG3", "DL1JPSBC01", 4),
    (2, "KL", "Calicut MCN", "KL4JPSBC01", 4),
    (2, "KL", "Trivandrum MCN", "KL5JPSBC01", 4),
    (2, "MH", "Pune SAG2", "MH3JPSBC01", 4),
    (2, "MP", "Bhopal MCN1", "MP1JPSBC01", 4),
    (2, "MU", "Mumbai GDC", "MU2JPSBC01", 4),
    (2, "MU", "Mumbai IDC1", "MU4JPSBC01", 4),
    (2, "PB", "Chandigarh MCN", "PB4JPSBC01", 4),
    (2, "PB", "Jalandhar MCN", "PB3JPSBC01", 4),

    (3, "AP", "Hyderabad LB Nagar AG3", "AP1JPSBC01", 4),
    (3, "AS", "Nagaon NLD AG2", "AS4JPSBC01", 4),
    (3, "BH", "Muzaffarpur MCN", "BH5JPSBC01", 4),
    (3, "BH", "Muzaffarpur MCN", "BH5JPSBC02", 4),
    (3, "BH", "Patna GF SAG2", "BH6JPSBC03", 4),
    (3, "BH", "Patna SAG2", "BH1JPSBC01", 4),
    (3, "GJ", "Jamnagar IDC", "GJ3JPSBC01", 4),
    (3, "HP", "Shimla Panthaghati SAG2", "HP1JPSBC01", 4),
    (3, "JK", "Nohata MAG2", "JK3JPSBC01", 4),
    (3, "KA", "Bangalore Whitefield AG3", "KA1JPSBC01", 4),
    (3, "KOL", "Kolkata AG3", "KOL1JPSBC01", 4),
    (3, "MH", "Pune SAG2", "MH3JPSBC02", 4),
    (3, "OR", "Sambalpur GF MCN", "OR5JPSBC01", 4),
    (3, "OR", "Sambalpur GF MCN", "OR5JPSBC02", 4),
    (3, "RJ", "Jodhpur MCN", "RJ5JPSBC01", 4),
    (3, "RJ", "Jodhpur MCN", "RJ5JPSBC02", 4),
    (3, "TN", "Coimbatore MCN", "TN4JPSBC01", 4),
    (3, "UPE", "Kanpur MCN1", "UPE4JPSBC01", 4),
    (3, "UPE", "Kanpur MCN1", "UPE4JPSBC02", 4),
    (3, "UPE", "Kanpur MCN1", "UPE4JPSBC03", 4),
    (3, "UPW", "Agra MCN", "UPW5JPSBC01", 4),
    (3, "WB", "Siliguri GF SAG2", "WB6JPSBC01", 4),
    (3, "WB", "Siliguri GF SAG2", "WB6JPSBC02", 4),
]


def load_scope():
    db = SessionLocal()

    project = db.query(Project).filter(
        Project.name == "Jio PSBC"
    ).first()

    if not project:
        print("❌ Project Jio PSBC not found")
        return

    for priority, circle, facility, node, servers in SCOPE_TABLE:
        scope = Scope(
            project_id=project.id,
            priority=priority,
            circle=circle,
            facility_name=facility,
            node_id=node,
            num_servers=servers,
            status="Not Started"
        )
        db.add(scope)

    db.commit()
    db.close()
    print("✅ Scope for Jio PSBC loaded successfully")


if __name__ == "__main__":
    load_scope()