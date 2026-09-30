import os
import json
from google import genai
from google.genai import types

def evaluate_answer_sheet(api_key, answer_images, question_paper_text, marking_pointers, q_images=None):
    """
    Use Gemini AI to grade the answer sheet.
    """
    if q_images is None:
        q_images = []
        
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
        
    for img_path in q_images:
        f = client.files.upload(file=img_path)
        files.append(f)
        
    contents = [prompt] + files
    
    import time
    from google.genai import errors
    print("Asking Gemini to grade...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            break
        except errors.ServerError as e:
            if "503" in str(e) and attempt < max_retries - 1:
                print(f"503 Server Busy. Retrying in 10 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(10)
            else:
                raise e
    
    try:
        result = json.loads(response.text)
        return result
    except Exception as e:
        print("Error parsing JSON:", e)
        return {"error": str(e), "raw": response.text}

if __name__ == "__main__":
    print("Grader AI ready. Me wait for API key and images.")
