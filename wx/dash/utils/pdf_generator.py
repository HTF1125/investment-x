"""
PDF generation utilities for market reports
"""
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


def create_pdf_report(universe_data, frequency="ME"):
    """Create a PDF report with all tables fitting on one horizontal A4 page"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.3*inch,
        leftMargin=0.3*inch,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch
    )

    elements = []
    styles = getSampleStyleSheet()

    # Universe icons
    universe_icons = {
        "Major Indices": "🌍",
        "Sectors": "🏢",
        "Themes": "🚀",
        "Global Markets": "🗺️",
        "Commodities": "💰",
    }

    # Title - smaller and more compact
    title_style = styles['Title']
    title_style.fontSize = 14
    title_style.textColor = colors.HexColor('#667eea')
    title = Paragraph("Global Market Returns", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.1*inch))

    # Frequency info - smaller
    freq_text = {
        "B": "Daily", "W-Fri": "Weekly", "ME": "Monthly", "YE": "Yearly"
    }.get(frequency, frequency)

    freq_para = Paragraph(f"Period: {freq_text}", styles['Normal'])
    freq_para.style.fontSize = 10
    elements.append(freq_para)
    elements.append(Spacer(1, 0.05*inch))

    # Create one consolidated table with all universe data
    all_table_data = []

    for universe_name, data in universe_data.items():
        if not data or len(data) == 0:
            continue

        # Use all data without limiting rows
        limited_data = data
        columns = list(limited_data[0].keys())

        # Add universe section header
        icon = universe_icons.get(universe_name, "")
        all_table_data.append([f"{icon} {universe_name}"] + [""] * (len(columns) - 1))

        # Add data rows
        for row in limited_data:
            all_table_data.append([str(row.get(col, "")) for col in columns])

        # Add separator row
        all_table_data.append([""] * len(columns))

    # Remove last empty separator row
    if all_table_data and all(cell == "" for cell in all_table_data[-1]):
        all_table_data.pop()

    if not all_table_data:
        elements.append(Paragraph("No data available", styles['Normal']))
    else:
        # Create the consolidated table with proper column widths
        columns = list(universe_data[next(iter(universe_data))][0].keys())
        col_widths = [1.2*inch] + [0.5*inch] * (len(columns) - 1)

        consolidated_table = Table(all_table_data, colWidths=col_widths, repeatRows=0)

        # Style the consolidated table
        table_style = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]

        # Add styling for each universe section
        current_row = 0
        for universe_name, data in universe_data.items():
            if not data or len(data) == 0:
                continue

            limited_data = data

            # Style universe header
            table_style.extend([
                ('BACKGROUND', (0, current_row), (-1, current_row), colors.HexColor('#667eea')),
                ('TEXTCOLOR', (0, current_row), (-1, current_row), colors.white),
                ('FONTNAME', (0, current_row), (-1, current_row), 'Helvetica-Bold'),
                ('FONTSIZE', (0, current_row), (-1, current_row), 9),
                ('SPAN', (0, current_row), (-1, current_row)),
            ])
            current_row += 1

            # Style data rows with conditional formatting
            for i, row in enumerate(limited_data):
                # Asset column
                table_style.extend([
                    ('ALIGN', (0, current_row), (0, current_row), 'LEFT'),
                    ('FONTNAME', (0, current_row), (0, current_row), 'Helvetica-Bold'),
                ])

                # Performance columns
                columns = list(row.keys())
                for col_idx, col_name in enumerate(columns):
                    if col_name != "Asset":
                        try:
                            value = float(row[col_name])
                            if value > 3:
                                table_style.extend([
                                    ('BACKGROUND', (col_idx, current_row), (col_idx, current_row), colors.HexColor('#10b981')),
                                    ('TEXTCOLOR', (col_idx, current_row), (col_idx, current_row), colors.white)
                                ])
                            elif value > 0:
                                table_style.extend([
                                    ('BACKGROUND', (col_idx, current_row), (col_idx, current_row), colors.HexColor('#d1fae5')),
                                    ('TEXTCOLOR', (col_idx, current_row), (col_idx, current_row), colors.HexColor('#065f46'))
                                ])
                            elif value < -3:
                                table_style.extend([
                                    ('BACKGROUND', (col_idx, current_row), (col_idx, current_row), colors.HexColor('#ef4444')),
                                    ('TEXTCOLOR', (col_idx, current_row), (col_idx, current_row), colors.white)
                                ])
                            elif value < 0:
                                table_style.extend([
                                    ('BACKGROUND', (col_idx, current_row), (col_idx, current_row), colors.HexColor('#fecaca')),
                                    ('TEXTCOLOR', (col_idx, current_row), (col_idx, current_row), colors.HexColor('#7f1d1d'))
                                ])
                        except (ValueError, TypeError):
                            pass

                current_row += 1

            # Skip separator row
            current_row += 1

        consolidated_table.setStyle(TableStyle(table_style))
        elements.append(consolidated_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer