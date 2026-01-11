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


def generate_text(title: str, unique_id: str, variant: int) -> str:
    specific_entries = {
        1: "Article 9: Seniority, Bumping Rights, and Recall Procedures.",
        2: "Grievance #2024-01: Denial of Overtime for Night Shift Differential.",
        3: "Health and Welfare: Kaiser vs. Blue Cross coverage tiers.",
        4: "Arbitration Ruling on Just Cause for termination regarding safety violations.",
    }
    seed_line = specific_entries.get(variant, f"Local 2024 Update: {title}")
    paragraphs = [
        f"[{unique_id}] Union Knowledge Base Seed Document: {title}",
        seed_line,
        "This memorandum outlines bargaining history, shop-floor practices, and steward notes.",
        "Key terms: seniority ladders, bumping rights, recall lists, grievance steps, and arbitration timelines.",
        "Operational directives include overtime equalization, safety committee findings, and wage scale alignment.",
        "Witness notes and remedy proposals are documented for case tracking and compliance follow-up.",
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
        unique_id = f"UKB-TEST-{index + 1:02d}"
        content = generate_text(title, unique_id, index + 1)
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
