import os
import random
import uuid

# Define some templates for synthetic messy documents
TEMPLATES = [
    # Medical Clinical Log
    "CLINICAL LOG - ID: {id} - DATE: {date}\nPatient {name}, age {age}, presented with {symptom}.\n"
    "Diagnosis: {diagnosis}. Treatment: Prescribed {treatment} at {dosage}.\n"
    "Notes:   The patient reports a history of {history}.   Follow up scheduled in {follow_up_weeks} weeks.  \n"
    "Confidential Medical Record - For Internal Use Only.",
    
    # IT Support Ticket
    "SUPPORT TICKET #{ticket_id}\nPriority: {priority}\nCategory: Network & Infrastructure\n"
    "Description:\n  User {username} reported that {service} is experiencing {issue}.\n"
    "Steps taken by engineer {engineer}:\n1. Pinged the host ({ip_address}).\n"
    "2. Restarted the {service} service.\n"
    "3. Log message observed: '{log_msg}'\nStatus: {status}.\nResolution Notes: {resolution}.",
    
    # Corporate Policy / SOP
    "STANDARD OPERATING PROCEDURE: SOP-{sop_id}\nSection: Human Resources and Operations\n"
    "Subject: {subject}\nEffective Date: {date}\n\n"
    "Purpose:   This document outlines the policy for {subject} at Enterprise Corp.   \n\n"
    "Guidelines:\n"
    "- Employees must request approval from {approval_role} at least {days} days in advance.\n"
    "- Maximum limit per calendar year is {limit}.\n"
    "- Any exceptions must be approved in writing by the VP of Human Resources.\n"
    "Violations of this policy will lead to disciplinary action.",
    
    # Server / Security Log
    "SECURITY AUDIT SYSLOG - HOSTNAME: {host} - TIMESTAMP: {date}T{time}Z\n"
    "EVENT ID: SEC-{event_id}\n"
    "Severity: {severity}\n"
    "Payload:\n"
    "  IP Source: {ip_address}\n"
    "  Request Method: {method} {path}\n"
    "  Response Code: {code}\n"
    "  Action Taken: {action_taken}\n"
    "  Analysis:   Suspicious user agent string '{user_agent}' detected. Origin Country: {country}."
]

NAMES = ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince", "Evan Wright", "Fiona Gallagher", "George Costanza", "Helen Mirren"]
SYMPTOMS = ["chronic migraine", "mild fever and dry cough", "acute lower back pain", "persistent fatigue", "sudden skin rash", "elevated blood pressure"]
DIAGNOSES = ["tension headache", "suspected viral infection", "lumbar muscle strain", "idiopathic fatigue syndrome", "contact dermatitis", "essential hypertension"]
TREATMENTS = ["Ibuprofen", "Acetaminophen", "Physical Therapy", "Vitamin D supplements", "Hydrocortisone cream", "Lisinopril"]
DOSAGES = ["400mg twice daily", "500mg as needed", "twice weekly sessions", "2000 IU daily", "apply thin layer twice daily", "10mg once daily"]
HISTORIES = ["diabetes mellitus", "seasonal allergies", "mild asthma", "no significant history", "hypothyroidism"]

SERVICES = ["Database Gateway", "OAuth Authentication", "User Profile Service", "Payment Gateway", "File Upload Broker", "Search API Indexer"]
ISSUES = ["extremely high latency (over 5000ms)", "frequent connection timeouts", "out of memory crash (OOM)", "corrupt database socket files", "unauthorized access attempts"]
ENGINEERS = ["Ken Thompson", "Dennis Ritchie", "Linus Torvalds", "Grace Hopper", "Ada Lovelace", "Guido van Rossum"]
LOG_MSGS = ["Connection pool exhausted", "Heap space out of memory", "NullPointerException at line 104", "SSL Handshake Failed", "Broken pipe on write socket"]
STATUSES = ["Resolved", "Escalated", "Closed", "Pending Vendor Analysis"]
RESOLUTIONS = ["Rebooted secondary node and scaled replica count", "Cleaned Docker heap caches and increased JVM memory limits", "Applied security patch and rotated private TLS keys", "Re-indexed partition tables and cleared bad cache locks"]

SUBJECTS = ["Remote Work Reimbursement", "Parental Leave Policy", "Corporate Travel Expense Limits", "Information Security Guidelines", "Employee Anti-Harassment", "Annual Performance Evaluation"]
ROLES = ["Direct Manager", "Department Head", "HR Business Partner", "Managing Director"]

HOSTS = ["prod-web-01", "prod-db-master", "auth-token-broker-02", "payment-api-04", "k8s-ingress-controller"]
SEVERITIES = ["CRITICAL", "WARNING", "INFO", "ALERT"]
METHODS = ["POST", "GET", "PUT", "DELETE", "PATCH"]
PATHS = ["/api/v1/auth/login", "/api/v2/payment/charge", "/admin/database/truncate", "/api/v1/users/profile", "/static/images/hero.jpg"]
ACTIONS = ["BLOCKED", "ALLOWED - FLAGGED FOR REVIEW", "RATE-LIMITED", "REDIRECTED TO HONEYPOT"]
USER_AGENTS = ["Mozilla/5.0 (compatible; MassScanner/1.0)", "curl/7.81.0", "Python-urllib/3.9", "Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36"]
COUNTRIES = ["United States", "Germany", "Romania", "China", "Russia", "Brazil", "India", "Netherlands"]

def generate_random_doc(index: int) -> str:
    template_idx = index % len(TEMPLATES)
    # Generate random parameters
    unique_id = str(uuid.uuid4())[:8]
    date = f"2026-0{random.randint(1,7)}-{random.randint(10,28)}"
    time = f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
    
    if template_idx == 0:
        return TEMPLATES[0].format(
            id=unique_id,
            date=date,
            name=random.choice(NAMES),
            age=random.randint(18, 85),
            symptom=random.choice(SYMPTOMS),
            diagnosis=random.choice(DIAGNOSES),
            treatment=random.choice(TREATMENTS),
            dosage=random.choice(DOSAGES),
            history=random.choice(HISTORIES),
            follow_up_weeks=random.randint(1, 12)
        )
    elif template_idx == 1:
        return TEMPLATES[1].format(
            ticket_id=10000 + index,
            priority=random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            username=random.choice(NAMES).lower().replace(" ", "."),
            service=random.choice(SERVICES),
            issue=random.choice(ISSUES),
            engineer=random.choice(ENGINEERS),
            ip_address=f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            log_msg=random.choice(LOG_MSGS),
            status=random.choice(STATUSES),
            resolution=random.choice(RESOLUTIONS)
        )
    elif template_idx == 2:
        return TEMPLATES[2].format(
            sop_id=2000 + index,
            subject=random.choice(SUBJECTS),
            date=date,
            approval_role=random.choice(ROLES),
            days=random.randint(2, 30),
            limit=random.choice(["$500 per incident", "12 weeks per birth/adoption", "$2,000 per fiscal year", "Unlimited with written notice"])
        )
    else:
        return TEMPLATES[3].format(
            host=random.choice(HOSTS),
            date=date,
            time=time,
            event_id=5000 + index,
            severity=random.choice(SEVERITIES),
            ip_address=f"192.168.{random.randint(1,254)}.{random.randint(1,254)}",
            method=random.choice(METHODS),
            path=random.choice(PATHS),
            code=random.choice([200, 401, 403, 404, 500]),
            action_taken=random.choice(ACTIONS),
            user_agent=random.choice(USER_AGENTS),
            country=random.choice(COUNTRIES)
        )

DATA_DIR = "./data"

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Generating 1,000 synthetic corporate documents in '{DATA_DIR}'...")
    
    # We will write 1,000 files
    for i in range(1000):
        doc_content = generate_random_doc(i)
        filename = f"doc_{i:04d}.txt"
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(doc_content)
            
    print("Dataset generation completed successfully.")

if __name__ == "__main__":
    main()

