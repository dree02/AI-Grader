import sys
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def make_result_sheet(graded_json_path, output_pdf_path, student_name="Student", total_score=""):
    with open(graded_json_path, 'r') as f:
        data = json.load(f)
        
    doc = SimpleDocTemplate(output_pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(name="TitleStyle", parent=styles['Heading1'], fontSize=16, spaceAfter=10)
    info_style = ParagraphStyle(name="InfoStyle", parent=styles['Normal'], fontSize=10, spaceAfter=2)
    cell_style = ParagraphStyle(name="CellStyle", parent=styles['Normal'], fontSize=9, leading=11)
    
    elements = []
    
    # Header
    elements.append(Paragraph("<b>Result Sheet</b>", title_style))
    elements.append(Paragraph(f"Assignment: Standard Test", info_style))
    elements.append(Paragraph(f"Student: {student_name}", info_style))
    elements.append(Paragraph(f"Total Score: {total_score}", info_style))
    elements.append(Spacer(1, 20))
    
    # Table Data
    table_data = [["Question", "Score", "Reason"]]
    
    for item in data:
        q = Paragraph(str(item.get("Question", "")), cell_style)
        s = Paragraph(str(item.get("Score", "")), cell_style)
        r = Paragraph(str(item.get("Reason", "")), cell_style)
        table_data.append([q, s, r])
        
    # Table Style
    t = Table(table_data, colWidths=[60, 50, 420])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('ALIGN', (2,0), (2,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
    ]))
    
    elements.append(t)
    doc.build(elements)
    print(f"Result Sheet PDF generated successfully at: {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_result_pdf.py <path_to_graded.json> <output_pdf.pdf>")
        sys.exit(1)
    make_result_sheet(sys.argv[1], sys.argv[2], student_name=os.path.basename(sys.argv[1]).replace(".pdf_graded.json", ""))
