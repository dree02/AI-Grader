package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	http.HandleFunc("/grade", handleGrade)
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "AI Grader Server is running. Send POST to /grade")
	})

	fmt.Println("Server listening on :8080...")
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func handleGrade(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	// 1. Parse multipart form (10 MB max memory)
	err := r.ParseMultipartForm(10 << 20)
	if err != nil {
		http.Error(w, "Failed to parse form", http.StatusBadRequest)
		return
	}

	// 2. Get the PDF file
	file, handler, err := r.FormFile("pdf")
	if err != nil {
		http.Error(w, "PDF file is required", http.StatusBadRequest)
		return
	}
	defer file.Close()

	// 3. Save PDF to temp directory
	tempDir, err := os.MkdirTemp("", "ai-grader-")
	if err != nil {
		http.Error(w, "Failed to create temp dir", http.StatusInternalServerError)
		return
	}
	// defer os.RemoveAll(tempDir) // Keep for debugging if needed

	pdfPath := filepath.Join(tempDir, handler.Filename)
	dst, err := os.Create(pdfPath)
	if err != nil {
		http.Error(w, "Failed to save PDF", http.StatusInternalServerError)
		return
	}
	defer dst.Close()
	if _, err := io.Copy(dst, file); err != nil {
		http.Error(w, "Failed to copy PDF", http.StatusInternalServerError)
		return
	}

	// 4. Get other form values (question, rules)
	question := r.FormValue("question")
	rules := r.FormValue("rules")

	fmt.Printf("Received request. PDF: %s, Question len: %d, Rules len: %d\n", pdfPath, len(question), len(rules))

	// 5. Call Python script using venv
	pythonPath := filepath.Join("..", "ai_grader", "venv", "bin", "python")
	scriptPath := filepath.Join("..", "ai_grader", "pdf_processor.py")
	cmd := exec.Command(pythonPath, scriptPath, pdfPath, question, rules)
	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Python Error: %s\n", string(output))
		http.Error(w, "Failed to process PDF", http.StatusInternalServerError)
		return
	}

	// For now, just return success
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"status": "success", "message": "PDF saved and processed", "pdf_path": "%s", "python_output": "%s"}`, pdfPath, string(output))
}
