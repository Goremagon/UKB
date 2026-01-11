import getpass

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User


def create_admin_user() -> None:
    init_db()
    username = input("Enter admin username: ").strip()
    if not username:
        raise SystemExit("Username is required.")

    password = getpass.getpass("Enter admin password: ").strip()
    if not password:
        raise SystemExit("Password is required.")

    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise SystemExit("User already exists.")

        user = User(
            username=username,
            hashed_password=hash_password(password),
            role="Admin",
        )
        db.add(user)
        db.commit()
        print(f"Admin user '{username}' created.")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
