#!/usr/bin/env python3
"""
MENA Job Monitor - Automated Job Search Pipeline
================================================
Built for: Moroccan MBA candidate targeting Spain EU Blue Card
Profile: Arabic (native), English (strong), French (professional)
         MBA from University of Bradford, Marketing/Business background

This system monitors target companies for live job openings and scores
them based on your profile. Run daily via cron or manually.

SETUP INSTRUCTIONS:
1. Install requirements: pip install -r requirements.txt
2. Configure your profile in config.yaml
3. Run: python job_monitor.py
4. (Optional) Set up daily cron: 0 9 * * * cd /path/to/monitor && python job_monitor.py

Author: Kimi K2.6
Date: 2026-07-12
"""

import json
import yaml
import time
import random
import smtplib
import logging
import hashlib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class JobPosting:
    """Represents a single job posting"""
    company: str
    title: str
    location: str
    url: str
    description: str = ""
    posted_date: str = ""
    industry: str = ""
    source: str = ""
    job_id: str = ""

    def __post_init__(self):
        # Generate unique job ID from URL + title
        self.job_id = hashlib.md5(
            f"{self.company}:{self.title}:{self.location}".encode()
        ).hexdigest()[:12]


@dataclass
class ScoredJob:
    """Job posting with scoring"""
    job: JobPosting
    match_score: int
    arabic_required: bool
    french_required: bool
    mena_focus: bool
    sponsorship_likelihood: str  # "High", "Medium", "Low"
    recommendation: str  # "HIGH PRIORITY", "Apply", "Monitor", "Skip"
    reasons: List[str]


class Config:
    """Configuration manager"""

    DEFAULT_CONFIG = {
        "profile": {
            "nationality": "Moroccan",
            "languages": ["Arabic", "English", "French"],
            "education": "MBA - University of Bradford",
            "experience_years": 10,
            "fields": ["Marketing", "Business Development", "Sales", "Consulting"],
            "target_locations": ["Spain", "Portugal", "Netherlands", "UAE"],
            "visa_target": "EU Blue Card"
        },
        "scoring": {
            "arabic_bonus": 15,
            "french_bonus": 10,
            "mena_bonus": 15,
            "mba_bonus": 10,
            "spain_location_bonus": 10,
            "intern_penalty": -30,
            "spanish_required_penalty": -20,
            "entry_level_penalty": -15,
            "sponsorship_high_bonus": 10,
            "sponsorship_low_penalty": -10,
            "min_score_threshold": 60
        },
        "companies": {
            "tier_1": [
                {"name": "Salesforce", "industry": "SaaS/CRM", "sponsorship": "High",
                 "career_urls": ["https://www.salesforce.com/company/careers/locations/emea/spain/"]},
                {"name": "Celonis", "industry": "SaaS/Process Intelligence", "sponsorship": "Medium",
                 "career_urls": ["https://careers.celonis.com/join-us/open-positions"]},
                {"name": "Criteo", "industry": "AdTech", "sponsorship": "High",
                 "career_urls": ["https://careers.criteo.com/en/jobs/"]},
                {"name": "Google", "industry": "Technology", "sponsorship": "High",
                 "career_urls": ["https://careers.google.com/jobs/"]},
                {"name": "Microsoft", "industry": "Cloud/SaaS", "sponsorship": "High",
                 "career_urls": ["https://careers.microsoft.com/us/en/locations/spain"]},
                {"name": "SAP", "industry": "Enterprise Software", "sponsorship": "High",
                 "career_urls": ["https://jobs.sap.com/go/Spain/9008801/"]},
                {"name": "Oracle", "industry": "Enterprise Software", "sponsorship": "High",
                 "career_urls": ["https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch"]},
                {"name": "Amadeus", "industry": "Travel Tech", "sponsorship": "High",
                 "career_urls": ["https://jobs.amadeus.com/"]},
                {"name": "ServiceNow", "industry": "SaaS/Enterprise", "sponsorship": "Medium",
                 "career_urls": ["https://careers.servicenow.com/"]},
                {"name": "HubSpot", "industry": "SaaS/CRM", "sponsorship": "Low",
                 "career_urls": ["https://www.hubspot.com/careers"]},
            ],
            "tier_2": [
                {"name": "Datadog", "industry": "SaaS/Observability", "sponsorship": "Medium",
                 "career_urls": ["https://careers.datadoghq.com/madrid/"]},
                {"name": "Palo Alto Networks", "industry": "Cybersecurity", "sponsorship": "Medium",
                 "career_urls": ["https://jobs.paloaltonetworks.com/en/location/spain-jobs/"]},
                {"name": "Snowflake", "industry": "SaaS/Data Cloud", "sponsorship": "Medium",
                 "career_urls": ["https://careers.snowflake.com/us/en/"]},
                {"name": "MongoDB", "industry": "SaaS/Database", "sponsorship": "Medium",
                 "career_urls": ["https://www.mongodb.com/careers"]},
                {"name": "Elastic", "industry": "SaaS/Search", "sponsorship": "Medium",
                 "career_urls": ["https://www.elastic.co/careers"]},
                {"name": "Glovo", "industry": "Marketplace Tech", "sponsorship": "Medium",
                 "career_urls": ["https://careers.glovoapp.com/"]},
                {"name": "Adobe", "industry": "SaaS/Creative", "sponsorship": "Medium",
                 "career_urls": ["https://careers.adobe.com/"]},
                {"name": "Cisco", "industry": "Technology/Networking", "sponsorship": "High",
                 "career_urls": ["https://careers.cisco.com/"]},
            ],
            "tier_3": [
                {"name": "Accenture", "industry": "Consulting", "sponsorship": "High",
                 "career_urls": ["https://www.accenture.com/us-en/careers"]},
                {"name": "Deloitte", "industry": "Consulting", "sponsorship": "High",
                 "career_urls": ["https://apply.deloitte.com/careers"]},
                {"name": "PwC", "industry": "Consulting", "sponsorship": "High",
                 "career_urls": ["https://www.pwc.com/gx/en/careers.html"]},
                {"name": "Capgemini", "industry": "Consulting", "sponsorship": "High",
                 "career_urls": ["https://www.capgemini.com/careers/"]},
                {"name": "Airbus", "industry": "Aerospace", "sponsorship": "High",
                 "career_urls": ["https://www.airbus.com/en/careers"]},
                {"name": "Schneider Electric", "industry": "Energy/Industrial", "sponsorship": "High",
                 "career_urls": ["https://www.se.com/ww/en/about-us/careers.jsp"]},
                {"name": "Mercedes-Benz", "industry": "Automotive", "sponsorship": "Medium",
                 "career_urls": ["https://group.mercedes-benz.com/careers/"]},
                {"name": "SEAT/CUPRA", "industry": "Automotive", "sponsorship": "Medium",
                 "career_urls": ["https://www.seat.com/careers.html"]},
            ]
        },
        "keywords": {
            "positive": [
                "MENA", "Middle East", "North Africa", "MEA", "Africa", "Arabic",
                "EMEA", "international", "regional", "global", "expansion",
                "business development", "account executive", "customer success",
                "partner manager", "growth", "strategic", "regional marketing",
                "go-to-market", "channel", "market development"
            ],
            "negative": [
                "intern", "internship", "student", "graduate program",
                "fluent spanish required", "native spanish", "spanish mandatory",
                "requires EU citizenship", "EU nationals only"
            ],
            "role_titles": [
                "Business Development Manager", "Account Executive", "Customer Success Manager",
                "Regional Marketing Manager", "Growth Manager", "Partner Manager",
                "Strategic Partnerships", "Go-to-Market Manager", "Market Development Manager",
                "International Sales Manager", "Channel Manager", "Account Strategist"
            ]
        },
        "notification": {
            "enabled": False,
            "email": "your-email@example.com",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "your-email@gmail.com",
            "smtp_password": "your-app-password",
            "min_score_to_notify": 75
        },
        "output": {
            "results_dir": "./results",
            "history_file": "./job_history.json",
            "max_age_days": 30
        }
    }

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.data = self._load_or_create()

    def _load_or_create(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.DEFAULT_CONFIG, f, default_flow_style=False)
            logger.info(f"Created default config at {self.config_path}")
            return self.DEFAULT_CONFIG

    def get(self, key: str, default=None):
        keys = key.split('.')
        data = self.data
        for k in keys:
            data = data.get(k, default)
            if data is None:
                return default
        return data


class JobHistory:
    """Manages previously seen jobs to avoid duplicates"""

    def __init__(self, history_file: str = "job_history.json"):
        self.history_file = Path(history_file)
        self.seen_jobs = self._load()

    def _load(self) -> Dict:
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {}

    def save(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.seen_jobs, f, indent=2)

    def has_seen(self, job_id: str) -> bool:
        return job_id in self.seen_jobs

    def mark_seen(self, job_id: str, job_data: dict):
        self.seen_jobs[job_id] = {
            "first_seen": datetime.now().isoformat(),
            "data": job_data
        }

    def cleanup_old(self, max_age_days: int = 30):
        cutoff = datetime.now() - timedelta(days=max_age_days)
        to_remove = []
        for job_id, data in self.seen_jobs.items():
            seen_date = datetime.fromisoformat(data["first_seen"])
            if seen_date < cutoff:
                to_remove.append(job_id)
        for job_id in to_remove:
            del self.seen_jobs[job_id]
        logger.info(f"Cleaned up {len(to_remove)} old job entries")


class WebScraper:
    """Handles web scraping with rate limiting and headers"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.last_request_time = 0
        self.min_delay = 2  # seconds between requests

    def get(self, url: str) -> Optional[BeautifulSoup]:
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed + random.uniform(0.5, 1.5))

        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            self.last_request_time = time.time()

            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None


class JobScorer:
    """Scores job postings based on candidate profile"""

    def __init__(self, config: Config):
        self.config = config
        self.scoring = config.get("scoring")
        self.keywords = config.get("keywords")

    def score(self, job: JobPosting) -> ScoredJob:
        score = 50  # Base score
        reasons = []
        arabic_required = False
        french_required = False
        mena_focus = False

        text = f"{job.title} {job.description} {job.location}".lower()

        # Positive signals
        if any(kw.lower() in text for kw in ["arabic", "arabic speaker", "arabic-speaking"]):
            score += self.scoring["arabic_bonus"]
            arabic_required = True
            reasons.append("Arabic language required (+15)")

        if any(kw.lower() in text for kw in ["french", "francophone", "french-speaking"]):
            score += self.scoring["french_bonus"]
            french_required = True
            reasons.append("French language required (+10)")

        if any(kw.lower() in text for kw in self.keywords["positive"]):
            score += self.scoring["mena_bonus"]
            mena_focus = True
            reasons.append("MENA/Africa/EMEA focus (+15)")

        if "mba" in text or "master" in text:
            score += self.scoring["mba_bonus"]
            reasons.append("MBA/Master's level role (+10)")

        if "spain" in job.location.lower() or "barcelona" in job.location.lower() or "madrid" in job.location.lower():
            score += self.scoring["spain_location_bonus"]
            reasons.append("Spain-based (+10)")

        # Negative signals
        if any(kw.lower() in text for kw in ["intern", "internship", "student program"]):
            score += self.scoring["intern_penalty"]
            reasons.append("Intern/entry-level role (-30)")

        if any(kw.lower() in text for kw in ["fluent spanish", "native spanish", "spanish mandatory", "spanish required"]):
            score += self.scoring["spanish_required_penalty"]
            reasons.append("Spanish required (-20)")

        if any(kw.lower() in text for kw in ["entry level", "junior", "0-1 years", "1-2 years"]):
            score += self.scoring["entry_level_penalty"]
            reasons.append("Entry-level experience (-15)")

        # Sponsorship likelihood
        company_sponsorship = self._get_company_sponsorship(job.company)
        if company_sponsorship == "High":
            score += self.scoring["sponsorship_high_bonus"]
            reasons.append("Company has high sponsorship history (+10)")
        elif company_sponsorship == "Low":
            score += self.scoring["sponsorship_low_penalty"]
            reasons.append("Company has low sponsorship history (-10)")

        # Clamp score
        score = max(0, min(100, score))

        # Determine recommendation
        if score >= 85:
            recommendation = "HIGH PRIORITY"
        elif score >= 70:
            recommendation = "Apply"
        elif score >= 60:
            recommendation = "Monitor"
        else:
            recommendation = "Skip"

        return ScoredJob(
            job=job,
            match_score=score,
            arabic_required=arabic_required,
            french_required=french_required,
            mena_focus=mena_focus,
            sponsorship_likelihood=company_sponsorship,
            recommendation=recommendation,
            reasons=reasons
        )

    def _get_company_sponsorship(self, company_name: str) -> str:
        """Look up company sponsorship history from config"""
        for tier in ["tier_1", "tier_2", "tier_3"]:
            companies = self.config.get(f"companies.{tier}", [])
            for company in companies:
                if company["name"].lower() in company_name.lower():
                    return company.get("sponsorship", "Medium")
        return "Medium"


class JobFetcher:
    """Fetches jobs from various sources"""

    def __init__(self, config: Config, scraper: WebScraper):
        self.config = config
        self.scraper = scraper
        self.companies = self._load_companies()

    def _load_companies(self) -> List[Dict]:
        companies = []
        for tier in ["tier_1", "tier_2", "tier_3"]:
            companies.extend(self.config.get(f"companies.{tier}", []))
        return companies

    def fetch_all(self) -> List[JobPosting]:
        """Fetch jobs from all configured sources"""
        all_jobs = []

        # Method 1: LinkedIn job search (via RSS/API concept)
        linkedin_jobs = self._fetch_linkedin()
        all_jobs.extend(linkedin_jobs)

        # Method 2: Company career pages (basic scraping)
        company_jobs = self._fetch_company_pages()
        all_jobs.extend(company_jobs)

        # Method 3: Job aggregators
        aggregator_jobs = self._fetch_aggregators()
        all_jobs.extend(aggregator_jobs)

        logger.info(f"Total jobs fetched: {len(all_jobs)}")
        return all_jobs

    def _fetch_linkedin(self) -> List[JobPosting]:
        """Fetch from LinkedIn job search"""
        jobs = []
        keywords = quote("Arabic MENA EMEA business development marketing")
        locations = ["Spain", "Portugal", "Netherlands"]

        for location in locations:
            url = f"https://www.linkedin.com/jobs/search?keywords={keywords}&location={location}"
            # Note: LinkedIn blocks scraping. Use their RSS feed or API
            # This is a placeholder - see README for workarounds
            logger.info(f"LinkedIn search: {location} (requires API key or manual setup)")

        return jobs

    def _fetch_company_pages(self) -> List[JobPosting]:
        """Fetch from company career pages"""
        jobs = []

        for company in self.companies[:5]:  # Limit to avoid rate limiting
            for url in company.get("career_urls", []):
                soup = self.scraper.get(url)
                if soup:
                    page_jobs = self._parse_company_page(soup, company, url)
                    jobs.extend(page_jobs)

        return jobs

    def _parse_company_page(self, soup: BeautifulSoup, company: Dict, base_url: str) -> List[JobPosting]:
        """Parse job listings from a company career page"""
        jobs = []

        # Common selectors for job listings
        selectors = [
            'a[href*="job"]', 'a[href*="career"]', 'a[href*="position"]',
            '.job-listing', '.job-card', '.opening', '.position',
            '[data-testid*="job"]', '[class*="job"]'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements[:10]:  # Limit per page
                title = elem.get_text(strip=True)
                href = elem.get('href', '')
                if href and title and len(title) > 5:
                    if not href.startswith('http'):
                        href = urljoin(base_url, href)

                    job = JobPosting(
                        company=company["name"],
                        title=title,
                        location="Spain",  # Default, would need page-specific parsing
                        url=href,
                        industry=company.get("industry", ""),
                        source=base_url
                    )
                    jobs.append(job)

        return jobs

    def _fetch_aggregators(self) -> List[JobPosting]:
        """Fetch from job aggregator sites"""
        jobs = []

        # Europe Language Jobs - good for multilingual roles
        aggregator_urls = [
            "https://www.europelanguagejobs.com/candidates/jobs?keywords=Arabic&location=Spain",
            "https://www.europelanguagejobs.com/candidates/jobs?keywords=MENA&location=Spain",
        ]

        for url in aggregator_urls:
            soup = self.scraper.get(url)
            if soup:
                # Parse job cards
                job_cards = soup.select('.job-card, .job-listing, [class*="job"]')
                for card in job_cards[:10]:
                    title_elem = card.select_one('.job-title, h2, h3, a')
                    company_elem = card.select_one('.company-name, [class*="company"]')
                    location_elem = card.select_one('.location, [class*="location"]')

                    if title_elem:
                        job = JobPosting(
                            company=company_elem.get_text(strip=True) if company_elem else "Unknown",
                            title=title_elem.get_text(strip=True),
                            location=location_elem.get_text(strip=True) if location_elem else "Spain",
                            url=title_elem.get('href', url),
                            source="Europe Language Jobs"
                        )
                        jobs.append(job)

        return jobs


class ResultsManager:
    """Manages and formats results"""

    def __init__(self, output_dir: str = "./results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def save(self, scored_jobs: List[ScoredJob], filename: str = None):
        if filename is None:
            filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

        filepath = self.output_dir / filename

        data = []
        for sj in scored_jobs:
            data.append({
                "job_id": sj.job.job_id,
                "company": sj.job.company,
                "title": sj.job.title,
                "location": sj.job.location,
                "url": sj.job.url,
                "industry": sj.job.industry,
                "match_score": sj.match_score,
                "arabic_required": sj.arabic_required,
                "french_required": sj.french_required,
                "mena_focus": sj.mena_focus,
                "sponsorship_likelihood": sj.sponsorship_likelihood,
                "recommendation": sj.recommendation,
                "reasons": sj.reasons,
                "source": sj.job.source,
                "scraped_at": datetime.now().isoformat()
            })

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(data)} jobs to {filepath}")
        return filepath

    def generate_report(self, scored_jobs: List[ScoredJob]) -> str:
        """Generate a human-readable report"""
        lines = [
            "=" * 70,
            "MENA JOB MONITOR - DAILY REPORT",
            "=" * 70,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total jobs analyzed: {len(scored_jobs)}",
            "",
            "HIGH PRIORITY ROLES (Score >= 85)",
            "-" * 70,
        ]

        high_priority = [sj for sj in scored_jobs if sj.recommendation == "HIGH PRIORITY"]
        for sj in high_priority:
            lines.extend([
                f"",
                f"Company: {sj.job.company}",
                f"Role: {sj.job.title}",
                f"Location: {sj.job.location}",
                f"Match Score: {sj.match_score}/100",
                f"Arabic: {'Yes' if sj.arabic_required else 'No'} | French: {'Yes' if sj.french_required else 'No'}",
                f"Sponsorship: {sj.sponsorship_likelihood}",
                f"URL: {sj.job.url}",
                f"Reasons: {'; '.join(sj.reasons)}",
            ])

        lines.extend([
            "",
            "APPLY ROLES (Score 70-84)",
            "-" * 70,
        ])

        apply_jobs = [sj for sj in scored_jobs if sj.recommendation == "Apply"]
        for sj in apply_jobs:
            lines.append(f"• {sj.job.company} | {sj.job.title} | Score: {sj.match_score} | {sj.job.location}")

        lines.extend([
            "",
            "MONITOR ROLES (Score 60-69)",
            "-" * 70,
        ])

        monitor_jobs = [sj for sj in scored_jobs if sj.recommendation == "Monitor"]
        for sj in monitor_jobs:
            lines.append(f"• {sj.job.company} | {sj.job.title} | Score: {sj.match_score}")

        return "\n".join(lines)

    def save_csv(self, scored_jobs: List[ScoredJob], filename: str = None):
        """Save results as CSV for easy viewing"""
        import csv

        if filename is None:
            filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Company", "Title", "Location", "Match Score", "Arabic Required",
                "French Required", "MENA Focus", "Sponsorship", "Recommendation", "URL"
            ])

            for sj in scored_jobs:
                writer.writerow([
                    sj.job.company,
                    sj.job.title,
                    sj.job.location,
                    sj.match_score,
                    "Yes" if sj.arabic_required else "No",
                    "Yes" if sj.french_required else "No",
                    "Yes" if sj.mena_focus else "No",
                    sj.sponsorship_likelihood,
                    sj.recommendation,
                    sj.job.url
                ])

        logger.info(f"Saved CSV to {filepath}")
        return filepath


class Notifier:
    """Sends email notifications for high-priority jobs"""

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.get("notification.enabled", False)
        self.email = config.get("notification.email")
        self.min_score = config.get("notification.min_score_to_notify", 75)

    def send(self, scored_jobs: List[ScoredJob]):
        if not self.enabled:
            logger.info("Notifications disabled")
            return

        high_priority = [sj for sj in scored_jobs 
                        if sj.match_score >= self.min_score and sj.recommendation == "HIGH PRIORITY"]

        if not high_priority:
            logger.info("No high-priority jobs to notify about")
            return

        subject = f"[Job Monitor] {len(high_priority)} High-Priority MENA Jobs Found"
        body = self._format_email(high_priority)

        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.get("notification.smtp_username")
            msg['To'] = self.email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(
                self.config.get("notification.smtp_server"),
                self.config.get("notification.smtp_port")
            )
            server.starttls()
            server.login(
                self.config.get("notification.smtp_username"),
                self.config.get("notification.smtp_password")
            )
            server.send_message(msg)
            server.quit()

            logger.info(f"Email notification sent to {self.email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def _format_email(self, jobs: List[ScoredJob]) -> str:
        lines = [f"Found {len(jobs)} high-priority jobs matching your profile:", ""]
        for sj in jobs:
            lines.extend([
                f"Company: {sj.job.company}",
                f"Role: {sj.job.title}",
                f"Location: {sj.job.location}",
                f"Score: {sj.match_score}/100",
                f"URL: {sj.job.url}",
                "-" * 40,
                ""
            ])
        return "\n".join(lines)


class JobMonitor:
    """Main orchestrator"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config(config_path)
        self.scraper = WebScraper()
        self.fetcher = JobFetcher(self.config, self.scraper)
        self.scorer = JobScorer(self.config)
        self.history = JobHistory(self.config.get("output.history_file"))
        self.results = ResultsManager(self.config.get("output.results_dir"))
        self.notifier = Notifier(self.config)

    def run(self):
        """Execute full monitoring pipeline"""
        logger.info("=" * 70)
        logger.info("Starting MENA Job Monitor")
        logger.info("=" * 70)

        # Step 1: Fetch jobs
        raw_jobs = self.fetcher.fetch_all()

        # Step 2: Filter already seen
        new_jobs = [j for j in raw_jobs if not self.history.has_seen(j.job_id)]
        logger.info(f"New jobs found: {len(new_jobs)} (filtered {len(raw_jobs) - len(new_jobs)} duplicates)")

        # Step 3: Score jobs
        scored_jobs = []
        for job in new_jobs:
            scored = self.scorer.score(job)
            scored_jobs.append(scored)
            self.history.mark_seen(job.job_id, asdict(job))

        # Step 4: Sort by score
        scored_jobs.sort(key=lambda x: x.match_score, reverse=True)

        # Step 5: Filter by threshold
        threshold = self.config.get("scoring.min_score_threshold", 60)
        filtered_jobs = [sj for sj in scored_jobs if sj.match_score >= threshold]

        # Step 6: Save results
        self.results.save(filtered_jobs)
        self.results.save_csv(filtered_jobs)

        # Step 7: Generate report
        report = self.results.generate_report(filtered_jobs)
        report_path = self.results.output_dir / f"report_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(report_path, 'w') as f:
            f.write(report)

        # Step 8: Send notifications
        self.notifier.send(filtered_jobs)

        # Step 9: Cleanup old history
        self.history.cleanup_old(self.config.get("output.max_age_days", 30))
        self.history.save()

        logger.info("=" * 70)
        logger.info(f"Monitor complete. {len(filtered_jobs)} jobs saved.")
        logger.info(f"Report: {report_path}")
        logger.info("=" * 70)

        return filtered_jobs


def main():
    monitor = JobMonitor()
    jobs = monitor.run()

    # Print summary to console
    print("\n" + "=" * 70)
    print("MONITORING COMPLETE")
    print("=" * 70)
    print(f"Jobs meeting threshold: {len(jobs)}")
    print(f"High Priority: {len([j for j in jobs if j.recommendation == 'HIGH PRIORITY'])}")
    print(f"Apply: {len([j for j in jobs if j.recommendation == 'Apply'])}")
    print(f"Monitor: {len([j for j in jobs if j.recommendation == 'Monitor'])}")


if __name__ == "__main__":
    main()
