import os
import json
from google import genai
from google.genai import types

def evaluate_answer_sheet(api_keys, answer_images, question_paper_text, marking_pointers, q_images=None):
    """
    Use Gemini AI to grade the answer sheet.
    """
    if q_images is None:
        q_images = []
        
    prompt = f"""
    You are an expert human teacher grading an exam.
    Question Paper:
    {question_paper_text}
    
    Marking Pointers (Rubric):
    {marking_pointers}
    
    Please grade the attached answer sheet images meticulously step-by-step.
    Provide a detailed mark breakdown for each question. Evaluate every step the student took, assigning partial marks according to the rubric.

    CRITICAL INSTRUCTIONS FOR MISTAKES & MARKS:
    1. Identify mistakes clearly in the feedback.
    2. Add a 'circle' mark to encircle the exact mistake on the image.
    3. Add a 'text' mark near the mistake to write the correct explanation and solution.
    4. For EVERY question attempted by the student, add a 'text' mark next to the question number on the image writing the marks awarded (e.g., "Q1: 2/5 marks").

    Output your response in JSON format.
    The JSON must contain:
    1. 'total_score': integer
    2. 'feedback': string (detailed step-by-step feedback)
    3. 'marks': a list of objects representing where to draw marks on the image.
       Each mark object must have:
       - 'page_index': integer (0-indexed, which image this mark belongs to)
       - 'type': string (one of 'tick', 'cross', 'circle', 'text')
       - 'bbox': [x1, y1, x2, y2] (approximate coordinates where to draw on a 1000x1000 scaled grid, 0,0 is top-left)
       - 'text': string (only if type is 'text', e.g. correct solution/explanation)
    """
    
    import time
    from google.genai import errors
    
    for key_index, current_api_key in enumerate(api_keys):
        print(f"Trying API Key {key_index + 1}/{len(api_keys)}...")
        client = genai.Client(api_key=current_api_key)
        
        print("Uploading images to Gemini...")
        files = []
        for img_path in answer_images:
            f = client.files.upload(file=img_path)
            files.append(f)
            
        for img_path in q_images:
            f = client.files.upload(file=img_path)
            files.append(f)
            
        contents = [prompt] + files
        
        print("Asking Gemini to grade...")
        success = False
        response = None
        base_wait = 10
        attempt = 0
        
        while not success:
            try:
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                success = True
                break
            except errors.ServerError as e:
                if "503" in str(e):
                    wait_time = 10
                    print(f"503 Server Busy. Retrying in {wait_time} seconds... (Attempt {attempt+1})")
                    time.sleep(wait_time)
                    attempt += 1
                else:
                    print(f"ServerError: {e}. Switching to next key...")
                    break # Switch to next API key
            except errors.ClientError as e:
                if "429" in str(e):
                    print(f"429 Too Many Requests on key {key_index+1}. Switching to next key...")
                    break # Switch to next API key
                else:
                    print(f"ClientError: {e}. Switching to next key...")
                    break # Switch to next API key
        
        if success and response:
            try:
                result = json.loads(response.text)
                return result
            except Exception as e:
                print("Error parsing JSON:", e)
                return {"error": str(e), "raw": response.text}
                
    return {"error": "All API keys failed or exhausted due to 429s."}

if __name__ == "__main__":
    print("Grader AI ready. Me wait for API key and images.")
