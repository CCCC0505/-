from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from backend.models import ColdStartSession, DiagnosticAnswer, QuestionBank, QuestionnaireAnswer, Student
from backend.seed_data import QUESTIONNAIRE_QUESTIONS
from backend.services.common import json_loads, make_id
from backend.services.modeling import build_initial_snapshot, map_questionnaire_answers
from backend.services.portrait_service import PortraitService


class ColdStartService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portrait_service = PortraitService(db)

    def create_session(self, payload) -> Dict[str, object]:
        if payload.grade != "grade_8":
            raise ValueError("V1 仅开放初二数学演示")

        student = Student(student_id=make_id("stu"), name=payload.name.strip(), grade=payload.grade)
        self.db.add(student)
        self.db.flush()

        session = ColdStartSession(session_id=make_id("cold"), student_id=student.student_id, status="created")
        self.db.add(session)
        self.db.commit()

        return {
            "session_id": session.session_id,
            "student_id": student.student_id,
            "student_name": student.name,
            "grade": student.grade,
            "status": session.status,
            "questionnaire_questions": [
                {
                    "code": item["code"],
                    "title": item["title"],
                    "prompt": item["prompt"],
                    "trait_code": item["trait_code"],
                    "trait_name": item["trait_name"],
                    "options": [{"label": option["label"], "value": option["value"]} for option in item["options"]],
                }
                for item in QUESTIONNAIRE_QUESTIONS
            ],
            "diagnostic_questions": [
                {
                    "question_id": row.question_id,
                    "title": row.title,
                    "stem": row.stem,
                    "options": json_loads(row.options_json, []),
                    "difficulty": row.difficulty,
                    "knowledge_tags": json_loads(row.knowledge_tags_json, []),
                    "cognitive_level": row.cognitive_level,
                    "target_duration_seconds": row.target_duration_seconds,
                }
                for row in self._diagnostic_questions()
            ],
        }

    def submit_questionnaire(self, session_id: str, answers: List[Dict[str, str]]) -> Dict[str, object]:
        session = self._get_session(session_id)
        answer_map = {item["question_code"]: item["answer_value"] for item in answers}
        required_codes = {item["code"] for item in QUESTIONNAIRE_QUESTIONS}
        if set(answer_map) != required_codes:
            raise ValueError("问卷需要完整提交 6 个题目")

        self.db.query(QuestionnaireAnswer).filter(QuestionnaireAnswer.session_id == session_id).delete()
        trait_records = map_questionnaire_answers(answer_map.items())

        for question in QUESTIONNAIRE_QUESTIONS:
            option = next(item for item in question["options"] if item["value"] == answer_map[question["code"]])
            self.db.add(
                QuestionnaireAnswer(
                    session_id=session_id,
                    question_code=question["code"],
                    answer_value=answer_map[question["code"]],
                    mapped_trait_code=question["trait_code"],
                    mapped_trait_score=float(option["score"]),
                )
            )

        session.questionnaire_completed = True
        session.status = "questionnaire_done"
        self.db.commit()
        return {"session_id": session_id, "saved_count": len(trait_records), "trait_preview": trait_records}

    def submit_diagnostic(self, session_id: str, answers: List[Dict[str, object]]) -> Dict[str, object]:
        session = self._get_session(session_id)
        question_lookup = {row.question_id: row for row in self._diagnostic_questions()}
        answer_map = {item["question_id"]: item for item in answers}
        if set(answer_map) != set(question_lookup):
            raise ValueError("诊断卷需要完整提交 24 道题")

        self.db.query(DiagnosticAnswer).filter(DiagnosticAnswer.session_id == session_id).delete()
        correct_count = 0

        for question_id, item in answer_map.items():
            question = question_lookup[question_id]
            is_correct = str(item["answer_text"]).strip().upper() == question.correct_answer.strip().upper()
            correct_count += 1 if is_correct else 0
            self.db.add(
                DiagnosticAnswer(
                    session_id=session_id,
                    student_id=session.student_id,
                    question_id=question_id,
                    answer_text=str(item["answer_text"]).strip(),
                    is_correct=is_correct,
                    duration_seconds=float(item["duration_seconds"]),
                )
            )

        session.diagnostic_completed = True
        session.status = "diagnostic_done"
        accuracy = round(correct_count / len(question_lookup) * 100, 2)
        self.db.commit()
        return {"session_id": session_id, "saved_count": len(question_lookup), "correct_count": correct_count, "accuracy": accuracy}

    def finalize(self, session_id: str, qwen_client):
        session = self._get_session(session_id)
        if session.finalized:
            raise ValueError("该冷启动会话已经完成")
        if not (session.questionnaire_completed and session.diagnostic_completed):
            raise ValueError("请先完成问卷和诊断卷")

        student = self.db.query(Student).filter(Student.student_id == session.student_id).first()
        questionnaire_rows = (
            self.db.query(QuestionnaireAnswer)
            .filter(QuestionnaireAnswer.session_id == session_id)
            .order_by(QuestionnaireAnswer.id.asc())
            .all()
        )
        diagnostic_rows = (
            self.db.query(DiagnosticAnswer)
            .filter(DiagnosticAnswer.session_id == session_id)
            .order_by(DiagnosticAnswer.id.asc())
            .all()
        )

        question_lookup = {
            row.question_id: {
                "question_id": row.question_id,
                "title": row.title,
                "difficulty": row.difficulty,
                "target_duration_seconds": row.target_duration_seconds,
                "knowledge_tags": json_loads(row.knowledge_tags_json, []),
                "cognitive_level": row.cognitive_level,
                "dimension_weights": json_loads(row.dimension_weights_json, {}),
            }
            for row in self._diagnostic_questions()
        }

        trait_records = [
            {
                "trait_code": row.mapped_trait_code,
                "trait_name": next(item["trait_name"] for item in QUESTIONNAIRE_QUESTIONS if item["trait_code"] == row.mapped_trait_code),
                "trait_value": row.mapped_trait_score,
                "trait_label": self._trait_label_for(row.question_code, row.answer_value),
                "source": "questionnaire",
            }
            for row in questionnaire_rows
        ]

        snapshot_payload = build_initial_snapshot(
            diagnostic_answers=[
                {
                    "question_id": row.question_id,
                    "is_correct": row.is_correct,
                    "duration_seconds": row.duration_seconds,
                }
                for row in diagnostic_rows
            ],
            question_lookup=question_lookup,
            trait_records=trait_records,
        )

        ai_output, ai_run = qwen_client.analyze_cold_start(student.student_id, student.name, snapshot_payload)
        snapshot = self.portrait_service.create_snapshot(
            student_id=student.student_id,
            source_stage="cold_start",
            payload=snapshot_payload,
            ai_output=ai_output,
            parent_snapshot_id=None,
        )
        student.updated_at = datetime.utcnow()
        session.finalized = True
        session.status = "finalized"
        self.db.commit()
        self.db.refresh(snapshot)
        self.db.refresh(ai_run)
        return session, snapshot, ai_run

    def _diagnostic_questions(self):
        return (
            self.db.query(QuestionBank)
            .filter(QuestionBank.grade == "grade_8", QuestionBank.stage == "diagnostic")
            .order_by(QuestionBank.question_id.asc())
            .all()
        )

    def _get_session(self, session_id: str) -> ColdStartSession:
        session = self.db.query(ColdStartSession).filter(ColdStartSession.session_id == session_id).first()
        if session is None:
            raise ValueError("冷启动会话不存在")
        return session

    def _trait_label_for(self, question_code: str, answer_value: str) -> str:
        question = next(item for item in QUESTIONNAIRE_QUESTIONS if item["code"] == question_code)
        option = next(item for item in question["options"] if item["value"] == answer_value)
        return option["trait_label"]
