import os
import sys
import json
import itertools
from google import genai
from google.genai import types

def get_api_key_cycle():
    with open('api_keys.txt', 'r') as f:
        keys = [line.strip() for line in f if line.strip()]
    return itertools.cycle(keys)

def grade_paper(answer_sheet_path, answer_key_path):
    print(f"Grading {answer_sheet_path}...")
    api_key_cycle = get_api_key_cycle()
    api_key = next(api_key_cycle)
    client = genai.Client(api_key=api_key)
    
    with open(answer_key_path, 'r') as f:
        answer_key_json = f.read()
    
    print(f"Uploading Student Paper using API Key ending in {api_key[-4:]}...")
    student_file = client.files.upload(file=answer_sheet_path)
    
    prompt = f"""
You are an expert teacher grading a student's answer sheet. Take your time, analyze thoroughly, and evaluate the answers carefully.
Do NOT hallucinate. Be very strict but fair.

Here is the correct Answer Key and Marking Scheme:
{answer_key_json}

Please grade the attached student answer sheet. Compare the student's work step-by-step against the marking scheme.

Return ONLY a JSON array with this exact structure for every question attempted:
[
  {{
    "Question": "Q1",
    "Score": "1/2",
    "Reason": "Awarded 1 mark for correct formula. Deducted 1 mark because final calculation was wrong."
  }}
]
No other text. Just the JSON.
"""
    print("Asking Gemini Flash to grade the paper...")
    
    for attempt in range(8): # Try up to 8 keys
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[student_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            break # Success!
        except Exception as e:
            print(f"Error with key {api_key[-4:]}: {e}")
            api_key = next(api_key_cycle)
            client = genai.Client(api_key=api_key)
            print(f"Retrying with key {api_key[-4:]}...")
            student_file = client.files.upload(file=answer_sheet_path)
    
    output_path = answer_sheet_path + "_graded.json"
    with open(output_path, 'w') as f:
        f.write(response.text)
        
    print(f"DONE! Grades saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python grade_with_key.py <path_to_student_paper.pdf> <path_to_answer_key.json>")
        sys.exit(1)
    grade_paper(sys.argv[1], sys.argv[2])
