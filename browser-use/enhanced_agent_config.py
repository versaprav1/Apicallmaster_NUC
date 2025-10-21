from browser_use import Agent, BrowserProfile
from browser_use.llm import ChatGoogle, ChatOpenAI
from browser_use.agent.views import AgentSettings
import asyncio

class OptimizedJobScrapingAgent:
    def __init__(self, model_provider="google"):
        # Configure browser profile for job scraping
        self.browser_profile = BrowserProfile(
            headless=False,  # Set to True for production
            user_data_dir="./browser_profiles/job_scraper",
            viewport={'width': 1920, 'height': 1080},
            wait_between_actions=2.0,  # Slower to avoid detection
            disable_security=False,
            ignore_https_errors=True,
            allowed_domains=[
                'linkedin.com', 'xing.com', 'stepstone.de', 'indeed.de',
                'jobs.de', 'monster.de', 'glassdoor.de', 'kununu.com'
            ]
        )
        
        # Configure LLM based on provider
        if model_provider == "google":
            self.llm = ChatGoogle(
                model="gemini-2.0-flash",
                temperature=0.2,  # Lower temperature for more consistent extraction
            )
        elif model_provider == "openai":
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.2,
            )
        
        # Configure agent settings
        self.agent_settings = AgentSettings(
            max_steps=50,  # Increased for complex navigation
            use_vision=True,  # Help with visual elements
            system_prompt=self.get_job_scraping_system_prompt()
        )
    
    def get_job_scraping_system_prompt(self) -> str:
        return """
        You are a specialized job scraping agent focused on finding AI/ML/Data Science/Cloud/Automation positions in Germany.

        CORE OBJECTIVES:
        1. Navigate to company career pages efficiently
        2. Use search functionality to find relevant jobs
        3. Extract structured job information accurately
        4. Handle common web elements (cookies, popups, pagination)
        5. Respect rate limits and avoid detection

        SEARCH STRATEGY:
        - Look for keywords: AI, Machine Learning, Data Science, Cloud, Automation, No-Code, DevOps
        - Focus on entry to mid-level positions
        - Prioritize German locations or remote positions available in Germany
        - Filter for recent postings (last 30-60 days)

        EXTRACTION REQUIREMENTS:
        For each job, extract:
        - Exact job title
        - Direct URL to job posting
        - Location (city, country)
        - Remote/Hybrid/Onsite status
        - Posting date (in YYYY-MM-DD format if possible)
        - Required skills (as list)
        - Brief job description (2-3 sentences)
        - Experience level required
        - Salary range (if available)

        NAVIGATION BEST PRACTICES:
        - Wait for pages to fully load before interacting
        - Handle cookie consent banners appropriately
        - Use search filters when available
        - Click through to individual job pages for complete information
        - If pagination exists, process multiple pages
        - Take screenshots of important pages for debugging

        ERROR HANDLING:
        - If a page doesn't load, try refreshing once
        - If search returns no results, try alternative keywords
        - If blocked by rate limiting, note this in your response
        - If job information is incomplete, mark fields as "N/A"

        OUTPUT FORMAT:
        Structure your findings as JSON objects for easy parsing.
        """
    
    async def create_navigation_agent(self, company: str) -> Agent:
        """Create agent specialized for initial navigation"""
        task = f"""
        Navigate to the {company} careers page and locate the job search functionality.
        
        Steps:
        1. Go to {company} official website
        2. Find and click on "Careers", "Jobs", or similar section
        3. Look for job search or filter options
        4. Take a screenshot of the careers page
        5. Report the URL of the careers/jobs page
        
        If you encounter cookie banners or popups, handle them appropriately.
        """
        
        return Agent(
            task=task,
            llm=self.llm,
            browser_profile=self.browser_profile,
            settings=self.agent_settings
        )
    
    async def create_search_agent(self, company: str, careers_url: str = None) -> Agent:
        """Create agent specialized for job searching"""
        base_url = f"starting from {careers_url}" if careers_url else f"{company} careers page"
        
        task = f"""
        Search for AI/ML/Data Science/Cloud/Automation jobs at {company} in Germany.
        
        Starting point: {base_url}
        
        Search Strategy:
        1. Use search functionality with keywords: "AI", "Machine Learning", "Data Science", "Cloud", "Automation"
        2. Apply location filter for Germany if available
        3. Apply date filter for recent postings (last 30 days) if available
        4. Apply experience level filter for Entry/Junior/Mid-level if available
        
        For each relevant job found:
        1. Click on the job title to view full details
        2. Extract all available information
        3. Take a screenshot of the job posting
        4. Return to search results and continue
        
        Target: Find up to 5 most relevant positions
        """
        
        return Agent(
            task=task,
            llm=self.llm,
            browser_profile=self.browser_profile,
            settings=self.agent_settings
        )
    
    async def create_extraction_agent(self, job_urls: list) -> Agent:
        """Create agent specialized for detailed data extraction"""
        task = f"""
        Extract detailed information from these job postings: {job_urls}
        
        For each URL, visit the page and extract:
        {{
            "job_title": "exact title from the page",
            "job_link": "current page URL",
            "company": "company name",
            "location": "job location",
            "remote_type": "Remote/Hybrid/Onsite",
            "posting_date": "when job was posted",
            "required_skills": ["skill1", "skill2", "skill3"],
            "job_description": "brief summary of responsibilities",
            "experience_level": "Entry/Junior/Mid/Senior",
            "salary_range": "if mentioned",
            "application_deadline": "if mentioned",
            "department": "which team/department",
            "job_type": "Full-time/Part-time/Contract"
        }}
        
        Return results as a JSON array. Use "N/A" for unavailable information.
        Take screenshots of each job posting for verification.
        """
        
        return Agent(
            task=task,
            llm=self.llm,
            browser_profile=self.browser_profile,
            settings=self.agent_settings
        )
    
    async def scrape_company_comprehensive(self, company: str) -> dict:
        """Comprehensive scraping using multiple specialized agents"""
        results = {
            'company': company,
            'timestamp': asyncio.get_event_loop().time(),
            'jobs': [],
            'errors': [],
            'metadata': {}
        }
        
        try:
            # Step 1: Navigation
            print(f"Step 1: Navigating to {company} careers page...")
            nav_agent = await self.create_navigation_agent(company)
            nav_result = await nav_agent.run()
            
            # Extract careers URL from navigation result
            careers_url = self.extract_careers_url(nav_result)
            results['metadata']['careers_url'] = careers_url
            
            # Step 2: Job Search
            print(f"Step 2: Searching for jobs at {company}...")
            search_agent = await self.create_search_agent(company, careers_url)
            search_result = await search_agent.run()
            
            # Extract job URLs from search result
            job_urls = self.extract_job_urls(search_result)
            results['metadata']['job_urls_found'] = len(job_urls)
            
            if job_urls:
                # Step 3: Detailed Extraction
                print(f"Step 3: Extracting details for {len(job_urls)} jobs...")
                extraction_agent = await self.create_extraction_agent(job_urls)
                extraction_result = await extraction_agent.run()
                
                # Parse extracted job data
                jobs = self.parse_job_data(extraction_result)
                results['jobs'] = jobs
            
        except Exception as e:
            error_msg = f"Error scraping {company}: {str(e)}"
            print(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def extract_careers_url(self, agent_result) -> str:
        """Extract careers page URL from agent result"""
        try:
            # Look through agent history for URLs
            for step in agent_result.history:
                if hasattr(step, 'result') and step.result:
                    for result in step.result:
                        if hasattr(result, 'url') and result.url:
                            url = result.url.lower()
                            if any(keyword in url for keyword in ['career', 'job', 'hiring', 'work']):
                                return result.url
            return "N/A"
        except Exception as e:
            print(f"Error extracting careers URL: {e}")
            return "N/A"
    
    def extract_job_urls(self, agent_result) -> list:
        """Extract job URLs from search result"""
        job_urls = []
        try:
            # Parse through agent history for job-related URLs
            for step in agent_result.history:
                if hasattr(step, 'result') and step.result:
                    for result in step.result:
                        if hasattr(result, 'extracted_content'):
                            content = result.extracted_content
                            # Look for URLs in extracted content
                            import re
                            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
                            job_urls.extend(urls)
                        elif hasattr(result, 'url'):
                            job_urls.append(result.url)
            
            # Remove duplicates and filter for job-related URLs
            unique_urls = list(set(job_urls))
            filtered_urls = [url for url in unique_urls if any(keyword in url.lower() for keyword in ['job', 'position', 'career', 'vacancy'])]
            return filtered_urls[:10]  # Limit to 10 URLs
            
        except Exception as e:
            print(f"Error extracting job URLs: {e}")
            return []
    
    def parse_job_data(self, agent_result) -> list:
        """Parse job data from extraction result"""
        jobs = []
        try:
            for step in agent_result.history:
                if hasattr(step, 'result') and step.result:
                    for result in step.result:
                        if hasattr(result, 'extracted_content'):
                            content = result.extracted_content
                            try:
                                import json
                                # Try to parse as JSON first
                                if content.strip().startswith('[') or content.strip().startswith('{'):
                                    job_data = json.loads(content)
                                    if isinstance(job_data, list):
                                        jobs.extend(job_data)
                                    else:
                                        jobs.append(job_data)
                                else:
                                    # Parse structured text content
                                    job = self.parse_text_job_data(content)
                                    if job:
                                        jobs.append(job)
                            except json.JSONDecodeError:
                                # Fallback to text parsing
                                job = self.parse_text_job_data(content)
                                if job:
                                    jobs.append(job)
            return jobs
        except Exception as e:
            print(f"Error parsing job data: {e}")
            return []
    
    def parse_text_job_data(self, content: str) -> dict:
        """Parse job data from text content"""
        job = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if 'title' in key:
                    job['job_title'] = value
                elif 'link' in key or 'url' in key:
                    job['job_link'] = value
                elif 'location' in key:
                    job['location'] = value
                elif 'skill' in key:
                    job['required_skills'] = value.split(',') if ',' in value else [value]
                elif 'description' in key:
                    job['job_description'] = value
                elif 'date' in key:
                    job['posting_date'] = value
                elif 'remote' in key or 'onsite' in key:
                    job['remote_type'] = value
        
        return job if len(job) >= 3 else None  # Only return if we have at least 3 fields

# Usage example
async def main():
    scraper = OptimizedJobScrapingAgent(model_provider="google")
    
    companies = ["Siemens", "SAP", "BMW"]
    
    for company in companies:
        print(f"\n=== Scraping {company} ===")
        result = await scraper.scrape_company_comprehensive(company)
        
        print(f"Found {len(result['jobs'])} jobs")
        if result['errors']:
            print(f"Errors: {result['errors']}")
        
        # Add delay between companies
        await asyncio.sleep(60)  # 1 minute delay

if __name__ == "__main__":
    asyncio.run(main())