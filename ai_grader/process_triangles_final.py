import os
import sys
import json
import glob
import re
from google import genai
from pdf_processor import images_to_pdf, find_empty_space_1000, pdf_to_images
import cv2
import traceback

def fix_json(s):
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    return s

def draw_marks_local(img_path, output_path, marks):
    img = cv2.imread(str(img_path))
    if img is None:
        return
    H, W = img.shape[:2]
    for mark in marks:
        bbox = mark.get("bbox", [0,0,0,0])
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            x1 = int(x1 * W / 1000)
            y1 = int(y1 * H / 1000)
            x2 = int(x2 * W / 1000)
            y2 = int(y2 * H / 1000)
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
            cv2.putText(img, text, (x1, y1 + 30), font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA)
    cv2.imwrite(output_path, img)

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    answer_sheets_dir = "../test_data/triangles/answer_sheets_rotated"
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

    output_folder = os.path.join(answer_sheets_dir, "graded_answer_sheets_final")
    os.makedirs(output_folder, exist_ok=True)
    
    with open("triangles_results_final.jsonl", "r") as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            req_id = data.get("id")
            if not req_id: continue
            
            # Skip ones already generated successfully (optimization)
            # Actually, let's just regenerate them to be safe
            
            try:
                resp_text = data["response"]["candidates"][0]["content"]["parts"][0]["text"]
                if resp_text.startswith("```json"): resp_text = resp_text[7:-3]
                resp_text = fix_json(resp_text)
                try:
                    result = json.loads(resp_text)
                except:
                    # Find first `{` and last `}`
                    start = resp_text.find('{')
                    end = resp_text.rfind('}')
                    if start != -1 and end != -1:
                        try:
                            result = json.loads(resp_text[start:end+1])
                        except:
                            print(f"Failed to parse JSON for {req_id}. Skipping.")
                            continue
                    else:
                        continue
                        
                pdf_file = pdf_mapping.get(req_id)
                if not pdf_file: continue
                print(f"Processing final output for: {pdf_file}")
                out_dir = pdf_file + "_images"
                if not os.path.exists(out_dir):
                    images = pdf_to_images(pdf_file, out_dir)
                else:
                    images = sorted(glob.glob(os.path.join(out_dir, "page_*.png")))
                if "marks" in result:
                    total_score = result.get("total_score", "?")
                    result["marks"] = [m for m in result["marks"] if not str(m.get("text", "")).startswith("FINAL MARKS")]
                    if images:
                        best_x, best_y = find_empty_space_1000(str(images[0]))
                        result["marks"].append({
                            "page_index": 0,
                            "type": "text",
                            "bbox": [best_x, best_y, best_x + 350, best_y + 80],
                            "text": f"FINAL MARKS: {total_score} / 28"
                        })
                    annotated_images = []
                    for i, img_path in enumerate(images):
                        page_marks = [m for m in result["marks"] if m.get("page_index") == i]
                        graded_img_path = os.path.join(out_dir, f"graded_page_final_{i}.png")
                        draw_marks_local(img_path, graded_img_path, page_marks)
                        annotated_images.append(graded_img_path)
                    student_name = result.get("student_name", "Unknown_Student")
                    safe_name = re.sub(r'[^a-zA-Z0-9_\- ]', '', student_name).strip()
                    if not safe_name: safe_name = "Unknown_Student"
                    final_pdf = os.path.join(output_folder, f"{safe_name}_graded.pdf")
                    images_to_pdf(annotated_images, final_pdf)
                    print(f"DONE! Saved to {final_pdf}")
            except Exception as e:
                print(f"Error processing {req_id}: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    main()
