import argparse

from backend.database import SessionLocal, init_database
from backend.services.bootstrap import seed_question_bank


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the grade-8 AI demo database.")
    parser.add_argument("--reset", action="store_true", help="Reset the question bank before seeding.")
    args = parser.parse_args()

    init_database()
    db = SessionLocal()
    try:
        total = seed_question_bank(db, reset=args.reset)
        print(f"question-bank-ready:{total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
