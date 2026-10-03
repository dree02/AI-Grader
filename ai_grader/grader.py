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
    2. CIRCLES: Add a 'circle' mark to encircle the exact mistake. BE EXTREMELY PRECISE with your bounding boxes (bbox). Circle the actual handwritten mistake, do NOT circle empty space. Do not make circles huge.
    3. MISSING WORK: If a step or answer is incomplete/missing, DO NOT draw a circle in empty space. Only use circles for written errors. For missing work, just place a 'text' mark explaining what is missing.
    4. TICKS & CROSSES: For 'tick' and 'cross' marks, make the bounding box small and tight (e.g., width and height of 30-40 units on the 1000x1000 scale). Place them exactly at the end of the specific math line.
    5. QUESTION NUMBERS: For EVERY question attempted, add a 'text' mark exactly NEXT TO the handwritten question number on the left margin writing the marks awarded (e.g., "Q1: 2/5 marks").
    6. SHORT TEXT: Keep 'text' explanations VERY SHORT (maximum 5-7 words per text mark). If you need to write a longer explanation, break it into multiple separate 'text' objects stacked vertically (increase the Y-coordinate by 30 for each new line) to create a neat paragraph.
    7. WHITESPACE: Always place 'text' marks in empty white space so they do not overlap the student's handwriting.
    8. FINAL SCORE: Add one 'text' mark on the first page (page_index: 0) containing the total score (e.g., "FINAL MARKS: 23 / 28"). Find a large empty white space at the top of the page (top-left or top-right) so it does NOT overlap any printed logos or student names.

    Output your response in JSON format.
    The JSON must contain:
    1. 'student_name': string (Extract the full name, including surname, written by the student on the first page. If no name is found, use "Unknown_Student").
    2. 'total_score': integer
    3. 'feedback': string (detailed step-by-step feedback)
    4. 'coordinate_reasoning': string (THINK step-by-step about exactly where each question number and mistake is physically located on the page BEFORE generating the marks. Explain the visual layout and why you chose specific coordinates).
    5. 'marks': a list of objects representing where to draw marks on the image.
       Each mark object must have:
       - 'page_index': integer (0-indexed, which image this mark belongs to)
       - 'type': string (one of 'tick', 'cross', 'circle', 'text')
       - 'bbox': [x1, y1, x2, y2] (approximate coordinates where to draw on a 1000x1000 scaled grid, 0,0 is top-left)
       - 'text': string (only if type is 'text', e.g. correct solution/explanation)
    """
    
    import time
    from google.genai import errors
    
    while True:
        for key_index, current_api_key in enumerate(api_keys):
            print(f"Trying API Key {key_index + 1}/{len(api_keys)}...")
            client = genai.Client(api_key=current_api_key)
            
            print("Uploading images to Gemini...")
            try:
                files = []
                for img_path in answer_images:
                    f = client.files.upload(file=img_path)
                    files.append(f)
                    
                for img_path in q_images:
                    f = client.files.upload(file=img_path)
                    files.append(f)
            except Exception as e:
                print(f"Upload failed: {e}. Switching key...")
                continue
                
            contents = [prompt] + files
            
            print("Asking Gemini to grade...")
            success = False
            response = None
            attempt = 0
            
            while not success:
                try:
                    response = client.models.generate_content(
                        model='gemini-3.1-pro-preview',
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
                        break
                except errors.ClientError as e:
                    if "429" in str(e):
                        print(f"429 Too Many Requests on key {key_index+1}. Switching to next key...")
                        break
                    else:
                        print(f"ClientError: {e}. Switching to next key...")
                        break
            
            if success and response:
                try:
                    result = json.loads(response.text)
                    return result
                except Exception as e:
                    print("Error parsing JSON:", e)
                    return {"error": str(e), "raw": response.text}
                    
        print("All API keys exhausted! Sleeping for 60 seconds and restarting the cycle to use Pro model...")
        time.sleep(60)

if __name__ == "__main__":
    print("Grader AI ready. Me wait for API key and images.")
