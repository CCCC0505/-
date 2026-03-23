from typing import List, Optional

from pydantic import BaseModel, Field


class GradeOption(BaseModel):
    code: str
    label: str
    active: bool
    status: str


class GradeCatalogResponse(BaseModel):
    grades: List[GradeOption]
    active_grade: str


class AICapabilityResponse(BaseModel):
    enabled: bool
    provider: str
    model_name: str
    base_url: str
    message: str


class QuestionOption(BaseModel):
    label: str
    value: str


class QuestionnaireQuestion(BaseModel):
    code: str
    title: str
    prompt: str
    trait_code: str
    trait_name: str
    options: List[QuestionOption]


class DiagnosticQuestion(BaseModel):
    question_id: str
    title: str
    stem: str
    options: List[QuestionOption]
    difficulty: int
    knowledge_tags: List[str]
    cognitive_level: str
    target_duration_seconds: int


class ColdStartSessionCreateRequest(BaseModel):
    name: str
    grade: str = "grade_8"


class ColdStartSessionResponse(BaseModel):
    session_id: str
    student_id: str
    student_name: str
    grade: str
    status: str
    questionnaire_questions: List[QuestionnaireQuestion]
    diagnostic_questions: List[DiagnosticQuestion]


class QuestionnaireAnswerItem(BaseModel):
    question_code: str
    answer_value: str


class QuestionnaireSubmitRequest(BaseModel):
    answers: List[QuestionnaireAnswerItem]


class TraitRecordResponse(BaseModel):
    trait_code: str
    trait_name: str
    trait_value: float
    trait_label: str
    source: str


class QuestionnaireSubmitResponse(BaseModel):
    session_id: str
    saved_count: int
    trait_preview: List[TraitRecordResponse]


class DiagnosticAnswerItem(BaseModel):
    question_id: str
    answer_text: str
    duration_seconds: float


class DiagnosticSubmitRequest(BaseModel):
    answers: List[DiagnosticAnswerItem]


class DiagnosticSubmitResponse(BaseModel):
    session_id: str
    saved_count: int
    correct_count: int
    accuracy: float


class AIStatusResponse(BaseModel):
    enabled: bool
    attempted: bool
    success: bool
    fallback_used: bool
    confidence: float
    error_summary: str
    analysis_summary: str
    stage: str
    request_type: str
    model_name: str


class DimensionScoreResponse(BaseModel):
    dimension_code: str
    dimension_name: str
    score: float
    level: str
    evidence: List[str] = Field(default_factory=list)


class KnowledgeMasteryResponse(BaseModel):
    knowledge_tag: str
    mastery_score: float
    needs_attention: bool
    evidence: List[str] = Field(default_factory=list)


class CognitiveDiagnosisResponse(BaseModel):
    level_code: str
    level_name: str
    accuracy: float
    needs_attention: bool
    evidence: List[str] = Field(default_factory=list)


class PortraitSnapshotResponse(BaseModel):
    snapshot_id: str
    version_number: int
    source_stage: str
    parent_snapshot_id: Optional[str] = None
    portrait_summary: str
    teacher_commentary: str
    training_focus: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    ai_confidence: float
    created_at: str
    dimensions: List[DimensionScoreResponse]
    knowledge_matrix: List[KnowledgeMasteryResponse]
    cognitive_diagnosis: List[CognitiveDiagnosisResponse]
    learner_traits: List[TraitRecordResponse]
    summary_card: dict


class ColdStartFinalizeResponse(BaseModel):
    session_id: str
    student_id: str
    snapshot: PortraitSnapshotResponse
    ai_status: AIStatusResponse


class PortraitLatestResponse(BaseModel):
    student_id: str
    snapshot: PortraitSnapshotResponse


class PortraitHistoryResponse(BaseModel):
    student_id: str
    snapshots: List[PortraitSnapshotResponse]


class RecommendationRequest(BaseModel):
    student_id: str
    requested_count: int = 9
    training_mode: str = "balanced"


class RecommendationItemResponse(BaseModel):
    question_id: str
    title: str
    stem: str
    options: List[QuestionOption]
    explanation: str
    difficulty: int
    target_duration_seconds: int
    knowledge_tags: List[str]
    recommendation_type: str
    rule_reason: str
    ai_reason: str
    completed: bool = False
    last_result: Optional[bool] = None
    last_feedback_summary: Optional[str] = None
    last_practiced_at: Optional[str] = None


class TrainingProgressResponse(BaseModel):
    total_questions: int
    completed_questions: int
    correct_count: int
    completion_rate: float
    estimated_minutes_remaining: int
    status: str


class DifficultyDistributionResponse(BaseModel):
    level: int
    count: int


class NamedDistributionResponse(BaseModel):
    label: str
    count: int


class RecommendationSummaryResponse(BaseModel):
    batch_id: str
    training_mode: str
    training_mode_label: str
    batch_goal: str
    batch_tags: List[str]
    difficulty_distribution: List[DifficultyDistributionResponse]
    type_distribution: List[NamedDistributionResponse]
    knowledge_distribution: List[NamedDistributionResponse]
    training_focus: List[str]
    overall_commentary: str
    progress: TrainingProgressResponse
    items: List[RecommendationItemResponse]


class RecommendationResponse(BaseModel):
    student_id: str
    batch_id: str
    training_mode: str
    training_mode_label: str
    batch_goal: str
    batch_tags: List[str]
    difficulty_distribution: List[DifficultyDistributionResponse]
    type_distribution: List[NamedDistributionResponse]
    knowledge_distribution: List[NamedDistributionResponse]
    training_focus: List[str]
    overall_commentary: str
    progress: TrainingProgressResponse
    items: List[RecommendationItemResponse]
    ai_status: AIStatusResponse
    created_at: str


class PracticeAnswerRequest(BaseModel):
    student_id: str
    batch_id: str
    question_id: str
    answer_text: str
    duration_seconds: float


class DimensionDeltaResponse(BaseModel):
    dimension_code: str
    dimension_name: str
    previous_score: float
    current_score: float
    delta: float


class PracticeAnswerResponse(BaseModel):
    student_id: str
    batch_id: str
    question_id: str
    is_correct: bool
    correct_answer: str
    reference_explanation: str
    feedback_summary: str
    next_steps: List[str]
    dimension_deltas: List[DimensionDeltaResponse] = Field(default_factory=list)
    snapshot: PortraitSnapshotResponse
    ai_status: AIStatusResponse


class WrongQuestionResponse(BaseModel):
    question_id: str
    title: str
    wrong_count: int
    status: str
    last_wrong_at: str
    root_cause_summary: str
    qwen_summary: str


class AIAnalysisRunResponse(BaseModel):
    run_id: str
    stage: str
    request_type: str
    model_name: str
    enabled: bool
    attempted: bool
    success: bool
    fallback_used: bool
    confidence: float
    error_summary: str
    analysis_summary: str
    raw_prompt_summary: str
    raw_response_text: str
    normalized_output_json: str
    structured_output_json: str
    created_at: str


class AIAnalysisRunsResponse(BaseModel):
    student_id: str
    runs: List[AIAnalysisRunResponse]


class DashboardCard(BaseModel):
    label: str
    value: str
    hint: str


class WorkbenchSuggestionResponse(BaseModel):
    title: str
    body: str
    priority: str


class WorkbenchAlertResponse(BaseModel):
    title: str
    body: str
    severity: str


class WorkbenchActivityResponse(BaseModel):
    title: str
    body: str
    occurred_at: str
    activity_type: str


class WeeklyGoalResponse(BaseModel):
    target_questions: int
    completed_this_week: int
    remaining_questions: int
    status: str


class WeeklyGoalUpdateRequest(BaseModel):
    target_questions: int


class AIChatRequest(BaseModel):
    message: str
    subject: str = ""
    grade: str = ""
    custom_system_prompt: str = ""


class AIChatResponse(BaseModel):
    reply: str


class HotspotQuestionResponse(BaseModel):
    id: str
    badge: str
    difficulty: str
    content: str
    tag: str


class AIUsageMetaResponse(BaseModel):
    enabled: bool
    attempted: bool
    success: bool
    fallback_used: bool
    model_name: str
    message: str


class HotspotQuestionsResponse(BaseModel):
    questions: List[HotspotQuestionResponse]
    ai_status: AIUsageMetaResponse


class UIColdStartCompleteRequest(BaseModel):
    name: str
    grade: str = "grade_8"
    session_id: Optional[str] = None
    questionnaire_answers: List[QuestionnaireAnswerItem]
    diagnostic_answers: List[DiagnosticAnswerItem]


class UIColdStartCompleteResponse(BaseModel):
    session_id: str
    student_id: str
    student_name: str
    grade: str
    snapshot: PortraitSnapshotResponse
    ai_status: AIStatusResponse


class LearningHeatmapDayResponse(BaseModel):
    date: str
    label: str
    count: int
    status: str


class WeeklyReportResponse(BaseModel):
    headline: str
    summary: str
    highlights: List[str]


class LifetimeStatsResponse(BaseModel):
    total_study_hours: float
    study_days: int
    total_practice_count: int
    achievements_count: int


class RecentStudentResponse(BaseModel):
    student_id: str
    name: str
    grade: str
    has_portrait: bool
    latest_snapshot_version: Optional[int] = None
    latest_snapshot_at: Optional[str] = None
    created_at: str


class RecentStudentsResponse(BaseModel):
    students: List[RecentStudentResponse]


class QuestionBankStatsResponse(BaseModel):
    total_questions: int
    diagnostic_count: int
    practice_count: int


class DashboardResponse(BaseModel):
    student_id: str
    student_name: str
    grade: str
    cards: List[DashboardCard]
    latest_snapshot: PortraitSnapshotResponse
    previous_snapshot: Optional[PortraitSnapshotResponse] = None
    latest_recommendation: Optional[RecommendationSummaryResponse] = None
    recent_wrong_questions: List[WrongQuestionResponse] = Field(default_factory=list)
    latest_ai_run: Optional[AIAnalysisRunResponse] = None
    today_suggestions: List[WorkbenchSuggestionResponse] = Field(default_factory=list)
    pending_alerts: List[WorkbenchAlertResponse] = Field(default_factory=list)
    recent_activities: List[WorkbenchActivityResponse] = Field(default_factory=list)
    weekly_goal: WeeklyGoalResponse
    streak_days: int
    learning_heatmap: List[LearningHeatmapDayResponse] = Field(default_factory=list)
    weekly_report: WeeklyReportResponse
    lifetime_stats: LifetimeStatsResponse
