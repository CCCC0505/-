from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from math import exp
from typing import Dict, Iterable, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import (
    AIAnalysisRun,
    DiagnosticAnswer,
    PortraitSnapshot,
    PracticeAnswer,
    QuestionBank,
    RecommendationBatch,
    Student,
    WrongQuestionRecord,
)
from backend.seed_data import DIMENSION_META
from backend.services.common import json_loads, mean
from backend.services.portrait_service import PortraitService
from backend.services.qwen_client import QwenClient
from backend.services.recommendation_service import RecommendationService


RANGE_DAY_MAP = {
    "week": 7,
    "month": 30,
    "semester": 120,
    "year": 365,
    "all": None,
}

DIFFICULTY_FACTORS = {
    1: 0.95,
    2: 1.00,
    3: 1.08,
    4: 1.15,
}


MODELING_REFERENCES = [
    {
        "id": "adding_it_up_2001",
        "title": "Adding It Up: Helping Children Learn Mathematics",
        "authors": "National Research Council",
        "year": 2001,
        "source": "The National Academies Press",
        "url": "https://doi.org/10.17226/9822",
        "used_for": "数学能力维度设计，尤其是程序性流畅、策略能力、推理能力与学习 disposition 的映射。",
    },
    {
        "id": "krathwohl_2002",
        "title": "A Revision of Bloom's Taxonomy: An Overview",
        "authors": "David R. Krathwohl",
        "year": 2002,
        "source": "Theory Into Practice",
        "url": "https://doi.org/10.1207/S15430421TIP4104_2",
        "used_for": "认知层级 remember / understand / apply / analyze 的层次划分。",
    },
    {
        "id": "corbett_anderson_1994",
        "title": "Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge",
        "authors": "Albert T. Corbett, John R. Anderson",
        "year": 1994,
        "source": "User Modeling and User-Adapted Interaction",
        "url": "https://doi.org/10.1007/BF01099821",
        "used_for": "知识点掌握度随作答证据持续更新的思路，强调基于练习证据动态估计掌握状态。",
    },
    {
        "id": "de_la_torre_2011",
        "title": "The Generalized DINA Model Framework",
        "authors": "Jimmy de la Torre",
        "year": 2011,
        "source": "Psychometrika",
        "url": "https://doi.org/10.1007/s11336-011-9207-7",
        "used_for": "认知诊断建模思想，支持按知识属性和题目设计矩阵解释学生的多维表现。",
    },
    {
        "id": "panadero_2017",
        "title": "A Review of Self-Regulated Learning: Six Models and Four Directions for Research",
        "authors": "Ernesto Panadero",
        "year": 2017,
        "source": "Frontiers in Psychology",
        "url": "https://doi.org/10.3389/fpsyg.2017.00422",
        "used_for": "问卷中的复盘、求助、节奏、自信等学习者特征，以及学习稳定性解释。",
    },
]


class UIDashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portrait_service = PortraitService(db)
        self.recommendation_service = RecommendationService(db)

    def build_analysis_dashboard(self, student_id: str, range_key: str = "month") -> Dict[str, object]:
        student = self._get_student(student_id)
        latest_snapshot = self.portrait_service.get_latest_snapshot(student_id)
        if latest_snapshot is None:
            raise HTTPException(status_code=404, detail="portrait snapshot not found")

        snapshots = self.portrait_service.get_snapshot_history(student_id)
        latest_payload = self.portrait_service.snapshot_to_payload(latest_snapshot)
        latest_recommendation = self.recommendation_service.latest_summary(student_id)
        events = self._answer_events(student_id, range_key)
        all_events = self._answer_events(student_id, "all")
        knowledge_tracking = self._build_knowledge_tracking(student_id, latest_payload, all_events)
        weak_items = self._build_weakness_items(latest_payload, events, knowledge_tracking)
        recommendation_upgrade = self.recommendation_service.compare_recommendation_schemes(student_id, requested_count=5)
        emotion_support = self._build_emotion_support(latest_payload, all_events)

        return {
            "student_id": student.student_id,
            "student_name": student.name,
            "grade": student.grade,
            "range": range_key,
            "summary_cards": self._build_analysis_summary_cards(student_id, latest_payload, events),
            "charts": {
                "progress": self._build_progress_chart(snapshots, range_key),
                "accuracy": self._build_accuracy_chart(latest_payload, events),
                "mastery": self._build_mastery_chart(latest_payload),
                "time_distribution": self._build_time_distribution_chart(events),
            },
            "weakness_items": weak_items,
            "report": self._build_analysis_report(student, latest_payload, latest_recommendation, weak_items, events, knowledge_tracking),
            "learning_plan": self._build_learning_plan(latest_payload, latest_recommendation),
            "portrait_modeling": self.build_portrait_modeling(student_id),
            "modeling_basis": self.build_modeling_basis(),
            "knowledge_tracking": knowledge_tracking,
            "recommendation_upgrade": recommendation_upgrade,
            "defense_assets": self._build_defense_assets(),
            "emotion_support": emotion_support,
        }

    def build_personal_dashboard(self, student_id: str) -> Dict[str, object]:
        student = self._get_student(student_id)
        latest_snapshot = self.portrait_service.get_latest_snapshot(student_id)
        if latest_snapshot is None:
            raise HTTPException(status_code=404, detail="portrait snapshot not found")

        latest_payload = self.portrait_service.snapshot_to_payload(latest_snapshot)
        snapshots = self.portrait_service.get_snapshot_history(student_id)
        latest_recommendation = self.recommendation_service.latest_summary(student_id)
        practice_rows = (
            self.db.query(PracticeAnswer)
            .filter(PracticeAnswer.student_id == student_id)
            .order_by(PracticeAnswer.created_at.desc(), PracticeAnswer.id.desc())
            .all()
        )
        diagnostic_rows = (
            self.db.query(DiagnosticAnswer)
            .filter(DiagnosticAnswer.student_id == student_id)
            .order_by(DiagnosticAnswer.created_at.desc(), DiagnosticAnswer.id.desc())
            .all()
        )
        wrong_rows = (
            self.db.query(WrongQuestionRecord)
            .filter(WrongQuestionRecord.student_id == student_id)
            .order_by(WrongQuestionRecord.updated_at.desc(), WrongQuestionRecord.id.desc())
            .all()
        )
        rhythm = self._build_learning_rhythm(student_id, student.weekly_target_questions)
        achievements = self._build_achievements(latest_payload, snapshots, practice_rows, wrong_rows, rhythm["streak_days"])

        return {
            "student_id": student.student_id,
            "student_name": student.name,
            "grade": student.grade,
            "joined_at": student.created_at.isoformat(),
            "profile_tags": self._build_profile_tags(latest_payload, rhythm["streak_days"]),
            "stats": {
                "total_study_hours": round((sum(row.duration_seconds for row in practice_rows) + sum(row.duration_seconds for row in diagnostic_rows)) / 3600, 1),
                "study_days": len({row.created_at.date() for row in practice_rows + diagnostic_rows}),
                "continuous_study": rhythm["streak_days"],
                "achievements_count": sum(1 for item in achievements if item["unlocked"]),
            },
            "today": self._build_today_stats(practice_rows, latest_recommendation),
            "progress_bars": self._build_progress_bars(latest_payload),
            "achievements": achievements,
            "advice": self._build_personal_advice(latest_payload, latest_recommendation, wrong_rows),
            "learning_report": self._build_personal_learning_report(latest_payload, practice_rows, diagnostic_rows, snapshots),
            "weakness_analysis": self._build_personal_weakness_analysis(latest_payload, latest_recommendation, wrong_rows),
            "practice_records": self._build_practice_records(student_id, snapshots, practice_rows, wrong_rows),
        }

    def build_portrait_modeling(self, student_id: str) -> Dict[str, object]:
        student = self._get_student(student_id)
        latest_snapshot = self.portrait_service.get_latest_snapshot(student_id)
        if latest_snapshot is None:
            raise HTTPException(status_code=404, detail="portrait snapshot not found")
        latest_payload = self.portrait_service.snapshot_to_payload(latest_snapshot)
        portrait_run = (
            self.db.query(AIAnalysisRun)
            .filter(AIAnalysisRun.student_id == student_id, AIAnalysisRun.request_type == "portrait_summary")
            .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
            .first()
        )
        qwen_client = QwenClient(self.db)
        ai_output = json_loads(portrait_run.structured_output_json, {}) if portrait_run else {}
        if not ai_output:
            ai_output = {
                "portrait_summary": latest_payload["portrait_summary"],
                "teacher_commentary": latest_payload["teacher_commentary"],
                "training_focus": latest_payload["training_focus"],
                "risk_flags": latest_payload["risk_flags"],
                "confidence": latest_payload["ai_confidence"],
                "dimension_insights": qwen_client._fallback_dimension_insights(latest_payload),
                "knowledge_insights": qwen_client._fallback_knowledge_insights(latest_payload),
                "cognitive_insights": qwen_client._fallback_cognitive_insights(latest_payload),
            }
        return {
            "student_id": student.student_id,
            "student_name": student.name,
            "snapshot_id": latest_payload["snapshot_id"],
            "version_number": latest_payload["version_number"],
            "rule_dimensions": latest_payload["dimensions"],
            "rule_knowledge_matrix": latest_payload["knowledge_matrix"],
            "rule_cognitive_diagnosis": latest_payload["cognitive_diagnosis"],
            "rule_traits": latest_payload["learner_traits"],
            "algorithm_pipeline": [
                {"step": "诊断证据采集", "detail": "采集 24 道诊断题 + 6 个学习行为问卷，形成首层证据。"},
                {"step": "规则建模层", "detail": "按题目维度权重、难度因子、认知层级因子、目标时长偏离进行量化。"},
                {"step": "知识/认知聚合", "detail": "把单题证据投影到知识点矩阵、认知层级和五维画像。"},
                {"step": "AI解释层", "detail": "Qwen 读取规则画像，生成摘要、点评、训练重点与风险提示，并补充结构化诊断。"},
                {"step": "版本化画像输出", "detail": "最终形成可追踪的 portrait snapshot，并进入训练推荐与分析页展示。"},
            ],
            "rule_formulae": [
                "单题证据 = 作答正误 × 难度因子 × 认知层级因子 × 速度修正",
                "维度分 = 维度累计命中 / 维度理论上限 × 100",
                "知识点掌握度 = 知识点累计命中 / 知识点理论上限 × 100",
                "练习后增量更新 = 当前画像 + 练习增量，再生成新快照版本",
            ],
            "ai_model_status": {
                "enabled": qwen_client.capability_status()["enabled"],
                "model_name": qwen_client.capability_status()["model_name"],
                "attempted": portrait_run.attempted if portrait_run else False,
                "success": portrait_run.success if portrait_run else False,
                "fallback_used": portrait_run.fallback_used if portrait_run else True,
                "error_summary": portrait_run.error_summary if portrait_run else "暂无画像 AI 调用记录",
            },
            "ai_output_schema": qwen_client.portrait_schema_definition(),
            "ai_output_data": ai_output,
        }

    def build_modeling_basis(self) -> Dict[str, object]:
        dimension_reference_map = {
            "计算准确性": ["adding_it_up_2001", "corbett_anderson_1994"],
            "知识点掌握度": ["corbett_anderson_1994", "de_la_torre_2011"],
            "逻辑策略": ["adding_it_up_2001", "krathwohl_2002"],
            "认知层级表现": ["krathwohl_2002", "de_la_torre_2011"],
            "学习稳定性": ["panadero_2017", "adding_it_up_2001"],
        }
        dimension_evidence = {
            "计算准确性": "作答正误、题目难度、目标用时偏离程度、与计算相关的题目权重。",
            "知识点掌握度": "按知识点聚合的正确率证据、知识点标签命中次数、练习后的增量更新。",
            "逻辑策略": "中高阶题目表现、分析层级题目证据、策略相关问卷因子。",
            "认知层级表现": "remember / understand / apply / analyze 四层作答表现。",
            "学习稳定性": "节奏、复盘、求助、自信等问卷特征，以及练习后表现波动。",
        }
        dimension_operation = {
            "计算准确性": "由诊断题与练习题中的维度权重累计证据，再按题目难度和速度因子校正。",
            "知识点掌握度": "对每个知识点维护掌握分，初始来自诊断，后续按练习正误做增量更新。",
            "逻辑策略": "优先读取 analyze/apply 层级题目的表现，并与 strategy_index 做轻度融合。",
            "认知层级表现": "四类认知层级独立累计命中率，用于解释学生停留在哪一层。",
            "学习稳定性": "把作答速度与问卷中的复盘/节奏/信心特征合成稳定性分数。",
        }
        dimension_rows = []
        for item in DIMENSION_META:
            dimension_rows.append(
                {
                    "name": item["name"],
                    "evidence": dimension_evidence[item["name"]],
                    "operationalization": dimension_operation[item["name"]],
                    "references": [ref for ref in MODELING_REFERENCES if ref["id"] in dimension_reference_map[item["name"]]],
                }
            )

        return {
            "overview": (
                "当前成长画像是一个规则化证据模型 V1：用题目作答证据、知识点标签、认知层级标签和问卷特征共同构建多维画像。"
                "它参考了认知诊断、知识追踪和自我调节学习研究，但不宣称当前版本已经训练出完整的参数化 G-DINA/BKT 模型。"
            ),
            "upgrade_scope": {
                "one_liner": "我们在现有画像和推荐系统上，增加了知识点长期掌握追踪与短期遗忘风险评估，并将两者融合到个性化推荐中。",
                "delivery": "在原有规则画像基础上，补充知识追踪与遗忘风险机制，增强个性化推荐。",
                "long_term_model": "轻量 KT",
                "short_term_model": "遗忘曲线",
                "fusion_layer": "推荐优先级与解释",
                "non_scope": ["LSTM 上线", "视觉/语音情感计算", "多学科产品化"],
            },
            "modeling_notes": [
                "基础得分由作答正误、题目难度、认知层级权重和目标用时共同决定。",
                "诊断题负责建立初始画像，练习题负责做增量更新，画像快照按版本串联。",
                "问卷特征只作为稳定性、策略、自信等辅助因子，不直接替代能力分。",
                "弱项阈值和认知预警阈值公开，便于答辩说明和后续迭代。",
            ],
            "parameter_table": [
                {"name": "难度修正", "value": "1->0.95, 2->1.00, 3->1.08, 4->1.15", "meaning": "同样答对时，高难题的证据权重更强。"},
                {"name": "认知层级修正", "value": "remember->0.94, understand->1.00, apply->1.06, analyze->1.12", "meaning": "高层级题目更能区分迁移与分析能力。"},
                {"name": "速度修正", "value": "目标时长比值处于 0.7~1.3 记 1.0，否则阶梯降权", "meaning": "避免只看对错，不看作答稳定性。"},
                {"name": "知识点预警阈值", "value": "55", "meaning": "低于该值记为 needs_attention。"},
                {"name": "认知层级预警阈值", "value": "58", "meaning": "低于该值说明该认知层级仍不稳定。"},
                {"name": "策略/稳定性融合", "value": "稳定性 75% 题证 + 25% 问卷；逻辑策略 90% 题证 + 10% 问卷", "meaning": "确保问卷只做辅助，不覆盖客观作答证据。"},
            ],
            "dimension_mapping": dimension_rows,
            "references": MODELING_REFERENCES,
            "future_upgrade": [
                "下一阶段可引入显式 Q-matrix 与 G-DINA / DINA 参数学习，替代当前规则权重。",
                "可用真实练习序列继续校准轻量 KT / BKT 参数，替代当前固定增量策略。",
                "可加入题目区分度、猜测/失误参数，提升心理测量解释力。",
            ],
        }

    def _get_student(self, student_id: str) -> Student:
        student = self.db.query(Student).filter(Student.student_id == student_id).first()
        if student is None:
            raise HTTPException(status_code=404, detail="student not found")
        return student

    def _range_start(self, range_key: str) -> Optional[datetime]:
        days = RANGE_DAY_MAP.get(range_key, RANGE_DAY_MAP["month"])
        if days is None:
            return None
        return datetime.utcnow() - timedelta(days=days - 1)

    def _in_range(self, created_at: datetime, range_key: str) -> bool:
        start = self._range_start(range_key)
        return start is None or created_at >= start

    def _question_lookup(self, question_ids: Iterable[str]) -> Dict[str, QuestionBank]:
        ids = sorted({question_id for question_id in question_ids if question_id})
        if not ids:
            return {}
        rows = self.db.query(QuestionBank).filter(QuestionBank.question_id.in_(ids)).all()
        return {row.question_id: row for row in rows}

    def _answer_events(self, student_id: str, range_key: str) -> List[Dict[str, object]]:
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
        events = []
        for row in practice_rows:
            if not self._in_range(row.created_at, range_key):
                continue
            question = question_lookup.get(row.question_id)
            if question is None:
                continue
            events.append(
                {
                    "student_id": student_id,
                    "question_id": row.question_id,
                    "knowledge_tags": json_loads(question.knowledge_tags_json, []),
                    "is_correct": bool(row.is_correct),
                    "duration_seconds": float(row.duration_seconds),
                    "difficulty": int(question.difficulty),
                    "created_at": row.created_at,
                    "title": question.title,
                    "snapshot_version": snapshot_version_lookup.get(row.snapshot_id),
                    "stage": "practice",
                    "target_duration_seconds": int(question.target_duration_seconds),
                }
            )
        for row in diagnostic_rows:
            if not self._in_range(row.created_at, range_key):
                continue
            question = question_lookup.get(row.question_id)
            if question is None:
                continue
            events.append(
                {
                    "student_id": student_id,
                    "question_id": row.question_id,
                    "knowledge_tags": json_loads(question.knowledge_tags_json, []),
                    "is_correct": bool(row.is_correct),
                    "duration_seconds": float(row.duration_seconds),
                    "difficulty": int(question.difficulty),
                    "created_at": row.created_at,
                    "title": question.title,
                    "snapshot_version": 0,
                    "stage": "diagnostic",
                    "target_duration_seconds": int(question.target_duration_seconds),
                }
            )
        events.sort(key=lambda item: (item["created_at"], item["question_id"], item["stage"]))
        return events

    def _build_knowledge_tracking(
        self,
        student_id: str,
        latest_payload: Dict[str, object],
        events: List[Dict[str, object]],
    ) -> Dict[str, object]:
        grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        sequence_rows: List[Dict[str, object]] = []
        for event in events:
            for tag in event["knowledge_tags"] or ["未分类"]:
                grouped[tag].append(event)
                sequence_rows.append(
                    {
                        "student_id": student_id,
                        "question_id": event["question_id"],
                        "knowledge_tag": tag,
                        "created_at": event["created_at"].isoformat(),
                        "is_correct": bool(event["is_correct"]),
                        "duration_seconds": float(event["duration_seconds"]),
                        "difficulty": int(event["difficulty"]),
                        "snapshot_version": event["snapshot_version"],
                        "stage": event["stage"],
                    }
                )

        baseline_map = {
            item["knowledge_tag"]: float(item["mastery_score"])
            for item in latest_payload["knowledge_matrix"]
        }
        states: List[Dict[str, object]] = []
        now = datetime.utcnow()

        for knowledge_tag, tag_events in grouped.items():
            ordered = sorted(tag_events, key=lambda item: (item["created_at"], item["question_id"]))
            last_event = ordered[-1]
            review_count = len(ordered)
            last_practiced_at = last_event["created_at"]
            recent_window = ordered[-5:]
            recent_results = [1.0 if item["is_correct"] else 0.0 for item in recent_window]
            recent_accuracy = sum(recent_results) / max(1, len(recent_results))
            previous_window = ordered[-10:-5]
            previous_results = [1.0 if item["is_correct"] else 0.0 for item in previous_window]
            previous_accuracy = (
                sum(previous_results) / len(previous_results)
                if previous_results
                else recent_accuracy
            )

            intervals = []
            for previous, current in zip(ordered, ordered[1:]):
                delta_days = max((current["created_at"] - previous["created_at"]).total_seconds() / 86400.0, 0.0)
                intervals.append(delta_days)
            interval_days = round(sum(intervals) / len(intervals), 1) if intervals else 1.0

            mastery_score = baseline_map.get(knowledge_tag, 55.0)
            for item in recent_window:
                factor = DIFFICULTY_FACTORS.get(int(item["difficulty"]), 1.0)
                mastery_score += (2.8 if item["is_correct"] else -3.6) * factor
            mastery_score += (recent_accuracy - 0.5) * 8.0
            mastery_score = max(0.0, min(100.0, round(mastery_score, 1)))

            trend_delta = round((recent_accuracy - previous_accuracy) * 100, 1)
            if trend_delta >= 8:
                trend_label = "上升"
            elif trend_delta <= -8:
                trend_label = "下降"
            else:
                trend_label = "稳定"

            delta_t = max((now - last_practiced_at).total_seconds() / 86400.0, 0.0)
            forgetting_lambda = 0.12
            if recent_accuracy < 0.67:
                forgetting_lambda += 0.06
            if not last_event["is_correct"]:
                forgetting_lambda += 0.05
            if review_count <= 2:
                forgetting_lambda += 0.03
            adjusted_delta = delta_t / max(interval_days, 1.0)
            retention = max(0.0, min(1.0, exp(-forgetting_lambda * adjusted_delta)))
            forgetting_risk = round(1 - retention, 3)
            if forgetting_risk >= 0.7:
                risk_level = "高遗忘风险"
            elif forgetting_risk >= 0.4:
                risk_level = "中遗忘风险"
            else:
                risk_level = "低遗忘风险"

            if adjusted_delta >= 2 and recent_accuracy < 0.67:
                review_reason = "很久没练 + 之前不稳定 = 优先复习"
            elif adjusted_delta >= 2:
                review_reason = "距离上次练习时间较长，建议优先回顾"
            elif not last_event["is_correct"]:
                review_reason = "最近一次练习答错，建议尽快回补"
            elif trend_label == "下降":
                review_reason = "最近表现有下降趋势，需要再次巩固"
            else:
                review_reason = "近期状态相对稳定，可按计划复习"

            needs_attention = mastery_score < 60 or trend_label == "下降"
            priority_score = round(
                forgetting_risk * 70
                + (100 - mastery_score) * 0.2
                + (8 if needs_attention else 0)
                + (5 if trend_label == "下降" else 0),
                1,
            )

            states.append(
                {
                    "knowledge_tag": knowledge_tag,
                    "last_practiced_at": last_practiced_at.isoformat(),
                    "review_count": review_count,
                    "last_result": "答对" if last_event["is_correct"] else "答错",
                    "interval_days": interval_days,
                    "current_mastery": mastery_score,
                    "trend_label": trend_label,
                    "trend_delta": trend_delta,
                    "needs_attention": needs_attention,
                    "retention": round(retention, 3),
                    "forgetting_risk": forgetting_risk,
                    "risk_level": risk_level,
                    "review_reason": review_reason,
                    "priority_score": priority_score,
                }
            )

        states.sort(key=lambda item: (-item["priority_score"], item["current_mastery"], item["knowledge_tag"]))
        return {
            "upgrade_scope": {
                "one_liner": "我们在现有画像和推荐系统上，增加了知识点长期掌握追踪与短期遗忘风险评估，并将两者融合到个性化推荐中。",
                "delivery": "在原有规则画像基础上，补充知识追踪与遗忘风险机制，增强个性化推荐。",
                "long_term_model": "轻量 KT",
                "short_term_model": "遗忘曲线",
                "fusion_layer": "推荐优先级与解释",
                "non_scope": ["LSTM 上线", "视觉/语音情感计算", "多学科产品化"],
            },
            "formulas": {
                "retention": "retention = exp(-lambda * delta_t)",
                "forgetting_risk": "forgetting_risk = 1 - retention",
                "mastery": "mastery_score = 历史掌握度 + 答对加分 - 答错扣分 + 最近表现平滑",
            },
            "data_fields": [
                "student_id",
                "question_id",
                "knowledge_tags",
                "created_at",
                "is_correct",
                "duration_seconds",
                "difficulty",
                "snapshot_version",
            ],
            "top_review": states[:3],
            "knowledge_states": states,
            "sequence_total": len(sequence_rows),
            "sequence_rows": sorted(sequence_rows, key=lambda item: item["created_at"], reverse=True)[:40],
        }

    def _build_analysis_summary_cards(self, student_id: str, latest_payload: Dict[str, object], events: List[Dict[str, object]]) -> List[Dict[str, object]]:
        total_hours = round(sum(float(item["duration_seconds"]) for item in events) / 3600, 1)
        avg_dimension = round(mean(float(item["score"]) for item in latest_payload["dimensions"]), 1)
        mastered_count = sum(1 for item in latest_payload["knowledge_matrix"] if float(item["mastery_score"]) >= 70)
        weak_count = sum(1 for item in latest_payload["knowledge_matrix"] if item["needs_attention"])
        previous = self.portrait_service.get_previous_snapshot(student_id, latest_payload["snapshot_id"])
        previous_payload = self.portrait_service.snapshot_to_payload(previous) if previous else None
        previous_avg = round(mean(float(item["score"]) for item in previous_payload["dimensions"]), 1) if previous_payload else None
        avg_trend = None if previous_avg is None else round(avg_dimension - previous_avg, 1)
        previous_weak_count = (
            sum(1 for item in previous_payload["knowledge_matrix"] if item["needs_attention"])
            if previous_payload
            else None
        )
        weak_trend = None if previous_weak_count is None else round(previous_weak_count - weak_count, 1)
        return [
            {"label": "学习时长", "value": total_hours, "unit": "小时", "trend": None},
            {"label": "综合画像", "value": round(avg_dimension), "unit": "%", "trend": avg_trend},
            {"label": "掌握知识点", "value": mastered_count, "unit": "个", "trend": None},
            {"label": "薄弱知识点", "value": weak_count, "unit": "个", "trend": weak_trend},
        ]

    def _build_progress_chart(self, snapshots: List[PortraitSnapshot], range_key: str) -> Dict[str, object]:
        filtered = [snapshot for snapshot in reversed(snapshots) if self._in_range(snapshot.created_at, range_key)]
        if not filtered:
            filtered = list(reversed(snapshots[:4]))
        labels = []
        current = []
        for snapshot in filtered[-6:]:
            payload = self.portrait_service.snapshot_to_payload(snapshot)
            labels.append(f"V{payload['version_number']}")
            current.append(round(mean(float(item["score"]) for item in payload["dimensions"]), 1))
        target_value = max(80.0, (current[-1] if current else 70.0) + 5.0)
        return {"labels": labels, "current": current, "target": [round(target_value, 1) for _ in labels]}

    def _build_accuracy_chart(self, latest_payload: Dict[str, object], events: List[Dict[str, object]]) -> Dict[str, object]:
        stat_map: Dict[str, Dict[str, float]] = defaultdict(lambda: {"attempts": 0.0, "correct": 0.0})
        for event in events:
            for tag in event["knowledge_tags"]:
                stat_map[tag]["attempts"] += 1
                stat_map[tag]["correct"] += 1 if event["is_correct"] else 0
        rows = sorted(stat_map.items(), key=lambda item: item[1]["attempts"], reverse=True)[:5]
        if not rows:
            rows = [
                (item["knowledge_tag"], {"attempts": 1.0, "correct": float(item["mastery_score"]) / 100.0})
                for item in latest_payload["knowledge_matrix"][:5]
            ]
        return {
            "labels": [label for label, _ in rows],
            "values": [round((stats["correct"] / max(1.0, stats["attempts"])) * 100, 1) for _, stats in rows],
        }

    def _build_mastery_chart(self, latest_payload: Dict[str, object]) -> Dict[str, object]:
        dimensions = latest_payload["dimensions"]
        return {
            "labels": [item["dimension_name"] for item in dimensions],
            "actual": [round(float(item["score"]), 1) for item in dimensions],
            "target": [78 for _ in dimensions],
        }

    def _build_time_distribution_chart(self, events: List[Dict[str, object]]) -> Dict[str, object]:
        minutes_by_tag: Dict[str, float] = defaultdict(float)
        for event in events:
            share = (float(event["duration_seconds"]) / 60.0) / max(1, len(event["knowledge_tags"]))
            for tag in event["knowledge_tags"] or ["未分类"]:
                minutes_by_tag[tag] += share
        rows = sorted(minutes_by_tag.items(), key=lambda item: item[1], reverse=True)[:5]
        return {
            "labels": [label for label, _ in rows],
            "values": [round(value, 1) for _, value in rows],
        }

    def _build_weakness_items(
        self,
        latest_payload: Dict[str, object],
        events: List[Dict[str, object]],
        knowledge_tracking: Dict[str, object],
    ) -> List[Dict[str, object]]:
        accuracy_map = {}
        accuracy_chart = self._build_accuracy_chart(latest_payload, events)
        for label, value in zip(accuracy_chart["labels"], accuracy_chart["values"]):
            accuracy_map[label] = value
        items = []
        tracking_map = {
            item["knowledge_tag"]: item
            for item in knowledge_tracking.get("knowledge_states", [])
        }
        for row in latest_payload["knowledge_matrix"]:
            if not row["needs_attention"] and len(items) >= 3:
                continue
            tracking_state = tracking_map.get(row["knowledge_tag"], {})
            items.append(
                {
                    "knowledge_tag": row["knowledge_tag"],
                    "accuracy": round(float(accuracy_map.get(row["knowledge_tag"], row["mastery_score"])), 1),
                    "description": tracking_state.get("review_reason") or "；".join(row["evidence"][:2]) or "该知识点近期表现波动，建议按“回顾-例题-专项训练”路径复盘。",
                    "review_url": f"subject-1.html?subject=数学&knowledge={row['knowledge_tag']}",
                    "practice_url": f"practice.html?subject=数学&knowledge={row['knowledge_tag']}",
                    "risk_level": tracking_state.get("risk_level", "中遗忘风险"),
                    "mastery": tracking_state.get("current_mastery", round(float(row["mastery_score"]), 1)),
                    "trend_label": tracking_state.get("trend_label", "稳定"),
                }
            )
            if len(items) >= 3:
                break
        return items

    def _build_analysis_report(
        self,
        student: Student,
        latest_payload: Dict[str, object],
        latest_recommendation: Optional[Dict[str, object]],
        weak_items: List[Dict[str, object]],
        events: List[Dict[str, object]],
        knowledge_tracking: Dict[str, object],
    ) -> Dict[str, object]:
        dimensions = latest_payload["dimensions"]
        strongest = max(dimensions, key=lambda item: float(item["score"]))
        weakest = min(dimensions, key=lambda item: float(item["score"]))
        strengths = [
            {
                "title": strongest["dimension_name"],
                "detail": f"当前得分 {round(float(strongest['score']))}，说明这部分已成为当前学习的稳定支点。",
            }
        ]
        strengths.extend(
            {
                "title": row["knowledge_tag"],
                "detail": f"当前掌握度 {round(float(row['mastery_score']))}，可以作为后续迁移练习的基础。",
            }
            for row in latest_payload["knowledge_matrix"]
            if float(row["mastery_score"]) >= 75
        )
        improvements = [
            {
                "title": weakest["dimension_name"],
                "detail": f"当前得分 {round(float(weakest['score']))}，建议优先安排低门槛、稳定反馈的训练。",
            }
        ]
        improvements.extend({"title": item["knowledge_tag"], "detail": item["description"]} for item in weak_items)
        hour_by_day: Dict[str, float] = defaultdict(float)
        for event in events:
            key = event["created_at"].strftime("%m-%d")
            hour_by_day[key] += float(event["duration_seconds"]) / 3600.0
        study_days = len(hour_by_day)
        avg_daily = round(sum(hour_by_day.values()) / max(1, study_days), 1)
        habits = (
            f"{student.name} 当前的画像摘要是：{latest_payload['portrait_summary']} "
            f"最近区间记录了 {study_days} 个活跃学习日，平均每天约 {avg_daily} 小时。"
        )
        recommendations = list(latest_payload["training_focus"][:4])
        if latest_recommendation:
            recommendations.append(latest_recommendation["overall_commentary"] or "继续完成当前训练批次。")
        recommendations.extend(f"重点回看：{item['knowledge_tag']}" for item in weak_items[:2])
        recommendations.extend(
            f"优先复习：{item['knowledge_tag']}（{item['risk_level']}）"
            for item in knowledge_tracking.get("top_review", [])[:2]
        )
        return {
            "summary": latest_payload["teacher_commentary"],
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "habits": habits,
            "recommendations": list(dict.fromkeys(recommendations))[:5],
        }

    def _build_defense_assets(self) -> Dict[str, object]:
        return {
            "plain_summary": "长期模型看学生会不会，短期模型看学生会不会忘，两者一起决定当前先练什么。",
            "one_minute_script": (
                "我们先收集学生在诊断和练习中的题目证据，再按知识点做长期掌握追踪。"
                "长期层用轻量 KT 看这个知识点到底掌握得怎么样、趋势是在上升还是下降；"
                "短期层用遗忘曲线看距离上次练习多久、现在是不是快忘了。"
                "最后把长期薄弱、短期遗忘风险和最近错误波动融合成推荐优先级，"
                "所以系统不仅能推荐题，还能解释这道题是因为长期不会、短期快忘了，还是最近表现不稳定而被前置。"
            ),
            "flow_steps": [
                {"title": "证据采集", "detail": "收集 student_id、question_id、knowledge_tags、created_at、is_correct、duration_seconds、difficulty、snapshot_version。"},
                {"title": "长期模型", "detail": "对每个知识点做轻量 KT，输出当前掌握度、最近趋势、是否需要关注。"},
                {"title": "短期模型", "detail": "用遗忘曲线估计 retention 与 forgetting_risk，并划分高/中/低风险。"},
                {"title": "融合推荐", "detail": "把长期薄弱、遗忘风险和错误波动融合成 priority，再输出整体理由和单题理由。"},
            ],
        }

    def _build_emotion_support(self, latest_payload: Dict[str, object], events: List[Dict[str, object]]) -> Dict[str, object]:
        trait_map = {
            item["trait_code"]: float(item["trait_value"])
            for item in latest_payload.get("learner_traits", [])
        }
        confidence_level = round(trait_map.get("confidence_level", 60.0), 1)
        recent_events = sorted(events, key=lambda item: item["created_at"], reverse=True)[:8]
        consecutive_errors = 0
        for item in recent_events:
            if item["is_correct"]:
                break
            consecutive_errors += 1
        overtime_count = sum(
            1
            for item in recent_events
            if float(item["duration_seconds"]) > float(item.get("target_duration_seconds") or 0) * 1.3
        )
        interruption_days = 0
        if recent_events:
            interruption_days = max(0, round((datetime.utcnow() - recent_events[0]["created_at"]).total_seconds() / 86400.0))

        if consecutive_errors >= 3 or (confidence_level < 45 and overtime_count >= 2):
            status = "轻度挫败风险"
            prompt = "当前连续错误较多，建议先进行巩固训练。"
        elif consecutive_errors >= 2 or overtime_count >= 3 or interruption_days >= 5 or confidence_level < 55:
            status = "建议鼓励"
            prompt = "当前状态有波动，建议先从低门槛题开始，逐步找回稳定节奏。"
        else:
            status = "稳定"
            prompt = "当前状态整体稳定，可以继续按计划推进训练。"

        return {
            "status": status,
            "confidence_level": confidence_level,
            "consecutive_errors": consecutive_errors,
            "overtime_count": overtime_count,
            "interruption_days": interruption_days,
            "prompt": prompt,
        }

    def _build_learning_plan(
        self,
        latest_payload: Dict[str, object],
        latest_recommendation: Optional[Dict[str, object]],
    ) -> Dict[str, object]:
        focus_topics = [row["knowledge_tag"] for row in latest_payload["knowledge_matrix"] if row["needs_attention"]][:4]
        focus_topics.extend(item.replace("优先修复 ", "") for item in latest_payload["training_focus"][:2])
        topics = [topic for topic in focus_topics if topic]
        if not topics:
            topics = ["当前画像复盘", "基础巩固", "迁移提升"]
        days = ["周一", "周二", "周三", "周四", "周五", "周末"]
        weeks = []
        for week_index in range(2):
            week_rows = []
            for day_index, day in enumerate(days):
                topic = topics[(week_index * len(days) + day_index) % len(topics)]
                week_rows.append(
                    {
                        "day_label": day,
                        "tasks": [
                            {"time": "30分钟" if day != "周末" else "45分钟", "task": f"{topic} 概念回顾与例题整理"},
                            {"time": "40分钟" if day != "周末" else "60分钟", "task": f"{topic} 分层训练与错因记录"},
                        ],
                    }
                )
            weeks.append({"week_label": f"第{week_index + 1}周", "days": week_rows})
        subtitle = latest_recommendation["batch_goal"] if latest_recommendation else "围绕当前成长画像安排两周训练节奏。"
        return {"title": "未来两周学习安排", "subtitle": subtitle, "weeks": weeks}

    def _build_learning_rhythm(self, student_id: str, weekly_target_questions: int) -> Dict[str, object]:
        today = datetime.utcnow().date()
        practice_rows = self.db.query(PracticeAnswer).filter(PracticeAnswer.student_id == student_id).all()
        snapshot_rows = self.db.query(PortraitSnapshot).filter(PortraitSnapshot.student_id == student_id).all()
        practice_counts: Dict[datetime.date, int] = defaultdict(int)
        activity_counts: Dict[datetime.date, int] = defaultdict(int)
        for row in practice_rows:
            day = row.created_at.date()
            practice_counts[day] += 1
            activity_counts[day] += 1
        for row in snapshot_rows:
            activity_counts[row.created_at.date()] = max(activity_counts[row.created_at.date()], 1)

        streak_days = 0
        cursor = today
        while activity_counts.get(cursor, 0) > 0:
            streak_days += 1
            cursor = cursor - timedelta(days=1)

        week_start = today - timedelta(days=6)
        completed_this_week = sum(count for day, count in practice_counts.items() if day >= week_start)
        return {
            "streak_days": streak_days,
            "completed_this_week": completed_this_week,
            "target_questions": max(4, weekly_target_questions),
        }

    def _build_profile_tags(self, latest_payload: Dict[str, object], streak_days: int) -> List[str]:
        summary_card = latest_payload["summary_card"]
        return [
            summary_card["strength_highlight"],
            summary_card["weakness_highlight"],
            f"{streak_days}天连续学习",
        ]

    def _build_today_stats(self, practice_rows: List[PracticeAnswer], latest_recommendation: Optional[Dict[str, object]]) -> Dict[str, object]:
        today = datetime.utcnow().date()
        today_rows = [row for row in practice_rows if row.created_at.date() == today]
        total_minutes = round(sum(float(row.duration_seconds) for row in today_rows) / 60)
        progress = latest_recommendation["progress"] if latest_recommendation else None
        return {
            "completion": round(progress["completion_rate"]) if progress else 0,
            "time_spent_text": f"{total_minutes}分钟" if today_rows else "今日暂未开始训练",
            "subjects": ["数学成长训练"],
            "completed_tasks": f"{progress['completed_questions']}/{progress['total_questions']}" if progress else "0/0",
        }

    def _build_progress_bars(self, latest_payload: Dict[str, object]) -> List[Dict[str, object]]:
        target_codes = ["calculation_accuracy", "knowledge_mastery", "logical_reasoning", "learning_stability"]
        rows = {item["dimension_code"]: item for item in latest_payload["dimensions"]}
        css_classes = ["math", "english", "physics", "chemistry"]
        payload = []
        for css_class, code in zip(css_classes, target_codes):
            row = rows.get(code)
            if row is None:
                continue
            payload.append({"label": row["dimension_name"], "value": round(float(row["score"])), "css_class": css_class})
        return payload

    def _build_achievements(
        self,
        latest_payload: Dict[str, object],
        snapshots: List[PortraitSnapshot],
        practice_rows: List[PracticeAnswer],
        wrong_rows: List[WrongQuestionRecord],
        streak_days: int,
    ) -> List[Dict[str, object]]:
        avg_dimension = mean(float(item["score"]) for item in latest_payload["dimensions"])
        resolved_wrong = sum(1 for row in wrong_rows if row.status == "resolved")
        open_wrong = sum(1 for row in wrong_rows if row.status == "open")
        return [
            {"title": "学习先锋", "description": "连续学习7天", "unlocked": streak_days >= 7},
            {"title": "训练执行者", "description": f"累计完成 {len(practice_rows)} 道训练题", "unlocked": len(practice_rows) >= 10},
            {"title": "画像成长者", "description": f"已形成 {len(snapshots)} 个成长版本", "unlocked": len(snapshots) >= 2},
            {"title": "稳定进步者", "description": f"当前综合画像 {round(avg_dimension)} 分", "unlocked": avg_dimension >= 70},
            {"title": "错题攻坚者", "description": f"已解决 {resolved_wrong} 道错题", "unlocked": resolved_wrong >= 1},
            {"title": "复盘跟进者", "description": f"待回流错题 {open_wrong} 道", "unlocked": open_wrong == 0 and len(wrong_rows) > 0},
        ]

    def _build_personal_advice(
        self,
        latest_payload: Dict[str, object],
        latest_recommendation: Optional[Dict[str, object]],
        wrong_rows: List[WrongQuestionRecord],
    ) -> List[Dict[str, object]]:
        items = []
        for focus in latest_payload["training_focus"][:2]:
            items.append({"badge": "训练重点", "text": focus})
        for row in latest_payload["risk_flags"][:2]:
            items.append({"badge": "风险提醒", "text": row})
        if latest_recommendation:
            items.append({"badge": "训练计划", "text": latest_recommendation["batch_goal"]})
        if wrong_rows:
            items.append({"badge": "错题回流", "text": f"当前仍有 {sum(1 for row in wrong_rows if row.status == 'open')} 道题需要回看。"})
        return items[:4]

    def _build_personal_learning_report(
        self,
        latest_payload: Dict[str, object],
        practice_rows: List[PracticeAnswer],
        diagnostic_rows: List[DiagnosticAnswer],
        snapshots: List[PortraitSnapshot],
    ) -> Dict[str, object]:
        today = datetime.utcnow().date()
        labels = []
        values = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            labels.append(f"{day.month}/{day.day}")
            total_seconds = sum(float(row.duration_seconds) for row in practice_rows if row.created_at.date() == day)
            total_seconds += sum(float(row.duration_seconds) for row in diagnostic_rows if row.created_at.date() == day)
            values.append(round(total_seconds / 3600, 1))
        previous_snapshot = snapshots[1] if len(snapshots) > 1 else None
        previous_avg = 0.0
        if previous_snapshot:
            previous_payload = self.portrait_service.snapshot_to_payload(previous_snapshot)
            previous_avg = mean(float(item["score"]) for item in previous_payload["dimensions"])
        current_avg = mean(float(item["score"]) for item in latest_payload["dimensions"])
        return {
            "title": "最近7天学习报告",
            "chart": {"labels": labels, "values": values},
            "highlights": [
                {"title": "画像进步", "detail": f"相较上一版，综合画像变化 {round(current_avg - previous_avg, 1)} 分。"},
                {"title": "训练重点", "detail": "、".join(latest_payload["training_focus"][:3]) or "当前暂无训练重点。"},
                {"title": "待关注知识点", "detail": latest_payload["summary_card"]["knowledge_risk_summary"]},
            ],
        }

    def _build_personal_weakness_analysis(
        self,
        latest_payload: Dict[str, object],
        latest_recommendation: Optional[Dict[str, object]],
        wrong_rows: List[WrongQuestionRecord],
    ) -> Dict[str, object]:
        weaknesses = []
        for index, row in enumerate(latest_payload["knowledge_matrix"][:3]):
            priority = "high" if index == 0 else "medium" if index == 1 else "low"
            weaknesses.append({"priority": priority, "text": f"{row['knowledge_tag']}：掌握度 {round(float(row['mastery_score']))} 分"})
        training_cards = []
        if latest_recommendation:
            for item in latest_recommendation["items"][:3]:
                training_cards.append(
                    {
                        "subject": "数学",
                        "title": item["title"],
                        "description": item["ai_reason"] or item["rule_reason"],
                        "time": f"预计用时: {item['target_duration_seconds']}秒",
                        "difficulty": f"难度: {item['difficulty']}",
                        "url": "practice.html",
                    }
                )
        if not training_cards:
            training_cards.append(
                {
                    "subject": "数学",
                    "title": "当前暂无训练方案",
                    "description": "先完成诊断建档或生成训练计划后，这里会自动同步后端推荐内容。",
                    "time": "预计用时: --",
                    "difficulty": "难度: --",
                    "url": "practice.html",
                }
            )
        return {
            "radar": {
                "labels": [item["dimension_name"] for item in latest_payload["dimensions"]],
                "values": [round(float(item["score"]), 1) for item in latest_payload["dimensions"]],
            },
            "summary_intro": (
                f"基于最近画像与练习记录，当前最需要关注的是 {latest_payload['summary_card']['weakness_highlight']}。"
                f"待回流错题 {sum(1 for row in wrong_rows if row.status == 'open')} 道。"
            ),
            "weaknesses": weaknesses,
            "training_cards": training_cards,
        }

    def _build_practice_records(
        self,
        student_id: str,
        snapshots: List[PortraitSnapshot],
        practice_rows: List[PracticeAnswer],
        wrong_rows: List[WrongQuestionRecord],
    ) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        batch_lookup = {
            row.batch_id: row
            for row in self.db.query(RecommendationBatch)
            .filter(RecommendationBatch.student_id == student_id)
            .order_by(RecommendationBatch.created_at.desc(), RecommendationBatch.id.desc())
            .all()
        }
        grouped_practice: Dict[str, List[PracticeAnswer]] = defaultdict(list)
        for row in practice_rows:
            grouped_practice[row.batch_id].append(row)
        for batch_id, answers in grouped_practice.items():
            latest_time = max(row.created_at for row in answers)
            correct_count = sum(1 for row in answers if row.is_correct)
            total_count = len(answers)
            score = round((correct_count / max(1, total_count)) * 100)
            batch = batch_lookup.get(batch_id)
            mode_label = self.recommendation_service.TRAINING_MODE_LABELS.get(batch.training_mode, "平衡训练") if batch else "训练批次"
            rows.append(
                {
                    "record_type": "plan",
                    "filter_key": "plan",
                    "date": latest_time.isoformat(),
                    "title": f"训练批次：{mode_label}",
                    "score": score,
                    "duration_text": f"{round(sum(float(row.duration_seconds) for row in answers) / 60)}分钟",
                    "question_count": total_count,
                    "accuracy": score,
                }
            )
        for snapshot in snapshots[:2]:
            payload = self.portrait_service.snapshot_to_payload(snapshot)
            avg_score = round(mean(float(item["score"]) for item in payload["dimensions"]))
            rows.append(
                {
                    "record_type": "snapshot",
                    "filter_key": "snapshot",
                    "date": snapshot.created_at.isoformat(),
                    "title": f"成长画像 V{payload['version_number']}",
                    "score": avg_score,
                    "duration_text": "画像更新",
                    "question_count": len(payload["training_focus"]),
                    "accuracy": avg_score,
                }
            )
        for row in wrong_rows[:2]:
            rows.append(
                {
                    "record_type": "wrong",
                    "filter_key": "wrong",
                    "date": row.updated_at.isoformat(),
                    "title": f"错题回流：{row.question_id}",
                    "score": max(20, 100 - row.wrong_count * 15),
                    "duration_text": f"错因复盘 {row.wrong_count} 次",
                    "question_count": row.wrong_count,
                    "accuracy": max(20, 100 - row.wrong_count * 15),
                }
            )
        rows.sort(key=lambda item: item["date"], reverse=True)
        return rows[:6]
