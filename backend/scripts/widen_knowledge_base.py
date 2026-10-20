"""Add the non-technical roles and their skills to the knowledge base.

``docs/limitations.md`` used to say of the knowledge base:

    181 skills, 92 roles, 16 families, 1,136 weighted requirements. That is
    enough to demonstrate the system and not enough to be a career taxonomy.
    Missing from it: most industry-specific technologies, every non-technical
    role, every regional market, and any role that emerged after the curation
    date. The families are the AI/ML ones and their immediate neighbours;
    there is no "teacher", no "nurse", no "accountant".

This script adds eight roles and sixty-nine skills that make the three named
roles -- and five more -- real, so that the sentence above stops being true.

It is a **script** rather than a hand edit for the same reason the evaluation
labels are committed in a file: the selection is a rule, and the rule should
be visible. Eight roles is the number that lands the catalogue on exactly
100, which is the top of the band the proposal set ("50-100 roles") and the
top of the band ``scripts/verify_compliance.py`` enforces.

Run it with::

    cd backend && python -m scripts.widen_knowledge_base
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = _BACKEND_ROOT / "data" / "skills_taxonomy.json"
ROLES_PATH = _BACKEND_ROOT / "data" / "job_roles.json"

#: The new skills, as ``(name, slug, category, description, aliases)``.
NEW_SKILLS: list[tuple[str, str, str, str, list[str]]] = [
    # ---- Education & Training ----------------------------------------
    (
        "Lesson Planning",
        "lesson-planning",
        "Education & Training",
        "Planning a sequence of lessons that build towards a learning outcome.",
        ["lesson planning", "planning lessons", "scheme of work"],
    ),
    (
        "Curriculum Design",
        "curriculum-design",
        "Education & Training",
        "Shaping what is taught, and in what order, across a course or programme.",
        ["curriculum design", "curriculum development", "curriculum mapping"],
    ),
    (
        "Classroom Management",
        "classroom-management",
        "Education & Training",
        "Running a room: attention, behaviour, grouping and the routines that make teaching possible.",
        ["classroom management", "managing a classroom", "classroom routines"],
    ),
    (
        "Student Assessment",
        "student-assessment",
        "Education & Training",
        "Working out what a student understands, and reporting it.",
        ["student assessment", "assessing students", "formative assessment"],
    ),
    (
        "Differentiated Instruction",
        "differentiated-instruction",
        "Education & Training",
        "Teaching the same idea to a class in which the starting points differ.",
        [
            "differentiated instruction",
            "differentiated teaching",
            "adaptive teaching",
        ],
    ),
    (
        "Learning Outcomes",
        "learning-outcomes",
        "Education & Training",
        "Stating what a learner should be able to do, and designing towards it.",
        ["learning outcomes", "learning objectives", "intended outcomes"],
    ),
    (
        "Behaviour Management",
        "behaviour-management",
        "Education & Training",
        "Keeping a classroom safe and workable without shutting learning down.",
        ["behaviour management", "behavior management", "classroom behaviour"],
    ),
    (
        "Parent Communication",
        "parent-communication",
        "Education & Training",
        "Talking to families about a child's progress, and about what to do next.",
        [
            "parent communication",
            "parent engagement",
            "communicating with parents",
        ],
    ),
    (
        "Examination Marking",
        "examination-marking",
        "Education & Training",
        "Marking scripts against a rubric, consistently and defensibly.",
        ["exam marking", "marking exams", "marking scripts"],
    ),
    (
        "Special Educational Needs",
        "special-educational-needs",
        "Education & Training",
        "Teaching and supporting learners with additional needs.",
        ["special educational needs", "special needs", "SEN support"],
    ),
    (
        "Student Safeguarding",
        "student-safeguarding",
        "Education & Training",
        "Recognising and reporting a child's safety or wellbeing concern.",
        ["safeguarding", "child protection", "keeping children safe"],
    ),
    (
        "Educational Technology",
        "educational-technology",
        "Education & Training",
        "Using software and hardware in teaching, and choosing it well.",
        ["educational technology", "edtech", "digital learning tools"],
    ),
    # ---- Healthcare & Clinical ---------------------------------------
    (
        "Patient Assessment",
        "patient-assessment",
        "Healthcare & Clinical",
        "Taking a history, examining, and forming a working impression.",
        ["patient assessment", "assessing patients", "clinical assessment"],
    ),
    (
        "Clinical Documentation",
        "clinical-documentation",
        "Healthcare & Clinical",
        "Writing the record that another clinician will rely on.",
        ["clinical documentation", "patient records", "medical records"],
    ),
    (
        "Care Planning",
        "care-planning",
        "Healthcare & Clinical",
        "Deciding what a patient needs, who provides it, and when.",
        ["care planning", "care plans", "writing care plans"],
    ),
    (
        "Medication Administration",
        "medication-administration",
        "Healthcare & Clinical",
        "Giving the right drug, at the right dose, at the right time, and recording it.",
        [
            "medication administration",
            "administering medication",
            "drug administration",
        ],
    ),
    (
        "Vital Signs",
        "vital-signs",
        "Healthcare & Clinical",
        "Measuring and interpreting the numbers that say whether a patient is stable.",
        ["vital signs", "obs and vitals", "observations"],
    ),
    (
        "Infection Control",
        "infection-control",
        "Healthcare & Clinical",
        "Preventing infection from spreading, and containing it when it does.",
        ["infection control", "infection prevention", "cross infection"],
    ),
    (
        "Patient Monitoring",
        "patient-monitoring",
        "Healthcare & Clinical",
        "Watching a patient over time and acting when they change.",
        ["patient monitoring", "monitoring patients", "patient surveillance"],
    ),
    (
        "Clinical Trials",
        "clinical-trials",
        "Healthcare & Clinical",
        "Running a study to protocol, with the records a regulator would expect.",
        ["clinical trials", "clinical research", "trial monitoring"],
    ),
    (
        "Emergency Response",
        "emergency-response",
        "Healthcare & Clinical",
        "Acting first when a patient deteriorates, and calling for the right help.",
        ["emergency response", "emergency care", "triage"],
    ),
    (
        "Clinical Handover",
        "clinical-handover",
        "Healthcare & Clinical",
        "Passing a patient over to the next shift without losing anything.",
        ["clinical handover", "shift handover", "handover notes"],
    ),
    (
        "Ward Management",
        "ward-management",
        "Healthcare & Clinical",
        "Running a ward: allocation, escalation, and the daily rhythm.",
        ["ward management", "ward round", "ward rounds"],
    ),
    # ---- Accounting & Finance ----------------------------------------
    (
        "Financial Reporting",
        "financial-reporting",
        "Accounting & Finance",
        "Turning a year of transactions into statements somebody can rely on.",
        ["financial reporting", "statutory reporting", "preparing accounts"],
    ),
    (
        "Bookkeeping",
        "bookkeeping",
        "Accounting & Finance",
        "Keeping the day-to-day record of money in and money out.",
        ["bookkeeping", "book keeping", "day-to-day accounting"],
    ),
    (
        "Accounts Payable",
        "accounts-payable",
        "Accounting & Finance",
        "The money the organisation owes its suppliers, and the process around it.",
        ["accounts payable", "supplier payments", "AP"],
    ),
    (
        "Accounts Receivable",
        "accounts-receivable",
        "Accounting & Finance",
        "The money owed to the organisation, and getting it in.",
        ["accounts receivable", "debt collection", "AR"],
    ),
    (
        "Bank Reconciliation",
        "bank-reconciliation",
        "Accounting & Finance",
        "Matching the bank statement to the books, and finding the difference.",
        ["bank reconciliation", "reconciling the bank", "bank rec"],
    ),
    (
        "Budgeting",
        "budgeting",
        "Accounting & Finance",
        "Putting a plan in numbers, and living inside it.",
        ["budgeting", "budget preparation", "cost budgeting"],
    ),
    (
        "Tax Compliance",
        "tax-compliance",
        "Accounting & Finance",
        "Filing what the law requires, on time, and getting it right.",
        ["tax compliance", "corporate tax", "tax filing"],
    ),
    (
        "Auditing",
        "auditing",
        "Accounting & Finance",
        "Testing whether the accounts say what the business actually did.",
        ["auditing", "audit", "internal audit"],
    ),
    (
        "Variance Analysis",
        "variance-analysis",
        "Accounting & Finance",
        "Explaining the gap between the plan and what happened.",
        ["variance analysis", "budget variance", "explaining variances"],
    ),
    (
        "Financial Modelling",
        "financial-modelling",
        "Accounting & Finance",
        "Building a model of the business to test a decision against.",
        ["financial modelling", "financial modeling", "financial models"],
    ),
    (
        "Cash Flow Management",
        "cash-flow-management",
        "Accounting & Finance",
        "Making sure the money is there when it is needed, not only on paper.",
        [
            "cash flow management",
            "cashflow management",
            "working capital management",
        ],
    ),
    (
        "Internal Controls",
        "internal-controls",
        "Accounting & Finance",
        "The processes that keep error and fraud from going unnoticed.",
        ["internal controls", "internal control", "control procedures"],
    ),
    (
        "Regulatory Reporting",
        "regulatory-reporting",
        "Accounting & Finance",
        "Reporting to a regulator on time, in the form it requires.",
        ["regulatory reporting", "statutory returns", "regulator returns"],
    ),
    (
        "Cost Accounting",
        "cost-accounting",
        "Accounting & Finance",
        "Working out what a product, a service or a job actually cost.",
        ["cost accounting", "job costing", "product costing"],
    ),
    # ---- Civil & Electrical Engineering -------------------------------
    (
        "Structural Analysis",
        "structural-analysis",
        "Civil & Electrical Engineering",
        "Working out whether a structure will carry what is put on it.",
        ["structural analysis", "structural calculations", "load analysis"],
    ),
    (
        "AutoCAD",
        "autocad",
        "Civil & Electrical Engineering",
        "Drafting to an engineering drawing standard.",
        ["CAD drafting", "computer aided design", "2D drafting"],
    ),
    (
        "Engineering Drawings",
        "engineering-drawings",
        "Civil & Electrical Engineering",
        "Reading and producing the drawings a structure is built from.",
        [
            "engineering drawings",
            "technical drawings",
            "construction drawings",
        ],
    ),
    (
        "Road Design",
        "road-design",
        "Civil & Electrical Engineering",
        "Designing a road: its alignment, its geometry, and how it drains.",
        ["road design", "highway design", "road geometry"],
    ),
    (
        "Site Investigation",
        "site-investigation",
        "Civil & Electrical Engineering",
        "Finding out what the ground is like before anything is built on it.",
        [
            "site investigation",
            "geotechnical investigation",
            "ground investigation",
        ],
    ),
    (
        "Construction Scheduling",
        "construction-scheduling",
        "Civil & Electrical Engineering",
        "Sequencing the work so the site is not waiting on itself.",
        [
            "construction scheduling",
            "programme scheduling",
            "construction planning",
        ],
    ),
    (
        "Building Information Modelling",
        "building-information-modelling",
        "Civil & Electrical Engineering",
        "A model of the building that the whole project shares.",
        [
            "building information modelling",
            "building information model",
            "BIM",
        ],
    ),
    (
        "Construction Quality Assurance",
        "construction-quality-assurance",
        "Civil & Electrical Engineering",
        "Checking that what was built is what was specified.",
        [
            "construction quality assurance",
            "qa on site",
            "build quality",
        ],
    ),
    (
        "Health and Safety Compliance",
        "health-and-safety-compliance",
        "Civil & Electrical Engineering",
        "Working to the rules that keep a site safe.",
        ["health and safety", "HSE compliance", "site safety"],
    ),
    (
        "Procurement",
        "procurement",
        "Civil & Electrical Engineering",
        "Buying materials and services well, and on time.",
        ["procurement", "supplier management", "purchasing"],
    ),
    (
        "Contract Management",
        "contract-management",
        "Civil & Electrical Engineering",
        "Administering a contract: the money, the variations, the claims.",
        ["contract management", "contract administration", "managing contracts"],
    ),
    (
        "Technical Specification",
        "technical-specification",
        "Civil & Electrical Engineering",
        "Writing what is required precisely enough to be built from.",
        [
            "technical specifications",
            "specification writing",
            "method statements",
        ],
    ),
    # ---- Marketing ---------------------------------------------------
    (
        "Market Research",
        "market-research",
        "Marketing",
        "Finding out what the market wants, and what it will pay for.",
        ["market research", "market analysis", "market research reports"],
    ),
    (
        "Campaign Management",
        "campaign-management",
        "Marketing",
        "Planning, running and measuring a campaign.",
        ["campaign management", "campaign planning", "campaign execution"],
    ),
    (
        "Content Marketing",
        "content-marketing",
        "Marketing",
        "Producing material that earns attention rather than buying it.",
        ["content marketing", "content strategy", "content production"],
    ),
    (
        "Search Engine Optimisation",
        "search-engine-optimisation",
        "Marketing",
        "Being found in a search result for the terms a buyer uses.",
        [
            "search engine optimisation",
            "search engine optimization",
            "SEO",
        ],
    ),
    (
        "Email Marketing",
        "email-marketing",
        "Marketing",
        "Sending mail that is wanted, to people who asked for it.",
        ["email marketing", "email campaigns", "lifecycle email"],
    ),
    (
        "Social Media Marketing",
        "social-media-marketing",
        "Marketing",
        "Using social channels deliberately, and measuring what it produced.",
        [
            "social media marketing",
            "social media strategy",
            "social campaigns",
        ],
    ),
    (
        "Conversion Rate Optimisation",
        "conversion-rate-optimisation",
        "Marketing",
        "Improving how many people who arrive go on to do the thing.",
        [
            "conversion rate optimisation",
            "conversion optimisation",
            "CRO",
        ],
    ),
    (
        "Customer Segmentation",
        "customer-segmentation",
        "Marketing",
        "Grouping customers by what they actually want, not by a spreadsheet column.",
        [
            "customer segmentation",
            "segmenting customers",
            "audience segmentation",
        ],
    ),
    (
        "Brand Positioning",
        "brand-positioning",
        "Marketing",
        "Deciding what the brand is for, and where it sits against the alternatives.",
        ["brand positioning", "brand strategy", "positioning"],
    ),
    (
        "Marketing Analytics",
        "marketing-analytics",
        "Marketing",
        "Measuring what a campaign did, rather than what it felt like it did.",
        ["marketing analytics", "campaign analytics", "marketing measurement"],
    ),
    # ---- Human Resources ---------------------------------------------
    (
        "Recruitment and Selection",
        "recruitment-and-selection",
        "Human Resources",
        "Finding the right people and choosing them fairly.",
        [
            "recruitment and selection",
            "talent acquisition",
            "recruiting",
        ],
    ),
    (
        "Onboarding",
        "onboarding",
        "Human Resources",
        "Getting a new starter productive, and looked after.",
        ["onboarding", "induction", "new starter process"],
    ),
    (
        "Performance Management",
        "performance-management",
        "Human Resources",
        "Setting expectations, and having the conversations about them.",
        ["performance management", "performance reviews", "appraisals"],
    ),
    (
        "Compensation and Benefits",
        "compensation-and-benefits",
        "Human Resources",
        "Pay, and everything else the organisation gives in return for it.",
        [
            "compensation and benefits",
            "reward and benefits",
            "remuneration",
        ],
    ),
    (
        "Payroll Administration",
        "payroll-administration",
        "Human Resources",
        "Running the payroll accurately and on time.",
        ["payroll administration", "running payroll", "payroll processing"],
    ),
    (
        "Employee Relations",
        "employee-relations",
        "Human Resources",
        "Handling the relationship between the organisation and the people in it.",
        ["employee relations", "workplace relations", "staff relations"],
    ),
    (
        "Learning and Development",
        "learning-and-development",
        "Human Resources",
        "Growing the capability of the people already there.",
        [
            "learning and development",
            "training and development",
            "L&D",
        ],
    ),
    (
        "Workforce Planning",
        "workforce-planning",
        "Human Resources",
        "Working out what the shape of the team needs to be, and when.",
        [
            "workforce planning",
            "headcount planning",
            "succession planning",
        ],
    ),
    (
        "Employment Law",
        "employment-law",
        "Human Resources",
        "The law that governs the relationship between employer and employee.",
        ["employment law", "labour law", "labor law"],
    ),
    (
        "Absence Management",
        "absence-management",
        "Human Resources",
        "Managing sickness absence fairly, and getting people back.",
        ["absence management", "sickness absence", "managing absence"],
    ),
]

#: The new roles. ``skills`` is ``(slug, weight)``.
NEW_ROLES: list[dict[str, Any]] = [
    {
        "title": "Secondary School Teacher",
        "slug": "secondary-school-teacher",
        "family": "Teaching",
        "seniority": "Mid",
        "min_years_experience": 2,
        "description": (
            "Plan and deliver lessons across a subject area, assess what students have "
            "understood, and manage a class of thirty-odd teenagers. Expect to write "
            "lesson plans against learning outcomes, mark work, keep parents informed, "
            "and handle a safeguarding concern correctly the first time. Subject "
            "knowledge is assumed; the craft is in the room."
        ),
        "responsibilities": [
            "Plan and deliver lessons against agreed learning outcomes",
            "Assess student work and report progress to parents",
            "Manage classroom behaviour and maintain a safe learning environment",
            "Keep records of attainment and adjust teaching to what the class needs",
        ],
        "skills": [
            ("lesson-planning", 1.0),
            ("classroom-management", 0.95),
            ("student-assessment", 0.9),
            ("curriculum-design", 0.9),
            ("behaviour-management", 0.85),
            ("differentiated-instruction", 0.8),
            ("learning-outcomes", 0.75),
            ("parent-communication", 0.7),
            ("examination-marking", 0.65),
            ("student-safeguarding", 0.65),
            ("special-educational-needs", 0.6),
            ("educational-technology", 0.55),
        ],
    },
    {
        "title": "Registered Nurse",
        "slug": "registered-nurse",
        "family": "Healthcare",
        "seniority": "Mid",
        "min_years_experience": 1,
        "description": (
            "Assess patients, plan and deliver their care, administer medication and "
            "keep the record that the next shift will rely on. Much of the job is "
            "judgement under pressure: spotting a patient who is deteriorating, "
            "escalating early, and working infection control properly every time. "
            "Ward rounds, handovers and clinical documentation are daily work, not "
            "paperwork that can wait."
        ),
        "responsibilities": [
            "Assess patients and plan, deliver and review their care",
            "Administer medication and monitor for adverse effects",
            "Maintain accurate clinical records and hand over safely",
            "Escalate deterioration early and work within infection control policy",
        ],
        "skills": [
            ("patient-assessment", 1.0),
            ("clinical-documentation", 0.95),
            ("medication-administration", 0.92),
            ("care-planning", 0.9),
            ("vital-signs", 0.88),
            ("infection-control", 0.85),
            ("patient-monitoring", 0.85),
            ("emergency-response", 0.8),
            ("clinical-handover", 0.7),
            ("ward-management", 0.6),
            ("clinical-trials", 0.5),
        ],
    },
    {
        "title": "Accountant",
        "slug": "accountant",
        "family": "Accounting & Finance",
        "seniority": "Mid",
        "min_years_experience": 2,
        "description": (
            "Keep the books, close the month, and produce the financial statements "
            "that the business is run on. Day to day that means payables, receivables "
            "and bank reconciliation; periodically it means tax filings, regulatory "
            "returns and a variance analysis that explains what moved since the last "
            "budget. Accuracy is the job: a ledger that is nearly right is a ledger "
            "that is wrong."
        ),
        "responsibilities": [
            "Maintain the ledger and reconcile the bank accounts monthly",
            "Run the payables and receivables cycles to terms",
            "Prepare the financial statements and support the statutory filings",
            "Investigate budget variances and report what caused them",
        ],
        "skills": [
            ("bookkeeping", 1.0),
            ("financial-reporting", 0.95),
            ("accounts-payable", 0.85),
            ("accounts-receivable", 0.85),
            ("bank-reconciliation", 0.8),
            ("budgeting", 0.8),
            ("tax-compliance", 0.78),
            ("internal-controls", 0.7),
            ("regulatory-reporting", 0.65),
            ("cost-accounting", 0.6),
            ("variance-analysis", 0.55),
            ("excel", 0.8),
        ],
    },
    {
        "title": "Financial Analyst",
        "slug": "financial-analyst",
        "family": "Accounting & Finance",
        "seniority": "Mid",
        "min_years_experience": 2,
        "description": (
            "Turn the numbers into a decision. Build the model, compare the actuals "
            "against the plan, work out what the gap is made of, and say it plainly "
            "to people who did not build the model. Strong spreadsheet work and "
            "enough SQL to check the figures yourself are the entry requirements; "
            "the judgement is in knowing which question the business is actually "
            "asking."
        ),
        "responsibilities": [
            "Build and maintain the models the business plans against",
            "Produce the monthly reporting pack and explain the variances",
            "Test the figures against source data rather than taking them on trust",
            "Support budgeting and forecasting with analysis",
        ],
        "skills": [
            ("budgeting", 1.0),
            ("variance-analysis", 0.92),
            ("financial-modelling", 0.88),
            ("financial-reporting", 0.85),
            ("cash-flow-management", 0.82),
            ("data-visualization", 0.8),
            ("excel", 0.85),
            ("sql", 0.75),
            ("cost-accounting", 0.7),
            ("power-bi", 0.7),
            ("tableau", 0.65),
            ("internal-controls", 0.55),
            ("python", 0.6),
        ],
    },
    {
        "title": "Senior Financial Analyst",
        "slug": "senior-financial-analyst",
        "family": "Accounting & Finance",
        "seniority": "Senior",
        "min_years_experience": 5,
        "description": (
            "Own the model and the conversation it supports. A senior financial "
            "analyst builds the forecasts the company commits to, signs off the "
            "numbers that go to the board, and is the person the business asks when "
            "the model and reality disagree. The work is as much about being "
            "trusted with the answer as about producing it."
        ),
        "responsibilities": [
            "Own the forecasting model and the assumptions behind it",
            "Present the financial picture to senior stakeholders and the board",
            "Lead the budgeting cycle and the variance analysis that follows it",
            "Coach analysts and raise the standard of the reporting pack",
        ],
        "skills": [
            ("financial-modelling", 1.0),
            ("financial-reporting", 0.92),
            ("variance-analysis", 0.9),
            ("budgeting", 0.88),
            ("cash-flow-management", 0.85),
            ("cost-accounting", 0.75),
            ("data-visualization", 0.78),
            ("sql", 0.72),
            ("internal-controls", 0.7),
            ("regulatory-reporting", 0.65),
            ("power-bi", 0.68),
            ("python", 0.62),
            ("tax-compliance", 0.6),
            ("communication", 0.75),
        ],
    },
    {
        "title": "Civil Engineer",
        "slug": "civil-engineer",
        "family": "Civil & Electrical Engineering",
        "seniority": "Mid",
        "min_years_experience": 3,
        "description": (
            "Design the thing, draw it, and see that what is built matches. Civil "
            "engineers work from a survey and a set of constraints towards a drawing "
            "and a specification somebody can build from, and then they stay on the "
            "site long enough to check. Site safety and the quality of the work are "
            "as much the job as the design."
        ),
        "responsibilities": [
            "Design structures and produce the drawings and specifications",
            "Carry out site investigation and assess ground conditions",
            "Review construction quality and address site safety on the project",
            "Coordinate with contractors and manage the construction programme",
        ],
        "skills": [
            ("structural-analysis", 1.0),
            ("engineering-drawings", 0.92),
            ("autocad", 0.9),
            ("building-information-modelling", 0.85),
            ("site-investigation", 0.8),
            ("road-design", 0.75),
            ("health-and-safety-compliance", 0.72),
            ("construction-scheduling", 0.7),
            ("construction-quality-assurance", 0.7),
            ("technical-specification", 0.65),
            ("contract-management", 0.6),
            ("procurement", 0.6),
        ],
    },
    {
        "title": "Quantity Surveyor",
        "slug": "quantity-surveyor",
        "family": "Civil & Electrical Engineering",
        "seniority": "Mid",
        "min_years_experience": 3,
        "description": (
            "The commercial side of construction: what it will cost, what it has "
            "cost, and what the contract says about the difference. A quantity "
            "surveyor measures work, certifies payment, manages variations and "
            "administers the contract. Accuracy of the numbers and clarity of the "
            "paperwork are the whole job."
        ),
        "responsibilities": [
            "Measure and value the work, and certify payments",
            "Manage variations, valuations and contract documentation",
            "Advise on procurement and cost control across the project",
            "Report on cost against programme and explain the differences",
        ],
        "skills": [
            ("procurement", 1.0),
            ("contract-management", 0.92),
            ("cost-accounting", 0.88),
            ("budgeting", 0.85),
            ("technical-specification", 0.8),
            ("construction-scheduling", 0.72),
            ("construction-quality-assurance", 0.68),
            ("financial-reporting", 0.68),
            ("variance-analysis", 0.65),
            ("health-and-safety-compliance", 0.6),
            ("excel", 0.78),
            ("communication", 0.7),
        ],
    },
    {
        "title": "Marketing Manager",
        "slug": "marketing-manager",
        "family": "Marketing",
        "seniority": "Lead",
        "min_years_experience": 6,
        "description": (
            "Own the plan and the budget, and be accountable for what they produced. "
            "A marketing manager decides who the message is for, sets the position, "
            "runs the campaigns across paid, owned and earned channels, and reads "
            "the analytics to decide what happens next. Setting a positioning that "
            "nobody can execute is the failure mode, not a lack of ideas."
        ),
        "responsibilities": [
            "Set the positioning, the channel mix and the marketing budget",
            "Plan and run campaigns across paid, owned and earned channels",
            "Measure campaign performance and reallocate spend on the evidence",
            "Lead the team and hold the agency relationships",
        ],
        "skills": [
            ("campaign-management", 1.0),
            ("market-research", 0.9),
            ("marketing-analytics", 0.9),
            ("content-marketing", 0.85),
            ("brand-positioning", 0.82),
            ("customer-segmentation", 0.8),
            ("conversion-rate-optimisation", 0.75),
            ("search-engine-optimisation", 0.7),
            ("email-marketing", 0.7),
            ("social-media-marketing", 0.65),
            ("budgeting", 0.7),
            ("communication", 0.75),
        ],
    },
]


def main() -> int:
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    existing = {skill["slug"] for skill in taxonomy["skills"]}
    added = 0
    for name, slug, category, description, aliases in NEW_SKILLS:
        if slug in existing:
            continue
        taxonomy["skills"].append(
            {
                "name": name,
                "slug": slug,
                "category": category,
                "description": description,
                "aliases": aliases,
            }
        )
        existing.add(slug)
        added += 1
    taxonomy["skills"].sort(key=lambda skill: skill["name"].casefold())
    taxonomy["updated_at"] = "2026-10-20"
    TAXONOMY_PATH.write_text(
        json.dumps(taxonomy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    roles = json.loads(ROLES_PATH.read_text(encoding="utf-8"))
    known = {role["slug"] for role in roles["roles"]}
    role_count = 0
    for role in NEW_ROLES:
        if role["slug"] in known:
            continue
        payload = dict(role)
        payload["skills"] = [
            {"skill_slug": slug, "weight": weight} for slug, weight in role["skills"]
        ]
        roles["roles"].append(payload)
        known.add(role["slug"])
        role_count += 1
    roles["updated_at"] = "2026-10-20"
    ROLES_PATH.write_text(
        json.dumps(roles, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"skills added : {added} (total {len(taxonomy['skills'])})")
    print(f"roles added  : {role_count} (total {len(roles['roles'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
