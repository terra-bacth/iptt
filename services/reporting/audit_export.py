# -*- coding: utf-8 -*-
"""Audit log export service providing CSV, Excel, and JSON generation for IPTT governance ledger."""

import csv
import io
import json
from datetime import datetime
from typing import List, Any


def generate_audit_csv(logs: List[Any]) -> bytes:
    """Generate RFC 4180 compliant CSV bytes with UTF-8 BOM for Microsoft Excel compatibility."""
    output = io.StringIO()
    # Write UTF-8 BOM so Excel on Windows opens accented/special characters correctly
    output.write("\ufeff")

    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header Row
    writer.writerow([
        "Event ID",
        "Timestamp (UTC)",
        "Operator",
        "Action",
        "Scope ID",
        "Task ID",
        "Field Modified",
        "Prior Value",
        "Committed Value",
    ])

    for log in logs:
        ts_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if getattr(log, "timestamp", None) else ""
        writer.writerow([
            getattr(log, "id", "") or "",
            ts_str,
            getattr(log, "user", "") or "",
            getattr(log, "action", "") or "",
            getattr(log, "scope_id", "") or "",
            getattr(log, "task_id", "") or "",
            getattr(log, "field", "") or "",
            getattr(log, "old_value", "") or "",
            getattr(log, "new_value", "") or "",
        ])

    return output.getvalue().encode("utf-8")


def generate_audit_excel(logs: List[Any]) -> bytes:
    """Generate a formatted, enterprise-styled Excel (.xlsx) workbook using OpenPyXL."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Audit Ledger"

    # Styling Palettes (Enterprise Dark Slate & Crisp Surfaces)
    title_font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    title_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")

    meta_font = Font(name="Calibri", size=10, italic=True, color="64748B")

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")

    data_font = Font(name="Calibri", size=10)
    mono_font = Font(name="Consolas", size=9.5)

    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    thin_border_side = Side(style="thin", color="CBD5E1")
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # 1. Title Block (Row 1)
    ws.merge_cells("A1:I1")
    ws["A1"] = "Integrated Project Tracking Tool (IPTT) — Audit & Governance Ledger"
    ws["A1"].font = title_font
    ws["A1"].fill = title_fill
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 36

    # 2. Subtitle / Metadata (Row 2)
    export_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ws.merge_cells("A2:I2")
    ws["A2"] = f"Exported: {export_time} | Total Recorded Events: {len(logs)} | Clearances: Administrator Governance Ledger"
    ws["A2"].font = meta_font
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20

    # 3. Blank spacer (Row 3)
    ws.row_dimensions[3].height = 10

    # 4. Header Row (Row 4)
    headers = [
        ("A", "Event ID", Alignment(horizontal="center", vertical="center")),
        ("B", "Timestamp (UTC)", Alignment(horizontal="center", vertical="center")),
        ("C", "Operator", Alignment(horizontal="left", vertical="center")),
        ("D", "Action", Alignment(horizontal="center", vertical="center")),
        ("E", "Scope ID", Alignment(horizontal="center", vertical="center")),
        ("F", "Task ID", Alignment(horizontal="center", vertical="center")),
        ("G", "Field Modified", Alignment(horizontal="left", vertical="center")),
        ("H", "Prior Value", Alignment(horizontal="left", vertical="center")),
        ("I", "Committed Value", Alignment(horizontal="left", vertical="center")),
    ]

    ws.row_dimensions[4].height = 28
    for col_letter, title, align in headers:
        cell = ws[f"{col_letter}4"]
        cell.value = title
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align
        cell.border = cell_border

    # 5. Populate Data Rows (Row 5+)
    row_num = 5
    for idx, log in enumerate(logs):
        ts_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if getattr(log, "timestamp", None) else ""
        row_fill = zebra_fill if idx % 2 == 1 else white_fill

        values = [
            (getattr(log, "id", None) or "", mono_font, Alignment(horizontal="center")),
            (ts_str, mono_font, Alignment(horizontal="center")),
            (getattr(log, "user", "") or "", data_font, Alignment(horizontal="left")),
            (getattr(log, "action", "") or "", data_font, Alignment(horizontal="center")),
            (getattr(log, "scope_id", "") or "", mono_font, Alignment(horizontal="center")),
            (getattr(log, "task_id", "") or "", mono_font, Alignment(horizontal="center")),
            (getattr(log, "field", "") or "", data_font, Alignment(horizontal="left")),
            (getattr(log, "old_value", "") or "", mono_font, Alignment(horizontal="left")),
            (getattr(log, "new_value", "") or "", mono_font, Alignment(horizontal="left")),
        ]

        ws.row_dimensions[row_num].height = 20
        cols = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        for col_letter, (val, font, align) in zip(cols, values):
            cell = ws[f"{col_letter}{row_num}"]
            cell.value = val
            cell.font = font
            cell.fill = row_fill
            cell.alignment = align
            cell.border = cell_border

        row_num += 1

    last_row = max(4, row_num - 1)

    # 6. Auto-filter on columns A to I
    ws.auto_filter.ref = f"A4:I{last_row}"

    # 7. Freeze header panes so scrolling keeps headers visible
    ws.freeze_panes = "A5"

    # 8. Auto-adjust column widths
    column_widths = {
        "A": 12,  # Event ID
        "B": 22,  # Timestamp
        "C": 18,  # Operator
        "D": 22,  # Action
        "E": 12,  # Scope ID
        "F": 12,  # Task ID
        "G": 20,  # Field Modified
        "H": 26,  # Prior Value
        "I": 26,  # Committed Value
    }
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    wb.close()
    return buffer.getvalue()


def generate_audit_json(logs: List[Any]) -> bytes:
    """Generate pretty-printed JSON bytes representing the audit trail."""
    items = []
    for log in logs:
        ts_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if getattr(log, "timestamp", None) else None
        items.append({
            "id": getattr(log, "id", None),
            "timestamp": ts_str,
            "user": getattr(log, "user", None),
            "action": getattr(log, "action", None),
            "scope_id": getattr(log, "scope_id", None),
            "task_id": getattr(log, "task_id", None),
            "field": getattr(log, "field", None),
            "old_value": getattr(log, "old_value", None),
            "new_value": getattr(log, "new_value", None),
        })

    payload = {
        "export_timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_records": len(items),
        "audit_logs": items,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
