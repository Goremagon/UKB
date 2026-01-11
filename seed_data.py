import random
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User
from app.services.ingestion import ingest_file

DOC_TYPES = ["CBA", "Grievance", "Policy", "Arbitration", "Other"]
DEPARTMENTS = ["Operations", "Safety", "HR"]
CBA_ARTICLES = [
    "Seniority and Layoffs",
    "Wage Scales 2024",
    "Health and Welfare Benefits",
]
GRIEVANCE_LOGS = [
    "Case #882: Unjust Discharge",
    "Case #912: Safety Violation in South Yard",
]
POLICY_MANUALS = [
    "Standard Operating Procedures v4",
    "Steward Handbook",
]
PASSWORDS = {
    "admin_test": ("Admin", "admin_test_pw"),
    "steward_test": ("Steward", "steward_test_pw"),
    "viewer_test": ("Read-only", "viewer_test_pw"),
}


def seed_users(db: Session) -> None:
    for username, (role, password) in PASSWORDS.items():
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            continue
        user = User(username=username, hashed_password=hash_password(password), role=role)
        db.add(user)
    db.commit()


UNION_CLAUSES = {
    "Seniority Bidding": "Seniority Bidding rules govern shift selection and displacement order.",
    "Just Cause Termination": "Just Cause Termination standards require documented progressive discipline.",
    "Health & Welfare Tiers": "Health & Welfare Tiers outline Kaiser vs. Blue Cross coverage tiers.",
    "Grievance Timelines": "Grievance Timelines specify step meetings within 5 business days.",
    "Overtime Equalization": "Overtime Equalization ensures fair distribution across classifications.",
    "Safety Committees": "Safety Committees must review incident reports within 48 hours.",
    "Wage Progression": "Wage Progression schedules define annual step increases.",
    "Bumping Rights": "Bumping Rights allow senior employees to displace junior roles.",
    "Recall Procedures": "Recall Procedures require written notice by certified mail.",
    "Training Standards": "Training Standards mandate certification before operating equipment.",
    "Shift Differential": "Shift Differential premiums apply to night shift hours.",
    "Attendance Policy": "Attendance Policy outlines point thresholds and corrective action.",
}


def generate_text(title: str, unique_id: str) -> str:
    clause_keys = random.sample(list(UNION_CLAUSES.keys()), k=4)
    clause_lines = [UNION_CLAUSES[key] for key in clause_keys]
    paragraphs = [
        f"[{unique_id}] Union Knowledge Base Seed Document: {title}",
        f"Control ID: [{unique_id}]",
        "This memorandum provides high-fidelity labor guidance for stewards and bargaining teams.",
        "Core clauses:",
        *clause_lines,
        "Notes include bargaining history, steward interviews, and compliance checkpoints.",
    ]
    return "\n\n".join(paragraphs)


def create_pdf(file_path: Path, title: str, content: str) -> None:
    pdf = canvas.Canvas(str(file_path), pagesize=letter)
    width, height = letter
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 50, title)
    pdf.setFont("Helvetica", 11)
    y = height - 80
    for line in content.split("\n"):
        if y < 60:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 60
        pdf.drawString(50, y, line)
        y -= 16
    pdf.save()


def seed_documents(db: Session, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    titles = []
    for item in CBA_ARTICLES:
        titles.append(item)
    for item in GRIEVANCE_LOGS:
        titles.append(item)
    for item in POLICY_MANUALS:
        titles.append(item)

    while len(titles) < 50:
        suffix = len(titles) + 1
        titles.append(f"Union Case File #{900 + suffix}: Workplace Review")

    random.shuffle(titles)
    sensitive_count = int(len(titles) * 0.2)

    for index, title in enumerate(titles):
        filename = f"seed_{index + 1:02d}.pdf"
        file_path = output_dir / filename
        unique_id = f"CBA-2026-{index + 1:02d}"
        content = generate_text(title, unique_id)
        create_pdf(file_path, title, content)
        metadata = {
            "doc_type": random.choice(DOC_TYPES),
            "department": random.choice(DEPARTMENTS),
            "date_published": date.today(),
            "tags": ["union", "contract", "case"],
            "is_sensitive": index < sensitive_count,
        }
        try:
            ingest_file(
                db=db,
                file_path=file_path.as_posix(),
                filename=filename,
                metadata=metadata,
                user_id=None,
            )
        except ValueError:
            continue


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
        output_dir = Path("data") / "seed_pdfs"
        seed_documents(db, output_dir)
    finally:
        db.close()


if __name__ == "__main__":
    main()
