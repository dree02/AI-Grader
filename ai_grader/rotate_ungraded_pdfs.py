import os
import glob
import pymupdf

input_dir = "../test_data/triangles/answer sheets"
output_dir = "../test_data/triangles/answer_sheets_rotated"

os.makedirs(output_dir, exist_ok=True)
pdfs = glob.glob(os.path.join(input_dir, "*.pdf"))

print(f"Found {len(pdfs)} PDFs to rotate.")

for pdf_path in pdfs:
    doc = pymupdf.open(pdf_path)
    for page in doc:
        # Rotate 90 degrees counter-clockwise
        current_rot = page.rotation
        page.set_rotation((current_rot - 90) % 360)
    
    filename = os.path.basename(pdf_path)
    output_path = os.path.join(output_dir, filename)
    doc.save(output_path)
    doc.close()
    print(f"Saved rotated PDF to {output_path}")

print("All un-graded PDFs rotated successfully!")
