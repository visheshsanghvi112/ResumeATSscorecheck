
# 🧠 Resume Analyzer Tool

This is a Python-based tool that analyzes resumes in `.pdf` and `.docx` formats. It extracts relevant sections, evaluates contact and personal information, checks grammar, and suggests improvements based on resume writing best practices.

---

## 📌 Features

* ✅ Extracts text from PDF and DOCX resumes
* 🔍 Detects contact information (email, phone, GitHub, LinkedIn, portfolio links)
* 🧹 Identifies prohibited personal info (DOB, gender, address, etc.)
* 📑 Splits resumes into standard sections (summary, experience, education, etc.)
* 💡 Analyzes experience bullet points for action verbs, quantification, and structure
* 📝 Checks grammar and spelling using `language_tool_python`
* 📈 Suggests improvements to make your resume more professional and impactful

---

## 🚀 Getting Started

### Prerequisites

Install the required packages:

```bash
pip install python-docx docx2txt pymupdf language-tool-python requests
```

### Optional (for GUI file selection)

If you want to use the `tkinter` file dialog:

```bash
sudo apt-get install python3-tk
```

---

## 🗂️ File Structure

* **`extract_text_from_pdf()`**: Extracts plain text from PDF using `PyMuPDF`
* **`extract_text_from_docx()`**: Extracts plain text from DOCX using `docx2txt`
* **`extract_contact_anywhere()`**: Detects emails, phone numbers, LinkedIn, GitHub, portfolio links, and flags prohibited personal info
* **`split_sections()`**: Organizes text into sections like summary, experience, education, etc.
* **`analyze_experience_bullets()`**: Analyzes action verbs and quantification in bullet points
* **`spelling_and_grammar_check()`**: Returns top 10 spelling/grammar suggestions using LanguageTool
* **`suggest_improvements()`**: Provides resume feedback and suggestions

---

## 🧪 Example Usage

```python
file_path = filedialog.askopenfilename()  # Opens GUI to select a file
if file_path.endswith(".pdf"):
    raw_text = extract_text_from_pdf(file_path)
elif file_path.endswith(".docx"):
    raw_text = extract_text_from_docx(file_path)

cleaned = clean_text(raw_text)
sections = split_sections(cleaned)
contact_info = extract_contact_anywhere(cleaned)
grammar_issues = spelling_and_grammar_check(cleaned)
experience_analysis = analyze_experience_bullets(sections.get("experience", "").split("\n"))
report = {
    "contact_info": contact_info,
    "sections": sections,
    "experience_analysis": experience_analysis,
    "grammar_issues": grammar_issues
}
suggestions = suggest_improvements(report)
```

---

## 🧠 Resume Writing Tips Used

* Start bullets with **strong action verbs**
* **Quantify** achievements and impact (e.g., "Increased efficiency by 30%")
* Include **essential contact info**: professional email, phone, LinkedIn, GitHub
* Avoid **personal info** like photo, DOB, gender
* Include **key sections**: summary, experience, education, skills, certifications

---

## 🛡️ Disclaimer

This tool does not guarantee job placement or resume perfection. It provides **automated analysis and general suggestions** based on best practices. Manual review is still recommended.

---

## 📃 License

This project is licensed under the MIT License. Feel free to modify and distribute with attribution.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

Let me know if you'd like this converted into a `.md` file or further customized for your portfolio or project report!
