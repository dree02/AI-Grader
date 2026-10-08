import os
import glob
import pymupdf

graded_dir = "../test_data/triangles/answer sheets/graded_answer_sheets"
pdfs = glob.glob(os.path.join(graded_dir, "*.pdf"))

print(f"Found {len(pdfs)} PDFs to rotate.")

for pdf_path in pdfs:
    doc = pymupdf.open(pdf_path)
    for page in doc:
        # PyMuPDF sets rotation absolutely. 270 degrees clockwise is 90 degrees counter-clockwise.
        # If it's already 0, 270 makes it 90 CCW.
        page.set_rotation(270)
    
    # We can save it in place by saving to a temp file and renaming
    temp_path = pdf_path + ".temp.pdf"
    doc.save(temp_path)
    doc.close()
    os.replace(temp_path, pdf_path)
    print(f"Rotated {os.path.basename(pdf_path)}")

print("All PDFs rotated successfully!")
