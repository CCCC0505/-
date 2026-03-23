from sqlalchemy.orm import Session

from backend.models import QuestionBank
from backend.seed_data import all_questions
from backend.services.common import json_dumps


def seed_question_bank(db: Session, reset: bool = False) -> int:
    if reset:
        db.query(QuestionBank).delete()
        db.commit()

    if db.query(QuestionBank).count() > 0:
        return db.query(QuestionBank).count()

    for row in all_questions():
        db.add(
            QuestionBank(
                question_id=row["question_id"],
                grade=row["grade"],
                stage=row["stage"],
                title=row["title"],
                stem=row["stem"],
                options_json=json_dumps(row["options"]),
                correct_answer=row["correct_answer"],
                explanation=row["explanation"],
                difficulty=row["difficulty"],
                target_duration_seconds=row["target_duration_seconds"],
                knowledge_tags_json=json_dumps(row["knowledge_tags"]),
                cognitive_level=row["cognitive_level"],
                dimension_weights_json=json_dumps(row["dimension_weights"]),
                training_tags_json=json_dumps(row["training_tags"]),
            )
        )
    db.commit()
    return db.query(QuestionBank).count()
