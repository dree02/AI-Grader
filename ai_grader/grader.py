import os
import json
from google import genai
from google.genai import types

def evaluate_answer_sheet(api_key, answer_images, question_paper_text, marking_pointers):
    """
    Use Gemini AI to grade the answer sheet.
    """
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an expert human teacher grading an exam.
    Question Paper:
    {question_paper_text}
    
    Marking Pointers (Rubric):
    {marking_pointers}
    
    Please grade the attached answer sheet images.
    Output your response in JSON format.
    The JSON must contain:
    1. 'total_score': integer
    2. 'feedback': string (overall feedback)
    3. 'marks': a list of objects representing where to draw marks on the image.
       Each mark object must have:
       - 'page_index': integer (0-indexed, which image this mark belongs to)
       - 'type': string (one of 'tick', 'cross', 'circle', 'text')
       - 'bbox': [x1, y1, x2, y2] (approximate coordinates where to draw on a 1000x1000 scaled grid, we will scale back)
       - 'text': string (only if type is 'text', e.g., '+2' or 'wrong formula')
    """
    
    print("Uploading images to Gemini...")
    files = []
    for img_path in answer_images:
        f = client.files.upload(file=img_path)
        files.append(f)
        
    contents = [prompt] + files
    
    print("Asking Gemini to grade...")
    response = client.models.generate_content(
        model='gemini-1.5-pro',
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )
    )
    
    try:
        result = json.loads(response.text)
        return result
    except Exception as e:
        print("Error parsing JSON:", e)
        return {"error": str(e), "raw": response.text}

if __name__ == "__main__":
    print("Grader AI ready. Me wait for API key and images.")
