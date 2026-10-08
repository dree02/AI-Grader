import os
import sys
import json
import glob
import re
from pdf_processor import draw_marks_on_image, images_to_pdf, find_empty_space_1000, pdf_to_images

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_batch2.py <answer_sheets_dir>")
        sys.exit(1)

    answer_sheets_dir = sys.argv[1]
    
    print("Processing PDFs from batch_results.jsonl...")
    
    output_folder = os.path.join(answer_sheets_dir, "graded_answer_sheets")
    os.makedirs(output_folder, exist_ok=True)
    
    pdf_files = sorted(glob.glob(os.path.join(answer_sheets_dir, "*.pdf")))
    pdf_mapping = {f"student_{i}": f for i, f in enumerate(pdf_files)}
    
    with open("batch_results.jsonl", "r") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            req_id = data.get("id")
            if not req_id:
                # Some lines might be job metadata
                continue
            try:
                resp_text = data["response"]["candidates"][0]["content"]["parts"][0]["text"]
                if resp_text.startswith("```json"):
                    resp_text = resp_text[7:-3]
                
                result = json.loads(resp_text)
                pdf_file = pdf_mapping.get(req_id)
                if not pdf_file:
                    print(f"Could not map {req_id} to a PDF file.")
                    continue
                    
                print(f"Processing graded output for: {pdf_file}")
                
                out_dir = pdf_file + "_images"
                if not os.path.exists(out_dir):
                    images = pdf_to_images(pdf_file, out_dir)
                else:
                    images = sorted(glob.glob(os.path.join(out_dir, "page_*.png")))
                    
                if "marks" in result:
                    total_score = result.get("total_score", "?")
                    result["marks"] = [m for m in result["marks"] if not m.get("text", "").startswith("FINAL MARKS")]
                    
                    if images:
                        best_x, best_y = find_empty_space_1000(images[0])
                        result["marks"].append({
                            "page_index": 0,
                            "type": "text",
                            "bbox": [best_x, best_y, best_x + 350, best_y + 80],
                            "text": f"FINAL MARKS: {total_score} / 28"
                        })
                    
                    annotated_images = []
                    for i, img_path in enumerate(images):
                        page_marks = [m for m in result["marks"] if m.get("page_index") == i]
                        graded_img_path = os.path.join(out_dir, f"graded_page_pixelscan_{i}.png")
                        draw_marks_on_image(img_path, graded_img_path, page_marks)
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
