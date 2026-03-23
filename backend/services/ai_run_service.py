from sqlalchemy.orm import Session

from backend.models import AIAnalysisRun


class AIRunService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_recent_runs(self, student_id: str, limit: int = 12):
        return (
            self.db.query(AIAnalysisRun)
            .filter(AIAnalysisRun.student_id == student_id)
            .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
            .limit(limit)
            .all()
        )

    def get_latest_run(self, student_id: str):
        return (
            self.db.query(AIAnalysisRun)
            .filter(AIAnalysisRun.student_id == student_id)
            .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
            .first()
        )

    def to_status(self, run: AIAnalysisRun):
        return {
            "enabled": run.enabled,
            "attempted": run.attempted,
            "success": run.success,
            "fallback_used": run.fallback_used,
            "confidence": run.confidence,
            "error_summary": run.error_summary,
            "analysis_summary": run.analysis_summary,
            "stage": run.stage,
            "request_type": run.request_type,
            "model_name": run.model_name,
        }

    def to_response(self, run: AIAnalysisRun):
        return {
            "run_id": run.run_id,
            "stage": run.stage,
            "request_type": run.request_type,
            "model_name": run.model_name,
            "enabled": run.enabled,
            "attempted": run.attempted,
            "success": run.success,
            "fallback_used": run.fallback_used,
            "confidence": run.confidence,
            "error_summary": run.error_summary,
            "analysis_summary": run.analysis_summary,
            "raw_prompt_summary": run.raw_prompt_summary,
            "raw_response_text": run.raw_response_text,
            "normalized_output_json": run.normalized_output_json,
            "structured_output_json": run.structured_output_json,
            "created_at": run.created_at.isoformat(),
        }
