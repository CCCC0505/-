from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from backend.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(64), nullable=False)
    grade = Column(String(32), nullable=False)
    weekly_target_questions = Column(Integer, nullable=False, default=12)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ColdStartSession(Base):
    __tablename__ = "cold_start_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    status = Column(String(32), default="created", nullable=False)
    questionnaire_completed = Column(Boolean, default=False, nullable=False)
    diagnostic_completed = Column(Boolean, default=False, nullable=False)
    finalized = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class QuestionnaireAnswer(Base):
    __tablename__ = "questionnaire_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), ForeignKey("cold_start_sessions.session_id"), nullable=False, index=True)
    question_code = Column(String(64), nullable=False)
    answer_value = Column(String(64), nullable=False)
    mapped_trait_code = Column(String(64), nullable=False)
    mapped_trait_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("session_id", "question_code", name="uq_questionnaire_session_question"),)


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True)
    question_id = Column(String(64), unique=True, nullable=False, index=True)
    grade = Column(String(32), nullable=False, index=True)
    stage = Column(String(32), nullable=False, index=True)
    title = Column(String(128), nullable=False)
    stem = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False, default="[]")
    correct_answer = Column(String(64), nullable=False)
    explanation = Column(Text, nullable=False, default="")
    difficulty = Column(Integer, nullable=False, default=2)
    target_duration_seconds = Column(Integer, nullable=False, default=90)
    knowledge_tags_json = Column(Text, nullable=False, default="[]")
    cognitive_level = Column(String(32), nullable=False)
    dimension_weights_json = Column(Text, nullable=False, default="{}")
    training_tags_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DiagnosticAnswer(Base):
    __tablename__ = "diagnostic_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), ForeignKey("cold_start_sessions.session_id"), nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    question_id = Column(String(64), ForeignKey("question_bank.question_id"), nullable=False, index=True)
    answer_text = Column(String(128), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    duration_seconds = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("session_id", "question_id", name="uq_diagnostic_session_question"),)


class PortraitSnapshot(Base):
    __tablename__ = "portrait_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    source_stage = Column(String(32), nullable=False)
    parent_snapshot_id = Column(String(64), nullable=True)
    portrait_summary = Column(Text, nullable=False, default="")
    teacher_commentary = Column(Text, nullable=False, default="")
    training_focus_json = Column(Text, nullable=False, default="[]")
    risk_flags_json = Column(Text, nullable=False, default="[]")
    ai_confidence = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PortraitDimensionScore(Base):
    __tablename__ = "portrait_dimension_scores"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String(64), ForeignKey("portrait_snapshots.snapshot_id"), nullable=False, index=True)
    dimension_code = Column(String(64), nullable=False)
    dimension_name = Column(String(64), nullable=False)
    score = Column(Float, nullable=False)
    evidence_json = Column(Text, nullable=False, default="[]")

    __table_args__ = (UniqueConstraint("snapshot_id", "dimension_code", name="uq_snapshot_dimension"),)


class KnowledgeMasteryRecord(Base):
    __tablename__ = "knowledge_mastery_records"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String(64), ForeignKey("portrait_snapshots.snapshot_id"), nullable=False, index=True)
    knowledge_tag = Column(String(64), nullable=False)
    mastery_score = Column(Float, nullable=False)
    needs_attention = Column(Boolean, nullable=False, default=False)
    evidence_json = Column(Text, nullable=False, default="[]")

    __table_args__ = (UniqueConstraint("snapshot_id", "knowledge_tag", name="uq_snapshot_knowledge"),)


class CognitiveDiagnosisRecord(Base):
    __tablename__ = "cognitive_diagnosis_records"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String(64), ForeignKey("portrait_snapshots.snapshot_id"), nullable=False, index=True)
    level_code = Column(String(64), nullable=False)
    level_name = Column(String(64), nullable=False)
    accuracy = Column(Float, nullable=False)
    needs_attention = Column(Boolean, nullable=False, default=False)
    evidence_json = Column(Text, nullable=False, default="[]")

    __table_args__ = (UniqueConstraint("snapshot_id", "level_code", name="uq_snapshot_cognitive"),)


class LearnerTraitRecord(Base):
    __tablename__ = "learner_trait_records"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String(64), ForeignKey("portrait_snapshots.snapshot_id"), nullable=False, index=True)
    trait_code = Column(String(64), nullable=False)
    trait_name = Column(String(64), nullable=False)
    trait_value = Column(Float, nullable=False)
    trait_label = Column(String(64), nullable=False)
    source = Column(String(32), nullable=False, default="questionnaire")

    __table_args__ = (UniqueConstraint("snapshot_id", "trait_code", name="uq_snapshot_trait"),)


class RecommendationBatch(Base):
    __tablename__ = "recommendation_batches"

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    snapshot_id = Column(String(64), ForeignKey("portrait_snapshots.snapshot_id"), nullable=False)
    requested_count = Column(Integer, nullable=False, default=9)
    training_mode = Column(String(32), nullable=False, default="balanced")
    training_focus_json = Column(Text, nullable=False, default="[]")
    overall_commentary = Column(Text, nullable=False, default="")
    ai_run_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id = Column(Integer, primary_key=True)
    batch_id = Column(String(64), ForeignKey("recommendation_batches.batch_id"), nullable=False, index=True)
    question_id = Column(String(64), ForeignKey("question_bank.question_id"), nullable=False, index=True)
    recommendation_type = Column(String(32), nullable=False)
    rank_score = Column(Float, nullable=False)
    rule_reason = Column(Text, nullable=False)
    ai_reason = Column(Text, nullable=False, default="")

    __table_args__ = (UniqueConstraint("batch_id", "question_id", name="uq_batch_question"),)


class PracticeAnswer(Base):
    __tablename__ = "practice_answers"

    id = Column(Integer, primary_key=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    batch_id = Column(String(64), ForeignKey("recommendation_batches.batch_id"), nullable=False, index=True)
    snapshot_id = Column(String(64), ForeignKey("portrait_snapshots.snapshot_id"), nullable=False)
    question_id = Column(String(64), ForeignKey("question_bank.question_id"), nullable=False, index=True)
    answer_text = Column(String(128), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    duration_seconds = Column(Float, nullable=False, default=0)
    feedback_summary = Column(Text, nullable=False, default="")
    ai_run_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WrongQuestionRecord(Base):
    __tablename__ = "wrong_question_records"

    id = Column(Integer, primary_key=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    question_id = Column(String(64), ForeignKey("question_bank.question_id"), nullable=False, index=True)
    wrong_count = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="open")
    root_cause_summary = Column(Text, nullable=False, default="")
    qwen_summary = Column(Text, nullable=False, default="")
    last_wrong_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("student_id", "question_id", name="uq_student_wrong_question"),)


class AIAnalysisRun(Base):
    __tablename__ = "ai_analysis_runs"

    id = Column(Integer, primary_key=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    student_id = Column(String(64), ForeignKey("students.student_id"), nullable=False, index=True)
    stage = Column(String(32), nullable=False)
    request_type = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False, default="dashscope")
    model_name = Column(String(64), nullable=False, default="")
    enabled = Column(Boolean, nullable=False, default=False)
    attempted = Column(Boolean, nullable=False, default=False)
    success = Column(Boolean, nullable=False, default=False)
    fallback_used = Column(Boolean, nullable=False, default=True)
    confidence = Column(Float, nullable=False, default=0)
    error_summary = Column(Text, nullable=False, default="")
    analysis_summary = Column(Text, nullable=False, default="")
    raw_prompt_summary = Column(Text, nullable=False, default="")
    raw_response_text = Column(Text, nullable=False, default="")
    normalized_output_json = Column(Text, nullable=False, default="{}")
    structured_output_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
