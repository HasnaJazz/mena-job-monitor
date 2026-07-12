#!/usr/bin/env python3
"""
MENA Job Monitor - Automated Job Search Pipeline
Built for: Moroccan MBA candidate targeting Spain EU Blue Card
"""

import json
import csv
import time
import random
import logging
import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ============== DATA MODELS ==============

@dataclass
class JobPosting:
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
        self.job_id = hashlib.md5(
            f"{self.company}:{self.title}:{self.location}".encode()
        ).hexdigest()[:12]


@dataclass
class ScoredJob:
    job: JobPosting
    match_score: int
    arabic_required: bool
    french_required: bool
    mena_focus: bool
    sponsorship_likelihood: str
    recommendation: str
    reasons: List[str]


# ============== CONFIGURATION ==============

SCORING = {
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
}

COMPANIES = {
    "tier_1": [
        {"name": "Salesforce", "industry": "SaaS/CRM", "sponsorship": "High"},
        {"name": "Celonis", "industry": "SaaS/Process Intelligence", "sponsorship": "Medium"},
        {"name": "Criteo", "industry": "AdTech", "sponsorship": "High"},
        {"name": "Google", "industry": "Technology", "sponsorship": "High"},
        {"name": "Microsoft", "industry": "Cloud/SaaS", "sponsorship": "High"},
        {"name": "SAP", "industry": "Enterprise Software", "sponsorship": "High"},
        {"name": "Oracle", "industry": "Enterprise Software", "sponsorship": "High"},
        {"name": "Amadeus", "industry": "Travel Tech", "sponsorship": "High"},
        {"name": "ServiceNow", "industry": "SaaS/Enterprise", "sponsorship": "Medium"},
        {"name": "HubSpot", "industry": "SaaS/CRM", "sponsorship": "Low"},
    ],
    "tier_2": [
        {"name": "Datadog", "industry": "SaaS/Observability", "sponsorship": "Medium"},
        {"name": "Palo Alto Networks", "industry": "Cybersecurity", "sponsorship": "Medium"},
        {"name": "Snowflake", "industry": "SaaS/Data Cloud", "sponsorship": "Medium"},
        {"name": "MongoDB", "industry": "SaaS/Database", "sponsorship": "Medium"},
        {"name": "Elastic", "industry": "SaaS/Search", "sponsorship": "Medium"},
        {"name": "Glovo", "industry": "Marketplace Tech", "sponsorship": "Medium"},
        {"name": "Adobe", "industry": "SaaS/Creative", "sponsorship": "Medium"},
        {"name": "Cisco", "industry": "Technology/Networking", "sponsorship": "High"},
    ],
    "tier_3": [
        {"name": "Accenture", "industry": "Consulting", "sponsorship": "High"},
        {"name": "Deloitte", "industry": "Consulting", "sponsorship": "High"},
        {"name": "PwC", "industry": "Consulting", "sponsorship": "High"},
        {"name": "Capgemini", "industry": "Consulting", "sponsorship": "High"},
        {"name": "Airbus", "industry": "Aerospace", "sponsorship": "High"},
        {"name": "Schneider Electric", "industry": "Energy/Industrial", "sponsorship": "High"},
        {"name": "Mercedes-Benz", "industry": "Automotive", "sponsorship": "Medium"},
        {"name": "SEAT/CUPRA", "industry": "Automotive", "sponsorship": "Medium"},
    ]
}

KEYWORDS = {
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
    ]
}


# ============== JOB HISTORY ==============

class JobHistory:
    def __init__(self, history_file: str = "job_history.json"):
        self.history_file = Path(history_file)
        self.seen_jobs = self._load()

    def _load(self) -> Dict:
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
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
            try:
                seen_date = datetime.fromisoformat(data["first_seen"])
                if seen_date < cutoff:
                    to_remove.append(job_id)
            except:
                to_remove.append(job_id)
        for job_id in to_remove:
            del self.seen_jobs[job_id]
        logger.info(f"Cleaned up {len(to_remove)} old job entries")


# ============== JOB SCORER ==============

class JobScorer:
    def score(self, job: JobPosting) -> ScoredJob:
        score = 50
        reasons = []
        arabic_required = False
        french_required = False
        mena_focus = False

        text = f"{job.title} {job.description} {job.location}".lower()

        if any(kw.lower() in text for kw in ["arabic", "arabic speaker", "arabic-speaking"]):
            score += SCORING["arabic_bonus"]
            arabic_required = True
            reasons.append("Arabic language required (+15)")

        if any(kw.lower() in text for kw in ["french", "francophone", "french-speaking"]):
            score += SCORING["french_bonus"]
            french_required = True
            reasons.append("French language required (+10)")

        if any(kw.lower() in text for kw in KEYWORDS["positive"]):
            score += SCORING["mena_bonus"]
            mena_focus = True
            reasons.append("MENA/Africa/EMEA focus (+15)")

        if "mba" in text or "master" in text:
            score += SCORING["mba_bonus"]
            reasons.append("MBA/Master's level role (+10)")

        if any(loc in job.location.lower() for loc in ["spain", "barcelona", "madrid"]):
            score += SCORING["spain_location_bonus"]
            reasons.append("Spain-based (+10)")

        if any(kw.lower() in text for kw in ["intern", "internship", "student program"]):
            score += SCORING["intern_penalty"]
            reasons.append("Intern/entry-level role (-30)")

        if any(kw.lower() in text for kw in ["fluent spanish", "native spanish", "spanish mandatory", "spanish required"]):
            score += SCORING["spanish_required_penalty"]
            reasons.append("Spanish required (-20)")

        if any(kw.lower() in text for kw in ["entry level", "junior", "0-1 years", "1-2 years"]):
            score += SCORING["entry_level_penalty"]
            reasons.append("Entry-level experience (-15)")

        company_sponsorship = self._get_company_sponsorship(job.company)
        if company_sponsorship == "High":
            score += SCORING["sponsorship_high_bonus"]
            reasons.append("Company has high sponsorship history (+10)")
        elif company_sponsorship == "Low":
            score += SCORING["sponsorship_low_penalty"]
            reasons.append("Company has low sponsorship history (-10)")

        score = max(0, min(100, score))

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
        for tier in ["tier_1", "tier_2", "tier_3"]:
            for company in COMPANIES.get(tier, []):
                if company["name"].lower() in company_name.lower():
                    return company.get("sponsorship", "Medium")
        return "Medium"


# ============== JOB FETCHER ==============

class JobFetcher:
    def __init__(self):
        self.all_companies = []
        for tier in ["tier_1", "tier_2", "tier_3"]:
            self.all_companies.extend(COMPANIES.get(tier, []))

    def fetch_all(self) -> List[JobPosting]:
        all_jobs = []

        # Try web scraping first
        try:
            import requests
            from bs4 import BeautifulSoup
            web_jobs = self._fetch_from_web()
            all_jobs.extend(web_jobs)
        except ImportError:
            logger.warning("requests/beautifulsoup4 not available, using fallback data")
        except Exception as e:
            logger.warning(f"Web scraping failed: {e}, using fallback data")

        # Always add known openings as fallback
        known_jobs = self._get_known_openings()
        all_jobs.extend(known_jobs)

        # Remove duplicates by job_id
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            if job.job_id not in seen:
                seen.add(job.job_id)
                unique_jobs.append(job)

        logger.info(f"Total unique jobs: {len(unique_jobs)}")
        return unique_jobs

    def _fetch_from_web(self) -> List[JobPosting]:
        jobs = []
        try:
            import requests
            from bs4 import BeautifulSoup

            # Europe Language Jobs
            urls = [
                "https://www.europelanguagejobs.com/candidates/jobs?keywords=Arabic&location=Spain",
                "https://www.europelanguagejobs.com/candidates/jobs?keywords=MENA&location=Spain",
            ]

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        job_cards = soup.select('.job-item, .job-card, [class*="job"]')
                        for card in job_cards[:10]:
                            title_elem = card.select_one('h2, h3, .job-title, a')
                            if title_elem:
                                href = title_elem.get('href', '')
                                if href and not href.startswith('http'):
                                    href = f"https://www.europelanguagejobs.com{href}"
                                job = JobPosting(
                                    company="Europe Language Jobs",
                                    title=title_elem.get_text(strip=True),
                                    location="Spain",
                                    url=href or url,
                                    source="Europe Language Jobs"
                                )
                                jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error fetching {url}: {e}")

        except Exception as e:
            logger.warning(f"Web fetch failed: {e}")

        return jobs

    def _get_known_openings(self) -> List[JobPosting]:
        known = [
            JobPosting(
                company="Criteo",
                title="Account Strategist MEA - Arabic Speaker",
                location="Barcelona, Spain",
                url="https://jobs.omegavp.com/companies/criteo/jobs/50011127-account-strategist-mea-arabic-speaker",
                industry="AdTech",
                source="Manual Research"
            ),
            JobPosting(
                company="Amadeus",
                title="Customer Success Manager (Arabic Speaker)",
                location="Barcelona, Spain",
                url="https://builtin.com/job/customer-success-manager/9300496",
                industry="Travel Tech",
                source="Manual Research"
            ),
            JobPosting(
                company="Celonis",
                title="Enterprise Business Development Representative (German + Arabic)",
                location="Madrid, Spain",
                url="https://es.expertini.com/job/enterprise-business-development-representative-german-arabic-speaker-madrid-celonis-36-13002512/",
                industry="SaaS/Process Intelligence",
                source="Manual Research"
            ),
            JobPosting(
                company="Salesforce",
                title="Account Executive - EMEA",
                location="Madrid, Spain",
                url="https://www.salesforce.com/company/careers/locations/emea/spain/",
                industry="SaaS/CRM",
                source="Manual Research"
            ),
            JobPosting(
                company="SAP",
                title="Territory Ecosystem Manager - Southern Africa",
                location="Barcelona, Spain",
                url="https://jobs.sap.com/go/Spain/9008801/",
                industry="Enterprise Software",
                source="Manual Research"
            ),
            JobPosting(
                company="Oracle",
                title="Senior Customer Success Manager - EMEA",
                location="Spain",
                url="https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch",
                industry="Enterprise Software",
                source="Manual Research"
            ),
            JobPosting(
                company="Datadog",
                title="Sales Development Representative - EMEA",
                location="Madrid, Spain",
                url="https://careers.datadoghq.com/madrid/",
                industry="SaaS/Observability",
                source="Manual Research"
            ),
            JobPosting(
                company="Palo Alto Networks",
                title="Territory Account Manager - Spain",
                location="Barcelona, Spain",
                url="https://jobs.paloaltonetworks.com/en/location/spain-jobs/",
                industry="Cybersecurity",
                source="Manual Research"
            ),
            JobPosting(
                company="Accenture",
                title="Management Consulting - MENA",
                location="Spain / MENA",
                url="https://www.accenture.com/us-en/careers",
                industry="Consulting",
                source="Manual Research"
            ),
            JobPosting(
                company="Glovo",
                title="Sr. People Business Partner - North Africa",
                location="Casablanca, Morocco (HQ: Barcelona)",
                url="https://careers.glovoapp.com/job/sr-people-business-partner-north-africa-morocco-tunisia-in-casablanca-jid-744000121754027/",
                industry="Marketplace Tech",
                source="Manual Research"
            ),
        ]
        logger.info(f"Known openings loaded: {len(known)}")
        return known


# ============== RESULTS MANAGER ==============

class ResultsManager:
    def __init__(self, output_dir: str = "./results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def save_json(self, scored_jobs: List[ScoredJob], filename: str = None):
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
        logger.info(f"Saved JSON to {filepath}")
        return filepath

    def save_csv(self, scored_jobs: List[ScoredJob], filename: str = None):
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
                    sj.job.company, sj.job.title, sj.job.location, sj.match_score,
                    "Yes" if sj.arabic_required else "No",
                    "Yes" if sj.french_required else "No",
                    "Yes" if sj.mena_focus else "No",
                    sj.sponsorship_likelihood, sj.recommendation, sj.job.url
                ])
        logger.info(f"Saved CSV to {filepath}")
        return filepath

    def generate_report(self, scored_jobs: List[ScoredJob]) -> str:
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

        high = [sj for sj in scored_jobs if sj.recommendation == "HIGH PRIORITY"]
        for sj in high:
            lines.extend([
                "",
                f"Company: {sj.job.company}",
                f"Role: {sj.job.title}",
                f"Location: {sj.job.location}",
                f"Match Score: {sj.match_score}/100",
                f"Arabic: {'Yes' if sj.arabic_required else 'No'} | French: {'Yes' if sj.french_required else 'No'}",
                f"Sponsorship: {sj.sponsorship_likelihood}",
                f"URL: {sj.job.url}",
                f"Reasons: {'; '.join(sj.reasons)}",
            ])

        lines.extend(["", "APPLY ROLES (Score 70-84)", "-" * 70])
        for sj in [j for j in scored_jobs if j.recommendation == "Apply"]:
            lines.append(f"  {sj.job.company} | {sj.job.title} | Score: {sj.match_score} | {sj.job.location}")

        lines.extend(["", "MONITOR ROLES (Score 60-69)", "-" * 70])
        for sj in [j for j in scored_jobs if j.recommendation == "Monitor"]:
            lines.append(f"  {sj.job.company} | {sj.job.title} | Score: {sj.match_score}")

        lines.extend(["", "SKIP ROLES (Score < 60)", "-" * 70])
        for sj in [j for j in scored_jobs if j.recommendation == "Skip"]:
            lines.append(f"  {sj.job.company} | {sj.job.title} | Score: {sj.match_score}")

        return "\n".join(lines)

    def save_report(self, report: str):
        filepath = self.output_dir / f"report_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(filepath, 'w') as f:
            f.write(report)
        logger.info(f"Saved report to {filepath}")
        return filepath


# ============== MAIN ORCHESTRATOR ==============

class JobMonitor:
    def __init__(self):
        self.fetcher = JobFetcher()
        self.scorer = JobScorer()
        self.history = JobHistory()
        self.results = ResultsManager()

    def run(self):
        logger.info("=" * 70)
        logger.info("Starting MENA Job Monitor")
        logger.info("=" * 70)

        raw_jobs = self.fetcher.fetch_all()
        logger.info(f"Raw jobs fetched: {len(raw_jobs)}")

        new_jobs = [j for j in raw_jobs if not self.history.has_seen(j.job_id)]
        logger.info(f"New jobs after dedup: {len(new_jobs)}")

        scored_jobs = []
        for job in new_jobs:
            scored = self.scorer.score(job)
            scored_jobs.append(scored)
            self.history.mark_seen(job.job_id, asdict(job))

        scored_jobs.sort(key=lambda x: x.match_score, reverse=True)

        threshold = SCORING["min_score_threshold"]
        filtered = [sj for sj in scored_jobs if sj.match_score >= threshold]

        self.results.save_json(filtered)
        self.results.save_csv(filtered)

        report = self.results.generate_report(filtered)
        self.results.save_report(report)

        self.history.cleanup_old(30)
        self.history.save()

        print("\n" + "=" * 70)
        print("MONITORING COMPLETE")
        print("=" * 70)
        print(f"Jobs meeting threshold (>= {threshold}): {len(filtered)}")
        print(f"  HIGH PRIORITY: {len([j for j in filtered if j.recommendation == 'HIGH PRIORITY'])}")
        print(f"  Apply: {len([j for j in filtered if j.recommendation == 'Apply'])}")
        print(f"  Monitor: {len([j for j in filtered if j.recommendation == 'Monitor'])}")
        print(f"  Skip: {len([j for j in filtered if j.recommendation == 'Skip'])}")
        print("=" * 70)

        return filtered


def main():
    monitor = JobMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
