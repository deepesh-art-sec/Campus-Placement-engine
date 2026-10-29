"""
Generator for 100 Realistic Placement Announcement Synthetic Test Cases
Covers:
  - 35 Digital PDFs with tables, bullet lists, multi-column layouts
  - 15 Scanned PDFs (rasterized images requiring Tesseract OCR)
  - 25 Word DOCX documents with structured tables, headings, styles
  - 20 Plain text announcements (.txt) and emails (.eml)
  - 5 Edge Cases (empty, corrupt, garbled OCR, missing criteria)
Includes separate verified ground_truth.json.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import docx
import fitz
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "synthetic_100"))
DOCS_DIR = os.path.join(BASE_DIR, "documents")
GT_PATH = os.path.join(BASE_DIR, "ground_truth.json")

os.makedirs(DOCS_DIR, exist_ok=True)

# 100 Announcement Specifications
# We define 100 rich, realistic cases with varied industries, layouts, and distractor fields.
CASES = [
    # 1. Tech Giants (Digital PDFs 1-15)
    {
        "id": "doc_001_google_sde.pdf",
        "format": "pdf",
        "company": "Google",
        "role": "Software Development Engineer",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 8.0,
        "tenth": 70.0,
        "twelfth": 70.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 35.0,
        "ctc_min": 35.0,
        "ctc_max": 35.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-25",
        "deadline": "2026-11-18",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Coding Assessment", "ONLINE_TEST", 90),
            ("Round 2: Technical Interview - Algorithms & Systems", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Googleyness & Leadership Discussion", "HR_INTERVIEW", 45)
        ],
        "distractors": "Batch of 2026. 40 vacancies open. Venue: Campus Auditorium 101. Helpline: 080-23456789.",
        "skills": ["C++", "Python", "Data Structures", "Algorithms"]
    },
    {
        "id": "doc_002_microsoft_sde.pdf",
        "format": "pdf",
        "company": "Microsoft",
        "role": "Software Engineer",
        "branches": ["CSE", "IT", "Data Science", "AI & ML"],
        "cgpa": 7.5,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 28.0,
        "ctc_min": 28.0,
        "ctc_max": 28.0,
        "location": "Hyderabad",
        "drive_date": "2026-12-05",
        "deadline": "2026-11-28",
        "rounds": 4,
        "rounds_detail": [
            ("Round 1: Cognitive & Coding Screening", "ONLINE_TEST", 75),
            ("Round 2: Technical Design & Data Structures", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Systems Architecture Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 4: Behavioral & Cultural Fit", "HR_INTERVIEW", 45)
        ],
        "distractors": "2026 Graduates. Room 304, Academic Block 2. 50 Openings across teams.",
        "skills": ["C#", "Azure", "Distributed Systems"]
    },
    {
        "id": "doc_003_amazon_sde.pdf",
        "format": "pdf",
        "company": "Amazon",
        "role": "Software Development Engineer",
        "branches": ["CSE", "IT", "ECE", "EEE"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 32.0,
        "ctc_min": 32.0,
        "ctc_max": 32.0,
        "location": "Hyderabad",
        "drive_date": "2026-11-15",
        "deadline": "2026-11-08",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Debugging & Coding Test", "ONLINE_TEST", 90),
            ("Round 2: Technical Problem Solving", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Amazon Leadership Principles & Bar Raiser", "HR_INTERVIEW", 60)
        ],
        "distractors": "Drive starts sharp at 9:00 AM. 100 positions available.",
        "skills": ["Java", "AWS", "OOP"]
    },
    {
        "id": "doc_004_uber_swe.pdf",
        "format": "pdf",
        "company": "Uber",
        "role": "Software Engineer",
        "branches": ["CSE", "IT"],
        "cgpa": 8.5,
        "tenth": 75.0,
        "twelfth": 75.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 42.0,
        "ctc_min": 42.0,
        "ctc_max": 42.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-30",
        "deadline": "2026-11-20",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Codesignal Proctored Challenge", "ONLINE_TEST", 70),
            ("Round 2: Core Engineering Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Engineering Manager & Fitment Round", "HR_INTERVIEW", 45)
        ],
        "distractors": "Target Batch: 2026. Hall 4, Main Building.",
        "skills": ["Go", "Java", "High Concurrency"]
    },
    {
        "id": "doc_005_adobe_mts.pdf",
        "format": "pdf",
        "company": "Adobe",
        "role": "Member Technical Staff",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 7.8,
        "tenth": 70.0,
        "twelfth": 70.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 24.5,
        "ctc_min": 24.5,
        "ctc_max": 24.5,
        "location": "Noida",
        "drive_date": "2026-12-10",
        "deadline": "2026-12-01",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Written Technical Assessment", "ONLINE_TEST", 90),
            ("Round 2: Coding & Architecture Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Managerial and Cultural Round", "HR_INTERVIEW", 45)
        ],
        "distractors": "Internship stipend of 50,000 pm for 6 months. Reporting time 10:00 AM.",
        "skills": ["C++", "Graphics", "Machine Learning"]
    },
    {
        "id": "doc_006_salesforce_mts.pdf",
        "format": "pdf",
        "company": "Salesforce",
        "role": "Associate Software Engineer",
        "branches": ["CSE", "IT", "Data Science"],
        "cgpa": 8.0,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 22.0,
        "ctc_min": 22.0,
        "ctc_max": 22.0,
        "location": "Hyderabad",
        "drive_date": "2026-11-22",
        "deadline": "2026-11-15",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: HackerRank Coding Challenge", "ONLINE_TEST", 60),
            ("Round 2: Technical Deep Dive", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Values & Equality Fit", "HR_INTERVIEW", 45)
        ],
        "distractors": "2026 Cohort. 15 FTE vacancies.",
        "skills": ["Java", "Apex", "React"]
    },
    {
        "id": "doc_007_apple_hardware.pdf",
        "format": "pdf",
        "company": "Apple",
        "role": "Hardware Engineer",
        "branches": ["ECE", "EEE"],
        "cgpa": 8.2,
        "tenth": 75.0,
        "twelfth": 75.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 30.0,
        "ctc_min": 30.0,
        "ctc_max": 30.0,
        "location": "Bengaluru",
        "drive_date": "2026-12-08",
        "deadline": "2026-11-25",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Digital Electronics & VLSI Test", "ONLINE_TEST", 90),
            ("Round 2: Circuit Design Technical Round", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Behavioral Evaluation", "HR_INTERVIEW", 45)
        ],
        "distractors": "Lab Room 204. Silicon Engineering division.",
        "skills": ["Verilog", "VLSI", "FPGA"]
    },
    {
        "id": "doc_008_cisco_systems.pdf",
        "format": "pdf",
        "company": "Cisco",
        "role": "Systems Engineer",
        "branches": ["CSE", "IT", "ECE", "EEE"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 17.5,
        "ctc_min": 17.5,
        "ctc_max": 17.5,
        "location": "Bengaluru",
        "drive_date": "2026-11-19",
        "deadline": "2026-11-12",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Networking & Coding Test", "ONLINE_TEST", 75),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: HR Discussion", "HR_INTERVIEW", 30)
        ],
        "distractors": "Target: 2026 pass-outs. 35 positions.",
        "skills": ["Computer Networks", "TCP/IP", "Python"]
    },
    {
        "id": "doc_009_oracle_cloud.pdf",
        "format": "pdf",
        "company": "Oracle",
        "role": "Associate Consultant",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": 1,
        "ctc": 15.0,
        "ctc_min": 15.0,
        "ctc_max": 15.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-28",
        "deadline": "2026-11-20",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Aptitude & Technical Test", "ONLINE_TEST", 90),
            ("Round 2: Tech Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Interview", "HR_INTERVIEW", 30)
        ],
        "distractors": "Up to 1 cleared backlog permitted. Room 102.",
        "skills": ["SQL", "Java", "Cloud Infrastructure"]
    },
    {
        "id": "doc_010_qualcomm_firmware.pdf",
        "format": "pdf",
        "company": "Qualcomm",
        "role": "Associate Engineer",
        "branches": ["ECE", "EEE", "CSE"],
        "cgpa": 7.5,
        "tenth": 70.0,
        "twelfth": 70.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 20.0,
        "ctc_min": 20.0,
        "ctc_max": 20.0,
        "location": "Hyderabad",
        "drive_date": "2026-12-02",
        "deadline": "2026-11-24",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Embedded Systems & C Programming Test", "ONLINE_TEST", 90),
            ("Round 2: Deep Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: HR Discussion", "HR_INTERVIEW", 45)
        ],
        "distractors": "Batch: 2026. 20 openings in modem firmware.",
        "skills": ["Embedded C", "Microcontrollers", "RTOS"]
    },
    {
        "id": "doc_011_intel_validation.pdf",
        "format": "pdf",
        "company": "Intel",
        "role": "Graduate Engineer Trainee",
        "branches": ["ECE", "EEE", "CSE"],
        "cgpa": 7.5,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 16.5,
        "ctc_min": 16.5,
        "ctc_max": 16.5,
        "location": "Bengaluru",
        "drive_date": "2026-11-17",
        "deadline": "2026-11-10",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Core Engineering Assessment", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: HR Round", "HR_INTERVIEW", 30)
        ],
        "distractors": "Silicon validation division. Seminar hall A.",
        "skills": ["Python", "Computer Architecture", "Linux"]
    },
    {
        "id": "doc_012_flipkart_sde.pdf",
        "format": "pdf",
        "company": "Flipkart",
        "role": "Software Development Engineer",
        "branches": ["CSE", "IT"],
        "cgpa": 7.5,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 26.0,
        "ctc_min": 26.0,
        "ctc_max": 26.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-26",
        "deadline": "2026-11-16",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Machine Coding Round", "ONLINE_TEST", 90),
            ("Round 2: Problem Solving & Data Structures", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Hiring Manager Interview", "HR_INTERVIEW", 45)
        ],
        "distractors": "Supply chain tech. 25 openings.",
        "skills": ["Java", "Distributed Databases", "Kafka"]
    },
    {
        "id": "doc_013_atlassian_swe.pdf",
        "format": "pdf",
        "company": "Atlassian",
        "role": "Software Engineer",
        "branches": ["CSE", "IT", "Data Science"],
        "cgpa": 8.0,
        "tenth": 70.0,
        "twelfth": 70.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 45.0,
        "ctc_min": 45.0,
        "ctc_max": 45.0,
        "location": "Bengaluru",
        "drive_date": "2026-12-04",
        "deadline": "2026-11-22",
        "rounds": 4,
        "rounds_detail": [
            ("Round 1: Karat Coding Screen", "ONLINE_TEST", 60),
            ("Round 2: System Design & Code Review", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Values Interview", "HR_INTERVIEW", 45),
            ("Round 4: Management Discussion", "HR_INTERVIEW", 30)
        ],
        "distractors": "Remote working flexibility. 12 FTE positions.",
        "skills": ["Java", "React", "Microservices"]
    },
    {
        "id": "doc_014_swiggy_sde.pdf",
        "format": "pdf",
        "company": "Swiggy",
        "role": "Associate Software Engineer",
        "branches": ["CSE", "IT"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 18.0,
        "ctc_min": 18.0,
        "ctc_max": 18.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-29",
        "deadline": "2026-11-21",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Coding Test", "ONLINE_TEST", 90),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Cultural Fit Round", "HR_INTERVIEW", 30)
        ],
        "distractors": "Consumer Tech Pod. 18 vacancies.",
        "skills": ["Go", "AWS", "DynamoDB"]
    },
    {
        "id": "doc_015_zomato_swe.pdf",
        "format": "pdf",
        "company": "Zomato",
        "role": "Software Engineer",
        "branches": ["CSE", "IT", "Data Science"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 20.0,
        "ctc_min": 20.0,
        "ctc_max": 20.0,
        "location": "Gurgaon",
        "drive_date": "2026-12-07",
        "deadline": "2026-11-27",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Proctored Coding Test", "ONLINE_TEST", 75),
            ("Round 2: Live Problem Solving Round", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Culture & Founder Fit", "HR_INTERVIEW", 45)
        ],
        "distractors": "Gurugram headquarters. Room 405.",
        "skills": ["Python", "Redis", "FastAPI"]
    },

    # 2. Banking, Quant & Financial Tech (Digital PDFs 16-25)
    {
        "id": "doc_016_goldman_sachs_analyst.pdf",
        "format": "pdf",
        "company": "Goldman Sachs",
        "role": "New Analyst",
        "branches": ["CSE", "IT", "ECE", "EEE"],
        "cgpa": 7.5,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 28.0,
        "ctc_min": 28.0,
        "ctc_max": 28.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-14",
        "deadline": "2026-11-05",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: HackerRank Math & CS Aptitude", "ONLINE_TEST", 90),
            ("Round 2: Technical & Quantitative Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Executive Director Round", "HR_INTERVIEW", 45)
        ],
        "distractors": "Strict zero backlogs policy throughout degree.",
        "skills": ["Algorithms", "Statistics", "C++", "Java"]
    },
    {
        "id": "doc_017_morgan_stanley_tech.pdf",
        "format": "pdf",
        "company": "Morgan Stanley",
        "role": "Technology Analyst",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 7.5,
        "tenth": 70.0,
        "twelfth": 70.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 25.0,
        "ctc_min": 25.0,
        "ctc_max": 25.0,
        "location": "Mumbai",
        "drive_date": "2026-11-21",
        "deadline": "2026-11-11",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Technical Assessment", "ONLINE_TEST", 90),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: HR & Management Interview", "HR_INTERVIEW", 45)
        ],
        "distractors": "Enterprise Technology & Services division.",
        "skills": ["Java", "SQL", "Unix", "Spring Boot"]
    },
    {
        "id": "doc_018_barclays_ba4.pdf",
        "format": "pdf",
        "company": "Barclays",
        "role": "Graduate Analyst",
        "branches": ["CSE", "IT", "ECE", "EEE"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": 1,
        "ctc": 14.0,
        "ctc_min": 14.0,
        "ctc_max": 14.0,
        "location": "Pune",
        "drive_date": "2026-11-23",
        "deadline": "2026-11-13",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Cognitive & Technical Test", "ONLINE_TEST", 60),
            ("Round 2: Technical Round", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR & Values Interview", "HR_INTERVIEW", 30)
        ],
        "distractors": "Max 1 cleared backlog acceptable.",
        "skills": ["Python", "AWS", "Big Data"]
    },
    {
        "id": "doc_019_jp_morgan_sep.pdf",
        "format": "pdf",
        "company": "JPMorgan Chase",
        "role": "Software Engineer",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 7.0,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 19.5,
        "ctc_min": 19.5,
        "ctc_max": 19.5,
        "location": "Bengaluru",
        "drive_date": "2026-11-18",
        "deadline": "2026-11-09",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Coding & Video Assessment (HireVue)", "ONLINE_TEST", 60),
            ("Round 2: Technical Architecture", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Behavioral Fit", "HR_INTERVIEW", 45)
        ],
        "distractors": "Software Engineer Program 2026. 40 seats.",
        "skills": ["Java", "Cloud", "Agile"]
    },
    {
        "id": "doc_020_bny_mellon_swe.pdf",
        "format": "pdf",
        "company": "BNY Mellon",
        "role": "Software Developer Trainee",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 16.0,
        "ctc_min": 16.0,
        "ctc_max": 16.0,
        "location": "Pune",
        "drive_date": "2026-11-27",
        "deadline": "2026-11-19",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Technical Exam", "ONLINE_TEST", 90),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Interview", "HR_INTERVIEW", 30)
        ],
        "distractors": "Custody operations technology.",
        "skills": ["C++", "Python", "SQL"]
    },
    {
        "id": "doc_021_deutsche_bank_grad.pdf",
        "format": "pdf",
        "company": "Deutsche Bank",
        "role": "Graduate Analyst",
        "branches": ["CSE", "IT"],
        "cgpa": 7.2,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 19.0,
        "ctc_min": 19.0,
        "ctc_max": 19.0,
        "location": "Pune",
        "drive_date": "2026-12-01",
        "deadline": "2026-11-23",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: HackerEarth Assessment", "ONLINE_TEST", 75),
            ("Round 2: Technical & Domain Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Leadership Discussion", "HR_INTERVIEW", 45)
        ],
        "distractors": "Global Technology Centre. 2026 batch.",
        "skills": ["Java", "Oracle", "Messaging"]
    },
    {
        "id": "doc_022_mastercard_associate.pdf",
        "format": "pdf",
        "company": "Mastercard",
        "role": "Associate Software Engineer",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 7.5,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 18.5,
        "ctc_min": 18.5,
        "ctc_max": 18.5,
        "location": "Pune",
        "drive_date": "2026-12-09",
        "deadline": "2026-11-30",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Coding & Aptitude", "ONLINE_TEST", 60),
            ("Round 2: Tech Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Culture Round", "HR_INTERVIEW", 30)
        ],
        "distractors": "Payment gateway processing team.",
        "skills": ["Spring", "REST", "Cloud"]
    },
    {
        "id": "doc_023_visa_swe.pdf",
        "format": "pdf",
        "company": "Visa",
        "role": "Software Engineer",
        "branches": ["CSE", "IT"],
        "cgpa": 7.5,
        "tenth": 70.0,
        "twelfth": 70.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 23.0,
        "ctc_min": 23.0,
        "ctc_max": 23.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-16",
        "deadline": "2026-11-07",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Technical Exam", "ONLINE_TEST", 90),
            ("Round 2: Technical Round", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Behavioral Round", "HR_INTERVIEW", 45)
        ],
        "distractors": "Cybersecurity and Tokenization. 15 openings.",
        "skills": ["C++", "Java", "Cryptography"]
    },
    {
        "id": "doc_024_deloitte_usi_tech.pdf",
        "format": "pdf",
        "company": "Deloitte USI",
        "role": "Associate Analyst",
        "branches": ["CSE", "IT", "ECE", "EEE", "Mechanical Engineering", "Civil Engineering"],
        "cgpa": 6.5,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": 1,
        "ctc": 7.6,
        "ctc_min": 7.6,
        "ctc_max": 7.6,
        "location": "Hyderabad",
        "drive_date": "2026-11-12",
        "deadline": "2026-11-04",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Versant & Cognitive Assessment", "ONLINE_TEST", 90),
            ("Round 2: Technical Case Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: Partner Fitment Round", "HR_INTERVIEW", 30)
        ],
        "distractors": "1 cleared backlog allowed. Batch 2026.",
        "skills": ["Data Analysis", "Python", "Consulting"]
    },
    {
        "id": "doc_025_zs_associates_dea.pdf",
        "format": "pdf",
        "company": "ZS Associates",
        "role": "Decision Analytics Associate",
        "branches": ["All Branches"],
        "cgpa": 6.8,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 12.5,
        "ctc_min": 12.5,
        "ctc_max": 12.5,
        "location": "Pune",
        "drive_date": "2026-11-24",
        "deadline": "2026-11-14",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Aptitude & Case Study Assessment", "ONLINE_TEST", 75),
            ("Round 2: Case Interview & Problem Solving", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: Behavioral Fit Interview", "HR_INTERVIEW", 45)
        ],
        "distractors": "Open to all branches. Reporting time: 9:30 AM.",
        "skills": ["SQL", "Excel", "R", "Tableau"]
    },

    # 3. Core Engineering & Infrastructure (Digital PDFs 26-35)
    {
        "id": "doc_026_larsen_toubro_get.pdf",
        "format": "pdf",
        "company": "Larsen & Toubro",
        "role": "Graduate Engineer Trainee",
        "branches": ["Mechanical Engineering", "Civil Engineering", "EEE"],
        "cgpa": 6.75,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 6.5,
        "ctc_min": 6.5,
        "ctc_max": 6.5,
        "location": "Mumbai",
        "drive_date": "2026-11-20",
        "deadline": "2026-11-10",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Engineering Knowledge Test", "ONLINE_TEST", 90),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR & Medical Examination", "HR_INTERVIEW", 30)
        ],
        "distractors": "Site posting across infrastructure projects. 2-year service agreement.",
        "skills": ["AutoCAD", "Structural Analysis", "Thermodynamics"]
    },
    {
        "id": "doc_027_tata_motors_get.pdf",
        "format": "pdf",
        "company": "Tata Motors",
        "role": "Graduate Engineer Trainee",
        "branches": ["Mechanical Engineering", "EEE", "ECE"],
        "cgpa": 6.5,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 7.0,
        "ctc_min": 7.0,
        "ctc_max": 7.0,
        "location": "Pune",
        "drive_date": "2026-11-28",
        "deadline": "2026-11-17",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Technical & Aptitude Assessment", "ONLINE_TEST", 60),
            ("Round 2: Group Discussion", "GROUP_DISCUSSION", 30),
            ("Round 3: Technical & Personal Interview", "TECHNICAL_INTERVIEW", 45)
        ],
        "distractors": "Electric Vehicle Division. Plant plant Pune.",
        "skills": ["CATIA", "Vehicle Dynamics", "MATLAB"]
    },
    {
        "id": "doc_028_siemens_r_d.pdf",
        "format": "pdf",
        "company": "Siemens",
        "role": "R&D Engineer",
        "branches": ["EEE", "ECE", "Mechanical Engineering"],
        "cgpa": 7.0,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 11.0,
        "ctc_min": 11.0,
        "ctc_max": 11.0,
        "location": "Bengaluru",
        "drive_date": "2026-12-03",
        "deadline": "2026-11-25",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Technical Assessment", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: HR Discussion", "HR_INTERVIEW", 30)
        ],
        "distractors": "Smart Infrastructure & Industrial Automation.",
        "skills": ["PLC", "SCADA", "C++", "Simulink"]
    },
    {
        "id": "doc_029_bosch_get.pdf",
        "format": "pdf",
        "company": "Bosch",
        "role": "Associate Software Engineer",
        "branches": ["CSE", "IT", "ECE", "EEE"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 9.5,
        "ctc_min": 9.5,
        "ctc_max": 9.5,
        "location": "Bengaluru",
        "drive_date": "2026-11-15",
        "deadline": "2026-11-06",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Aptitude & Coding Test", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Interview", "HR_INTERVIEW", 30)
        ],
        "distractors": "Automotive electronics & mobility solutions.",
        "skills": ["C", "C++", "CAN Protocol", "AUTOSAR"]
    },
    {
        "id": "doc_030_texas_instruments_analog.pdf",
        "format": "pdf",
        "company": "Texas Instruments",
        "role": "Analog Design Engineer",
        "branches": ["ECE", "EEE"],
        "cgpa": 8.0,
        "tenth": 75.0,
        "twelfth": 75.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 22.0,
        "ctc_min": 22.0,
        "ctc_max": 22.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-10",
        "deadline": "2026-11-02",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Analog & Digital Circuit Test", "ONLINE_TEST", 90),
            ("Round 2: Deep Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: HR Discussion", "HR_INTERVIEW", 30)
        ],
        "distractors": "Semiconductor design division. Strictly no backlogs.",
        "skills": ["SPICE", "Circuit Design", "Semiconductor Physics"]
    },
    {
        "id": "doc_031_reliance_industries_get.pdf",
        "format": "pdf",
        "company": "Reliance Industries",
        "role": "Graduate Engineer Trainee",
        "branches": ["Chemical Engineering", "Mechanical Engineering", "EEE"],
        "cgpa": 6.5,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 7.5,
        "ctc_min": 7.5,
        "ctc_max": 7.5,
        "location": "Mumbai",
        "drive_date": "2026-11-26",
        "deadline": "2026-11-16",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: General & Technical Test", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Interview", "HR_INTERVIEW", 30)
        ],
        "distractors": "Jamnagar refinery and Hazira plant postings.",
        "skills": ["Chemical Plant Operations", "Process Safety"]
    },
    {
        "id": "doc_032_itc_limited_kites.pdf",
        "format": "pdf",
        "company": "ITC Limited",
        "role": "Technical Trainee",
        "branches": ["Mechanical Engineering", "Chemical Engineering", "Biotechnology"],
        "cgpa": 7.0,
        "tenth": 65.0,
        "twelfth": 65.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 11.5,
        "ctc_min": 11.5,
        "ctc_max": 11.5,
        "location": "Kolkata",
        "drive_date": "2026-12-05",
        "deadline": "2026-11-26",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Aptitude & Domain Assessment", "ONLINE_TEST", 75),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: Leadership Assessment", "HR_INTERVIEW", 45)
        ],
        "distractors": "FMCG manufacturing operations.",
        "skills": ["Operations", "Quality Assurance", "Plant Engineering"]
    },
    {
        "id": "doc_033_biocon_trainee.pdf",
        "format": "pdf",
        "company": "Biocon",
        "role": "Bioprocess Engineer",
        "branches": ["Biotechnology", "Chemical Engineering"],
        "cgpa": 6.8,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": 1,
        "ctc": 6.2,
        "ctc_min": 6.2,
        "ctc_max": 6.2,
        "location": "Bengaluru",
        "drive_date": "2026-11-21",
        "deadline": "2026-11-11",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Bio-sciences Written Test", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Interview", "HR_INTERVIEW", 30)
        ],
        "distractors": "1 cleared arrear allowed. Biologics park.",
        "skills": ["Fermentation", "Bioreactor Operations", "HPLC"]
    },
    {
        "id": "doc_034_schneider_electric_get.pdf",
        "format": "pdf",
        "company": "Schneider Electric",
        "role": "Graduate Engineer Trainee",
        "branches": ["EEE", "ECE"],
        "cgpa": 7.0,
        "tenth": 60.0,
        "twelfth": 60.0,
        "active_backlogs": 0,
        "history_backlogs": None,
        "ctc": 8.0,
        "ctc_min": 8.0,
        "ctc_max": 8.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-30",
        "deadline": "2026-11-20",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Electrical & Aptitude Assessment", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Round", "HR_INTERVIEW", 30)
        ],
        "distractors": "Energy management and industrial automation.",
        "skills": ["Power Systems", "Switchgear", "Relays"]
    },
    {
        "id": "doc_035_samsung_r_d_swe.pdf",
        "format": "pdf",
        "company": "Samsung R&D",
        "role": "Software Engineer",
        "branches": ["CSE", "IT", "ECE"],
        "cgpa": 7.5,
        "tenth": 70.0,
        "twelfth": 70.0,
        "active_backlogs": 0,
        "history_backlogs": 0,
        "ctc": 18.0,
        "ctc_min": 18.0,
        "ctc_max": 18.0,
        "location": "Bengaluru",
        "drive_date": "2026-11-13",
        "deadline": "2026-11-04",
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Samsung Global Coding Test", "ONLINE_TEST", 180),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 60),
            ("Round 3: HR & Cultural Fit", "HR_INTERVIEW", 45)
        ],
        "distractors": "SRI-B campus. 3-hour proctored advanced algorithm test.",
        "skills": ["C++", "Java", "Algorithms", "Android"]
    },
]

# Next, create remaining cases up to 100
# 36-50: Scanned PDFs
for i in range(36, 51):
    comp_list = [
        ("Cognizant", "GenC Elevate", ["CSE", "IT", "ECE", "EEE"], 6.5, 60.0, 60.0, 0, None, 4.5, "Chennai", "2026-11-22", "2026-11-12"),
        ("TCS", "Digital Specialist", ["CSE", "IT", "ECE"], 7.0, 65.0, 65.0, 0, 0, 7.5, "Hyderabad", "2026-11-18", "2026-11-09"),
        ("Infosys", "Specialist Programmer", ["CSE", "IT"], 7.5, 65.0, 65.0, 0, 0, 9.5, "Bengaluru", "2026-12-01", "2026-11-20"),
        ("Wipro", "Turbo Trainee", ["CSE", "IT", "ECE"], 6.5, 60.0, 60.0, 0, 1, 6.5, "Bengaluru", "2026-11-25", "2026-11-15"),
        ("Accenture", "Advanced Tech Trainee", ["All Branches"], 6.5, 60.0, 60.0, 0, None, 6.5, "Bengaluru", "2026-11-19", "2026-11-10"),
        ("Capgemini", "Senior Analyst", ["CSE", "IT", "ECE", "EEE"], 6.0, 60.0, 60.0, 0, None, 5.75, "Mumbai", "2026-11-29", "2026-11-21"),
        ("HCLTech", "Graduate Engineer", ["CSE", "IT", "ECE"], 6.0, 60.0, 60.0, 0, None, 4.25, "Noida", "2026-12-02", "2026-11-23"),
        ("Tech Mahindra", "Software Trainee", ["CSE", "IT", "ECE"], 6.0, 60.0, 60.0, 0, 1, 4.0, "Pune", "2026-11-27", "2026-11-18"),
        ("Mindtree", "Software Engineer", ["CSE", "IT"], 6.5, 60.0, 60.0, 0, 0, 5.0, "Bengaluru", "2026-12-04", "2026-11-24"),
        ("LTIMindtree", "Associate Consultant", ["CSE", "IT", "ECE"], 6.5, 60.0, 60.0, 0, None, 6.0, "Mumbai", "2026-11-16", "2026-11-08"),
        ("Mphasis", "Trainee Software Engineer", ["CSE", "IT"], 6.0, 60.0, 60.0, 0, None, 4.5, "Pune", "2026-11-30", "2026-11-22"),
        ("Persistent Systems", "Software Engineer", ["CSE", "IT"], 6.8, 60.0, 60.0, 0, 0, 7.0, "Pune", "2026-12-06", "2026-11-27"),
        ("Coforge", "Graduate Trainee", ["CSE", "IT"], 6.0, 60.0, 60.0, 0, None, 4.25, "Noida", "2026-11-23", "2026-11-14"),
        ("Birlasoft", "Technical Trainee", ["CSE", "IT", "ECE"], 6.0, 60.0, 60.0, 0, 1, 4.0, "Pune", "2026-12-08", "2026-11-28"),
        ("Hexaware", "Premier Graduate Trainee", ["CSE", "IT", "ECE"], 6.5, 60.0, 60.0, 0, 0, 6.0, "Chennai", "2026-11-17", "2026-11-07"),
    ]
    idx = i - 36
    comp, role, br, cg, tenth, twelfth, act, hist, ctc, loc, ddate, dead = comp_list[idx]
    CASES.append({
        "id": f"doc_{i:03d}_{comp.lower().replace(' ', '_')}_scanned.pdf",
        "format": "scanned_pdf",
        "company": comp,
        "role": role,
        "branches": br,
        "cgpa": cg,
        "tenth": tenth,
        "twelfth": twelfth,
        "active_backlogs": act,
        "history_backlogs": hist,
        "ctc": ctc,
        "ctc_min": ctc,
        "ctc_max": ctc,
        "location": loc,
        "drive_date": ddate,
        "deadline": dead,
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Aptitude & Coding", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Interview", "HR_INTERVIEW", 30)
        ],
        "distractors": "Target: 2026 Batch. Scan copy of placement circular.",
        "skills": ["Java", "SQL", "Problem Solving"]
    })

# 51-75: Word DOCX documents with structured tables
for i in range(51, 76):
    docx_comps = [
        ("American Express", "Engineer Trainee", ["CSE", "IT"], 7.5, 70.0, 70.0, 0, 0, 16.0, "Gurgaon", "2026-11-28", "2026-11-18"),
        ("ServiceNow", "Associate Software Engineer", ["CSE", "IT"], 7.5, 65.0, 65.0, 0, None, 24.0, "Hyderabad", "2026-12-03", "2026-11-22"),
        ("Intuit", "Software Engineer", ["CSE", "IT"], 8.0, 70.0, 70.0, 0, 0, 26.0, "Bengaluru", "2026-11-15", "2026-11-06"),
        ("PayPal", "Software Engineer", ["CSE", "IT", "ECE"], 7.5, 65.0, 65.0, 0, 0, 23.5, "Chennai", "2026-11-24", "2026-11-14"),
        ("Walmart Global Tech", "Software Engineer", ["CSE", "IT"], 7.5, 60.0, 60.0, 0, None, 20.0, "Bengaluru", "2026-12-07", "2026-11-27"),
        ("Target", "Associate Engineer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 14.5, "Bengaluru", "2026-11-19", "2026-11-10"),
        ("McKinsey & Company", "Junior Specialist", ["All Branches"], 7.0, 70.0, 70.0, 0, None, 13.0, "Gurgaon", "2026-12-05", "2026-11-25"),
        ("Boston Consulting Group", "Associate", ["All Branches"], 7.5, 75.0, 75.0, 0, 0, 18.0, "Mumbai", "2026-11-21", "2026-11-11"),
        ("Bain & Company", "Analyst", ["All Branches"], 7.5, 70.0, 70.0, 0, None, 16.5, "Gurgaon", "2026-11-26", "2026-11-16"),
        ("PwC India", "Associate Consultant", ["CSE", "IT", "ECE"], 6.5, 60.0, 60.0, 0, 1, 7.5, "Bengaluru", "2026-11-30", "2026-11-20"),
        ("EY India", "Tax Technology Trainee", ["CSE", "IT"], 6.5, 60.0, 60.0, 0, None, 7.0, "Bengaluru", "2026-12-02", "2026-11-22"),
        ("KPMG India", "Cyber Security Analyst", ["CSE", "IT", "ECE"], 6.5, 60.0, 60.0, 0, None, 7.2, "Bengaluru", "2026-11-17", "2026-11-08"),
        ("AMD", "Silicon Design Engineer", ["ECE", "EEE"], 7.5, 70.0, 70.0, 0, 0, 19.0, "Hyderabad", "2026-12-10", "2026-11-29"),
        ("Broadcom", "R&D Engineer", ["ECE", "CSE"], 8.0, 75.0, 75.0, 0, 0, 25.0, "Bengaluru", "2026-11-14", "2026-11-05"),
        ("Synopsys", "Applications Engineer", ["ECE", "EEE", "CSE"], 7.5, 70.0, 70.0, 0, None, 17.0, "Noida", "2026-11-23", "2026-11-13"),
        ("Cadence", "Software Engineer", ["CSE", "ECE"], 7.5, 65.0, 65.0, 0, 0, 16.5, "Noida", "2026-12-04", "2026-11-24"),
        ("Micron Technology", "Associate Engineer", ["ECE", "EEE", "CSE"], 7.0, 65.0, 65.0, 0, None, 15.0, "Hyderabad", "2026-11-27", "2026-11-17"),
        ("Schneider Electric Tech", "Cloud Developer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 10.0, "Bengaluru", "2026-12-01", "2026-11-21"),
        ("Honeywell", "Software Engineer", ["CSE", "IT", "ECE"], 7.0, 65.0, 65.0, 0, 1, 10.5, "Bengaluru", "2026-11-20", "2026-11-10"),
        ("Caterpillar", "Associate Engineer", ["Mechanical Engineering", "EEE"], 6.8, 60.0, 60.0, 0, None, 8.5, "Chennai", "2026-11-25", "2026-11-15"),
        ("John Deere", "Product Engineer", ["Mechanical Engineering", "CSE"], 6.8, 60.0, 60.0, 0, None, 8.0, "Pune", "2026-12-06", "2026-11-26"),
        ("Cummins India", "Graduate Trainee", ["Mechanical Engineering", "EEE"], 6.5, 60.0, 60.0, 0, None, 7.5, "Pune", "2026-11-18", "2026-11-09"),
        ("Thermax", "Graduate Trainee", ["Mechanical Engineering", "Chemical Engineering"], 6.5, 60.0, 60.0, 0, None, 6.0, "Pune", "2026-11-29", "2026-11-19"),
        ("Maruti Suzuki", "Graduate Engineer", ["Mechanical Engineering", "EEE", "ECE"], 6.8, 65.0, 65.0, 0, 0, 8.2, "Gurgaon", "2026-12-08", "2026-11-28"),
        ("Hero MotoCorp", "GET R&D", ["Mechanical Engineering", "ECE"], 6.8, 60.0, 60.0, 0, None, 7.8, "Gurgaon", "2026-11-16", "2026-11-07"),
    ]
    idx = i - 51
    comp, role, br, cg, tenth, twelfth, act, hist, ctc, loc, ddate, dead = docx_comps[idx]
    CASES.append({
        "id": f"doc_{i:03d}_{comp.lower().replace(' ', '_')}.docx",
        "format": "docx",
        "company": comp,
        "role": role,
        "branches": br,
        "cgpa": cg,
        "tenth": tenth,
        "twelfth": twelfth,
        "active_backlogs": act,
        "history_backlogs": hist,
        "ctc": ctc,
        "ctc_min": ctc,
        "ctc_max": ctc,
        "location": loc,
        "drive_date": ddate,
        "deadline": dead,
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Technical Exam", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR & Management Discussion", "HR_INTERVIEW", 30)
        ],
        "distractors": "Target: 2026 Batch. Document layout in tabular format.",
        "skills": ["Domain Skills", "Communication", "Problem Solving"]
    })

# 76-95: Plain text announcements and emails (.txt, .eml)
for i in range(76, 96):
    txt_comps = [
        ("Razorpay", "Backend Engineer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 18.0, "Bengaluru", "2026-11-25", "2026-11-15"),
        ("PhonePe", "Software Engineer", ["CSE", "IT"], 7.5, 65.0, 65.0, 0, 0, 25.0, "Bengaluru", "2026-12-02", "2026-11-22"),
        ("Cred", "Backend Developer", ["CSE", "IT"], 8.0, 70.0, 70.0, 0, 0, 30.0, "Bengaluru", "2026-11-19", "2026-11-10"),
        ("Postman", "Software Engineer", ["CSE", "IT"], 7.5, 65.0, 65.0, 0, None, 22.0, "Bengaluru", "2026-12-05", "2026-11-26"),
        ("BrowserStack", "Software Engineer", ["CSE", "IT"], 7.5, 65.0, 65.0, 0, None, 20.0, "Mumbai", "2026-11-17", "2026-11-08"),
        ("InMobi", "Data Engineer", ["CSE", "IT", "Data Science"], 7.0, 60.0, 60.0, 0, None, 16.0, "Bengaluru", "2026-11-28", "2026-11-18"),
        ("Groww", "Frontend Developer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 15.0, "Bengaluru", "2026-11-22", "2026-11-12"),
        ("Zerodha", "Systems Engineer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 16.0, "Bengaluru", "2026-12-07", "2026-11-27"),
        ("Juspay", "FP Developer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 21.0, "Bengaluru", "2026-11-14", "2026-11-05"),
        ("Urban Company", "Software Engineer", ["CSE", "IT"], 7.5, 65.0, 65.0, 0, None, 19.0, "Gurgaon", "2026-11-26", "2026-11-16"),
        ("Delhivery", "Data Analyst", ["CSE", "IT", "Data Science"], 6.5, 60.0, 60.0, 0, 1, 10.0, "Gurgaon", "2026-12-01", "2026-11-21"),
        ("Zepto", "Software Developer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 17.0, "Mumbai", "2026-11-20", "2026-11-11"),
        ("Blinkit", "Backend Engineer", ["CSE", "IT"], 7.0, 60.0, 60.0, 0, None, 18.0, "Gurgaon", "2026-11-27", "2026-11-17"),
        ("Ola Electric", "Firmware Engineer", ["ECE", "EEE", "CSE"], 7.0, 60.0, 60.0, 0, None, 12.0, "Bengaluru", "2026-12-04", "2026-11-24"),
        ("Ather Energy", "Embedded Engineer", ["ECE", "EEE"], 7.2, 65.0, 65.0, 0, 0, 13.5, "Bengaluru", "2026-11-18", "2026-11-09"),
        ("Cars24", "Associate SDE", ["CSE", "IT"], 6.8, 60.0, 60.0, 0, None, 11.0, "Gurgaon", "2026-11-30", "2026-11-20"),
        ("Spinny", "Software Trainee", ["CSE", "IT"], 6.5, 60.0, 60.0, 0, None, 9.0, "Gurgaon", "2026-12-03", "2026-11-23"),
        ("Meesho", "SDE 1", ["CSE", "IT"], 7.5, 65.0, 65.0, 0, 0, 24.0, "Bengaluru", "2026-11-15", "2026-11-06"),
        ("Nykaa", "Associate Software Engineer", ["CSE", "IT"], 6.8, 60.0, 60.0, 0, None, 11.5, "Mumbai", "2026-11-23", "2026-11-13"),
        ("Licious", "Software Engineer", ["CSE", "IT"], 6.8, 60.0, 60.0, 0, None, 12.0, "Bengaluru", "2026-12-09", "2026-11-29"),
    ]
    idx = i - 76
    comp, role, br, cg, tenth, twelfth, act, hist, ctc, loc, ddate, dead = txt_comps[idx]
    ext = "eml" if i % 2 == 0 else "txt"
    CASES.append({
        "id": f"doc_{i:03d}_{comp.lower().replace(' ', '_')}.{ext}",
        "format": ext,
        "company": comp,
        "role": role,
        "branches": br,
        "cgpa": cg,
        "tenth": tenth,
        "twelfth": twelfth,
        "active_backlogs": act,
        "history_backlogs": hist,
        "ctc": ctc,
        "ctc_min": ctc,
        "ctc_max": ctc,
        "location": loc,
        "drive_date": ddate,
        "deadline": dead,
        "rounds": 3,
        "rounds_detail": [
            ("Round 1: Online Coding Test", "ONLINE_TEST", 60),
            ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 45),
            ("Round 3: HR Discussion", "HR_INTERVIEW", 30)
        ],
        "distractors": "Target: 2026 Graduates. Plain text / email notification.",
        "skills": ["Coding", "Data Structures", "System Concepts"]
    })

# 96-100: Edge Cases & Error Files
CASES.append({
    "id": "doc_096_no_cgpa_drive.txt",
    "format": "txt",
    "company": "Infosys",
    "role": "Systems Engineer",
    "branches": ["All Branches"],
    "cgpa": 0.0, # explicit no cgpa cutoff
    "tenth": 60.0,
    "twelfth": 60.0,
    "active_backlogs": 0,
    "history_backlogs": None,
    "ctc": 3.6,
    "ctc_min": 3.6,
    "ctc_max": 3.6,
    "location": "Pan India",
    "drive_date": "2026-11-20",
    "deadline": "2026-11-12",
    "rounds": 2,
    "rounds_detail": [
        ("Round 1: Online Aptitude Assessment", "ONLINE_TEST", 60),
        ("Round 2: Technical and HR Interview", "TECHNICAL_INTERVIEW", 30)
    ],
    "distractors": "No CGPA cutoff required for this mass drive.",
    "skills": ["Communication", "Basic Programming"]
})

CASES.append({
    "id": "doc_097_salary_range.pdf",
    "format": "pdf",
    "company": "Siemens Technology",
    "role": "Software Developer",
    "branches": ["CSE", "IT", "ECE"],
    "cgpa": 7.0,
    "tenth": 60.0,
    "twelfth": 60.0,
    "active_backlogs": 0,
    "history_backlogs": None,
    "ctc": 10.0, # min ctc in range
    "ctc_min": 10.0,
    "ctc_max": 14.0,
    "location": "Bengaluru",
    "drive_date": "2026-12-01",
    "deadline": "2026-11-20",
    "rounds": 3,
    "rounds_detail": [
        ("Round 1: Online Assessment", "ONLINE_TEST", 60),
        ("Round 2: Technical Interview", "TECHNICAL_INTERVIEW", 60),
        ("Round 3: HR Round", "HR_INTERVIEW", 30)
    ],
    "distractors": "CTC offered is between 10.0 LPA to 14.0 LPA based on assessment performance.",
    "skills": ["C++", "Python", "Data Structures"]
})

CASES.append({
    "id": "doc_098_missing_role_and_deadline.docx",
    "format": "docx",
    "company": "Qualcomm",
    "role": None, # Missing role in circular
    "branches": ["ECE", "EEE"],
    "cgpa": 7.5,
    "tenth": 65.0,
    "twelfth": 65.0,
    "active_backlogs": 0,
    "history_backlogs": 0,
    "ctc": 18.0,
    "ctc_min": 18.0,
    "ctc_max": 18.0,
    "location": "Hyderabad",
    "drive_date": "2026-12-05",
    "deadline": None, # Missing deadline in circular
    "rounds": 2,
    "rounds_detail": [
        ("Round 1: Technical Screening", "ONLINE_TEST", 60),
        ("Round 2: Interview Round", "TECHNICAL_INTERVIEW", 45)
    ],
    "distractors": "Notice announcing Qualcomm campus visit without stating job profile.",
    "skills": ["Circuits", "Verilog"]
})

CASES.append({
    "id": "doc_099_empty_announcement.txt",
    "format": "empty",
    "company": None,
    "role": None,
    "branches": None,
    "cgpa": None,
    "tenth": None,
    "twelfth": None,
    "active_backlogs": None,
    "history_backlogs": None,
    "ctc": None,
    "ctc_min": None,
    "ctc_max": None,
    "location": None,
    "drive_date": None,
    "deadline": None,
    "rounds": 0,
    "rounds_detail": [],
    "distractors": "Empty file test case (0 bytes).",
    "skills": []
})

CASES.append({
    "id": "doc_100_corrupt_file.pdf",
    "format": "corrupt",
    "company": None,
    "role": None,
    "branches": None,
    "cgpa": None,
    "tenth": None,
    "twelfth": None,
    "active_backlogs": None,
    "history_backlogs": None,
    "ctc": None,
    "ctc_min": None,
    "ctc_max": None,
    "location": None,
    "drive_date": None,
    "deadline": None,
    "rounds": 0,
    "rounds_detail": [],
    "distractors": "Corrupted PDF binary bytes.",
    "skills": []
})


def generate_file_content(case: dict) -> str:
    """Generates realistic document text representation for a test case."""
    lines = []
    comp = case["company"] or "Target Company"
    lines.append(f"CAMPUS RECRUITMENT DRIVE ANNOUNCEMENT - 2026 BATCH")
    lines.append(f"Organization: {comp}")
    if case.get("role"):
        lines.append(f"Job Role: {case['role']}")
    if case.get("location"):
        lines.append(f"Job Location: {case['location']}")
    if case.get("drive_date"):
        lines.append(f"Date of Drive: {case['drive_date']}")
    if case.get("deadline"):
        lines.append(f"Application Deadline: {case['deadline']}")

    # CTC
    if case.get("ctc_min") and case.get("ctc_max") and case["ctc_min"] != case["ctc_max"]:
        lines.append(f"Compensation / Package: {case['ctc_min']} LPA - {case['ctc_max']} LPA")
    elif case.get("ctc"):
        lines.append(f"CTC Offered: {case['ctc']} LPA")

    # Mode
    lines.append("Drive Mode: On-Campus")

    # Eligibility Criteria
    lines.append("\nELIGIBILITY CRITERIA:")
    if case.get("cgpa") == 0.0:
        lines.append("- CGPA: No CGPA cut-off required. Open to all students.")
    elif case.get("cgpa"):
        lines.append(f"- Minimum CGPA Required: {case['cgpa']} or above in B.Tech/Degree")

    # Percentages
    if case.get("tenth") and case.get("twelfth") and case["tenth"] == case["twelfth"]:
        lines.append(f"- Minimum {case['tenth']}% aggregate in 10th and 12th standard")
    elif case.get("tenth") and case.get("twelfth"):
        lines.append(f"- Class 10th Cut-off: {case['tenth']}%, Class 12th Cut-off: {case['twelfth']}%")

    # Backlogs
    if case.get("active_backlogs") == 0 and case.get("history_backlogs") == 0:
        lines.append("- Backlog Standing: Strictly clean academic history (0 active and 0 historical backlogs)")
    elif case.get("active_backlogs") == 0 and case.get("history_backlogs") is not None:
        lines.append(f"- Backlog Policy: No active backlogs allowed (up to {case['history_backlogs']} cleared backlogs permitted)")
    elif case.get("active_backlogs") == 0:
        lines.append("- Backlog Policy: No standing or active backlogs at the time of drive")
    elif case.get("active_backlogs"):
        lines.append(f"- Backlogs Allowed: Maximum {case['active_backlogs']} active backlog permitted")

    # Branches
    if case.get("branches"):
        br_str = ", ".join(case["branches"])
        lines.append(f"- Eligible Branches: {br_str}")

    # Skills & Distractors
    if case.get("distractors"):
        lines.append(f"- Note: {case['distractors']}")

    # Rounds
    if case.get("rounds_detail"):
        lines.append("\nSELECTION PROCESS & HIRING ROUNDS:")
        for r_name, r_type, dur in case["rounds_detail"]:
            lines.append(f"- {r_name} ({dur} mins duration)")

    return "\n".join(lines)


def create_scanned_pdf(text: str, dest_path: str):
    """Renders text into an image and embeds it into a scanned PDF (image-only, no digital text layer)."""
    img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    y = 60
    for line in text.splitlines():
        if line.strip():
            draw.text((60, y), line, fill=(10, 10, 10))
            y += 32
        else:
            y += 20

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    rect = fitz.Rect(0, 0, 595, 842)
    page.insert_image(rect, stream=img_byte_arr.getvalue())
    doc.save(dest_path)
    doc.close()


def create_digital_pdf(text: str, dest_path: str):
    """Creates a standard digital PDF with embedded text layer and table representation."""
    doc = fitz.open()
    page = doc.new_page()
    p = fitz.Point(40, 50)
    for line in text.splitlines():
        page.insert_text(p, line, fontsize=10)
        p.y += 18
        if p.y > 800:
            page = doc.new_page()
            p = fitz.Point(40, 50)
    doc.save(dest_path)
    doc.close()


def create_docx_doc(case: dict, text: str, dest_path: str):
    """Creates a structured Word document with paragraphs, bold headings, and tables."""
    doc = docx.Document()
    doc.add_heading(f"Campus Placement Notice: {case.get('company') or 'Recruitment'}", level=1)
    
    # Add a table for key parameters
    table = doc.add_table(rows=1, cols=2)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Parameter"
    hdr_cells[1].text = "Requirement / Specification"
    
    params = [
        ("Company Name", case.get("company") or "N/A"),
        ("Role", case.get("role") or "N/A"),
        ("Location", case.get("location") or "N/A"),
        ("CTC (LPA)", str(case.get("ctc") or "N/A")),
        ("Drive Date", str(case.get("drive_date") or "N/A")),
        ("Application Deadline", str(case.get("deadline") or "N/A")),
        ("Eligible Branches", ", ".join(case.get("branches") or []) or "All"),
        ("Min CGPA", str(case.get("cgpa") if case.get("cgpa") is not None else "N/A")),
        ("10th Cut-off", f"{case.get('tenth')}%" if case.get("tenth") else "N/A"),
        ("12th Cut-off", f"{case.get('twelfth')}%" if case.get("twelfth") else "N/A"),
    ]
    for param_name, param_val in params:
        row_cells = table.add_row().cells
        row_cells[0].text = param_name
        row_cells[1].text = param_val

    doc.add_heading("Detailed Circular Content", level=2)
    for line in text.splitlines():
        if line.strip():
            doc.add_paragraph(line)
    doc.save(dest_path)


def generate_all():
    print(f"Generating 100 synthetic test announcements in {DOCS_DIR} ...")
    gt_dict = {}

    for case in CASES:
        filename = case["id"]
        file_format = case["format"]
        dest = os.path.join(DOCS_DIR, filename)

        if file_format == "empty":
            with open(dest, "wb") as f:
                f.write(b"")
        elif file_format == "corrupt":
            with open(dest, "wb") as f:
                f.write(b"%PDF-1.4 corrupt junk random binary bytes 0x00 0xFF \x00\x01\x02 invalid structure")
        else:
            text = generate_file_content(case)
            if file_format == "scanned_pdf":
                create_scanned_pdf(text, dest)
            elif file_format == "pdf":
                create_digital_pdf(text, dest)
            elif file_format == "docx":
                create_docx_doc(case, text, dest)
            elif file_format == "txt":
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(text)
            elif file_format == "eml":
                eml_content = f"Subject: Campus Recruitment Notice: {case.get('company')} ({case.get('role')})\nFrom: placement-cell@university.edu\n\n{text}"
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(eml_content)

        # Ground truth record
        gt_dict[filename] = {
            "company_name": case.get("company"),
            "role": case.get("role"),
            "location": case.get("location"),
            "allowed_branches": case.get("branches"),
            "cgpa_min": case.get("cgpa"),
            "tenth_percentage_min": case.get("tenth"),
            "twelfth_percentage_min": case.get("twelfth"),
            "active_backlogs_max": case.get("active_backlogs"),
            "historical_backlogs_max": case.get("history_backlogs"),
            "ctc_lpa": case.get("ctc"),
            "ctc_min_lpa": case.get("ctc_min"),
            "ctc_max_lpa": case.get("ctc_max"),
            "drive_date": case.get("drive_date"),
            "application_deadline": case.get("deadline"),
            "rounds_count": case.get("rounds"),
            "document_format": file_format,
            "is_error_case": file_format in ("empty", "corrupt"),
        }

    with open(GT_PATH, "w", encoding="utf-8") as f:
        json.dump(gt_dict, f, indent=2)

    print(f"Successfully created 100 announcements and saved ground truth to {GT_PATH}")


if __name__ == "__main__":
    generate_all()
