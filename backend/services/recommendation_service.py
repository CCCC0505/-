from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.models import PracticeAnswer, QuestionBank, RecommendationBatch, RecommendationItem, Student, WrongQuestionRecord
from backend.services.common import json_dumps, json_loads, make_id, mean
from backend.services.portrait_service import PortraitService


class RecommendationService:
    TRAINING_MODE_LABELS = {
        "weakness": "刷弱项",
        "accuracy": "稳定正确率",
        "challenge": "挑战提升",
        "balanced": "平衡训练",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.portrait_service = PortraitService(db)

    def generate(self, student_id: str, requested_count: int, training_mode: str = "balanced") -> Tuple[RecommendationBatch, List[Dict[str, object]], Dict[str, object]]:
        student = self.db.query(Student).filter(Student.student_id == student_id).first()
        if student is None:
            raise ValueError("学生不存在")

        latest_snapshot = self.portrait_service.get_latest_snapshot(student_id)
        if latest_snapshot is None:
            raise ValueError("请先完成冷启动画像")

        previous_snapshot = self.portrait_service.get_previous_snapshot(student_id, latest_snapshot.snapshot_id)
        snapshot_payload = self.portrait_service.snapshot_to_payload(latest_snapshot)
        previous_payload = self.portrait_service.snapshot_to_payload(previous_snapshot) if previous_snapshot else None

        candidates = (
            self.db.query(QuestionBank)
            .filter(QuestionBank.grade == student.grade, QuestionBank.stage == "practice")
            .order_by(QuestionBank.question_id.asc())
            .all()
        )
        answered_questions = {
            row.question_id
            for row in self.db.query(PracticeAnswer.question_id).filter(PracticeAnswer.student_id == student_id).all()
        }
        wrong_rows = self.db.query(WrongQuestionRecord).filter(WrongQuestionRecord.student_id == student_id).all()
        wrong_question_ids = {row.question_id for row in wrong_rows if row.status == "open"}

        scored = [
            self._score_candidate(
                question=question,
                current_snapshot=snapshot_payload,
                previous_snapshot=previous_payload,
                answered_questions=answered_questions,
                wrong_question_ids=wrong_question_ids,
                training_mode=training_mode,
            )
            for question in candidates
        ]

        selected = self._select_by_quota(scored, requested_count=max(3, requested_count), training_mode=training_mode)
        batch = RecommendationBatch(
            batch_id=make_id("batch"),
            student_id=student_id,
            snapshot_id=latest_snapshot.snapshot_id,
            requested_count=requested_count,
            training_mode=training_mode,
            training_focus_json=json_dumps(snapshot_payload["training_focus"]),
            overall_commentary="",
            ai_run_id=None,
        )
        self.db.add(batch)
        self.db.flush()

        response_items = []
        for item in selected:
            self.db.add(
                RecommendationItem(
                    batch_id=batch.batch_id,
                    question_id=item["question_id"],
                    recommendation_type=item["recommendation_type"],
                    rank_score=item["rank_score"],
                    rule_reason=item["rule_reason"],
                    ai_reason="",
                )
            )
            response_items.append(item)

        self.db.commit()
        self.db.refresh(batch)
        return batch, response_items, snapshot_payload

    def apply_ai_output(self, batch_id: str, ai_output: Dict[str, object], ai_run_id: str) -> None:
        batch = self.db.query(RecommendationBatch).filter(RecommendationBatch.batch_id == batch_id).first()
        if batch is None:
            return

        batch.overall_commentary = str(ai_output.get("overall_commentary", ""))
        batch.training_focus_json = json_dumps(ai_output.get("training_focus", []))
        batch.ai_run_id = ai_run_id

        reason_map = {item["question_id"]: item["reason"] for item in ai_output.get("item_reasons", []) if item["question_id"]}
        rows = self.db.query(RecommendationItem).filter(RecommendationItem.batch_id == batch_id).all()
        for row in rows:
            row.ai_reason = reason_map.get(row.question_id, row.rule_reason)
        self.db.commit()

    def batch_to_response(self, batch: RecommendationBatch) -> Dict[str, object]:
        items = (
            self.db.query(RecommendationItem, QuestionBank)
            .join(QuestionBank, RecommendationItem.question_id == QuestionBank.question_id)
            .filter(RecommendationItem.batch_id == batch.batch_id)
            .order_by(RecommendationItem.rank_score.desc(), RecommendationItem.id.asc())
            .all()
        )
        latest_practice_map = self._latest_practice_map(batch.batch_id)
        progress = self._build_progress(batch.batch_id, items)
        batch_meta = self._build_batch_meta(items, json_loads(batch.training_focus_json, []), batch.training_mode)
        return {
            "batch_id": batch.batch_id,
            "training_mode": batch.training_mode,
            "training_mode_label": self.TRAINING_MODE_LABELS.get(batch.training_mode, "平衡训练"),
            "batch_goal": batch_meta["batch_goal"],
            "batch_tags": batch_meta["batch_tags"],
            "difficulty_distribution": batch_meta["difficulty_distribution"],
            "type_distribution": batch_meta["type_distribution"],
            "knowledge_distribution": batch_meta["knowledge_distribution"],
            "training_focus": json_loads(batch.training_focus_json, []),
            "overall_commentary": batch.overall_commentary,
            "progress": progress,
            "items": [
                {
                    "question_id": question.question_id,
                    "title": question.title,
                    "stem": question.stem,
                    "options": json_loads(question.options_json, []),
                    "explanation": question.explanation,
                    "difficulty": question.difficulty,
                    "target_duration_seconds": question.target_duration_seconds,
                    "knowledge_tags": json_loads(question.knowledge_tags_json, []),
                    "recommendation_type": row.recommendation_type,
                    "rule_reason": row.rule_reason,
                    "ai_reason": row.ai_reason or row.rule_reason,
                    "completed": question.question_id in latest_practice_map,
                    "last_result": latest_practice_map[question.question_id]["is_correct"] if question.question_id in latest_practice_map else None,
                    "last_feedback_summary": latest_practice_map[question.question_id]["feedback_summary"] if question.question_id in latest_practice_map else None,
                    "last_practiced_at": latest_practice_map[question.question_id]["created_at"] if question.question_id in latest_practice_map else None,
                }
                for row, question in items
            ],
        }

    def latest_summary(self, student_id: str):
        batch = (
            self.db.query(RecommendationBatch)
            .filter(RecommendationBatch.student_id == student_id)
            .order_by(RecommendationBatch.created_at.desc(), RecommendationBatch.id.desc())
            .first()
        )
        if batch is None:
            return None
        return self.batch_to_response(batch)

    def _score_candidate(
        self,
        question: QuestionBank,
        current_snapshot: Dict[str, object],
        previous_snapshot: Optional[Dict[str, object]],
        answered_questions: set[str],
        wrong_question_ids: set[str],
        training_mode: str,
    ) -> Dict[str, object]:
        dimension_scores = {item["dimension_code"]: float(item["score"]) for item in current_snapshot["dimensions"]}
        knowledge_scores = {item["knowledge_tag"]: float(item["mastery_score"]) for item in current_snapshot["knowledge_matrix"]}
        previous_dimension_scores = (
            {item["dimension_code"]: float(item["score"]) for item in previous_snapshot["dimensions"]} if previous_snapshot else {}
        )
        question_dimensions = json_loads(question.dimension_weights_json, {})
        knowledge_tags = json_loads(question.knowledge_tags_json, [])

        dimension_need = mean([100.0 - dimension_scores.get(code, 60.0) for code in question_dimensions], default=35.0)
        knowledge_need = mean([100.0 - knowledge_scores.get(tag, 60.0) for tag in knowledge_tags], default=35.0)
        decline_bonus = mean(
            [max(previous_dimension_scores.get(code, dimension_scores.get(code, 60.0)) - dimension_scores.get(code, 60.0), 0.0) for code in question_dimensions],
            default=0.0,
        )
        average_dimension = mean(dimension_scores.values(), default=60.0)
        difficulty_target = 1 if average_dimension < 55 else 2 if average_dimension < 75 else 3
        if training_mode == "weakness":
            difficulty_target = max(1, difficulty_target - 1)
        elif training_mode == "challenge":
            difficulty_target = min(3, difficulty_target + 1)
        elif training_mode == "accuracy":
            difficulty_target = 2
        difficulty_fit = max(0.0, 12.0 - abs(question.difficulty - difficulty_target) * 4.0)
        wrong_bonus = 10.0 if question.question_id in wrong_question_ids else 0.0
        novelty_bonus = 6.0 if question.question_id not in answered_questions else -10.0
        challenge_bonus = 8.0 if training_mode == "challenge" and question.difficulty >= 3 else 0.0
        if training_mode == "weakness":
            rank_score = round(0.46 * dimension_need + 0.40 * knowledge_need + decline_bonus + difficulty_fit + wrong_bonus * 1.2 + novelty_bonus, 2)
        elif training_mode == "accuracy":
            rank_score = round(0.28 * dimension_need + 0.26 * knowledge_need + decline_bonus + difficulty_fit * 1.4 + wrong_bonus + novelty_bonus * 0.7, 2)
        elif training_mode == "challenge":
            rank_score = round(0.26 * dimension_need + 0.22 * knowledge_need + decline_bonus * 1.2 + difficulty_fit + wrong_bonus * 0.7 + novelty_bonus + challenge_bonus, 2)
        else:
            rank_score = round(0.38 * dimension_need + 0.34 * knowledge_need + decline_bonus + difficulty_fit + wrong_bonus + novelty_bonus, 2)

        recommendation_type = self._recommendation_type(dimension_need, knowledge_need, question.difficulty)
        if training_mode == "weakness":
            if recommendation_type == "补弱题":
                rank_score += 18
            elif recommendation_type == "提升题":
                rank_score -= 10
        elif training_mode == "accuracy":
            if question.difficulty == 2:
                rank_score += 14
            if recommendation_type == "巩固题":
                rank_score += 10
        elif training_mode == "challenge":
            if recommendation_type == "提升题":
                rank_score += 18
            if question.difficulty >= 3:
                rank_score += 12
            if recommendation_type == "补弱题":
                rank_score -= 8
        weak_dimensions = sorted(question_dimensions, key=lambda code: dimension_scores.get(code, 60.0))[:2]
        weak_dimension_names = [next(item["dimension_name"] for item in current_snapshot["dimensions"] if item["dimension_code"] == code) for code in weak_dimensions]
        weak_knowledge = sorted(knowledge_tags, key=lambda tag: knowledge_scores.get(tag, 60.0))[:2]
        rule_reason = (
            f"匹配当前较弱的 {('、'.join(weak_dimension_names) or '基础能力')}，"
            f"并围绕 {('、'.join(weak_knowledge) or '核心知识点')} 做 {recommendation_type}。"
        )

        return {
            "question_id": question.question_id,
            "title": question.title,
            "stem": question.stem,
            "options": json_loads(question.options_json, []),
            "difficulty": question.difficulty,
            "target_duration_seconds": question.target_duration_seconds,
            "knowledge_tags": knowledge_tags,
            "recommendation_type": recommendation_type,
            "rule_reason": rule_reason,
            "rank_score": rank_score,
        }

    def _recommendation_type(self, dimension_need: float, knowledge_need: float, difficulty: int) -> str:
        if dimension_need >= 45 or knowledge_need >= 45 or difficulty <= 1:
            return "补弱题"
        if difficulty == 2 or max(dimension_need, knowledge_need) >= 25:
            return "巩固题"
        return "提升题"

    def _select_by_quota(self, scored_items: List[Dict[str, object]], requested_count: int, training_mode: str) -> List[Dict[str, object]]:
        order = ["补弱题", "巩固题", "提升题"]
        if training_mode == "weakness":
            quotas = {"补弱题": max(2, requested_count - 2), "巩固题": 1, "提升题": 1 if requested_count >= 4 else 0}
        elif training_mode == "accuracy":
            quotas = {"补弱题": 1, "巩固题": max(2, requested_count - 2), "提升题": 1 if requested_count >= 4 else 0}
        elif training_mode == "challenge":
            quotas = {"补弱题": 1 if requested_count >= 4 else 0, "巩固题": 1, "提升题": max(2, requested_count - 2)}
        else:
            quotas = {"补弱题": requested_count // 3, "巩固题": requested_count // 3, "提升题": requested_count // 3}
            remainder = requested_count % 3
            for idx in range(remainder):
                quotas[order[idx]] += 1

        grouped = defaultdict(list)
        for item in sorted(scored_items, key=lambda row: row["rank_score"], reverse=True):
            grouped[item["recommendation_type"]].append(item)

        selected = []
        selected_ids = set()
        for bucket in order:
            for item in grouped[bucket]:
                if len([row for row in selected if row["recommendation_type"] == bucket]) >= quotas[bucket]:
                    break
                if item["question_id"] in selected_ids:
                    continue
                selected.append(item)
                selected_ids.add(item["question_id"])

        if len(selected) < requested_count:
            for item in sorted(scored_items, key=lambda row: row["rank_score"], reverse=True):
                if item["question_id"] in selected_ids:
                    continue
                selected.append(item)
                selected_ids.add(item["question_id"])
                if len(selected) >= requested_count:
                    break

        return selected[:requested_count]

    def _latest_practice_map(self, batch_id: str) -> Dict[str, Dict[str, object]]:
        rows = (
            self.db.query(PracticeAnswer)
            .filter(PracticeAnswer.batch_id == batch_id)
            .order_by(PracticeAnswer.created_at.desc(), PracticeAnswer.id.desc())
            .all()
        )
        latest = {}
        for row in rows:
            if row.question_id in latest:
                continue
            latest[row.question_id] = {
                "is_correct": row.is_correct,
                "feedback_summary": row.feedback_summary,
                "created_at": row.created_at.isoformat(),
            }
        return latest

    def _build_progress(self, batch_id: str, items) -> Dict[str, object]:
        total_questions = len(items)
        latest_practice_map = self._latest_practice_map(batch_id)
        completed_questions = len(latest_practice_map)
        correct_count = sum(1 for value in latest_practice_map.values() if value["is_correct"])
        unanswered_durations = [
            question.target_duration_seconds
            for _, question in items
            if question.question_id not in latest_practice_map
        ]
        estimated_minutes_remaining = round(sum(unanswered_durations) / 60) if unanswered_durations else 0
        completion_rate = round((completed_questions / total_questions) * 100, 2) if total_questions else 0.0
        if completed_questions == 0:
            status = "not_started"
        elif completed_questions < total_questions:
            status = "in_progress"
        else:
            status = "completed"
        return {
            "total_questions": total_questions,
            "completed_questions": completed_questions,
            "correct_count": correct_count,
            "completion_rate": completion_rate,
            "estimated_minutes_remaining": estimated_minutes_remaining,
            "status": status,
        }

    def _build_batch_meta(self, items, training_focus: List[str], training_mode: str) -> Dict[str, object]:
        difficulty_counts = {}
        type_counts = {}
        tags = []
        for row, question in items:
            difficulty_counts[question.difficulty] = difficulty_counts.get(question.difficulty, 0) + 1
            type_counts[row.recommendation_type] = type_counts.get(row.recommendation_type, 0) + 1
            tags.extend(json_loads(question.knowledge_tags_json, []))
        top_tags = []
        for tag in tags:
            if tag not in top_tags:
                top_tags.append(tag)
        knowledge_counts = {}
        for tag in tags:
            knowledge_counts[tag] = knowledge_counts.get(tag, 0) + 1
        if training_mode == "weakness":
            batch_goal = "优先修复当前薄弱点，建立更稳定的基础表现"
        elif training_mode == "accuracy":
            batch_goal = "围绕稳定正确率设计训练节奏，先稳住当前掌握水平"
        elif training_mode == "challenge":
            batch_goal = "在可控范围内提升题目挑战度，拉高迁移与上限"
        elif any("补强知识点" in focus or "优先修复" in focus for focus in training_focus):
            batch_goal = "优先修复当前薄弱点，建立更稳定的基础表现"
        else:
            batch_goal = "围绕当前成长画像推进分层训练，保持稳定提升"
        return {
            "batch_goal": batch_goal,
            "batch_tags": [self.TRAINING_MODE_LABELS.get(training_mode, "平衡训练")] + top_tags[:3],
            "difficulty_distribution": [
                {"level": level, "count": count}
                for level, count in sorted(difficulty_counts.items(), key=lambda item: item[0])
            ],
            "type_distribution": [
                {"label": label, "count": count}
                for label, count in sorted(type_counts.items(), key=lambda item: item[0])
            ],
            "knowledge_distribution": [
                {"label": label, "count": count}
                for label, count in sorted(knowledge_counts.items(), key=lambda item: item[1], reverse=True)[:6]
            ],
        }
