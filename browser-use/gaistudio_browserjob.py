import asyncio
import csv
import os
import time
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# --- Core Dependencies ---
# Ensure you have installed the browser-use library: pip install "browser-use>=0.2.0"
# It is assumed that the browser_use.Agent and browser_use.llm.ChatGoogle classes are available.
# If not, you may need to install a specific version or adapt the code.
# For this example, we will mock the agent's functionality if the library is not present.

try:
    from browser_use import Agent
    from browser_use.llm import ChatGoogle
    AGENT_ENABLED = True
except ImportError:
    print("WARNING: 'browser-use' library not found. Agent functionality will be mocked. Please install with 'pip install \"browser-use>=0.2.0\"'")
    AGENT_ENABLED = False

# --- Configuration ---

# File paths for data storage and reporting
CSV_FILE = "job_findings.csv"
FALLBACK_FILE = "job_fallbacks.csv"
REPORT_FILE = "job_search_report.txt"

# List of companies to search for jobs
COMPANIES = [
    "TCS Germany", "Capgemini Germany", "Accenture Germany", "IBM Germany", "Deloitte Germany", "PwC Germany", "KPMG Germany", "EY Germany",
    "Siemens", "SAP", "Bosch", "Allianz", "Deutsche Telekom", "Bayer", "BMW", "Volkswagen", "Mercedes-Benz", "Infineon", "Zalando",
    "Amazon", "Google", "Microsoft", "Oracle", "Salesforce", "NVIDIA", "Meta", "Apple", "Tesla", "Palantir", "Celonis", "Delivery Hero",
    "HelloFresh", "Scout24", "TeamViewer", "Otto Group", "ProSiebenSat.1", "Commerzbank", "Deutsche Bank", "Munich Re",
    "Continental", "Henkel", "BASF", "Evonik", "Festo", "Hannover Re", "RWE", "E.ON", "Uniper", "Vattenfall", "EnBW", "Roche", "Merck",
    "BioNTech", "CureVac", "Qiagen", "Sartorius", "Fresenius", "Beiersdorf", "Hapag-Lloyd", "MAN", "Knorr-Bremse", "MTU Aero Engines",
    "Rheinmetall", "SMA Solar", "Symrise", "Wacker Chemie", "Varta", "Dräger", "Software AG", "United Internet", "1&1",
    "Trivago", "FlixBus", "N26", "Check24", "Rocket Internet", "GFT Technologies", "Arvato", "Atos", "CGI", "DXC Technology",
    "HCL Technologies", "Wipro", "Infosys", "Mindtree", "Persistent Systems", "Sopra Steria", "T-Systems", "Zühlke", "Adesso", "msg systems",
    "Reply", "Valtech", "Capco", "BearingPoint", "Altran", "AlixPartners", "Roland Berger", "Simon-Kucher", "Oliver Wyman", "McKinsey",
    "Boston Consulting Group", "Bain & Company", "Kearney", "Accenture Song", "Publicis Sapient", "Cognizant", "EPAM Systems", "Luxoft",
    "Globant", "ThoughtWorks", "Endava", "Avanade", "SUSE", "Red Hat", "Canonical", "OpenAI", "DeepMind", "Anthropic", "Hugging Face"
]

# Keywords to filter relevant jobs
KEYWORDS = [
    "junior", "entry-level", "associate", "graduate", "fresher",
    "ai", "artificial intelligence", "machine learning", "ml", "data science", "automation", "prompt", "chatbot", "conversational",
    "cloud", "aws", "azure", "gcp", "oracle", "no-code", "low-code", "ops", "integration", "support", "qa", "test"
]

# CSV headers for output files
CSV_FIELDS = [
    "Serial No", "Company Name", "Job Title", "Job Link", "Skills Required",
    "Job Description", "Posting Date", "Location", "Remote/Onsite", "Extraction Method"
]
FALLBACK_FIELDS = ["Company Name", "Fallback Type", "Job Title", "Job Link", "Details"]

# --- Helper Functions ---

def log_important(message):
    """Logs a message to both the console and the report file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    try:
        with open(REPORT_FILE, 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
            f.flush()
    except Exception as e:
        print(f"ERROR: Failed to write to report.txt: {e}")

def ensure_file_has_header(filename, fieldnames):
    """Creates a file with a CSV header if it doesn't exist or is empty."""
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        log_important(f"Initialized '{filename}' with headers.")

def read_existing_job_links():
    """Reads existing job links from the CSV to prevent duplicates."""
    job_links = set()
    serial = 1
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        return job_links, serial
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Job Link"):
                job_links.add(row["Job Link"].strip())
            if row.get("Serial No") and row["Serial No"].isdigit():
                serial = max(serial, int(row["Serial No"]))
    return job_links, serial + 1

def append_data_to_csv(filename, fieldnames, data_rows):
    """Appends a list of dictionaries to a specified CSV file."""
    if not data_rows:
        return
    file_exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.path.getsize(filename) == 0:
            writer.writeheader()
        for row in data_rows:
            writer.writerow(row)

def is_recent_date(date_str):
    """Checks if a date string is within the last 31 days."""
    if not date_str:
        return False
    try:
        # Handle relative dates like "Posted Today", "Posted 5 days ago"
        if "today" in date_str.lower() or "posted" in date_str.lower() and "hour" in date_str.lower():
            return True
        if "day" in date_str.lower():
            days_ago = int(''.join(filter(str.isdigit, date_str)))
            if days_ago <= 31:
                return True
        # Handle absolute date formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%m/%d/%Y"):
            try:
                job_date = datetime.strptime(date_str.strip(), fmt)
                return job_date >= datetime.now() - timedelta(days=31)
            except (ValueError, TypeError):
                continue
        return False
    except Exception:
        return False

def job_matches_keywords(job):
    """Checks if a job's text content matches any of the defined keywords."""
    text = (job.get("Job Title", "") + " " + job.get("Skills Required", "") + " " + job.get("Job Description", "")).lower()
    return any(kw in text for kw in KEYWORDS)

# --- Phase 1: Selector Finder Agent ---

async def find_job_board_selectors(company_name):
    """
    Uses an AI agent to find the company's job board and the CSS selectors for scraping.
    """
    if not AGENT_ENABLED:
        log_important("Agent is disabled. Selector finder cannot run.")
        return None

    log_important(f"Initiating selector-finder agent for {company_name}...")
    task = (
        f"Your task is to act as a web scraping expert. First, find the primary careers or job listings page for '{company_name}' specifically for Germany. "
        "Once you are on a page with a list of multiple jobs, carefully analyze its HTML structure. "
        "Your goal is to identify the most reliable CSS selectors for the following elements: "
        "1. A container that wraps a single job posting (e.g., 'div.job-card', 'li.search-result'). "
        "2. The link (`<a>` tag) inside the container that leads to the detailed job description page. "
        "3. The element containing the job title. "
        "4. The element containing the job location. "
        "5. The element containing the posting date. "
        "Return your findings STRICTLY in the following JSON format. Do not include any other text or explanation. "
        '{"job_listing_page_url": "URL_OF_THE_JOB_LISTING_PAGE", "selectors": {'
        '"job_card": "CSS_SELECTOR_FOR_JOB_CONTAINER", "job_link": "CSS_SELECTOR_FOR_JOB_LINK", '
        '"title": "CSS_SELECTOR_FOR_TITLE", "location": "CSS_SELECTOR_FOR_LOCATION", "date": "CSS_SELECTOR_FOR_DATE"}}'
    )
    
    agent = Agent(
        task=task,
        llm=ChatGoogle(model="gemini-1.5-flash", temperature=0.0),
    )
    
    try:
        history = await agent.run()
        # The agent's final output should be the JSON
        if history and history.history[-1].model_output:
            content = history.history[-1].model_output.result
            # Clean the content to extract only the JSON part
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            if data.get("selectors", {}).get("job_card"):
                log_important(f"Selector-finder agent succeeded for {company_name}.")
                return data
            else:
                raise ValueError("Extracted JSON is missing key selectors.")
    except Exception as e:
        log_important(f"Selector-finder agent failed for {company_name}. Reason: {e}")
        return None

# --- Phase 2: Dynamic Playwright Scraper ---

async def extract_text(element, selector):
    """Safely extracts text from an element using a selector."""
    try:
        target_element = await element.query_selector(selector)
        if target_element:
            return await target_element.inner_text()
    except Exception:
        pass
    return "Not Found"

def get_absolute_url(base_url, href):
    """Constructs an absolute URL from a base URL and a relative href."""
    from urllib.parse import urljoin
    return urljoin(base_url, href)

async def extract_jobs_with_playwright(listing_url, selectors, company_name, max_jobs=5):
    """
    Scrapes job listings from a URL using dynamically provided selectors.
    """
    log_important(f"Starting Playwright scrape for {company_name} at {listing_url}")
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(listing_url, timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_selector(selectors['job_card'], timeout=15000)
            
            job_cards = await page.query_selector_all(selectors['job_card'])
            log_important(f"Found {len(job_cards)} potential job cards on the page.")

            for card in job_cards[:max_jobs * 2]: # Look at more cards to find relevant ones
                if len(jobs) >= max_jobs:
                    break

                title = await extract_text(card, selectors['title'])
                location = await extract_text(card, selectors['location'])
                date = await extract_text(card, selectors['date'])
                
                link_element = await card.query_selector(selectors['job_link'])
                link = ""
                if link_element:
                    href = await link_element.get_attribute('href')
                    if href:
                        link = get_absolute_url(listing_url, href)

                job_data = {
                    "Company Name": company_name,
                    "Job Title": title.strip(),
                    "Job Link": link,
                    "Posting Date": date.strip(),
                    "Location": location.strip(),
                    "Remote/Onsite": "", # To be filled later if possible
                    "Skills Required": "", # To be filled later
                    "Job Description": f"Title: {title.strip()}, Location: {location.strip()}", # Placeholder description
                    "Extraction Method": "Playwright Scraper"
                }

                # Basic filtering at scrape time
                if job_matches_keywords(job_data) and is_recent_date(job_data["Posting Date"]):
                    jobs.append(job_data)
                else:
                    log_important(f"Skipping job '{title.strip()}' - did not meet keyword/recency criteria.")

        except PlaywrightTimeoutError:
            log_important(f"Timeout error: Could not find job cards using selector '{selectors['job_card']}' at {listing_url}.")
        except Exception as e:
            log_important(f"An error occurred during Playwright scraping for {company_name}: {e}")
        finally:
            await browser.close()
    
    log_important(f"Playwright scrape for {company_name} finished. Found {len(jobs)} relevant jobs.")
    return jobs

# --- Phase 3: Fallback General Agent ---

async def run_general_agent_search(company_name, max_jobs=2):
    """
    Runs a general agent to find jobs when the scraper fails.
    """
    if not AGENT_ENABLED:
        log_important("Agent is disabled. General search cannot run.")
        return []

    log_important(f"Running general agent search for {company_name}.")
    task = (
        f"Search for the {max_jobs} most relevant, recently posted (within the last month) jobs at '{company_name}' in Germany matching these keywords: "
        f"{', '.join(KEYWORDS)}. "
        "For each job found, extract: job title, the direct job link, required skills, a brief job description, the posting date, the location, and remote/onsite status. "
        "Prioritize jobs with detailed descriptions. If remote/global jobs are available and can be done from Germany, include them. "
        "Return the findings as a list of JSON objects."
    )
    
    agent = Agent(
        task=task,
        llm=ChatGoogle(model="gemini-1.5-flash", temperature=0.5),
    )

    extracted_jobs = []
    try:
        history = await agent.run()
        # Simplified extraction from the agent's final output
        if history and history.history[-1].model_output:
            content = history.history[-1].model_output.result
            # Attempt to parse the content as a list of JSONs
            try:
                # Find the start of the list and the end
                list_start = content.find('[')
                list_end = content.rfind(']') + 1
                if list_start != -1 and list_end != 0:
                    json_str = content[list_start:list_end]
                    found_jobs = json.loads(json_str)
                    for item in found_jobs:
                        job = {
                            "Company Name": company_name,
                            "Job Title": item.get("job_title", "N/A"),
                            "Job Link": item.get("job_link", ""),
                            "Skills Required": ", ".join(item.get("required_skills", [])) if isinstance(item.get("required_skills"), list) else item.get("required_skills", ""),
                            "Job Description": item.get("job_description", ""),
                            "Posting Date": item.get("posting_date", ""),
                            "Location": item.get("location", ""),
                            "Remote/Onsite": item.get("remote_onsite", ""),
                            "Extraction Method": "General Agent"
                        }
                        extracted_jobs.append(job)
            except json.JSONDecodeError:
                 log_important(f"Could not parse general agent output for {company_name} as JSON.")

    except Exception as e:
        log_important(f"Error running general agent for {company_name}: {e}")

    log_important(f"General agent search for {company_name} finished. Found {len(extracted_jobs)} potential jobs.")
    return extracted_jobs

# --- Main Control Loop ---

async def run_for_company(company, serial_start, existing_links):
    """
    Orchestrates the job search for a single company.
    """
    log_important(f"--- Processing Company: {company} ---")
    jobs_found = []

    # Step 1: Try to find selectors and scrape with Playwright
    selector_data = await find_job_board_selectors(company)
    
    if selector_data and "job_listing_page_url" in selector_data and "selectors" in selector_data:
        jobs_found = await extract_jobs_with_playwright(
            listing_url=selector_data["job_listing_page_url"],
            selectors=selector_data["selectors"],
            company_name=company
        )

    # Step 2: If scraping fails or finds nothing, use the general agent as a fallback
    if not jobs_found:
        if selector_data:
            log_important(f"Scraper ran but found 0 relevant jobs for {company}. Falling back to general agent.")
        else:
            log_important(f"Could not find selectors for {company}. Using general agent search.")
        jobs_found = await run_general_agent_search(company)

    # Step 3: Process and deduplicate the results
    unique_new_jobs = []
    if not jobs_found:
        log_important(f"No new jobs found for {company} in this run.")
        return []

    for job in jobs_found:
        # Final filtering and deduplication
        if job.get("Job Link") and job["Job Link"].strip() not in existing_links:
            if job_matches_keywords(job) and is_recent_date(job.get("Posting Date")):
                unique_new_jobs.append(job)
                existing_links.add(job["Job Link"].strip()) # Add to set to prevent duplicates within the same run
            else:
                log_important(f"Skipping job '{job.get('Job Title')}' post-processing - failed keyword/recency filter.")
        else:
            log_important(f"Skipping job '{job.get('Job Title')}' - link is missing or already exists in database.")
    
    # Assign serial numbers
    for i, job in enumerate(unique_new_jobs):
        job["Serial No"] = str(serial_start + i)

    return unique_new_jobs

async def main():
    """Main function to run the continuous job search cycle."""
    log_important("Starting the Intelligent Job Finder script.")
    ensure_file_has_header(CSV_FILE, CSV_FIELDS)
    ensure_file_has_header(FALLBACK_FILE, FALLBACK_FIELDS) # Fallbacks not implemented in this version but file is created
    
    while True:
        batch_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_important(f"\n{'='*20} Starting New Batch Run at {batch_time} {'='*20}")
        
        # Read existing data at the start of each batch
        existing_job_links, current_serial = read_existing_job_links()
        total_jobs_in_batch = 0

        for company in COMPANIES:
            try:
                new_jobs = await run_for_company(company, current_serial, existing_job_links)
                
                if new_jobs:
                    append_data_to_csv(CSV_FILE, CSV_FIELDS, new_jobs)
                    num_new_jobs = len(new_jobs)
                    total_jobs_in_batch += num_new_jobs
                    current_serial += num_new_jobs
                    log_important(f"SUCCESS: Added {num_new_jobs} new jobs for {company}.")
                    summary = f"Company: {company} - Found: {num_new_jobs} new jobs."
                    for job in new_jobs:
                        summary += f"\n  - {job['Job Title']} ({job['Extraction Method']})"
                    log_important(summary)
                else:
                    log_important(f"No new jobs added for {company}.")

                # Wait before processing the next company to avoid rate limiting
                wait_time = 60 # 1 minute
                log_important(f"Waiting for {wait_time} seconds before the next company...")
                await asyncio.sleep(wait_time)

            except Exception as e:
                log_important(f"FATAL ERROR during processing for {company}: {e}")
                continue # Move to the next company

        log_important(f"\n{'='*20} Batch Run Summary {'='*20}")
        log_important(f"Batch completed at {datetime.now().strftime('%Y-%m-%d %H:%M')}.")
        log_important(f"Total new jobs added in this batch: {total_jobs_in_batch}.")
        
        # Wait before starting the next full cycle
        cycle_wait_time = 300 # 5 minutes
        log_important(f"All companies processed. Waiting for {cycle_wait_time / 60:.0f} minutes before the next full cycle...")
        await asyncio.sleep(cycle_wait_time)

if __name__ == "__main__":
    # Check if API key is present
    if not os.getenv("GOOGLE_API_KEY"):
        log_important("FATAL: GOOGLE_API_KEY not found in .env file. Please create the file and add your key.")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            log_important("\nScript interrupted by user. Exiting.")