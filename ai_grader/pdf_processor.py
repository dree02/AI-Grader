import pymupdf
from PIL import Image
import os
import cv2
import json

def pdf_to_images(pdf_path, output_dir):
    """
    Convert a PDF file to a list of images.
    """
    doc = pymupdf.open(pdf_path)
    image_paths = []
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=200)
        
        output_path = os.path.join(output_dir, f"page_{page_num}.png")
        pix.save(output_path)
        image_paths.append(output_path)
        
    return image_paths

def draw_marks_on_image(image_path, output_path, marks):
    """
    Draw red marks on the image based on coordinates.
    """
    img = cv2.imread(image_path)
    
    for mark in marks:
        x1, y1, x2, y2 = mark['bbox']
        if mark['type'] == 'circle':
            cv2.ellipse(img, (int((x1+x2)/2), int((y1+y2)/2)), (int((x2-x1)/2), int((y2-y1)/2)), 0, 0, 360, (0, 0, 255), 3)
        elif mark['type'] == 'tick':
            cv2.line(img, (x1, int((y1+y2)/2)), (int((x1+x2)/2), y2), (0, 0, 255), 3)
            cv2.line(img, (int((x1+x2)/2), y2), (x2, y1), (0, 0, 255), 3)
        elif mark['type'] == 'cross':
            cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.line(img, (x2, y1), (x1, y2), (0, 0, 255), 3)
        elif mark['type'] == 'text':
            cv2.putText(img, mark.get('text', ''), (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
    cv2.imwrite(output_path, img)
    return output_path

def images_to_pdf(image_paths, output_pdf_path):
    images = [Image.open(img).convert('RGB') for img in image_paths]
    if images:
        images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
    return output_pdf_path

if __name__ == "__main__":
    import sys
    from grader import evaluate_answer_sheet
    
    if len(sys.argv) > 3:
        pdf_file = sys.argv[1]
        question_input = sys.argv[2]
        rules = sys.argv[3]
        
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY not set")
            sys.exit(1)
            
        out_dir = pdf_file + "_images"
        print(f"Processing Answer PDF: {pdf_file}")
        images = pdf_to_images(pdf_file, out_dir)
        
        question_paper = question_input
        q_images = []
        if question_input.lower().endswith('.pdf'):
            print(f"Processing Question PDF: {question_input}")
            q_out_dir = question_input + "_images"
            q_images = pdf_to_images(question_input, q_out_dir)
            question_paper = "Please refer to the uploaded Question Paper images."
        
        print("Calling Gemini...")
        # We need to pass question images to evaluate_answer_sheet. Let's update that next.
        result = evaluate_answer_sheet(api_key, images, question_paper, rules, q_images)
        
        print("Grading Result:", json.dumps(result, indent=2))
        
        if "marks" in result:
            annotated_images = []
            for i, img_path in enumerate(images):
                page_marks = [m for m in result["marks"] if m.get("page_index") == i]
                out_img = os.path.join(out_dir, f"graded_page_{i}.png")
                draw_marks_on_image(img_path, out_img, page_marks)
                annotated_images.append(out_img)
                
            final_pdf = pdf_file + "_graded.pdf"
            images_to_pdf(annotated_images, final_pdf)
            print(f"DONE. Final PDF: {final_pdf}")
        else:
            print("No marks returned. Outputting raw images as PDF.")
            final_pdf = pdf_file + "_graded.pdf"
            images_to_pdf(images, final_pdf)
            print(f"DONE. Final PDF: {final_pdf}")
    else:
        print("Usage: python3 pdf_processor.py <pdf_path> <question> <rules>")
