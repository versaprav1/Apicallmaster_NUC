import asyncio
from browser_use import Agent
from browser_use.llm import ChatGoogle
from job_extractor_template import extract_jobs_from_listing  # Your manual Playwright extractor
import os

COMPANIES = [
    "TCS Germany", "Capgemini Germany", "Accenture Germany", "IBM Germany", "Deloitte Germany", "PwC Germany", "KPMG Germany", "EY Germany",
    # ... (rest of your list)
]

# Example: Map companies to their job listing URLs (for manual extraction fallback)
COMPANY_JOB_URLS = {
    "Capgemini Germany": "https://www.capgemini.com/de-de/karriere/jobs/",
    "Siemens": "https://jobs.siemens.com/jobs",
    # Add more as needed
}

# Example: Companies known to need manual extraction
MANUAL_EXTRACTION_COMPANIES = {"Capgemini Germany", "Siemens"}

async def inspect_and_decide(page):
    """
    Inspect the DOM and decide which extraction approach to use.
    This can be as simple as checking for certain elements, or as advanced as sending a DOM sample to an LLM.
    """
    # Example: If a login wall is detected, return 'manual'
    if await page.query_selector("input[type='password']"):
        return "manual"
    # Example: If job cards are easily found, use agent
    if await page.query_selector(".job-card, .job-listing"):
        return "agent"
    # Fallback: Use agent
    return "agent"

async def run_for_company(company):
    # If company is in manual list, use manual extraction
    if company in MANUAL_EXTRACTION_COMPANIES and company in COMPANY_JOB_URLS:
        print(f"Using manual extraction for {company}")
        jobs = await extract_jobs_from_listing(COMPANY_JOB_URLS[company], max_jobs=2)
        return jobs
    # Otherwise, use the agent
    print(f"Using agent for {company}")
    agent = Agent(
        task=(
            f"Search for the 2 most relevant, recently posted (within the last month) AI/ML/Data Science/Automation/Cloud/No-Code jobs at {company} in Germany. "
            "Prioritize jobs with detailed descriptions, clear skill requirements, and mention of AI agents, no-code frameworks, or cloud platforms (AWS, Azure, GCP, Oracle). "
            "Extract job title, job link, required skills, job description, posting date, location, and remote/onsite for each job. If remote/global jobs are available and can be done from Germany, include them."
        ),
        llm=ChatGoogle(model="gemini-2.0-flash", temperature=1.0),
    )
    history = await agent.run()
    # Parse jobs from agent history as in your main script
    # (You can reuse your extract_jobs_from_history function here)
    return history  # Or parsed jobs

async def main():
    for company in COMPANIES:
        print(f"Processing {company}...")
        jobs = await run_for_company(company)
        print(f"Extracted jobs for {company}: {jobs}")
        # Save jobs to CSV, handle deduplication, etc. (reuse your helpers)
        print("Waiting 5 minutes before next company...")
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
