from models import (
    LeadershipAction
)

from datetime import date
# =========================================
# GET PROJECT ACTIONS
# =========================================

def get_leadership_actions(
    project_id,
    db
):

    actions = db.query(
        LeadershipAction
    ).filter(

        LeadershipAction.project_id == project_id

    ).order_by(

        LeadershipAction.priority.desc(),

        LeadershipAction.target_date.asc()

    ).all()

    result = []

    for a in actions:
        overdue_days = 0
        
        if (
            a.target_date and
            a.status != "Closed" and
            a.target_date < date.today()
        ):
        
            overdue_days = (
                date.today() - a.target_date
            ).days
        if overdue_days >= 15:
        
            escalation = "Critical"
        
        elif overdue_days >= 7:
        
            escalation = "High"
        
        elif overdue_days > 0:
        
            escalation = "Medium"
        
        else:
        
            escalation = "Normal"        
        
        result.append({

            "id": a.id,

           "action": a.action_required,

            "owner": a.owner,

            "priority": a.priority,

            "status": a.status,
            
            "overdue_days": overdue_days,

            "escalation": escalation,

            "target_date": (
                a.target_date.strftime("%d-%b-%Y")
                if a.target_date else "-"
            ),

            "remarks": a.remarks or "-"
        })

    return result


# =========================================
# CREATE ACTION
# =========================================

def create_leadership_action(

    project_id,
    action,
    owner,
    priority,
    status,
    target_date,
    remarks,
    db
):

    new_action = LeadershipAction(

        project_id=project_id,
        
        circle="-",

        node="-",

        risk_area="-",

        action_required=action,

        owner=owner,

        priority=priority,

        status="Open",

        target_date=target_date,

        remarks=remarks
    )

    db.add(new_action)

    db.commit()

    db.refresh(new_action)

    return new_action


# =========================================
# UPDATE ACTION STATUS
# =========================================

def update_leadership_action(

    action_id,
    status,
    priority,
    target_date,
    remarks,
    db
):

    action = db.query(
        LeadershipAction
    ).filter(

        LeadershipAction.id == action_id

    ).first()

    if not action:
        return None

    action.status = status
    
    action.priority = priority

    action.target_date = target_date

    action.remarks = remarks

    db.commit()

    db.refresh(action)

    return action


# =========================================
# DELETE ACTION
# =========================================

def delete_leadership_action(

    action_id,
    db
):

    action = db.query(
        LeadershipAction
    ).filter(

        LeadershipAction.id == action_id

    ).first()

    if not action:
        return False

    db.delete(action)

    db.commit()

    return True