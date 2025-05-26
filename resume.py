import re
import os
import tkinter as tk
from tkinter import filedialog
import requests
import language_tool_python
import docx2txt
import fitz  # PyMuPDF

lang_tool = language_tool_python.LanguageTool('en-US')

CONTACT_PATTERNS = [
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email"),
    (r"\+?\d[\d \-]{8,}", "phone"),
    (r"(linkedin\.com/[^\s,;|]+|Linkedin\s*:\s*[a-zA-Z0-9._-]+)", "linkedin"),
    (r"(github\.com/[^\s,;|]+|GitHub\s*:\s*[a-zA-Z0-9._-]+)", "github"),
    (r"(www\.[^\s,;|]+|https?://[^\s,;|]+)", "url"),
    (r"portfolio\s*:\s*([a-zA-Z0-9\.\-]+(\.[a-z]{2,}))", "portfolio"),
    (r"(?<!@)(?<![A-Za-z0-9._%+-])([A-Za-z0-9._-]{5,20})(?!@)(?!\.[a-z]{2,})", "username")
]

SECTION_HEADERS = [
    ("summary", r"(summary|objective|profile)"),
    ("experience", r"(professional|work|employment).*experience|experience"),
    ("internships", r"internship"),
    ("projects", r"projects?"),
    ("education", r"education|bachelor|master|university|college|school|degree|cgpa|gpa"),
    ("skills", r"skills|technologies|proficiencies|core skills|technical skills"),
    ("certifications", r"certifications?|credentials?|achievements?|accomplishments?"),
    ("awards", r"awards?|honors?|recognition"),
    ("leadership", r"leadership|extracurricular|volunteer|positions|roles|club|nss|head"),
    ("contact", r"contact|details|info"),
]

PROHIBITED_PERSONAL_INFO = ['dob', 'date of birth', 'gender', 'photo', 'religion', 'address']

ACTION_VERBS = set([
    "led", "created", "designed", "implemented", "developed", "managed", "delivered",
    "improved", "automated", "analyzed", "built", "optimized", "deployed", "executed",
    "shipped", "initiated", "planned", "organized", "facilitated", "mentored", "launched",
    "conducted", "revamped", "advised", "streamlined", "performed", "executed"
])
WEAK_VERBS = {"worked", "helped", "assisted", "participated", "did"}

def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text("text") + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return ""

def clean_text(text):
    return re.sub(r'\n+', '\n', text.strip())

def split_sections(text):
    # Find all section headers, split into {section: content}
    sections = {}
    lines = text.split("\n")
    current = "header"
    sections[current] = []
    for line in lines:
        found = False
        for sec, pat in SECTION_HEADERS:
            if re.search(rf"\b{pat}\b", line, re.I):
                current = sec
                found = True
                if current not in sections:
                    sections[current] = []
                break
        if not found:
            sections.setdefault(current, []).append(line)
    for k, v in sections.items():
        sections[k] = "\n".join(v).strip()
    return sections

def extract_contact_anywhere(text):
    # Get all contact info, wherever it appears
    matches = {
        "emails": set(),
        "phones": set(),
        "linkedin": set(),
        "github": set(),
        "portfolio": set(),
        "prohibited_info": set()
    }
    lines = text.splitlines()
    for line in lines:
        l = line.strip()
        for pat, typ in CONTACT_PATTERNS:
            for m in re.findall(pat, l, re.I):
                if typ == "email": matches["emails"].add(m)
                elif typ == "phone": matches["phones"].add(m.replace(" ", ""))
                elif typ == "linkedin":
                    if isinstance(m, tuple): m = m[0]
                    if "linkedin.com/" in m: matches["linkedin"].add("https://" + m if not m.startswith("http") else m)
                    else: matches["linkedin"].add(f"https://linkedin.com/in/{m.split(':')[-1].strip()}")
                elif typ == "github":
                    if isinstance(m, tuple): m = m[0]
                    if "github.com/" in m: matches["github"].add("https://" + m if not m.startswith("http") else m)
                    else: matches["github"].add(f"https://github.com/{m.split(':')[-1].strip()}")
                elif typ == "url":
                    url = m[0] if isinstance(m, tuple) else m
                    # Only count as portfolio if not github/linkedin
                    if "github" not in url and "linkedin" not in url: matches["portfolio"].add(url)
                elif typ == "portfolio":
                    matches["portfolio"].add(m[0] if isinstance(m, tuple) else m)
                elif typ == "username":
                    # Try to infer github/linkedin if short and not email
                    if len(m) > 3 and "@" not in m and "." not in m and not m.isdigit():
                        matches["github"].add(f"https://github.com/{m}")
                        matches["linkedin"].add(f"https://linkedin.com/in/{m}")
    lower_text = text.lower()
    for word in PROHIBITED_PERSONAL_INFO:
        if word in lower_text:
            matches["prohibited_info"].add(word)
    # Convert all sets to lists
    for k in matches:
        matches[k] = list(matches[k])
    return matches

def ping_url(url):
    try:
        if not url.startswith("http"):
            url = "https://" + url
        resp = requests.head(url, timeout=5, allow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False

def spelling_and_grammar_check(text):
    matches = lang_tool.check(text)
    issues = []
    for m in matches[:10]:
        issues.append({
            "message": m.message,
            "offset": m.offset,
            "errorLength": m.errorLength,
            "replacements": m.replacements
        })
    return issues

def analyze_experience_bullets(bullets):
    counts = {"action_verbs": 0, "weak_verbs": 0, "quantified": 0, "total": len(bullets)}
    quantifier_patterns = [r'\b\d+%', r'\$\d+', r'\d+ users', r'[1-9]\d{2,}', r'\d+\+', r'\d+\s+(requests|individuals|workshops|engagement|users|students|participants|projects|certificates|awards|attendees)']
    for bullet in bullets:
        bullet_lower = bullet.lower()
        words = bullet_lower.split()
        first_word = words[:1]
        if first_word:
            fw = first_word[0].lower()
            if fw in ACTION_VERBS:
                counts["action_verbs"] += 1
            elif fw in WEAK_VERBS:
                counts["weak_verbs"] += 1
        if any(re.search(pat, bullet) for pat in quantifier_patterns):
            counts["quantified"] += 1
    return counts

def count_words_and_lines(text):
    words = len(text.split())
    lines = len(text.splitlines())
    return words, lines

def quantification_suggestion(exp_analysis):
    if exp_analysis["total"] == 0: return False
    ratio = exp_analysis["quantified"] / exp_analysis["total"]
    return ratio < 0.5

def suggest_improvements(report):
    suggestions = []
    strengths = []
    c = report.get('contact_info', {})
    if c.get('emails'):
        strengths.append("✔️ Professional email address found.")
    else:
        suggestions.append("Add a professional email address.")
    if c.get('linkedin'):
        strengths.append("✔️ LinkedIn profile detected.")
    else:
        suggestions.append("Add a LinkedIn profile link.")
    if c.get('phones'):
        strengths.append("✔️ Phone number present.")
    else:
        suggestions.append("Add a phone number.")
    if c.get('github'):
        strengths.append("✔️ GitHub link present.")
    if c.get('portfolio'):
        strengths.append("✔️ Portfolio link present.")
    if c.get('prohibited_info'):
        suggestions.append("Remove personal info like DOB, photo, or full address.")
    if report.get("sections", {}).get("summary"):
        strengths.append("✔️ Summary section found.")
    if report.get("sections", {}).get("skills"):
        strengths.append("✔️ Skills section present.")
    else:
        suggestions.append("Add a skills section.")
    exp = report.get('experience_analysis', {})
    if "experience" in report.get("sections", {}):
        strengths.append("✔️ Work/Internship experience section found.")
        if not exp.get("total"):
            suggestions.append("Add detailed experience bullets.")
        elif not quantification_suggestion(exp):
            strengths.append("✔️ Many experience bullets are quantified.")
        else:
            suggestions.append("Quantify more of your experience and internship bullets with numbers, %, or results.")
        if exp.get("action_verbs", 0) > 0:
            strengths.append("✔️ Experience bullets start with action verbs.")
        else:
            suggestions.append("Start more bullets with strong action verbs.")
    else:
        suggestions.append("Add a detailed experience/internship section.")
    if report.get("education_score", 0) >= 2:
        strengths.append("✔️ Education section is complete.")
    else:
        suggestions.append("Add degree, university, and graduation year to education section.")
    for sec in ["certifications", "projects", "awards"]:
        if report.get(f"{sec}_score", 0) > 0:
            strengths.append(f"✔️ {sec.capitalize()} section present.")
        elif sec in report.get("sections", {}):
            suggestions.append(f"Add more detail to your {sec} section.")
        else:
            suggestions.append(f"Add a {sec} section if you have relevant content.")
    if report.get("formatting_score", 0) >= 4:
        strengths.append("✔️ Formatting and layout are clear.")
    else:
        suggestions.append("Improve formatting with more whitespace and clear headers.")
    grammar = report.get("grammar_issues", 0)
    if grammar <= 3:
        strengths.append("✔️ Minimal grammar and spelling errors.")
    elif grammar > 6:
        issues = report.get("grammar_spelling_issues", [])
        suggestions.append("Fix grammar and spelling errors throughout. (Eg: " +
            "; ".join([x["message"] for x in issues[:3]]) + ")")
    words = report.get('word_count', 0)
    lines = report.get('line_count', 0)
    if words < 250:
        suggestions.append("Resume may be too short. Add more details to showcase your profile.")
    elif words > 1200:
        suggestions.append("Resume is too long. Condense and focus on your most relevant information.")
    if lines > 80:
        suggestions.append("Too many lines. Use concise statements and avoid unnecessary line breaks.")
    return strengths, suggestions

class ResumeAnalyzer:
    def __init__(self, resume_file, jd_keywords):
        self.resume_file = resume_file
        self.jd_keywords = jd_keywords
        self.raw_text = ""
        self.sections = {}
        self.contact_info = {}
        self.analysis_report = {}

    def extract_text(self):
        ext = os.path.splitext(self.resume_file)[1].lower()
        if ext == ".pdf":
            self.raw_text = extract_text_from_pdf(self.resume_file)
        elif ext == ".docx":
            self.raw_text = extract_text_from_docx(self.resume_file)
        else:
            raise ValueError("Unsupported file format. Use PDF or DOCX.")
        self.raw_text = clean_text(self.raw_text)
        print("[INFO] Text extracted.")

    def parse_sections(self):
        self.sections = split_sections(self.raw_text)
        print("[INFO] Sections detected:", list(self.sections.keys()))

    def analyze_contact_info(self):
        self.contact_info = extract_contact_anywhere(self.raw_text)
        self.analysis_report['contact_info'] = self.contact_info

    def check_external_links(self):
        links = (self.contact_info.get('linkedin', []) +
                 self.contact_info.get('github', []) +
                 self.contact_info.get('portfolio', []))
        reachable = {}
        for link in links:
            reachable[link] = ping_url(link)
        self.analysis_report['external_links'] = reachable

    def grammar_spelling_report(self):
        issues = spelling_and_grammar_check(self.raw_text)
        self.analysis_report['grammar_issues'] = len(issues)
        self.analysis_report['grammar_spelling_issues'] = issues

    def score_summary_section(self):
        summary_text = self.sections.get("summary", "")
        n_words = len(summary_text.split())
        score = 2 if summary_text and n_words >= 8 else 0
        self.analysis_report['summary_score'] = score

    def score_skills_section(self):
        skills_text = self.sections.get("skills", "")
        score = 2 if skills_text else 0
        self.analysis_report['skills_score'] = score

    def score_experience_section(self):
        exp_text = self.sections.get("experience", "") + "\n" + self.sections.get("internships", "")
        # Get all lines that look like bullets or significant sentences
        bullets = [line.strip("-*• \t") for line in exp_text.split('\n') if line.strip()]
        counts = analyze_experience_bullets(bullets)
        score = 2 if counts["total"] > 0 else 0
        if counts["quantified"] > 0: score += 1
        if counts["action_verbs"] > 0: score += 1
        self.analysis_report['experience_score'] = score
        self.analysis_report['experience_analysis'] = counts

    def score_education_section(self):
        edu_text = self.sections.get("education", "")
        found_degree = bool(re.search(r"bachelor|master|phd|msc|bsc|university|college|degree|diploma|cgpa|gpa", edu_text, re.I))
        found_year = bool(re.search(r"\b(19|20)\d{2}\b", edu_text))
        score = 0
        if found_degree: score += 1
        if found_year: score += 1
        self.analysis_report['education_score'] = score

    def score_projects_section(self):
        proj_text = self.sections.get("projects", "")
        lines = [l for l in proj_text.split('\n') if l.strip()]
        score = min(len(lines)//2, 2)
        self.analysis_report['projects_score'] = score

    def score_certifications_section(self):
        cert_text = self.sections.get("certifications", "")
        lines = [l for l in cert_text.split('\n') if l.strip()]
        score = min(len(lines)//2, 2)
        self.analysis_report['certifications_score'] = score

    def score_awards_section(self):
        awards_text = self.sections.get("awards", "")
        lines = [l for l in awards_text.split('\n') if l.strip()]
        score = min(len(lines)//2, 2)
        self.analysis_report['awards_score'] = score

    def score_formatting(self):
        text = self.raw_text
        score = 4
        if len(text) < 300:
            score -= 1
        if len(text) > 2500:
            score -= 1
        if "\t" in text:
            score -= 1
        if re.search(r' {2,}', text):
            score -= 1
        words, lines = count_words_and_lines(text)
        self.analysis_report['word_count'] = words
        self.analysis_report['line_count'] = lines
        self.analysis_report['formatting_score'] = max(score, 0)

    def generate_final_score(self):
        score = sum([
            self.analysis_report.get('summary_score', 0),
            self.analysis_report.get('skills_score', 0),
            self.analysis_report.get('experience_score', 0),
            self.analysis_report.get('education_score', 0),
            self.analysis_report.get('projects_score', 0),
            self.analysis_report.get('certifications_score', 0),
            self.analysis_report.get('awards_score', 0),
            self.analysis_report.get('formatting_score', 0)
        ])
        errors = self.analysis_report.get('grammar_issues', 0)
        if errors > 10:
            score -= (errors - 10) * 0.2
        final_score = max(score, 0)
        self.analysis_report['final_score'] = round(final_score, 2)

    def analyze(self):
        self.extract_text()
        self.parse_sections()
        self.analyze_contact_info()
        self.check_external_links()
        self.grammar_spelling_report()
        self.score_summary_section()
        self.score_skills_section()
        self.score_experience_section()
        self.score_education_section()
        self.score_projects_section()
        self.score_certifications_section()
        self.score_awards_section()
        self.score_formatting()
        self.analysis_report['sections'] = self.sections
        self.generate_final_score()
        strengths, suggestions = suggest_improvements(self.analysis_report)
        self.analysis_report['strengths'] = strengths
        self.analysis_report['suggestions'] = suggestions
        return self.analysis_report

def select_resume_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Resume File",
        filetypes=[("PDF files", "*.pdf"), ("Word files", "*.docx")]
    )
    return file_path

if __name__ == "__main__":
    example_jd_keywords = [
        "Python", "Java", "SQL", "AWS", "Machine Learning", "Communication",
        "Project Management", "Docker", "Kubernetes", "Leadership"
    ]
    print("Please select your resume file (PDF or DOCX)...")
    resume_path = select_resume_file()
    if not resume_path:
        print("No file selected. Exiting.")
        exit(1)
    analyzer = ResumeAnalyzer(resume_path, example_jd_keywords)
    report = analyzer.analyze()
    print("\n=== Resume Analysis Report ===")
    for key, value in report.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for k2, v2 in value.items():
                print(f"  {k2}: {v2}")
        elif isinstance(value, list) and len(value) > 5 and key not in ["suggestions", "strengths"]:
            print(f"{key}: {len(value)} items (list truncated)")
        else:
            print(f"{key}: {value}")
    print("\n--- Strengths ---")
    for s in report.get('strengths', []):
        print(f"* {s}")
    print("\n--- Suggestions for Improvement ---")
    for suggestion in report.get('suggestions', []):
        print(f"- {suggestion}")
