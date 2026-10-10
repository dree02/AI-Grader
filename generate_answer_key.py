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

def generate_answer_key(question_paper_path):
    print(f"Generating Answer Key for {question_paper_path}...")
    api_key_cycle = get_api_key_cycle()
    
    # We can just read the PDF directly using genai File API if we want, or just upload it
    api_key = next(api_key_cycle)
    client = genai.Client(api_key=api_key)
    
    print(f"Uploading Question Paper using API Key ending in {api_key[-4:]}...")
    qp_file = client.files.upload(file=question_paper_path)
    
    prompt = """
You are an expert teacher. Please read this question paper and generate a comprehensive marking scheme / answer key.
For each question, provide the correct answer and the key points required for full marks.

Return ONLY a JSON array with this exact structure:
[
  {
    "question": "Q1",
    "correct_answer": "The final correct answer",
    "marking_points": ["Point 1 for 1 mark", "Point 2 for 1 mark"],
    "total_marks": 2
  }
]
No other text. Just the JSON.
"""
    print("Asking Gemini Flash to solve the paper...")
    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=[qp_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    
    # Save the output
    output_path = question_paper_path + "_answer_key.json"
    with open(output_path, 'w') as f:
        f.write(response.text)
        
    print(f"DONE! Answer Key saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_answer_key.py <path_to_question_paper.pdf>")
        sys.exit(1)
    generate_answer_key(sys.argv[1])
