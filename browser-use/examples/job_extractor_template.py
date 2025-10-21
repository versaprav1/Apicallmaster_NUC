import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Customize these selectors for each job board/company
SELECTORS = {
    "job_card": ".job-card",  # Update this to match the job card container
    "job_link": "a.job-link",  # Update this to match the job link
    "title": ".job-title",     # Update for job title
    "company": ".company-name",# Update for company name
    "location": ".location",   # Update for location
    "skills": ".skills-list",  # Update for skills (if available)
    "description": ".job-description", # Update for description
    "date": ".posting-date",   # Update for posting date
    "remote_onsite": ".remote-onsite"  # Update for remote/onsite info
}

async def extract_job_details(page, link):
    try:
        await page.goto(link)
        await page.wait_for_selector(SELECTORS["title"], timeout=10000)
        job = {
            "title": await (await page.query_selector(SELECTORS["title"])).inner_text(),
            "company": await (await page.query_selector(SELECTORS["company"])).inner_text(),
            "location": await (await page.query_selector(SELECTORS["location"])).inner_text(),
            "skills": await extract_skills(page),
            "description": await (await page.query_selector(SELECTORS["description"])).inner_text(),
            "date": await extract_date(page),
            "remote_onsite": await extract_remote_onsite(page),
            "link": link
        }
        return job
    except PlaywrightTimeoutError:
        print(f"Timeout extracting job at {link}")
        return None
    except Exception as e:
        print(f"Error extracting job at {link}: {e}")
        return None

async def extract_skills(page):
    skills_el = await page.query_selector(SELECTORS["skills"])
    if skills_el:
        skills = [await li.inner_text() for li in await skills_el.query_selector_all("li")]
        return ", ".join(skills)
    # Fallback: try to extract from description
    desc_el = await page.query_selector(SELECTORS["description"])
    if desc_el:
        desc = await desc_el.inner_text()
        # Simple keyword extraction (customize as needed)
        keywords = ["Python", "AWS", "Azure", "GCP", "Oracle", "ML", "AI", "Data Science", "No-Code"]
        found = [kw for kw in keywords if kw.lower() in desc.lower()]
        return ", ".join(found)
    return ""

async def extract_date(page):
    date_el = await page.query_selector(SELECTORS["date"])
    if date_el:
        return await date_el.inner_text()
    return ""

async def extract_remote_onsite(page):
    ro_el = await page.query_selector(SELECTORS["remote_onsite"])
    if ro_el:
        return await ro_el.inner_text()
    desc_el = await page.query_selector(SELECTORS["description"])
    if desc_el:
        desc = await desc_el.inner_text()
        if "remote" in desc.lower():
            return "Remote"
        if "onsite" in desc.lower() or "office" in desc.lower():
            return "Onsite"
    return "Not specified"

async def extract_jobs_from_listing(listing_url, max_jobs=2):
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(listing_url)
        await page.wait_for_selector(SELECTORS["job_card"], timeout=15000)
        # Optionally scroll or paginate here if needed
        job_links = []
        for el in await page.query_selector_all(SELECTORS["job_card"]):
            link_el = await el.query_selector(SELECTORS["job_link"])
            if link_el:
                href = await link_el.get_attribute("href")
                if href:
                    job_links.append(href)
            if len(job_links) >= max_jobs:
                break
        for link in job_links:
            job = await extract_job_details(page, link)
            if job:
                jobs.append(job)
        await browser.close()
    return jobs

# Example usage:
if __name__ == "__main__":
    # Replace with the actual job listing URL for the company
    listing_url = "https://example.com/jobs"
    jobs = asyncio.run(extract_jobs_from_listing(listing_url, max_jobs=2))
    for job in jobs:
        print(job)