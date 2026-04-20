from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import PracticeAnswer, QuestionBank, RecommendationBatch, Student, WrongQuestionRecord
from backend.services.common import json_loads
from backend.services.modeling import summarize_snapshot_delta, update_snapshot_from_practice
from backend.services.portrait_service import PortraitService


class PracticeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portrait_service = PortraitService(db)

    def submit_answer(
        self,
        student_id: str,
        batch: RecommendationBatch,
        question: QuestionBank,
        answer_text: str,
        duration_seconds: float,
        qwen_client,
    ):
        student = self.db.query(Student).filter(Student.student_id == student_id).first()
        if student is None:
            raise ValueError("学生不存在")
        latest_snapshot = self.portrait_service.get_latest_snapshot(student_id)
        if latest_snapshot is None:
            raise ValueError("画像快照不存在")

        is_correct = answer_text.strip().upper() == question.correct_answer.strip().upper()
        current_payload = self.portrait_service.snapshot_to_payload(latest_snapshot)
        question_payload = {
            "question_id": question.question_id,
            "title": question.title,
            "difficulty": question.difficulty,
            "target_duration_seconds": question.target_duration_seconds,
            "knowledge_tags": json_loads(question.knowledge_tags_json, []),
            "cognitive_level": question.cognitive_level,
            "dimension_weights": json_loads(question.dimension_weights_json, {}),
        }
        new_payload = update_snapshot_from_practice(
            current_snapshot=current_payload,
            question_payload=question_payload,
            is_correct=is_correct,
            duration_seconds=duration_seconds,
        )
        dimension_deltas = self._dimension_deltas(current_payload, new_payload)
        delta_summary = summarize_snapshot_delta(current_payload, new_payload)
        practice_payload = {
            "question_id": question.question_id,
            "answer_text": answer_text.strip(),
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "duration_seconds": duration_seconds,
        }
        ai_output, ai_run = qwen_client.generate_practice_feedback(
            student_id=student_id,
            student_name=student.name,
            question_payload={
                "title": question.title,
                "stem": question.stem,
                "knowledge_tags": question_payload["knowledge_tags"],
                "difficulty": question.difficulty,
            },
            practice_payload=practice_payload,
            delta_summary=delta_summary,
        )
        snapshot = self.portrait_service.create_snapshot(
            student_id=student_id,
            source_stage="practice",
            payload=new_payload,
            ai_output={
                "portrait_summary": new_payload["fallback_summary"],
                "teacher_commentary": ai_output["feedback_summary"],
                "training_focus": new_payload["training_focus"],
                "risk_flags": new_payload["risk_flags"],
                "confidence": ai_output["confidence"],
            },
            parent_snapshot_id=latest_snapshot.snapshot_id,
        )
        self.db.add(
            PracticeAnswer(
                student_id=student_id,
                batch_id=batch.batch_id,
                snapshot_id=snapshot.snapshot_id,
                question_id=question.question_id,
                answer_text=answer_text.strip(),
                is_correct=is_correct,
                duration_seconds=duration_seconds,
                feedback_summary=ai_output["feedback_summary"],
                ai_run_id=ai_run.run_id,
            )
        )
        student.updated_at = datetime.utcnow()
        self._update_wrong_question(student_id, question, is_correct, ai_output)
        self.db.commit()
        self.db.refresh(snapshot)
        self.db.refresh(ai_run)
        return {
            "student_id": student_id,
            "batch_id": batch.batch_id,
            "question_id": question.question_id,
            "is_correct": is_correct,
            "correct_answer": question.correct_answer,
            "reference_explanation": question.explanation,
            "feedback_summary": ai_output["feedback_summary"],
            "next_steps": ai_output["next_steps"],
            "dimension_deltas": dimension_deltas,
            "snapshot": self.portrait_service.snapshot_to_response(snapshot),
            "ai_run": ai_run,
        }

    def _update_wrong_question(self, student_id: str, question: QuestionBank, is_correct: bool, ai_output):
        record = (
            self.db.query(WrongQuestionRecord)
            .filter(WrongQuestionRecord.student_id == student_id, WrongQuestionRecord.question_id == question.question_id)
            .first()
        )
        if is_correct:
            if record:
                record.status = "resolved"
                record.qwen_summary = ai_output["feedback_summary"]
            return
        if record is None:
            record = WrongQuestionRecord(
                student_id=student_id,
                question_id=question.question_id,
                wrong_count=1,
                status="open",
                root_cause_summary="；".join(ai_output.get("mistake_analysis", [])[:2]),
                qwen_summary=ai_output["feedback_summary"],
                last_wrong_at=datetime.utcnow(),
            )
            self.db.add(record)
        else:
            record.wrong_count += 1
            record.status = "open"
            record.root_cause_summary = "；".join(ai_output.get("mistake_analysis", [])[:2]) or record.root_cause_summary
            record.qwen_summary = ai_output["feedback_summary"]
            record.last_wrong_at = datetime.utcnow()

    def _dimension_deltas(self, previous_snapshot, new_snapshot):
        previous_map = {item["dimension_code"]: float(item["score"]) for item in previous_snapshot["dimensions"]}
        rows = []
        for item in new_snapshot["dimensions"]:
            previous_score = previous_map.get(item["dimension_code"], float(item["score"]))
            current_score = float(item["score"])
            rows.append(
                {
                    "dimension_code": item["dimension_code"],
                    "dimension_name": item["dimension_name"],
                    "previous_score": round(previous_score, 2),
                    "current_score": round(current_score, 2),
                    "delta": round(current_score - previous_score, 2),
                }
            )
        rows.sort(key=lambda row: abs(row["delta"]), reverse=True)
        return rows
