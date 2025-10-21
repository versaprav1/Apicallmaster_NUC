import asyncio
import csv
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
from browser_use import Agent
from browser_use.llm import ChatGoogle
from job_extractor_template import extract_jobs_from_listing

CSV_FILE = "agent_findings.csv"
FALLBACK_FILE = "agent_fallbacks.csv"
REPORT_FILE = "report.txt"

# Expanded company list for broad coverage
COMPANIES = [
    "TCS Germany", "Capgemini Germany", "Accenture Germany", "IBM Germany", "Deloitte Germany", "PwC Germany", "KPMG Germany", "EY Germany",
    "Siemens", "SAP", "Bosch", "Allianz", "Deutsche Telekom", "Bayer", "BMW", "Volkswagen", "Mercedes-Benz", "Infineon", "Zalando",
    "Amazon", "Google", "Microsoft", "Oracle", "Salesforce", "NVIDIA", "Meta", "Apple", "Tesla", "Palantir", "Celonis", "Delivery Hero",
    "HelloFresh", "Scout24", "TeamViewer", "Wirecard", "Otto Group", "ProSiebenSat.1", "Commerzbank", "Deutsche Bank", "Munich Re",
    "Continental", "Henkel", "BASF", "Evonik", "Festo", "Hannover Re", "RWE", "E.ON", "Uniper", "Vattenfall", "EnBW", "Roche", "Merck",
    "BioNTech", "CureVac", "Qiagen", "Sartorius", "Fresenius", "Beiersdorf", "Hapag-Lloyd", "MAN", "Knorr-Bremse", "MTU Aero Engines",
    "Rheinmetall", "SMA Solar", "Symrise", "Wacker Chemie", "Varta", "Dräger", "Sartorius", "Software AG", "United Internet", "1&1",
    "Bitkom", "Trivago", "FlixBus", "N26", "Check24", "Rocket Internet", "GFT Technologies", "Arvato", "Atos", "CGI", "DXC Technology",
    "HCL Technologies", "Wipro", "Infosys", "Mindtree", "Persistent Systems", "Sopra Steria", "T-Systems", "Zühlke", "Adesso", "msg systems",
    "Reply", "Valtech", "Capco", "BearingPoint", "Altran", "AlixPartners", "Roland Berger", "Simon-Kucher", "Oliver Wyman", "McKinsey",
    "Boston Consulting Group", "Bain & Company", "Kearney", "Accenture Song", "Publicis Sapient", "Cognizant", "EPAM Systems", "Luxoft",
    "Globant", "ThoughtWorks", "Endava", "Avanade", "SUSE", "Red Hat", "Canonical", "OpenAI", "DeepMind", "Anthropic", "Hugging Face"
]

# Expanded CSV fields
CSV_FIELDS = [
    "Serial No", "Company Name", "Job Title", "Job Link", "Skills Required",
    "Job Description", "Posting Date", "Location", "Remote/Onsite"
]
FALLBACK_FIELDS = ["Company Name", "Fallback Type", "Job Title", "Job Link", "Details"]
KEYWORDS = [
    "junior", "entry-level", "associate", "graduate", "fresher",
    "ai", "artificial intelligence", "machine learning", "ml", "data science", "automation", "prompt", "chatbot", "conversational",
    "cloud", "aws", "azure", "gcp", "oracle", "no-code", "low-code", "ops", "integration", "support", "qa", "test"
]

# Ensure CSVs and report file have headers or exist
def ensure_csv_has_header(filename, fieldnames):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

def ensure_report_file():
    if not os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write("")

# Helper to read existing jobs for duplicate checking
def read_existing_jobs():
    jobs = set()
    serial = 1
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
        return jobs, serial
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.add((row["Company Name"].strip(), row["Job Title"].strip(), row["Job Link"].strip()))
            serial = max(serial, int(row["Serial No"]))
    return jobs, serial

def append_jobs_to_csv(new_jobs):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists or os.path.getsize(CSV_FILE) == 0:
            writer.writeheader()
        for job in new_jobs:
            writer.writerow(job)

def append_fallbacks_to_csv(fallbacks):
    file_exists = os.path.exists(FALLBACK_FILE)
    with open(FALLBACK_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FALLBACK_FIELDS)
        if not file_exists or os.path.getsize(FALLBACK_FILE) == 0:
            writer.writeheader()
        for fb in fallbacks:
            writer.writerow(fb)

def append_summary_to_report(summary):
    print(f"DEBUG: Writing summary to report.txt:\n{summary}")
    try:
        with open(REPORT_FILE, 'a', encoding='utf-8') as f:
            f.write(summary + '\n')
            f.flush()
        print("DEBUG: Successfully wrote to report.txt")
    except Exception as e:
        print(f"ERROR: Failed to write to report.txt: {e}")

# Helper: check if job is recent (last month)
def is_recent_date(date_str):
    try:
        # Try common date formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%d %b %Y"):
            try:
                job_date = datetime.strptime(date_str.strip(), fmt)
                break
            except Exception:
                continue
        else:
            return False
        return job_date >= datetime.now() - timedelta(days=31)
    except Exception:
        return False

# Helper: check if job matches keywords in title, skills, or description
def job_matches_keywords(job):
    text = (job.get("Job Title", "") + " " + job.get("Skills Required", "") + " " + job.get("Job Description", "")).lower()
    return any(kw in text for kw in KEYWORDS)

# Extraction logic: expects agent to extract all fields, fallback if missing
def extract_jobs_from_history(history, company, max_jobs=2):
    jobs = []
    fallbacks = []
    for h in history.history:
        job_title = job_link = skills = job_desc = posting_date = location = remote_onsite = ""
        fallback_type = None
        if h.model_output and h.model_output.action:
            for action in h.model_output.action:
                for r in h.result:
                    if r.extracted_content:
                        import json
                        try:
                            data = json.loads(r.extracted_content)
                            job_title = data.get("job_title", "")
                            job_link = data.get("job_link", "") or data.get("page_link", "") or data.get("Page Link", "")
                            skills = data.get("required_skills", "")
                            if isinstance(skills, list):
                                skills = ", ".join(skills)
                            job_desc = data.get("job_description", "")
                            posting_date = data.get("posting_date", "")
                            location = data.get("location", "")
                            remote_onsite = data.get("remote_onsite", "")
                            if not job_title and "sponsored" in data.get("Extracted Content", "").lower():
                                fallback_type = "Sponsored"
                        except Exception:
                            text = r.extracted_content
                            if "job title" in text.lower():
                                for line in text.splitlines():
                                    if "job title" in line.lower():
                                        job_title = line.split(":",1)[-1].strip()
                                    if "required skills" in line.lower():
                                        skills = line.split(":",1)[-1].strip()
                                    if "job link" in line.lower() or "page link" in line.lower():
                                        job_link = line.split(":",1)[-1].strip()
                                    if "job description" in line.lower():
                                        job_desc = line.split(":",1)[-1].strip()
                                    if "posting date" in line.lower():
                                        posting_date = line.split(":",1)[-1].strip()
                                    if "location" in line.lower():
                                        location = line.split(":",1)[-1].strip()
                                    if "remote" in line.lower() or "onsite" in line.lower():
                                        remote_onsite = line.split(":",1)[-1].strip()
                            if "sponsored" in text.lower():
                                fallback_type = "Sponsored"
                        if job_title or job_link or skills or job_desc:
                            job = {
                                "Company Name": company,
                                "Job Title": job_title,
                                "Job Link": job_link,
                                "Skills Required": skills,
                                "Job Description": job_desc,
                                "Posting Date": posting_date,
                                "Location": location,
                                "Remote/Onsite": remote_onsite,
                            }
                            print(f"DEBUG: Extracted job candidate: {job}")  # Debug print
                            # Filter: must match keywords and be recent (or warn if no date)
                            if job_matches_keywords(job):
                                if posting_date:
                                    if is_recent_date(posting_date):
                                        jobs.append((job, None))
                                    else:
                                        jobs.append((job, "Warning: Job posting date is not within last month."))
                                else:
                                    jobs.append((job, "Warning: No posting date available."))
                                if len(jobs) >= max_jobs:
                                    return jobs, fallbacks
                            elif fallback_type:
                                fallbacks.append({
                                    "Company Name": company,
                                    "Fallback Type": fallback_type,
                                    "Job Title": job_title,
                                    "Job Link": job_link,
                                    "Details": r.extracted_content[:200],
                                })
    if not jobs:
        print(f"DEBUG: No jobs extracted for {company} in this round.")
    return jobs, fallbacks

async def run_for_company(company, serial_start):
    # Qualitative, modern agent prompt
    agent = Agent(
        task=(
            f"Search for the 2 most relevant, recently posted (within the last month) AI/ML/Data Science/Automation/Cloud/No-Code jobs at {company} in Germany. "
            "Prioritize jobs with detailed descriptions, clear skill requirements, and mention of AI agents, no-code frameworks, or cloud platforms (AWS, Azure, GCP, Oracle). "
            "Extract job title, job link, required skills, job description, posting date, location, and remote/onsite for each job. If remote/global jobs are available and can be done from Germany, include them."
        ),
        llm=ChatGoogle(model="gemini-2.0-flash", temperature=1.0),
    )
    history = await agent.run()
    jobs, fallbacks = extract_jobs_from_history(history, company, max_jobs=2)
    for i, (job, warn) in enumerate(jobs):
        job["Serial No"] = str(serial_start + i)
    return jobs, fallbacks

# Retry logic for dynamic sites
import time as _time

# Add a custom exception for 429 handling
class ResourceExhaustedError(Exception):
    pass

# Helper to log important messages to report.txt and print
from datetime import datetime

def log_important(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    with open(REPORT_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
        f.flush()

# Wrap run_for_company to handle 429 errors with retry and wait
async def run_for_company_with_429_handling(company, serial_start, max_retries=3, wait_minutes=5):
    retries = 0
    total_429s = 0
    while retries < max_retries:
        try:
            jobs, fallbacks = await run_for_company(company, serial_start)
            # Check if jobs contains a 429 error (simulate by checking for a known error message)
            # If your agent raises a specific exception, catch it instead
            if jobs and isinstance(jobs, list):
                for job, warn in jobs:
                    if warn and 'RESOURCE_EXHAUSTED' in str(warn):
                        raise ResourceExhaustedError('429 RESOURCE_EXHAUSTED detected in job warning')
            return jobs, fallbacks, retries, total_429s
        except ResourceExhaustedError as e:
            retries += 1
            total_429s += 1
            log_important(f"429 RESOURCE_EXHAUSTED for {company} (attempt {retries}/{max_retries}). Waiting {wait_minutes} minutes before retrying...")
            import time as _time
            _time.sleep(wait_minutes * 60)
            log_important(f"Resuming {company} after 429 wait (attempt {retries}/{max_retries})...")
        except Exception as e:
            # If the agent's API client raises a 429 error as an exception, catch it here
            if 'RESOURCE_EXHAUSTED' in str(e) or '429' in str(e):
                retries += 1
                total_429s += 1
                log_important(f"429 RESOURCE_EXHAUSTED for {company} (attempt {retries}/{max_retries}). Waiting {wait_minutes} minutes before retrying...")
                import time as _time
                _time.sleep(wait_minutes * 60)
                log_important(f"Resuming {company} after 429 wait (attempt {retries}/{max_retries})...")
            else:
                log_important(f"Error running agent for {company}: {e}")
                return [], [], retries, total_429s
    log_important(f"Max retries reached for {company} due to 429 errors. Skipping to next company.")
    return [], [], retries, total_429s

async def main():
    ensure_csv_has_header(CSV_FILE, CSV_FIELDS)
    ensure_csv_has_header(FALLBACK_FILE, FALLBACK_FIELDS)
    ensure_report_file()
    while True:
        batch_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"\n=== Starting a new batch for all companies at {batch_time} ===\n")
        summary_lines = [f"=== Batch Run: {batch_time} ==="]
        existing_jobs, last_serial = read_existing_jobs()
        serial = last_serial + 1
        total_429s_batch = 0
        for company in COMPANIES:
            print(f"Running agent for {company}...")
            try:
                jobs, fallbacks, retries, total_429s = await run_for_company_with_429_handling(company, serial)
                total_429s_batch += total_429s
            except Exception as e:
                error_summary = f"[{batch_time}] ERROR for {company}: {str(e)}"
                append_summary_to_report(error_summary)
                continue
            # Deduplicate
            unique_jobs = []
            job_warnings = []
            for job, warn in jobs:
                key = (job["Company Name"].strip(), job["Job Title"].strip(), job["Job Link"].strip())
                if key not in existing_jobs:
                    unique_jobs.append(job)
                    existing_jobs.add(key)
                    if warn:
                        job_warnings.append((job, warn))
            if unique_jobs:
                append_jobs_to_csv(unique_jobs)
                serial += len(unique_jobs)
                print(f"Added {len(unique_jobs)} new jobs for {company}.")
                summary_lines.append(f"Company: {company} - Jobs found: {len(unique_jobs)}")
                for job in unique_jobs:
                    summary_lines.append(f"- {job['Job Title']}: {job['Job Link']} ({job.get('Posting Date','')}, {job.get('Location','')}, {job.get('Remote/Onsite','')})")
                for job, warn in job_warnings:
                    summary_lines.append(f"  * {warn}")
                if retries > 0:
                    summary_lines.append(f"  * WARNING: {retries} retries due to 429 errors for {company}")
            else:
                print(f"No new jobs found for {company}.")
                summary_lines.append(f"Company: {company} - No jobs found.")
                if retries > 0:
                    summary_lines.append(f"  * WARNING: {retries} retries due to 429 errors for {company}")
            if fallbacks:
                append_fallbacks_to_csv(fallbacks)
                print(f"Logged {len(fallbacks)} fallback/sponsored jobs for {company}.")
                summary_lines.append(f"Company: {company} - Fallbacks: {len(fallbacks)}")
            print("Waiting 5 minutes before next company...")
            import time as _time
            _time.sleep(300)  # 5 minutes
        batch_summary = f"[{batch_time}] Batch completed. Total jobs found: {serial - last_serial}. Companies processed: {len(COMPANIES)}."
        append_summary_to_report(batch_summary)
        summary_lines.append(f"Total 429 errors this batch: {total_429s_batch}")
        summary_lines.append("-------------------------------\n")
        summary = '\n'.join(summary_lines)
        print(summary)
        append_summary_to_report(summary)
        print("All companies processed. Waiting 5 minutes before next full cycle...")
        import time as _time
        _time.sleep(300)  # Wait before starting the next full cycle

if __name__ == "__main__":
    asyncio.run(main())