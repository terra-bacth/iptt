# constants/reporting_weights.py

STAGE_WEIGHTS = {

    # -----------------------------------
    # PRE-EXECUTION
    # -----------------------------------

    "Not Started": 0,

    "Ordering Completed": 2,

    "Planning Completed": 5,

    # -----------------------------------
    # MATERIAL
    # -----------------------------------

    "Material Available": 7,

    "Material in Transit": 8,

    "Material at Site": 10,

    # -----------------------------------
    # INFRA / IP
    # -----------------------------------

    "Infra Allocated": 12,

    "IP Readiness WIP": 13,

    "IP Readiness Completed": 15,

    # -----------------------------------
    # DEPLOYMENT
    # -----------------------------------

    "Cabling WIP": 16,
    
    "Labeling WIP": 17,

    "HW Deployment Completed": 20,

    "Under HW Configuration": 25,

    "HW Configuration completed": 27,

    # -----------------------------------
    # APPLICATION
    # -----------------------------------

    "HW Handover to Application I&C": 30,

    "Integration Readiness": 45,

    "Application Deployment & Integration WIP": 50,

    # -----------------------------------
    # TESTING
    # -----------------------------------

    "Testing Readiness": 55,

    "Under Testing": 60,

    "Validation & Testing Completed": 80,

    # -----------------------------------
    # ATP
    # -----------------------------------

    "Under ATP": 85,

    "ATP Acceptance": 90,

    # -----------------------------------
    # HANDOVER
    # -----------------------------------

    "IDC & NOC Handover WIP": 94,

    "IDC & NOC Handover Completed": 97,

    "Security Clearance": 98,

    "RFS": 99,

    # -----------------------------------
    # LIVE
    # -----------------------------------

    "Live": 100
}