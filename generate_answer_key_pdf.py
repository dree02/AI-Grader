import sys
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def make_answer_key_pdf(json_path, output_pdf_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    doc = SimpleDocTemplate(output_pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(name="TitleStyle", parent=styles['Heading1'], fontSize=16, spaceAfter=10)
    cell_style = ParagraphStyle(name="CellStyle", parent=styles['Normal'], fontSize=9, leading=11)
    
    elements = []
    
    # Header
    elements.append(Paragraph("<b>Answer Key & Marking Scheme</b>", title_style))
    elements.append(Spacer(1, 20))
    
    # Table Data
    table_data = [["Q No.", "Correct Answer", "Marking Points", "Total Marks"]]
    
    for item in data:
        q = Paragraph(str(item.get("question", "")), cell_style)
        ans = Paragraph(str(item.get("correct_answer", "")), cell_style)
        
        # Join marking points with bullets or newlines
        points = item.get("marking_points", [])
        if isinstance(points, list):
            points_str = "<br/>".join([f"• {p}" for p in points])
        else:
            points_str = str(points)
            
        pts = Paragraph(points_str, cell_style)
        marks = Paragraph(str(item.get("total_marks", "")), cell_style)
        
        table_data.append([q, ans, pts, marks])
        
    # Table Style
    t = Table(table_data, colWidths=[40, 100, 350, 40])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (3,0), (3,-1), 'CENTER'),
        ('ALIGN', (1,0), (2,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
    ]))
    
    elements.append(t)
    doc.build(elements)
    print(f"Answer Key PDF generated successfully at: {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_answer_key_pdf.py <path_to_answer_key.json> <output_pdf.pdf>")
        sys.exit(1)
    make_answer_key_pdf(sys.argv[1], sys.argv[2])
