import fitz  # PyMuPDF
from PIL import Image
import os

def pdf_to_images(pdf_path, output_dir):
    """
    Convert a PDF file to a list of images.
    """
    doc = fitz.open(pdf_path)
    image_paths = []
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=200)
        
        output_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
        pix.save(output_path)
        image_paths.append(output_path)
        
    return image_paths

def draw_marks_on_image(image_path, output_path, marks):
    """
    Draw red marks on the image based on coordinates.
    marks is a list of dicts: {'type': 'tick'/'cross'/'circle'/'text', 'bbox': [x1, y1, x2, y2], 'text': 'optional text'}
    """
    import cv2
    import numpy as np
    
    img = cv2.imread(image_path)
    
    for mark in marks:
        x1, y1, x2, y2 = mark['bbox']
        if mark['type'] == 'circle':
            cv2.ellipse(img, (int((x1+x2)/2), int((y1+y2)/2)), (int((x2-x1)/2), int((y2-y1)/2)), 0, 0, 360, (0, 0, 255), 3)
        elif mark['type'] == 'tick':
            # Simple tick mark
            cv2.line(img, (x1, int((y1+y2)/2)), (int((x1+x2)/2), y2), (0, 0, 255), 3)
            cv2.line(img, (int((x1+x2)/2), y2), (x2, y1), (0, 0, 255), 3)
        elif mark['type'] == 'cross':
            cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.line(img, (x2, y1), (x1, y2), (0, 0, 255), 3)
        elif mark['type'] == 'text':
            cv2.putText(img, mark.get('text', ''), (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
    cv2.imwrite(output_path, img)
    return output_path

if __name__ == "__main__":
    print("PDF processor ready.")
