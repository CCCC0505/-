from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models import (
    CognitiveDiagnosisRecord,
    KnowledgeMasteryRecord,
    LearnerTraitRecord,
    PortraitDimensionScore,
    PortraitSnapshot,
    RecommendationBatch,
    RecommendationItem,
)
from backend.services.common import json_dumps, json_loads, make_id


class PortraitService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest_snapshot(self, student_id: str) -> Optional[PortraitSnapshot]:
        return (
            self.db.query(PortraitSnapshot)
            .filter(PortraitSnapshot.student_id == student_id)
            .order_by(PortraitSnapshot.version_number.desc(), PortraitSnapshot.id.desc())
            .first()
        )

    def get_previous_snapshot(self, student_id: str, current_snapshot_id: str) -> Optional[PortraitSnapshot]:
        current = self.db.query(PortraitSnapshot).filter(PortraitSnapshot.snapshot_id == current_snapshot_id).first()
        if current is None or current.version_number <= 1:
            return None
        return (
            self.db.query(PortraitSnapshot)
            .filter(
                PortraitSnapshot.student_id == student_id,
                PortraitSnapshot.version_number == current.version_number - 1,
            )
            .first()
        )

    def get_snapshot_history(self, student_id: str) -> List[PortraitSnapshot]:
        return (
            self.db.query(PortraitSnapshot)
            .filter(PortraitSnapshot.student_id == student_id)
            .order_by(PortraitSnapshot.version_number.desc(), PortraitSnapshot.id.desc())
            .all()
        )

    def create_snapshot(
        self,
        student_id: str,
        source_stage: str,
        payload: Dict[str, object],
        ai_output: Dict[str, object],
        parent_snapshot_id: Optional[str] = None,
    ) -> PortraitSnapshot:
        latest = self.get_latest_snapshot(student_id)
        version_number = 1 if latest is None else latest.version_number + 1
        snapshot = PortraitSnapshot(
            snapshot_id=make_id("snapshot"),
            student_id=student_id,
            version_number=version_number,
            source_stage=source_stage,
            parent_snapshot_id=parent_snapshot_id,
            portrait_summary=str(ai_output.get("portrait_summary") or payload["fallback_summary"]),
            teacher_commentary=str(ai_output.get("teacher_commentary") or payload["fallback_commentary"]),
            training_focus_json=json_dumps(ai_output.get("training_focus") or payload["training_focus"]),
            risk_flags_json=json_dumps(ai_output.get("risk_flags") or payload["risk_flags"]),
            ai_confidence=float(ai_output.get("confidence", 0.0) or 0.0),
        )
        self.db.add(snapshot)
        self.db.flush()

        for row in payload["dimensions"]:
            self.db.add(
                PortraitDimensionScore(
                    snapshot_id=snapshot.snapshot_id,
                    dimension_code=row["dimension_code"],
                    dimension_name=row["dimension_name"],
                    score=float(row["score"]),
                    evidence_json=json_dumps(row["evidence"]),
                )
            )
        for row in payload["knowledge_matrix"]:
            self.db.add(
                KnowledgeMasteryRecord(
                    snapshot_id=snapshot.snapshot_id,
                    knowledge_tag=row["knowledge_tag"],
                    mastery_score=float(row["mastery_score"]),
                    needs_attention=bool(row["needs_attention"]),
                    evidence_json=json_dumps(row["evidence"]),
                )
            )
        for row in payload["cognitive_diagnosis"]:
            self.db.add(
                CognitiveDiagnosisRecord(
                    snapshot_id=snapshot.snapshot_id,
                    level_code=row["level_code"],
                    level_name=row["level_name"],
                    accuracy=float(row["accuracy"]),
                    needs_attention=bool(row["needs_attention"]),
                    evidence_json=json_dumps(row["evidence"]),
                )
            )
        for row in payload["learner_traits"]:
            self.db.add(
                LearnerTraitRecord(
                    snapshot_id=snapshot.snapshot_id,
                    trait_code=row["trait_code"],
                    trait_name=row["trait_name"],
                    trait_value=float(row["trait_value"]),
                    trait_label=row["trait_label"],
                    source=row["source"],
                )
            )
        self.db.flush()
        return snapshot

    def snapshot_to_payload(self, snapshot: PortraitSnapshot) -> Dict[str, object]:
        dimension_rows = (
            self.db.query(PortraitDimensionScore)
            .filter(PortraitDimensionScore.snapshot_id == snapshot.snapshot_id)
            .order_by(PortraitDimensionScore.score.asc(), PortraitDimensionScore.id.asc())
            .all()
        )
        knowledge_rows = (
            self.db.query(KnowledgeMasteryRecord)
            .filter(KnowledgeMasteryRecord.snapshot_id == snapshot.snapshot_id)
            .order_by(KnowledgeMasteryRecord.mastery_score.asc(), KnowledgeMasteryRecord.id.asc())
            .all()
        )
        cognitive_rows = (
            self.db.query(CognitiveDiagnosisRecord)
            .filter(CognitiveDiagnosisRecord.snapshot_id == snapshot.snapshot_id)
            .order_by(CognitiveDiagnosisRecord.accuracy.asc(), CognitiveDiagnosisRecord.id.asc())
            .all()
        )
        trait_rows = (
            self.db.query(LearnerTraitRecord)
            .filter(LearnerTraitRecord.snapshot_id == snapshot.snapshot_id)
            .order_by(LearnerTraitRecord.id.asc())
            .all()
        )
        payload = {
            "snapshot_id": snapshot.snapshot_id,
            "version_number": snapshot.version_number,
            "source_stage": snapshot.source_stage,
            "parent_snapshot_id": snapshot.parent_snapshot_id,
            "portrait_summary": snapshot.portrait_summary,
            "teacher_commentary": snapshot.teacher_commentary,
            "training_focus": json_loads(snapshot.training_focus_json, []),
            "risk_flags": json_loads(snapshot.risk_flags_json, []),
            "ai_confidence": snapshot.ai_confidence,
            "created_at": snapshot.created_at.isoformat(),
            "dimensions": [
                {
                    "dimension_code": row.dimension_code,
                    "dimension_name": row.dimension_name,
                    "score": row.score,
                    "level": self._level_label(row.score),
                    "evidence": json_loads(row.evidence_json, []),
                }
                for row in dimension_rows
            ],
            "knowledge_matrix": [
                {
                    "knowledge_tag": row.knowledge_tag,
                    "mastery_score": row.mastery_score,
                    "needs_attention": row.needs_attention,
                    "evidence": json_loads(row.evidence_json, []),
                }
                for row in knowledge_rows
            ],
            "cognitive_diagnosis": [
                {
                    "level_code": row.level_code,
                    "level_name": row.level_name,
                    "accuracy": row.accuracy,
                    "needs_attention": row.needs_attention,
                    "evidence": json_loads(row.evidence_json, []),
                }
                for row in cognitive_rows
            ],
            "learner_traits": [
                {
                    "trait_code": row.trait_code,
                    "trait_name": row.trait_name,
                    "trait_value": row.trait_value,
                    "trait_label": row.trait_label,
                    "source": row.source,
                }
                for row in trait_rows
            ],
        }
        payload["summary_card"] = self._build_summary_card(payload)
        return payload

    def snapshot_to_response(self, snapshot: PortraitSnapshot) -> Dict[str, object]:
        return self.snapshot_to_payload(snapshot)

    def latest_recommendation_summary(self, student_id: str) -> Optional[Dict[str, object]]:
        batch = (
            self.db.query(RecommendationBatch)
            .filter(RecommendationBatch.student_id == student_id)
            .order_by(RecommendationBatch.created_at.desc(), RecommendationBatch.id.desc())
            .first()
        )
        if batch is None:
            return None
        items = (
            self.db.query(RecommendationItem)
            .filter(RecommendationItem.batch_id == batch.batch_id)
            .order_by(RecommendationItem.rank_score.desc(), RecommendationItem.id.asc())
            .all()
        )
        question_lookup = {
            row.question_id: row
            for row in items
        }
        return {
            "batch_id": batch.batch_id,
            "training_focus": json_loads(batch.training_focus_json, []),
            "overall_commentary": batch.overall_commentary,
            "items": [
                {
                    "question_id": row.question_id,
                    "title": question_lookup[row.question_id].question_id if row.question_id in question_lookup else row.question_id,
                    "stem": "",
                    "options": [],
                    "difficulty": 0,
                    "knowledge_tags": [],
                    "recommendation_type": row.recommendation_type,
                    "rule_reason": row.rule_reason,
                    "ai_reason": row.ai_reason,
                }
                for row in items
            ],
        }

    def _level_label(self, score: float) -> str:
        if score >= 80:
            return "优势"
        if score >= 60:
            return "稳定"
        if score >= 45:
            return "待加强"
        return "预警"

    def _build_summary_card(self, payload: Dict[str, object]) -> Dict[str, object]:
        dimensions = payload["dimensions"]
        weakest = min(dimensions, key=lambda item: item["score"]) if dimensions else None
        strongest = max(dimensions, key=lambda item: item["score"]) if dimensions else None
        weak_knowledge = [item["knowledge_tag"] for item in payload["knowledge_matrix"] if item["needs_attention"]][:3]
        return {
            "headline": payload["portrait_summary"],
            "teacher_message": payload["teacher_commentary"],
            "strength_highlight": strongest["dimension_name"] if strongest else "暂无",
            "weakness_highlight": weakest["dimension_name"] if weakest else "暂无",
            "focus_summary": "、".join(payload["training_focus"][:3]) or "暂无",
            "knowledge_risk_summary": "、".join(weak_knowledge) or "当前无明显薄弱知识点",
            "report_lines": [
                f"当前优势维度：{strongest['dimension_name']}" if strongest else "当前优势维度：暂无",
                f"当前关注维度：{weakest['dimension_name']}" if weakest else "当前关注维度：暂无",
                f"训练重点：{'、'.join(payload['training_focus'][:3]) or '暂无'}",
                f"待关注知识点：{'、'.join(weak_knowledge) or '暂无'}",
            ],
        }
