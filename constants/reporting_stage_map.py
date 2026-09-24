# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

REPORTING_STAGE_MAP = {

    "H/W Order Completed": "Ordering Completed",
    "IRM Ordering Completed": "Ordering Completed",
    "Cabaling Service PO Available": "Ordering Completed",
    "Application service PO Availibility": "Ordering Completed",
    "Scope defined and available": "Planning Completed",
    "Project Initiation": "Planning Completed",

    "H/W at NWH": "Material Available",
    "IRM at NWH": "Material Available",
    "DMTO/SO1 Creation for HW": "Material in Transit",
    "HW @SWH": "Material in Transit",
    "HW @Site": "Material at Site",
    "IRM disptatched": "Material in Transit",
    "IRM @SWH": "Material in Transit",
    "IRM @Site": "Material at Site",

    "Facility Readiness and allocation": "Infra Allocated",
    "Rack Layout availibility": "Infra Allocated",
    "Cable length to be available": "Infra Allocated",
    "NSIP ID Creation": "Material in Transit",
    "P2P Availibility": "IP Readiness WIP",
    "Final P2P Upload": "IP Readiness WIP",
    "P2P Approved": "IP Readiness WIP",
    "ToR Site Survey": "IP Readiness WIP",
    "IP readiness": "IP Readiness Completed",
    "NEID Availibility": "Integration Readiness",
    "Security Clearance": "Security Clearance",
    "NIT Clearance": "Testing Readiness",

    "TOR  HW I & C": "IP Readiness WIP",
    "HW Rack-stack & Power ON": "HW Deployment Completed",
    "Ilo Reachability check": "HW Deployment Completed",
    "Server to ToR Cabaling": "Cabling WIP",
    "Lebeling": "Labeling WIP",
    "HW HOTO Checklist Imp.": "Under HW Configuration",
    "SO2 Completion": "HW Configuration completed",
    "HW Handover to Application Team": "HW Handover to Application I&C",
    "OS Installation": "Application Deployment & Integration WIP",
    "Application I & C": "Application Deployment & Integration WIP",
    "SO3 Submission": "Integration Readiness",
    "SO4 Completion": "Application Deployment & Integration WIP",
    "Nw Integration": "Application Deployment & Integration WIP",
    "OSS Integration": "Application Deployment & Integration WIP",

    "Testing Offered": "Under Testing",
    "Testing Completion": "Validation & Testing Completed",
    "ATP Offer": "Under ATP",
    "ATP Acceptance": "ATP Acceptance",

    "IDC - Node Offer": "IDC & NOC Handover WIP",
    "IDC -  Node Acceptance": "IDC & NOC Handover WIP",
    "NOC - Node offer": "IDC & NOC Handover WIP",
    "NOC - Node Acceptance": "IDC & NOC Handover Completed",
    "Ready for Service": "RFS",

    "Go Live": "Live"
}