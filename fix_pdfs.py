import os
import glob
import json
from generate_result_pdf import make_result_sheet

def fix_all():
    output_dir = "/Users/dhruvrawat/Desktop/AI-Grader/test_data/triangles/graded_result_sheets"
    json_files = glob.glob(os.path.join(output_dir, "*.json"))
    
    for json_path in json_files:
        student_name = os.path.basename(json_path).replace(".json", "")
        output_pdf_path = os.path.join(output_dir, f"{student_name}_Result_Sheet.pdf")
        
        try:
            with open(json_path, 'r') as f:
                grades = json.load(f)
            
            total_earned = 0.0
            total_possible = 0.0
            
            for item in grades:
                score_str = str(item.get("Score", ""))
                if "/" in score_str:
                    try:
                        earned, possible = score_str.split("/")
                        total_earned += float(earned.strip())
                        total_possible += float(possible.strip())
                    except ValueError:
                        pass
            
            # Format nicely (remove .0 if it's an integer)
            earned_str = f"{int(total_earned)}" if total_earned.is_integer() else f"{total_earned}"
            possible_str = f"{int(total_possible)}" if total_possible.is_integer() else f"{total_possible}"
            
            total_score_str = f"{earned_str}/{possible_str}" if total_possible > 0 else ""
            
            print(f"Regenerating PDF for {student_name} with Total Score: {total_score_str}")
            make_result_sheet(json_path, output_pdf_path, student_name=student_name.replace("_", " "), total_score=total_score_str)
            
            # Now delete the JSON file
            os.remove(json_path)
            print(f"Deleted {json_path}")
            
        except Exception as e:
            print(f"Failed processing {json_path}: {e}")

if __name__ == "__main__":
    fix_all()
