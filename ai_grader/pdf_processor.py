import pymupdf
from PIL import Image
import os
import cv2
import json

from google import genai
import time

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
    h, w = img.shape[:2]
    
    for mark in marks:
        x1_norm, y1_norm, x2_norm, y2_norm = mark['bbox']
        # Scale from 1000x1000 grid to actual image size
        x1 = int(x1_norm * w / 1000.0)
        y1 = int(y1_norm * h / 1000.0)
        x2 = int(x2_norm * w / 1000.0)
        y2 = int(y2_norm * h / 1000.0)
        
        if mark['type'] == 'circle':
            # Add padding so circle doesn't overlap text exactly
            cv2.ellipse(img, (int((x1+x2)/2), int((y1+y2)/2)), (int((x2-x1)/2)+10, int((y2-y1)/2)+10), 0, 0, 360, (0, 0, 255), 3)
        elif mark['type'] == 'tick':
            cx, cy = int((x1+x2)/2), int((y1+y2)/2)
            cv2.line(img, (cx-30, cy), (cx, cy+30), (0, 0, 255), 5)
            cv2.line(img, (cx, cy+30), (cx+40, cy-40), (0, 0, 255), 5)
        elif mark['type'] == 'cross':
            cx, cy = int((x1+x2)/2), int((y1+y2)/2)
            cv2.line(img, (cx-30, cy-30), (cx+30, cy+30), (0, 0, 255), 5)
            cv2.line(img, (cx+30, cy-30), (cx-30, cy+30), (0, 0, 255), 5)
        elif mark['type'] == 'text':
            text = mark.get('text', '')
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            thickness = 2
            
            if x1 < w / 2:
                max_width = max(int(w / 2) - x1 - 10, 200)
            else:
                max_width = max(w - x1 - 10, 200)
                
            words = text.split()
            lines = []
            curr_line = []
            for word in words:
                curr_line.append(word)
                text_size = cv2.getTextSize(" ".join(curr_line), font, font_scale, thickness)[0]
                if text_size[0] > max_width and len(curr_line) > 1:
                    curr_line.pop()
                    lines.append(" ".join(curr_line))
                    curr_line = [word]
            if curr_line:
                lines.append(" ".join(curr_line))
            
            y_offset = y2 + 30
            total_text_height = len(lines) * 35
            if y_offset + total_text_height > h:
                y_offset = max(30, y1 - total_text_height - 10)
                
            for line in lines:
                cv2.putText(img, line, (x1, y_offset), font, font_scale, (0, 0, 255), thickness)
                y_offset += 35
            
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
        
        api_keys_str = os.environ.get("GEMINI_API_KEYS")
        if not api_keys_str:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print("Error: GEMINI_API_KEYS or GEMINI_API_KEY not set")
                sys.exit(1)
            api_keys = [api_key]
        else:
            api_keys = [k.strip() for k in api_keys_str.split(',')]
            
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
        result = evaluate_answer_sheet(api_keys, images, question_paper, rules, q_images)
        
        print("Grading Result:", json.dumps(result, indent=2))
        
        if "marks" in result:
            total_score = result.get("total_score", "?")
            result["marks"].append({
                "page_index": 0,
                "type": "text",
                "bbox": [50, 50, 300, 100],
                "text": f"FINAL MARKS: {total_score} / 28"
            })
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
