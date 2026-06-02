# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from reportlab.lib import colors

from reportlab.lib.styles import getSampleStyleSheet

from reportlab.lib.pagesizes import A4


def generate_circle_pdf(report):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elements = []

    # =====================================
    # TITLE
    # =====================================

    title = f"""
    Circle Executive Dashboard
    <br/>
    {report['project_name']} → {report['circle']}
    """

    elements.append(
        Paragraph(title, styles['Title'])
    )

    elements.append(Spacer(1, 20))

    # =====================================
    # KPI TABLE
    # =====================================

    kpi_data = [

        ["Metric", "Value"],

        ["Total Nodes", report["total_nodes"]],

        ["Live Nodes", report["live_nodes"]],

        ["Completion %", f"{report['completion']}%"],

        ["Health", f"{report['health']}%"]
    ]

    kpi_table = Table(kpi_data)

    kpi_table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f2933")),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))

    elements.append(kpi_table)

    elements.append(Spacer(1, 20))

    # =====================================
    # EXECUTIVE SUMMARY
    # =====================================

    elements.append(
        Paragraph(
            "<b>Executive Summary</b>",
            styles['Heading2']
        )
    )

    elements.append(
        Paragraph(
            report["executive_summary"],
            styles['BodyText']
        )
    )

    elements.append(Spacer(1, 20))

    # =====================================
    # STAGE BREAKDOWN
    # =====================================

    stage_data = [

        ["Stage", "Nodes", "% Under Stage"]
    ]

    for stage, count in report["stage_summary"].items():

        stage_data.append([

            stage,

            count,

            f"{report['stage_percent'].get(stage,0)}%"
        ])

    stage_table = Table(stage_data)

    stage_table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f2933")),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))

    elements.append(stage_table)

    elements.append(Spacer(1, 20))

    # =====================================
    # NODE DETAILS
    # =====================================

    node_data = [

        ["Node", "Facility", "Stage", "Delay"]
    ]

    for n in report["node_details"]:

        node_data.append([

            n["node"],

            n["facility"],

            n["stage"],

            f"{n['delay']} Days"
        ])

    node_table = Table(node_data)

    node_table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f2933")),

        ('TEXTCOLOR', (0,0), (-1,0), colors.white),

        ('GRID', (0,0), (-1,-1), 1, colors.black),

        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
    ]))

    elements.append(node_table)

    elements.append(Spacer(1, 20))

    # =====================================
    # DELAY ITEMS
    # =====================================

    if report["delayed_items"]:

        delay_data = [

            ["Node", "Task", "Delay"]
        ]

        for d in report["delayed_items"][:15]:

            delay_data.append([

                d["node"],

                d["task"],

                f"{d['delay']} Days"
            ])

        delay_table = Table(delay_data)

        delay_table.setStyle(TableStyle([

            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7f1d1d")),

            ('TEXTCOLOR', (0,0), (-1,0), colors.white),

            ('GRID', (0,0), (-1,-1), 1, colors.black),

            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))

        elements.append(delay_table)

    # =====================================
    # BUILD
    # =====================================

    doc.build(elements)

    pdf = buffer.getvalue()

    buffer.close()

    return pdf