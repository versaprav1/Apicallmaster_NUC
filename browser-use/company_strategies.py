"""
Company-specific navigation strategies for better job extraction
"""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CompanyStrategy:
    """Strategy configuration for specific companies"""
    base_url: str
    search_path: str
    search_params: Dict[str, str]
    navigation_steps: List[str]
    extraction_selectors: Dict[str, str]
    special_handling: List[str]

class CompanyNavigationStrategies:
    """Company-specific strategies for better job scraping"""
    
    def __init__(self):
        self.strategies = self._initialize_strategies()
    
    def _initialize_strategies(self) -> Dict[str, CompanyStrategy]:
        return {
            "capgemini_germany": CompanyStrategy(
                base_url="https://www.capgemini.com/de-de/careers/job-search/",
                search_path="/job-search",
                search_params={
                    "country": "Germany",
                    "keywords": "AI,Machine Learning,Data Science,Cloud,Automation"
                },
                navigation_steps=[
                    "Accept cookies if prompted",
                    "Use advanced search filters",
                    "Filter by location: Germany",
                    "Filter by job category: Technology, Consulting",
                    "Click on individual job postings for full details"
                ],
                extraction_selectors={
                    "job_title": ".job-title, h1, .position-title",
                    "job_description": ".job-description, .job-content, .description",
                    "location": ".location, .job-location",
                    "skills": ".skills, .requirements, .qualifications"
                },
                special_handling=[
                    "Handle dynamic loading with wait times",
                    "Look for 'Capgemini Invent' specific roles",
                    "Check for German language job descriptions"
                ]
            ),
            
            "siemens": CompanyStrategy(
                base_url="https://jobs.siemens.com/careers",
                search_path="/careers/search",
                search_params={
                    "location": "Germany",
                    "category": "Information Technology,Digital Industries"
                },
                navigation_steps=[
                    "Navigate to careers section",
                    "Use location filter for Germany",
                    "Search for keywords: AI, ML, Cloud, Automation",
                    "Apply job category filters",
                    "Click 'View Details' for each relevant job"
                ],
                extraction_selectors={
                    "job_title": "h1.job-title, .position-title",
                    "job_description": ".job-description, .job-summary",
                    "requirements": ".requirements, .qualifications",
                    "location": ".job-location, .location-info"
                },
                special_handling=[
                    "Handle Siemens job portal authentication",
                    "Look for Digital Industries and Smart Infrastructure roles",
                    "Check for Industry 4.0 and IoT positions"
                ]
            ),
            
            "sap": CompanyStrategy(
                base_url="https://jobs.sap.com/",
                search_path="/search",
                search_params={
                    "location": "Germany",
                    "workArea": "Software Development,Cloud,AI"
                },
                navigation_steps=[
                    "Go to SAP careers portal",
                    "Use advanced search with location filter",
                    "Filter by work areas: Software Development, Cloud, AI/ML",
                    "Apply experience level filters if needed",
                    "Open job details pages"
                ],
                extraction_selectors={
                    "job_title": ".job-title, h1.position-title",
                    "job_description": ".job-description, .position-description",
                    "requirements": ".requirements, .what-you-bring",
                    "location": ".location, .job-location"
                },
                special_handling=[
                    "Handle SAP SuccessFactors portal",
                    "Look for cloud platform and enterprise software roles",
                    "Check for HANA, Analytics, and AI-related positions"
                ]
            ),
            
            "accenture_germany": CompanyStrategy(
                base_url="https://www.accenture.com/de-de/careers/jobsearch",
                search_path="/careers/jobsearch",
                search_params={
                    "country": "Germany",
                    "jobType": "Technology,Consulting"
                },
                navigation_steps=[
                    "Navigate to German Accenture careers page",
                    "Use job search with technology focus",
                    "Filter by location and job type",
                    "Look for specific practice areas: AI, Cloud, Data",
                    "Click through to detailed job descriptions"
                ],
                extraction_selectors={
                    "job_title": ".job-title, h2.position-title",
                    "job_description": ".job-description, .role-description",
                    "skills": ".skills-required, .key-responsibilities",
                    "location": ".job-location, .office-location"
                },
                special_handling=[
                    "Handle Accenture's multi-step application process",
                    "Look for specific service lines: Technology, Strategy, Operations",
                    "Check for German language requirements"
                ]
            ),
            
            "ibm_germany": CompanyStrategy(
                base_url="https://www.ibm.com/careers/search",
                search_path="/careers/search",
                search_params={
                    "location": "Germany",
                    "jobCategory": "Software Development,AI,Cloud"
                },
                navigation_steps=[
                    "Go to IBM careers search",
                    "Filter by location: Germany",
                    "Search for AI, Watson, Cloud, and Red Hat roles",
                    "Use job category filters",
                    "Access full job descriptions"
                ],
                extraction_selectors={
                    "job_title": ".job-title, h1.bx--type-productive-heading-05",
                    "job_description": ".job-description, .job-summary",
                    "requirements": ".required-skills, .preferred-skills",
                    "location": ".job-location, .location-details"
                },
                special_handling=[
                    "Handle IBM's Workday-based system",
                    "Look for Watson AI, Red Hat, and Cloud roles",
                    "Check for consulting and technical positions"
                ]
            )
        }
    
    def get_strategy(self, company: str) -> CompanyStrategy:
        """Get strategy for a specific company"""
        company_key = company.lower().replace(' ', '_').replace('germany', '').strip('_')
        return self.strategies.get(company_key, self._get_default_strategy())
    
    def _get_default_strategy(self) -> CompanyStrategy:
        """Default strategy for companies without specific configurations"""
        return CompanyStrategy(
            base_url="",
            search_path="/careers",
            search_params={"location": "Germany"},
            navigation_steps=[
                "Navigate to company careers page",
                "Search for technology and AI-related roles",
                "Filter by location if possible",
                "Click on job postings for details"
            ],
            extraction_selectors={
                "job_title": "h1, .job-title, .position-title",
                "job_description": ".job-description, .description, .summary",
                "location": ".location, .job-location",
                "skills": ".skills, .requirements, .qualifications"
            },
            special_handling=[
                "Handle cookie consent dialogs",
                "Wait for dynamic content to load",
                "Look for pagination in job listings"
            ]
        )
    
    def create_enhanced_prompt(self, company: str) -> str:
        """Create company-specific enhanced prompt"""
        strategy = self.get_strategy(company)
        
        prompt = f"""
        COMPANY-SPECIFIC JOB SEARCH: {company}
        
        NAVIGATION STRATEGY:
        {chr(10).join(f"- {step}" for step in strategy.navigation_steps)}
        
        SPECIAL CONSIDERATIONS:
        {chr(10).join(f"- {handling}" for handling in strategy.special_handling)}
        
        EXTRACTION TARGETS:
        - Job Title: Look for elements like {strategy.extraction_selectors.get('job_title', 'h1, .job-title')}
        - Description: Find content in {strategy.extraction_selectors.get('job_description', '.job-description')}
        - Location: Extract from {strategy.extraction_selectors.get('location', '.location')}
        - Skills: Identify in {strategy.extraction_selectors.get('skills', '.skills, .requirements')}
        
        SEARCH FOCUS:
        - AI/ML roles (Machine Learning Engineer, Data Scientist, AI Consultant)
        - Cloud positions (Cloud Architect, DevOps Engineer, Platform Engineer)
        - Automation roles (RPA Developer, Process Automation Specialist)
        - No-code/Low-code positions
        - Junior and entry-level opportunities
        
        QUALITY REQUIREMENTS:
        - Jobs must be located in Germany or remote-friendly for Germany
        - Posted within last 30 days preferred
        - Include complete job details, not just summaries
        - Verify job links are functional
        
        OUTPUT FORMAT:
        Provide structured JSON for each job with all available fields.
        """
        
        return prompt.strip()

# Integration example
def get_company_specific_agent_config(company: str) -> Dict:
    """Get company-specific agent configuration"""
    strategies = CompanyNavigationStrategies()
    strategy = strategies.get_strategy(company)
    
    return {
        "enhanced_prompt": strategies.create_enhanced_prompt(company),
        "browser_config": {
            "headless": True,
            "timeout": 180000,  # 3 minutes
            "wait_between_actions": 3,
            "viewport": {"width": 1920, "height": 1080}
        },
        "extraction_config": {
            "selectors": strategy.extraction_selectors,
            "special_handling": strategy.special_handling
        }
    }