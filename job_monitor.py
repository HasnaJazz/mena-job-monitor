#!/usr/bin/env python3
"""
MENA Job Monitor - Known Openings Only
No web scraping - runs instantly on GitHub Actions
"""

import json
import csv
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

# ============== DATA MODELS ==============

@dataclass
class JobPosting:
    company: str
    title: str
    location: str
    url: str
    description: str = ""
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
    reasons: list


# ============== CONFIG ==============

SCORING = {
    "arabic_bonus": 15, "french_bonus": 10, "mena_bonus": 15,
    "mba_bonus": 10, "spain_location_bonus": 10,
    "intern_penalty": -30, "spanish_required_penalty": -20,
    "entry_level_penalty": -15,
    "sponsorship_high_bonus": 10, "sponsorship_low_penalty": -10,
    "min_score_threshold": 60
}

COMPANIES = {
    "Salesforce": "High", "Celonis": "Medium", "Criteo": "High",
    "Google": "High", "Microsoft": "High", "SAP": "High",
    "Oracle": "High", "Amadeus": "High", "ServiceNow": "Medium",
    "HubSpot": "Low", "Datadog": "Medium", "Palo Alto Networks": "Medium",
    "Snowflake": "Medium", "MongoDB": "Medium", "Elastic": "Medium",
    "Glovo": "Medium", "Adobe": "Medium", "Cisco": "High",
    "Accenture": "High", "Deloitte": "High", "PwC": "High",
    "Capgemini": "High", "Airbus": "High", "Schneider Electric": "High",
    "Mercedes-Benz": "Medium", "SEAT/CUPRA": "Medium"
}

POSITIVE_KWS = ["MENA", "Middle East", "North Africa", "MEA", "Africa", "Arabic",
    "EMEA", "international", "regional", "global", "expansion",
    "business development", "account executive", "customer success",
    "partner manager", "growth", "strategic", "regional marketing",
    "go-to-market", "channel", "market development"]

# ============== KNOWN OPENINGS ==============

KNOWN_JOBS = [
    {"company": "Criteo", "title": "Account Strategist MEA - Arabic Speaker",
     "location": "Barcelona, Spain", "url": "https://jobs.omegavp.com/companies/criteo/jobs/50011127-account-strategist-mea-arabic-speaker",
     "industry": "AdTech"},
    {"company": "Amadeus", "title": "Customer Success Manager (Arabic Speaker)",
     "location": "Barcelona, Spain", "url": "https://builtin.com/job/customer-success-manager/9300496",
     "industry": "Travel Tech"},
    {"company": "Celonis", "title": "Enterprise Business Development Representative (German + Arabic)",
     "location": "Madrid, Spain", "url": "https://es.expertini.com/job/enterprise-business-development-representative-german-arabic-speaker-madrid-celonis-36-13002512/",
     "industry": "SaaS/Process Intelligence"},
    {"company": "Salesforce", "title": "Account Executive - EMEA",
     "location": "Madrid, Spain", "url": "https://www.salesforce.com/company/careers/locations/emea/spain/",
     "industry": "SaaS/CRM"},
    {"company": "SAP", "title": "Territory Ecosystem Manager - Southern Africa",
     "location": "Barcelona, Spain", "url": "https://jobs.sap.com/go/Spain/9008801/",
     "industry": "Enterprise Software"},
    {"company": "Oracle", "title": "Senior Customer Success Manager - EMEA",
     "location": "Spain", "url": "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch",
     "industry": "Enterprise Software"},
    {"company": "Datadog", "title": "Sales Development Representative - EMEA",
     "location": "Madrid, Spain", "url": "https://careers.datadoghq.com/madrid/",
     "industry": "SaaS/Observability"},
    {"company": "Palo Alto Networks", "title": "Territory Account Manager - Spain",
     "location": "Barcelona, Spain", "url": "https://jobs.paloaltonetworks.com/en/location/spain-jobs/",
     "industry": "Cybersecurity"},
    {"company": "Accenture", "title": "Management Consulting - MENA",
     "location": "Spain / MENA", "url": "https://www.accenture.com/us-en/careers",
     "industry": "Consulting"},
    {"company": "Glovo", "title": "Sr. People Business Partner - North Africa",
     "location": "Casablanca, Morocco (HQ: Barcelona)", "url": "https://careers.glovoapp.com/job/sr-people-business-partner-north-africa-morocco-tunisia-in-casablanca-jid-744000121754027/",
     "industry": "Marketplace Tech"},
    {"company": "Microsoft", "title": "Business Development Manager - MENA",
     "location": "Madrid, Spain", "url": "https://careers.microsoft.com/us/en/locations/spain",
     "industry": "Cloud/SaaS"},
    {"company": "Google", "title": "Growth Manager - Middle East",
     "location": "Barcelona, Spain", "url": "https://careers.google.com/jobs/",
     "industry": "Technology"},
    {"company": "ServiceNow", "title": "Enterprise Sales - EMEA",
     "location": "Spain", "url": "https://careers.servicenow.com/",
     "industry": "SaaS/Enterprise"},
    {"company": "Snowflake", "title": "Solutions Architect - EMEA North",
     "location": "Remote, Spain", "url": "https://careers.snowflake.com/us/en/",
     "industry": "SaaS/Data Cloud"},
    {"company": "Cisco", "title": "Account Manager - Saudi Arabia",
     "location": "Saudi Arabia / EMEA", "url": "https://careers.cisco.com/",
     "industry": "Technology/Networking"},
]


# ============== SCORER ==============

def score_job(job: JobPosting) -> ScoredJob:
    score = 50
    reasons = []
    arabic = False
    french = False
    mena = False

    text = f"{job.title} {job.location}".lower()

    if any(kw.lower() in text for kw in ["arabic", "arabic speaker", "arabic-speaking"]):
        score += SCORING["arabic_bonus"]
        arabic = True
        reasons.append("Arabic required (+15)")

    if any(kw.lower() in text for kw in ["french", "francophone"]):
        score += SCORING["french_bonus"]
        french = True
        reasons.append("French required (+10)")

    if any(kw.lower() in text for kw in POSITIVE_KWS):
        score += SCORING["mena_bonus"]
        mena = True
        reasons.append("MENA/EMEA focus (+15)")

    if "mba" in text or "master" in text:
        score += SCORING["mba_bonus"]
        reasons.append("MBA level (+10)")

    if any(loc in job.location.lower() for loc in ["spain", "barcelona", "madrid"]):
        score += SCORING["spain_location_bonus"]
        reasons.append("Spain-based (+10)")

    if any(kw in text for kw in ["intern", "internship", "student"]):
        score += SCORING["intern_penalty"]
        reasons.append("Intern (-30)")

    if any(kw in text for kw in ["fluent spanish", "native spanish", "spanish mandatory"]):
        score += SCORING["spanish_required_penalty"]
        reasons.append("Spanish required (-20)")

    if any(kw in text for kw in ["entry level", "junior", "0-1 years"]):
        score += SCORING["entry_level_penalty"]
        reasons.append("Entry-level (-15)")

    sponsorship = COMPANIES.get(job.company, "Medium")
    if sponsorship == "High":
        score += SCORING["sponsorship_high_bonus"]
        reasons.append("High sponsorship history (+10)")
    elif sponsorship == "Low":
        score += SCORING["sponsorship_low_penalty"]
        reasons.append("Low sponsorship history (-10)")

    score = max(0, min(100, score))

    if score >= 85:
        rec = "HIGH PRIORITY"
    elif score >= 70:
        rec = "Apply"
    elif score >= 60:
        rec = "Monitor"
    else:
        rec = "Skip"

    return ScoredJob(job=job, match_score=score, arabic_required=arabic,
                     french_required=french, mena_focus=mena,
                     sponsorship_likelihood=sponsorship, recommendation=rec, reasons=reasons)


# ============== HISTORY ==============

class JobHistory:
    def __init__(self, history_file="job_history.json"):
        self.history_file = Path(history_file)
        self.seen = self._load()

    def _load(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.seen, f, indent=2)

    def has_seen(self, job_id):
        return job_id in self.seen

    def mark_seen(self, job_id, data):
        self.seen[job_id] = {"first_seen": datetime.now().isoformat(), "data": data}


# ============== RESULTS ==============

def save_results(scored_jobs, output_dir="./results"):
    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    # JSON
    data = []
    for sj in scored_jobs:
        data.append({
            "job_id": sj.job.job_id, "company": sj.job.company, "title": sj.job.title,
            "location": sj.job.location, "url": sj.job.url, "industry": sj.job.industry,
            "match_score": sj.match_score, "arabic_required": sj.arabic_required,
            "french_required": sj.french_required, "mena_focus": sj.mena_focus,
            "sponsorship_likelihood": sj.sponsorship_likelihood,
            "recommendation": sj.recommendation, "reasons": sj.reasons,
            "source": sj.job.source, "scraped_at": datetime.now().isoformat()
        })
    with open(out / f"jobs_{ts}.json", 'w') as f:
        json.dump(data, f, indent=2)

    # CSV
    with open(out / f"jobs_{ts}.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Company", "Title", "Location", "Match Score", "Arabic Required",
            "French Required", "MENA Focus", "Sponsorship", "Recommendation", "URL"])
        for sj in scored_jobs:
            writer.writerow([sj.job.company, sj.job.title, sj.job.location, sj.match_score,
                "Yes" if sj.arabic_required else "No",
                "Yes" if sj.french_required else "No",
                "Yes" if sj.mena_focus else "No",
                sj.sponsorship_likelihood, sj.recommendation, sj.job.url])

    # Report
    lines = ["=" * 70, "MENA JOB MONITOR - DAILY REPORT", "=" * 70,
             f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"Total jobs analyzed: {len(scored_jobs)}", "",
             "HIGH PRIORITY ROLES (Score >= 85)", "-" * 70]

    for sj in scored_jobs:
        if sj.recommendation == "HIGH PRIORITY":
            lines.extend(["", f"Company: {sj.job.company}", f"Role: {sj.job.title}",
                f"Location: {sj.job.location}", f"Match Score: {sj.match_score}/100",
                f"Arabic: {'Yes' if sj.arabic_required else 'No'} | French: {'Yes' if sj.french_required else 'No'}",
                f"Sponsorship: {sj.sponsorship_likelihood}", f"URL: {sj.job.url}",
                f"Reasons: {'; '.join(sj.reasons)}"])

    lines.extend(["", "APPLY ROLES (Score 70-84)", "-" * 70])
    for sj in scored_jobs:
        if sj.recommendation == "Apply":
            lines.append(f"  {sj.job.company} | {sj.job.title} | Score: {sj.match_score} | {sj.job.location}")

    lines.extend(["", "MONITOR ROLES (Score 60-69)", "-" * 70])
    for sj in scored_jobs:
        if sj.recommendation == "Monitor":
            lines.append(f"  {sj.job.company} | {sj.job.title} | Score: {sj.match_score}")

    report_text = "\n".join(lines)
    with open(out / f"report_{datetime.now().strftime('%Y%m%d')}.txt", 'w') as f:
        f.write(report_text)

    print("\n" + report_text)
    return out


# ============== MAIN ==============

def main():
    print("=" * 70)
    print("MENA JOB MONITOR - Starting")
    print("=" * 70)

    # Load known jobs
    jobs = [JobPosting(**j, source="Known Openings") for j in KNOWN_JOBS]
    print(f"Loaded {len(jobs)} known openings")

    # Filter duplicates
    history = JobHistory()
    new_jobs = [j for j in jobs if not history.has_seen(j.job_id)]
    print(f"New jobs: {len(new_jobs)}")

    # Score
    scored = [score_job(j) for j in new_jobs]
    scored.sort(key=lambda x: x.match_score, reverse=True)

    # Filter threshold
    threshold = SCORING["min_score_threshold"]
    filtered = [sj for sj in scored if sj.match_score >= threshold]

    # Mark as seen
    for sj in filtered:
        history.mark_seen(sj.job.job_id, asdict(sj.job))
    history.save()

    # Save
    save_results(filtered)

    print("\n" + "=" * 70)
    print("MONITORING COMPLETE")
    print("=" * 70)
    print(f"Jobs meeting threshold (>= {threshold}): {len(filtered)}")
    print(f"  HIGH PRIORITY: {len([j for j in filtered if j.recommendation == 'HIGH PRIORITY'])}")
    print(f"  Apply: {len([j for j in filtered if j.recommendation == 'Apply'])}")
    print(f"  Monitor: {len([j for j in filtered if j.recommendation == 'Monitor'])}")
    print("=" * 70)


if __name__ == "__main__":
    main()
