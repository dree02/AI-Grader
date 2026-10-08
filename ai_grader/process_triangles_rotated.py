import os
import sys
import json
import glob
import re
import cv2
from PIL import Image
from pdf_processor import images_to_pdf

def find_empty_space_1000(img):
    if img is None:
        return (50, 50)
    H, W = img.shape[:2]
    if len(img.shape) == 3:
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        img_gray = img
    target_w_ratio = 0.35
    target_h_ratio = 0.08
    box_w = int(W * target_w_ratio)
    box_h = int(H * target_h_ratio)
    _, binary = cv2.threshold(img_gray, 230, 1, cv2.THRESH_BINARY_INV)
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

def draw_marks_on_rotated_image(img_path, output_path, marks):
    # Load original image
    img = cv2.imread(img_path)
    if img is None:
        return
        
    # Rotate image 90 degrees CCW
    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    
    H, W, _ = img.shape
    
    for mark in marks:
        bbox = mark.get("bbox", [0,0,0,0])
        if len(bbox) == 4:
            x1_old, y1_old, x2_old, y2_old = bbox
            
            # Transform normalized coordinates (0-1000) for 90 CCW rotation
            # new_x = old_y
            # new_y = 1000 - old_x
            new_x1 = y1_old
            new_y1 = 1000 - x2_old
            new_x2 = y2_old
            new_y2 = 1000 - x1_old
            
            x1 = int(new_x1 * W / 1000)
            y1 = int(new_y1 * H / 1000)
            x2 = int(new_x2 * W / 1000)
            y2 = int(new_y2 * H / 1000)
        else:
            continue
            
        mtype = mark.get("type", "")
        text = mark.get("text", "")
        
        if mtype == "circle":
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            axes = (abs(x2 - x1) // 2, abs(y2 - y1) // 2)
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
            # For text, we draw from the top-left of the transformed box
            cv2.putText(img, text, (x1, y1 + 30), font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA)
            
    cv2.imwrite(output_path, img)

def main():
    answer_sheets_dir = "../test_data/triangles/answer sheets"
    
    ordered_files = [
        "Adobe Scan Oct 3, 2026 (4).pdf", "Adobe Scan Oct 3, 2026 (17).pdf", "Adobe Scan Oct 3, 2026 (21).pdf",
        "Adobe Scan Oct 3, 2026 (8).pdf", "Adobe Scan Oct 3, 2026 (9).pdf", "Adobe Scan Oct 3, 2026 (20).pdf",
        "Adobe Scan Oct 3, 2026 (16).pdf", "Adobe Scan Oct 3, 2026 (5).pdf", "Adobe Scan Oct 3, 2026 (27).pdf",
        "Adobe Scan Oct 3, 2026 (2).pdf", "Adobe Scan Oct 3, 2026 (11).pdf", "Adobe Scan Oct 3, 2026 (10).pdf",
        "Adobe Scan Oct 3, 2026 (3).pdf", "Adobe Scan Oct 3, 2026.pdf", "Adobe Scan Oct 3, 2026 (26).pdf",
        "Adobe Scan Oct 3, 2026 (25).pdf", "Adobe Scan Oct 3, 2026 (13).pdf", "Adobe Scan Oct 3, 2026 (29).pdf",
        "Adobe Scan Oct 3, 2026 (28).pdf", "Adobe Scan Oct 3, 2026 (1).pdf", "Adobe Scan Oct 3, 2026 (12).pdf",
        "Adobe Scan Oct 3, 2026 (24).pdf", "Adobe Scan Oct 3, 2026 (15).pdf", "Adobe Scan Oct 3, 2026 (6).pdf",
        "Adobe Scan Oct 3, 2026 (19).pdf", "Adobe Scan Oct 3, 2026 (23).pdf", "Adobe Scan Oct 3, 2026 (22).pdf",
        "Adobe Scan Oct 3, 2026 (18).pdf", "Adobe Scan Oct 3, 2026 (7).pdf", "Adobe Scan Oct 3, 2026 (14).pdf"
    ]
    
    pdf_mapping = {}
    for i, fname in enumerate(ordered_files):
        pdf_mapping[f"student_{i}"] = os.path.join(answer_sheets_dir, fname)

    output_folder = os.path.join(answer_sheets_dir, "graded_answer_sheets_rot_text")
    os.makedirs(output_folder, exist_ok=True)
    
    with open("triangles_results.jsonl", "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            req_id = data.get("id")
            if not req_id:
                continue
            try:
                resp_text = data["response"]["candidates"][0]["content"]["parts"][0]["text"]
                if resp_text.startswith("```json"):
                    resp_text = resp_text[7:-3]
                
                result = json.loads(resp_text)
                pdf_file = pdf_mapping.get(req_id)
                if not pdf_file:
                    continue
                    
                print(f"Processing properly rotated output for: {pdf_file}")
                
                out_dir = pdf_file + "_images"
                images = sorted(glob.glob(os.path.join(out_dir, "page_*.png")))
                    
                if "marks" in result:
                    total_score = result.get("total_score", "?")
                    result["marks"] = [m for m in result["marks"] if not m.get("text", "").startswith("FINAL MARKS")]
                    
                    if images:
                        # Find empty space on the ROTATED image
                        first_img = cv2.imread(images[0])
                        first_img_rot = cv2.rotate(first_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                        best_x, best_y = find_empty_space_1000(first_img_rot)
                        
                        # Note: We append this to the raw result list. But our draw_marks function assumes
                        # ALL marks are in the original unrotated coordinates! 
                        # So we must INVERSE transform these normalized coordinates back to the original sideways system
                        # so that when draw_marks transforms them, they end up at best_x, best_y!
                        # Inverse of 90 CCW:
                        # old_x = 1000 - new_y
                        # old_y = new_x
                        old_x1 = 1000 - (best_y + 80)
                        old_y1 = best_x
                        old_x2 = 1000 - best_y
                        old_y2 = best_x + 350
                        
                        result["marks"].append({
                            "page_index": 0,
                            "type": "text",
                            "bbox": [old_x1, old_y1, old_x2, old_y2],
                            "text": f"FINAL MARKS: {total_score} / 28"
                        })
                    
                    annotated_images = []
                    for i, img_path in enumerate(images):
                        page_marks = [m for m in result["marks"] if m.get("page_index") == i]
                        graded_img_path = os.path.join(out_dir, f"graded_page_rot_{i}.png")
                        draw_marks_on_rotated_image(img_path, graded_img_path, page_marks)
                        annotated_images.append(graded_img_path)
                        
                    student_name = result.get("student_name", "Unknown_Student")
                    safe_name = re.sub(r'[^a-zA-Z0-9_\- ]', '', student_name).strip()
                    if not safe_name:
                        safe_name = "Unknown_Student"
                        
                    final_pdf = os.path.join(output_folder, f"{safe_name}_graded.pdf")
                    images_to_pdf(annotated_images, final_pdf)
                    print(f"DONE! Saved to {final_pdf}")
                    
            except Exception as e:
                print(f"Error processing {req_id}: {e}")

if __name__ == "__main__":
    main()
