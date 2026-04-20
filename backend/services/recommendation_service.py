from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import exp
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.models import DiagnosticAnswer, PortraitSnapshot, PracticeAnswer, QuestionBank, RecommendationBatch, RecommendationItem, Student, WrongQuestionRecord
from backend.services.common import json_dumps, json_loads, make_id, mean
from backend.services.portrait_service import PortraitService


class RecommendationService:
    TRAINING_MODE_LABELS = {
        "weakness": "补弱优先",
        "accuracy": "稳定正确率",
        "challenge": "挑战提升",
        "balanced": "均衡训练",
    }
    FUSION_WEIGHTS = {
        "long_term": 0.45,
        "forgetting": 0.35,
        "volatility": 0.20,
    }
    FUSION_FORMULA_TEXT = "priority = 0.45 * 长期薄弱程度 + 0.35 * 遗忘风险 + 0.20 * 最近错误波动"

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
        knowledge_tracking = self._build_knowledge_tracking(student_id, snapshot_payload)

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
                knowledge_tracking=knowledge_tracking,
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
            overall_commentary=self._build_overall_reason_template(selected, training_mode),
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
        snapshot = self.db.query(PortraitSnapshot).filter(PortraitSnapshot.snapshot_id == batch.snapshot_id).first()
        snapshot_payload = self.portrait_service.snapshot_to_payload(snapshot) if snapshot else {"knowledge_matrix": [], "dimensions": []}
        previous_snapshot = self.portrait_service.get_previous_snapshot(batch.student_id, batch.snapshot_id) if snapshot else None
        previous_payload = self.portrait_service.snapshot_to_payload(previous_snapshot) if previous_snapshot else None
        answered_questions = {
            row.question_id
            for row in self.db.query(PracticeAnswer.question_id).filter(PracticeAnswer.student_id == batch.student_id).all()
        }
        wrong_rows = self.db.query(WrongQuestionRecord).filter(WrongQuestionRecord.student_id == batch.student_id).all()
        wrong_question_ids = {row.question_id for row in wrong_rows if row.status == "open"}
        knowledge_tracking = self._build_knowledge_tracking(batch.student_id, snapshot_payload)
        scored_map = {
            row.question_id: self._score_candidate(
                question=question,
                current_snapshot=snapshot_payload,
                previous_snapshot=previous_payload,
                answered_questions=answered_questions,
                wrong_question_ids=wrong_question_ids,
                training_mode=batch.training_mode,
                knowledge_tracking=knowledge_tracking,
            )
            for row, question in items
        }
        latest_practice_map = self._latest_practice_map(batch.batch_id)
        progress = self._build_progress(batch.batch_id, items)
        batch_meta = self._build_batch_meta(items, json_loads(batch.training_focus_json, []), batch.training_mode)
        selected_scored = [scored_map.get(question.question_id) for _, question in items if scored_map.get(question.question_id)]
        return {
            "batch_id": batch.batch_id,
            "training_mode": batch.training_mode,
            "training_mode_label": self.TRAINING_MODE_LABELS.get(batch.training_mode, "均衡训练"),
            "batch_goal": batch_meta["batch_goal"],
            "batch_tags": batch_meta["batch_tags"],
            "fusion_formula": self.FUSION_FORMULA_TEXT,
            "overall_reason_template": self._build_overall_reason_template(selected_scored, batch.training_mode),
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
                    "priority": scored_map[question.question_id]["rank_score"] if question.question_id in scored_map else row.rank_score,
                    "long_term_mastery": scored_map[question.question_id]["long_term_mastery"] if question.question_id in scored_map else 0.0,
                    "long_term_weakness": scored_map[question.question_id]["long_term_weakness"] if question.question_id in scored_map else 0.0,
                    "forgetting_risk": scored_map[question.question_id]["forgetting_risk"] if question.question_id in scored_map else 0.0,
                    "recent_error_volatility": scored_map[question.question_id]["recent_error_volatility"] if question.question_id in scored_map else 0.0,
                    "recommendation_driver": scored_map[question.question_id]["recommendation_driver"] if question.question_id in scored_map else "长期薄弱",
                    "recommendation_template": scored_map[question.question_id]["recommendation_template"] if question.question_id in scored_map else row.rule_reason,
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

    def compare_recommendation_schemes(self, student_id: str, requested_count: int = 5) -> Dict[str, object]:
        student = self.db.query(Student).filter(Student.student_id == student_id).first()
        if student is None:
            return {
                "formula": self.FUSION_FORMULA_TEXT,
                "question_reason_template": "",
                "scheme_results": [],
                "case_studies": [],
                "summary": "当前没有可比较的推荐样本。",
            }

        latest_snapshot = self.portrait_service.get_latest_snapshot(student_id)
        if latest_snapshot is None:
            return {
                "formula": self.FUSION_FORMULA_TEXT,
                "question_reason_template": "",
                "scheme_results": [],
                "case_studies": [],
                "summary": "请先完成画像冷启动，再查看升级前后对比实验。",
            }

        snapshot_payload = self.portrait_service.snapshot_to_payload(latest_snapshot)
        previous_snapshot = self.portrait_service.get_previous_snapshot(student_id, latest_snapshot.snapshot_id)
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
        knowledge_tracking = self._build_knowledge_tracking(student_id, snapshot_payload)

        scored = [
            self._score_candidate(
                question=question,
                current_snapshot=snapshot_payload,
                previous_snapshot=previous_payload,
                answered_questions=answered_questions,
                wrong_question_ids=wrong_question_ids,
                training_mode="balanced",
                knowledge_tracking=knowledge_tracking,
            )
            for question in candidates
        ]

        scheme_configs = [
            ("原始规则推荐", "rule_only_score"),
            ("规则 + 遗忘曲线", "forgetting_augmented_score"),
            ("规则 + 遗忘曲线 + 轻量 KT", "rank_score"),
        ]
        scheme_results = []
        rank_maps = {}
        for label, key in scheme_configs:
            ordered = sorted(scored, key=lambda item: item[key], reverse=True)
            rank_maps[label] = {item["question_id"]: index + 1 for index, item in enumerate(ordered)}
            scheme_results.append(
                {
                    "label": label,
                    "items": [
                        {
                            "question_id": item["question_id"],
                            "title": item["title"],
                            "knowledge_tags": item["knowledge_tags"],
                            "score": round(item[key], 2),
                            "driver": item["recommendation_driver"],
                        }
                        for item in ordered[:requested_count]
                    ],
                }
            )

        case_pool = []
        for item in scored:
            base_rank = rank_maps["原始规则推荐"][item["question_id"]]
            fusion_rank = rank_maps["规则 + 遗忘曲线 + 轻量 KT"][item["question_id"]]
            delta = base_rank - fusion_rank
            if delta == 0:
                continue
            case_pool.append(
                {
                    "question_id": item["question_id"],
                    "title": item["title"],
                    "knowledge_tags": item["knowledge_tags"],
                    "base_rank": base_rank,
                    "forgetting_rank": rank_maps["规则 + 遗忘曲线"][item["question_id"]],
                    "fusion_rank": fusion_rank,
                    "rank_delta": delta,
                    "reason": item["recommendation_template"],
                }
            )
        case_pool.sort(key=lambda row: abs(row["rank_delta"]), reverse=True)

        return {
            "formula": self.FUSION_FORMULA_TEXT,
            "question_reason_template": "该题关联知识点 X，当前长期掌握度偏低，且最近复习间隔较长，因此优先纳入本轮训练。",
            "scheme_results": scheme_results,
            "case_studies": case_pool[:3] if case_pool else [],
            "summary": "同一学生在三种方案下的推荐差异，重点看哪些题因为长期薄弱或快忘了而被前置。",
        }

    def _question_lookup(self, question_ids: List[str]) -> Dict[str, QuestionBank]:
        ids = sorted({question_id for question_id in question_ids if question_id})
        if not ids:
            return {}
        rows = self.db.query(QuestionBank).filter(QuestionBank.question_id.in_(ids)).all()
        return {row.question_id: row for row in rows}

    def _answer_events(self, student_id: str) -> List[Dict[str, object]]:
        snapshot_version_lookup = {
            row.snapshot_id: row.version_number
            for row in self.db.query(PortraitSnapshot)
            .filter(PortraitSnapshot.student_id == student_id)
            .order_by(PortraitSnapshot.version_number.asc(), PortraitSnapshot.id.asc())
            .all()
        }
        practice_rows = (
            self.db.query(PracticeAnswer)
            .filter(PracticeAnswer.student_id == student_id)
            .order_by(PracticeAnswer.created_at.asc(), PracticeAnswer.id.asc())
            .all()
        )
        diagnostic_rows = (
            self.db.query(DiagnosticAnswer)
            .filter(DiagnosticAnswer.student_id == student_id)
            .order_by(DiagnosticAnswer.created_at.asc(), DiagnosticAnswer.id.asc())
            .all()
        )
        question_lookup = self._question_lookup([row.question_id for row in practice_rows + diagnostic_rows])
        events: List[Dict[str, object]] = []
        for row in practice_rows:
            question = question_lookup.get(row.question_id)
            if question is None:
                continue
            events.append(
                {
                    "question_id": row.question_id,
                    "knowledge_tags": json_loads(question.knowledge_tags_json, []),
                    "is_correct": bool(row.is_correct),
                    "duration_seconds": float(row.duration_seconds),
                    "difficulty": int(question.difficulty),
                    "created_at": row.created_at,
                    "snapshot_version": snapshot_version_lookup.get(row.snapshot_id),
                    "target_duration_seconds": int(question.target_duration_seconds),
                }
            )
        for row in diagnostic_rows:
            question = question_lookup.get(row.question_id)
            if question is None:
                continue
            events.append(
                {
                    "question_id": row.question_id,
                    "knowledge_tags": json_loads(question.knowledge_tags_json, []),
                    "is_correct": bool(row.is_correct),
                    "duration_seconds": float(row.duration_seconds),
                    "difficulty": int(question.difficulty),
                    "created_at": row.created_at,
                    "snapshot_version": 0,
                    "target_duration_seconds": int(question.target_duration_seconds),
                }
            )
        events.sort(key=lambda item: (item["created_at"], item["question_id"]))
        return events

    def _build_knowledge_tracking(self, student_id: str, snapshot_payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        events = self._answer_events(student_id)
        grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        for event in events:
            for tag in event["knowledge_tags"] or ["未分类"]:
                grouped[tag].append(event)

        baseline_map = {
            item["knowledge_tag"]: float(item["mastery_score"])
            for item in snapshot_payload.get("knowledge_matrix", [])
        }
        now = datetime.utcnow()
        states = {}

        for knowledge_tag, tag_events in grouped.items():
            ordered = sorted(tag_events, key=lambda item: (item["created_at"], item["question_id"]))
            last_event = ordered[-1]
            review_count = len(ordered)
            recent_window = ordered[-5:]
            recent_accuracy = sum(1.0 if item["is_correct"] else 0.0 for item in recent_window) / max(1, len(recent_window))
            previous_window = ordered[-10:-5]
            previous_accuracy = (
                sum(1.0 if item["is_correct"] else 0.0 for item in previous_window) / len(previous_window)
                if previous_window
                else recent_accuracy
            )

            intervals = [
                max((current["created_at"] - previous["created_at"]).total_seconds() / 86400.0, 0.0)
                for previous, current in zip(ordered, ordered[1:])
            ]
            interval_days = round(sum(intervals) / len(intervals), 1) if intervals else 1.0

            recent_errors = [0 if item["is_correct"] else 1 for item in recent_window]
            transition_count = sum(1 for prev, cur in zip(recent_errors, recent_errors[1:]) if prev != cur)
            error_rate = sum(recent_errors) / max(1, len(recent_errors))
            recent_error_volatility = round(min(100.0, error_rate * 70.0 + (transition_count / max(1, len(recent_errors) - 1)) * 30.0), 1)

            mastery_score = baseline_map.get(knowledge_tag, 55.0)
            for item in recent_window:
                factor = self._difficulty_factor(int(item["difficulty"]))
                mastery_score += (2.8 if item["is_correct"] else -3.6) * factor
            mastery_score += (recent_accuracy - 0.5) * 8.0
            mastery_score = max(0.0, min(100.0, round(mastery_score, 1)))
            long_term_weakness = round(100 - mastery_score, 1)

            trend_delta = round((recent_accuracy - previous_accuracy) * 100, 1)
            if trend_delta >= 8:
                trend_label = "上升"
            elif trend_delta <= -8:
                trend_label = "下降"
            else:
                trend_label = "稳定"

            delta_t = max((now - last_event["created_at"]).total_seconds() / 86400.0, 0.0)
            forgetting_lambda = 0.12
            if recent_accuracy < 0.67:
                forgetting_lambda += 0.06
            if not last_event["is_correct"]:
                forgetting_lambda += 0.05
            if review_count <= 2:
                forgetting_lambda += 0.03
            adjusted_delta = delta_t / max(interval_days, 1.0)
            retention = max(0.0, min(1.0, exp(-forgetting_lambda * adjusted_delta)))
            forgetting_risk = round((1 - retention) * 100, 1)

            if forgetting_risk >= 70:
                risk_level = "高遗忘风险"
            elif forgetting_risk >= 40:
                risk_level = "中遗忘风险"
            else:
                risk_level = "低遗忘风险"

            states[knowledge_tag] = {
                "knowledge_tag": knowledge_tag,
                "long_term_mastery": mastery_score,
                "long_term_weakness": long_term_weakness,
                "forgetting_risk": forgetting_risk,
                "recent_error_volatility": recent_error_volatility,
                "review_count": review_count,
                "last_result": "答对" if last_event["is_correct"] else "答错",
                "last_practiced_at": last_event["created_at"].isoformat(),
                "interval_days": interval_days,
                "trend_label": trend_label,
                "needs_attention": mastery_score < 60 or trend_label == "下降",
                "risk_level": risk_level,
            }

        for item in snapshot_payload.get("knowledge_matrix", []):
            if item["knowledge_tag"] in states:
                continue
            states[item["knowledge_tag"]] = {
                "knowledge_tag": item["knowledge_tag"],
                "long_term_mastery": round(float(item["mastery_score"]), 1),
                "long_term_weakness": round(100 - float(item["mastery_score"]), 1),
                "forgetting_risk": 35.0,
                "recent_error_volatility": 20.0,
                "review_count": 0,
                "last_result": "暂无记录",
                "last_practiced_at": "",
                "interval_days": 0.0,
                "trend_label": "稳定",
                "needs_attention": bool(item["needs_attention"]),
                "risk_level": "中遗忘风险" if item["needs_attention"] else "低遗忘风险",
            }

        return states

    def _difficulty_factor(self, level: int) -> float:
        return {1: 0.95, 2: 1.0, 3: 1.08, 4: 1.15}.get(level, 1.0)

    def _score_candidate(
        self,
        question: QuestionBank,
        current_snapshot: Dict[str, object],
        previous_snapshot: Optional[Dict[str, object]],
        answered_questions: set[str],
        wrong_question_ids: set[str],
        training_mode: str,
        knowledge_tracking: Dict[str, Dict[str, object]],
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
        tag_states = [knowledge_tracking.get(tag) for tag in knowledge_tags if knowledge_tracking.get(tag)]
        long_term_mastery = round(mean([float(item["long_term_mastery"]) for item in tag_states], default=max(0.0, 100.0 - knowledge_need)), 1)
        long_term_weakness = round(mean([float(item["long_term_weakness"]) for item in tag_states], default=knowledge_need), 1)
        forgetting_risk = round(mean([float(item["forgetting_risk"]) for item in tag_states], default=35.0), 1)
        recent_error_volatility = round(mean([float(item["recent_error_volatility"]) for item in tag_states], default=20.0), 1)
        priority_core = round(
            self.FUSION_WEIGHTS["long_term"] * long_term_weakness
            + self.FUSION_WEIGHTS["forgetting"] * forgetting_risk
            + self.FUSION_WEIGHTS["volatility"] * recent_error_volatility,
            2,
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
            rule_only_score = round(0.46 * dimension_need + 0.40 * knowledge_need + decline_bonus + difficulty_fit + wrong_bonus * 1.2 + novelty_bonus, 2)
        elif training_mode == "accuracy":
            rule_only_score = round(0.28 * dimension_need + 0.26 * knowledge_need + decline_bonus + difficulty_fit * 1.4 + wrong_bonus + novelty_bonus * 0.7, 2)
        elif training_mode == "challenge":
            rule_only_score = round(0.26 * dimension_need + 0.22 * knowledge_need + decline_bonus * 1.2 + difficulty_fit + wrong_bonus * 0.7 + novelty_bonus + challenge_bonus, 2)
        else:
            rule_only_score = round(0.38 * dimension_need + 0.34 * knowledge_need + decline_bonus + difficulty_fit + wrong_bonus + novelty_bonus, 2)

        forgetting_augmented_score = round(rule_only_score + forgetting_risk * self.FUSION_WEIGHTS["forgetting"], 2)
        rank_score = round(rule_only_score * 0.55 + priority_core * 0.45, 2)

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
        if long_term_weakness >= forgetting_risk and long_term_weakness >= recent_error_volatility:
            recommendation_driver = "长期薄弱"
        elif forgetting_risk >= recent_error_volatility:
            recommendation_driver = "快忘了"
        else:
            recommendation_driver = "最近错误波动"
        weak_dimensions = sorted(question_dimensions, key=lambda code: dimension_scores.get(code, 60.0))[:2]
        weak_dimension_names = [next(item["dimension_name"] for item in current_snapshot["dimensions"] if item["dimension_code"] == code) for code in weak_dimensions]
        weak_knowledge = sorted(knowledge_tags, key=lambda tag: knowledge_scores.get(tag, 60.0))[:2]
        rule_reason = (
            f"该题关联知识点 {('、'.join(weak_knowledge) or '核心知识点')}，当前长期掌握度 {long_term_mastery} 分，"
            f"遗忘风险 {forgetting_risk}%，最近错误波动 {recent_error_volatility} 分，因此优先纳入本轮训练。"
        )
        recommendation_template = self._recommendation_template(
            knowledge_tags=weak_knowledge or knowledge_tags,
            long_term_mastery=long_term_mastery,
            forgetting_risk=forgetting_risk,
            recent_error_volatility=recent_error_volatility,
            recommendation_driver=recommendation_driver,
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
            "recommendation_template": recommendation_template,
            "recommendation_driver": recommendation_driver,
            "priority_core": priority_core,
            "rule_only_score": rule_only_score,
            "forgetting_augmented_score": forgetting_augmented_score,
            "rank_score": rank_score,
            "long_term_mastery": long_term_mastery,
            "long_term_weakness": long_term_weakness,
            "forgetting_risk": forgetting_risk,
            "recent_error_volatility": recent_error_volatility,
        }

    def _recommendation_type(self, dimension_need: float, knowledge_need: float, difficulty: int) -> str:
        if dimension_need >= 45 or knowledge_need >= 45 or difficulty <= 1:
            return "补弱题"
        if difficulty == 2 or max(dimension_need, knowledge_need) >= 25:
            return "巩固题"
        return "提升题"

    def _recommendation_template(
        self,
        knowledge_tags: List[str],
        long_term_mastery: float,
        forgetting_risk: float,
        recent_error_volatility: float,
        recommendation_driver: str,
    ) -> str:
        joined_tags = "、".join(knowledge_tags[:2]) or "当前知识点"
        if recommendation_driver == "长期薄弱":
            return f"该题关联知识点 {joined_tags}，当前长期掌握度偏低（{long_term_mastery} 分），因此优先纳入本轮训练。"
        if recommendation_driver == "快忘了":
            return f"该题关联知识点 {joined_tags}，当前复习间隔较长，遗忘风险达到 {forgetting_risk}% ，因此优先纳入本轮训练。"
        return f"该题关联知识点 {joined_tags}，最近错误波动为 {recent_error_volatility} 分，说明表现仍不稳定，因此优先纳入本轮训练。"

    def _build_overall_reason_template(self, items: List[Optional[Dict[str, object]]], training_mode: str) -> str:
        valid_items = [item for item in items if item]
        if not valid_items:
            return "当前批次会根据成长画像、知识点掌握与练习记录综合生成。"
        driver_counts = defaultdict(int)
        tags = []
        for item in valid_items:
            driver_counts[str(item["recommendation_driver"])] += 1
            tags.extend(item.get("knowledge_tags", [])[:1])
        dominant_driver = max(driver_counts.items(), key=lambda row: row[1])[0] if driver_counts else "长期薄弱"
        unique_tags = []
        for tag in tags:
            if tag and tag not in unique_tags:
                unique_tags.append(tag)
        driver_text = {
            "长期薄弱": "长期掌握度偏低",
            "快忘了": "短期遗忘风险升高",
            "最近错误波动": "最近错误波动明显",
        }.get(dominant_driver, dominant_driver)
        return (
            f"本轮采用 {self.FUSION_FORMULA_TEXT}，并结合 {self.TRAINING_MODE_LABELS.get(training_mode, '均衡训练')} 做分层筛题。"
            f"当前优先覆盖 {('、'.join(unique_tags[:3]) or '核心知识点')}，主要原因是 {driver_text}。"
        )

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
            "batch_tags": [self.TRAINING_MODE_LABELS.get(training_mode, "均衡训练")] + top_tags[:3],
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
