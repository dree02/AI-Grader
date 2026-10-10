import os
import time
import sys
import json
import itertools
from google import genai
from google.genai import types

def get_api_key_cycle():
    with open('api_keys.txt', 'r') as f:
        keys = [line.strip() for line in f if line.strip()]
    return itertools.cycle(keys)

def grade_single_paper_with_retry(pdf_path, answer_key_json, api_key_cycle, output_dir):
    for attempt in range(10):
        try:
            api_key = next(api_key_cycle)
            client = genai.Client(api_key=api_key)
            print(f"[{attempt+1}/10] Uploading {os.path.basename(pdf_path)} using key ending in {api_key[-4:]}...")
            student_file = client.files.upload(file=pdf_path)
            
            prompt = f"""
You are an expert teacher grading a student's answer sheet. Take your time, analyze thoroughly.

Here is the correct Answer Key and Marking Scheme:
{answer_key_json}

First, extract the student's name from the top of the first page.
Then, grade the attached student answer sheet against the marking scheme.

Return ONLY a JSON object with this exact structure:
{{
  "student_name": "Extracted Name",
  "grades": [
    {{
      "Question": "Q1",
      "Score": "1/2",
      "Reason": "Awarded 1 mark for correct formula. Deducted 1 mark because final calculation was wrong."
    }}
  ]
}}
No other text. Just the JSON.
"""
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[student_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            result = json.loads(response.text)
            student_name = result.get("student_name", "Unknown_Student").replace("/", "_").replace(" ", "_")
            grades = result.get("grades", [])
            
            # Save JSON
            json_path = os.path.join(output_dir, f"{student_name}.json")
            with open(json_path, 'w') as f:
                json.dump(grades, f, indent=2)
                
            print(f"DONE grading for {student_name}!")
            return json_path, student_name
            
        except Exception as e:
            print(f"Failed attempt {attempt+1} for {os.path.basename(pdf_path)}: {e}")
            print("Waiting 10 seconds before retrying with next key...")
            time.sleep(10)
            
    print(f"Completely failed to grade {pdf_path} after 10 attempts.")
    return None, None

def main():
    missing_pdfs = [
        "/Users/dhruvrawat/Desktop/AI-Grader/test_data/triangles/answer sheets/Adobe Scan Oct 3, 2026 (5).pdf",
        "/Users/dhruvrawat/Desktop/AI-Grader/test_data/triangles/answer sheets/Adobe Scan Oct 3, 2026 (2).pdf"
    ]
    answer_key_path = "/Users/dhruvrawat/Desktop/AI-Grader/test_data/triangles/2026-27 X Triangles Test.pdf_answer_key.json"
    output_dir = "/Users/dhruvrawat/Desktop/AI-Grader/test_data/triangles/graded_result_sheets"
    
    with open(answer_key_path, 'r') as f:
        answer_key_json = f.read()
        
    api_key_cycle = get_api_key_cycle()
    
    from generate_result_pdf import make_result_sheet
    
    for pdf_path in missing_pdfs:
        json_path, student_name = grade_single_paper_with_retry(pdf_path, answer_key_json, api_key_cycle, output_dir)
        if json_path and student_name:
            output_pdf_path = os.path.join(output_dir, f"{student_name}_Result_Sheet.pdf")
            try:
                make_result_sheet(json_path, output_pdf_path, student_name=student_name.replace("_", " "))
            except Exception as e:
                print(f"Failed to generate PDF for {student_name}: {e}")

if __name__ == "__main__":
    main()
