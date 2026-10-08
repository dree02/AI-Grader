import cv2
import numpy as np
import pymupdf
from PIL import Image
import os
import json
import base64
from openai import OpenAI
import time

def pdf_to_images(pdf_path, output_dir, dpi=150):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    doc = pymupdf.open(pdf_path)
    image_paths = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(dpi/72, dpi/72))
        img_path = os.path.join(output_dir, f"page_{i}.png")
        pix.save(img_path)
        image_paths.append(img_path)
    return image_paths

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def find_empty_space_1000(img_path):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return (50, 50)
    H, W = img.shape
    target_w_ratio = 0.35
    target_h_ratio = 0.08
    box_w = int(W * target_w_ratio)
    box_h = int(H * target_h_ratio)
    _, binary = cv2.threshold(img, 230, 1, cv2.THRESH_BINARY_INV)
    integral = cv2.integral(binary)
    best_x, best_y = 50, 50
    min_ink = float('inf')
    step = 20
    for y in range(0, int(H * 0.12) - box_h, step):
        for x in range(int(W * 0.05), W - box_w, step):
            ink = integral[y+box_h, x+box_w] - integral[y, x+box_w] - integral[y+box_h, x] + integral[y, x]
            if ink < min_ink:
                min_ink = ink
                best_x, best_y = x, y
    return int(best_x * 1000 / W), int(best_y * 1000 / H)

def draw_marks_on_image(img_path, output_path, marks):
    img = cv2.imread(img_path)
    if img is None:
        return
    H, W, _ = img.shape
    
    for mark in marks:
        # Qwen bbox: [ymin, xmin, ymax, xmax] normalized 0-1000
        bbox = mark.get("bbox", [0,0,0,0])
        if len(bbox) == 4:
            ymin, xmin, ymax, xmax = bbox
            x1 = int(xmin * W / 1000)
            y1 = int(ymin * H / 1000)
            x2 = int(xmax * W / 1000)
            y2 = int(ymax * H / 1000)
        else:
            continue
            
        mtype = mark.get("type", "")
        text = mark.get("text", "")
        
        if mtype == "circle":
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            axes = ((x2 - x1) // 2, (y2 - y1) // 2)
            cv2.ellipse(img, center, axes, 0, 0, 360, (0, 0, 255), 3)
        elif mtype == "cross":
            cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 4)
            cv2.line(img, (x2, y1), (x1, y2), (0, 0, 255), 4)
        elif mtype == "tick":
            mid_x = x1 + (x2 - x1) // 3
            mid_y = y2
            cv2.line(img, (x1, y1 + (y2 - y1) // 2), (mid_x, mid_y), (0, 0, 255), 4)
            cv2.line(img, (mid_x, mid_y), (x2, y1), (0, 0, 255), 4)
        elif mtype == "text":
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            thickness = 2
            cv2.putText(img, text, (x1, y1 + 30), font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA)
            
    cv2.imwrite(output_path, img)

def images_to_pdf(image_paths, output_pdf_path):
    if not image_paths:
        return
    images = [Image.open(p).convert('RGB') for p in image_paths]
    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])

def evaluate_answer_sheet(api_key, base_url, model_name, answer_sheet_images, question_paper_images, rules):
    client = OpenAI(base_url=base_url, api_key=api_key)
    
    prompt = f"""You are an expert examiner grading a student's answer sheet.
Attached are the images of the student's answer sheet and the Question Paper.
Here are the grading rules and rubric:
{rules}

Please grade the attached answer sheet images meticulously step-by-step.
Provide a detailed mark breakdown for each question. Evaluate every step the student took, assigning partial marks according to the rubric.

CRITICAL INSTRUCTIONS FOR MISTAKES & MARKS:
1. CIRCLES: Add a 'circle' mark to encircle the exact mistake. BE EXTREMELY PRECISE with your bounding boxes (bbox). Circle the actual handwritten mistake, do NOT circle empty space.
2. MISSING WORK: If a step or answer is incomplete/missing, DO NOT draw a circle in empty space. For missing work, just place a 'text' mark explaining what is missing.
3. TICKS & CROSSES: For 'tick' and 'cross' marks, make the bounding box small and tight (e.g., width and height of 30-40 units on the 1000x1000 scale).
4. QUESTION NUMBERS: For EVERY question attempted, add a 'text' mark writing the marks awarded (e.g., "Q1: 2/5 marks"). Place this text strictly BELOW the handwritten question number.
5. SHORT TEXT: Keep 'text' explanations VERY SHORT (maximum 5-7 words per text mark). Break long explanations into multiple stacked text objects.
6. WHITESPACE: Always place 'text' marks in empty white space so they do not overlap handwriting.

IMPORTANT QWEN FORMATTING:
Qwen expects bounding boxes strictly in the format: [ymin, xmin, ymax, xmax].
All coordinates must be on a 0-1000 scale, where (0,0) is top-left and (1000, 1000) is bottom-right.

Output your response strictly in JSON format matching this structure:
{{
  "student_name": "Extract full name or Unknown_Student",
  "total_score": 100,
  "feedback": "...",
  "coordinate_reasoning": "...",
  "marks": [
    {{
      "page_index": 0,
      "type": "tick",
      "bbox": [ymin, xmin, ymax, xmax],
      "text": "optional text"
    }}
  ]
}}"""

    contents = [{"type": "text", "text": prompt}]
    
    # Add question paper images
    for img in question_paper_images:
        b64 = encode_image(img)
        contents.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
        
    # Add answer sheet images
    for img in answer_sheet_images:
        b64 = encode_image(img)
        contents.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})

    print("Sending request to Qwen API... (this may take a minute)")
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": contents}],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    try:
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        print("Failed to parse JSON from Qwen:", e)
        print("Raw Output:", response.choices[0].message.content)
        return {"error": str(e), "marks": []}

def grade_answer_sheets(pdf_dir, question_pdf, rules_text, api_key, base_url, model_name):
    import glob
    q_out_dir = question_pdf + "_images"
    q_images = pdf_to_images(question_pdf, q_out_dir)

    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    if not pdf_files:
        print("No PDFs found in directory.")
        return

    for pdf_file in pdf_files:
        print(f"\nProcessing {pdf_file}...")
        out_dir = pdf_file + "_qwen_images"
        images = pdf_to_images(pdf_file, out_dir)
        
        result = evaluate_answer_sheet(api_key, base_url, model_name, images, q_images, rules_text)
        print("Qwen Result received!")
        
        if "marks" in result:
            total_score = result.get("total_score", "?")
            if images:
                best_x, best_y = find_empty_space_1000(images[0])
                # Qwen uses [ymin, xmin, ymax, xmax]
                result["marks"].append({
                    "page_index": 0,
                    "type": "text",
                    "bbox": [best_y, best_x, best_y + 80, best_x + 350],
                    "text": f"FINAL MARKS: {total_score} / 28"
                })
                
            annotated_images = []
            for i, img_path in enumerate(images):
                page_marks = [m for m in result["marks"] if m.get("page_index") == i]
                out_img = os.path.join(out_dir, f"graded_page_{i}.png")
                draw_marks_on_image(img_path, out_img, page_marks)
                annotated_images.append(out_img)
                
            student_name = result.get("student_name", "Unknown_Student")
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_\- ]', '', student_name).strip()
            final_pdf = os.path.join(pdf_dir, f"{safe_name}_graded_qwen.pdf")
            images_to_pdf(annotated_images, final_pdf)
            print(f"DONE! Saved to {final_pdf}")
