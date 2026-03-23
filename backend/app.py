import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import SessionLocal, get_db, init_database
from backend.models import DiagnosticAnswer, PortraitSnapshot, PracticeAnswer, QuestionBank, RecommendationBatch, Student, WrongQuestionRecord
from backend.schemas import (
    AICapabilityResponse,
    AIChatRequest,
    AIChatResponse,
    AIAnalysisRunsResponse,
    ColdStartFinalizeResponse,
    ColdStartSessionCreateRequest,
    ColdStartSessionResponse,
    DashboardCard,
    DashboardResponse,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
    GradeCatalogResponse,
    GradeOption,
    RecentStudentsResponse,
    PortraitHistoryResponse,
    PortraitLatestResponse,
    PracticeAnswerRequest,
    PracticeAnswerResponse,
    QuestionBankStatsResponse,
    QuestionnaireSubmitRequest,
    QuestionnaireSubmitResponse,
    RecommendationRequest,
    RecommendationResponse,
    HotspotQuestionsResponse,
    UIColdStartCompleteRequest,
    UIColdStartCompleteResponse,
    WeeklyGoalResponse,
    WeeklyGoalUpdateRequest,
    WrongQuestionResponse,
)
from backend.seed_data import GRADE_CATALOG
from backend.services.ai_run_service import AIRunService
from backend.services.bootstrap import seed_question_bank
from backend.services.cold_start_service import ColdStartService
from backend.services.common import percent
from backend.services.portrait_service import PortraitService
from backend.services.practice_service import PracticeService
from backend.services.qwen_client import QwenClient
from backend.services.recommendation_service import RecommendationService
from backend.services.ui_dashboard_service import UIDashboardService


settings = get_settings()
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"
CSS_DIR = FRONTEND_DIR / "css"
JS_DIR = FRONTEND_DIR / "js"
IMAGES_DIR = FRONTEND_DIR / "images"
PAGES_DIR = FRONTEND_DIR / "pages"

app = FastAPI(title="初中数学智能学习平台", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_static_cache(request, call_next):
    response = await call_next(request)
    path = request.url.path.lower()
    if path == "/" or path.endswith(".html") or path.endswith(".js") or path.endswith(".css"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
if CSS_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(CSS_DIR)), name="css")
if JS_DIR.exists():
    app.mount("/js", StaticFiles(directory=str(JS_DIR)), name="js")
if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
if PAGES_DIR.exists():
    app.mount("/pages", StaticFiles(directory=str(PAGES_DIR)), name="pages")


QUESTIONNAIRE_DEMO_ANSWERS = [
    {"question_code": "difficulty_preference", "answer_value": "balanced"},
    {"question_code": "practice_pace", "answer_value": "steady"},
    {"question_code": "review_habit", "answer_value": "sometimes"},
    {"question_code": "confidence_level", "answer_value": "stable"},
    {"question_code": "help_seeking", "answer_value": "balanced"},
    {"question_code": "learning_preference", "answer_value": "trial"},
]

DIAGNOSTIC_DEMO_ANSWERS = {
    "DIAG-001": "C",
    "DIAG-002": "B",
    "DIAG-003": "C",
    "DIAG-004": "C",
    "DIAG-005": "C",
    "DIAG-006": "D",
    "DIAG-007": "C",
    "DIAG-008": "C",
    "DIAG-009": "C",
    "DIAG-010": "B",
    "DIAG-011": "A",
    "DIAG-012": "B",
    "DIAG-013": "C",
    "DIAG-014": "B",
    "DIAG-015": "B",
    "DIAG-016": "D",
    "DIAG-017": "C",
    "DIAG-018": "C",
    "DIAG-019": "C",
    "DIAG-020": "B",
    "DIAG-021": "B",
    "DIAG-022": "B",
    "DIAG-023": "C",
    "DIAG-024": "B",
}


SUBJECT_CATALOG = {
    "小学": ["语文", "数学", "英语"],
    "初中": ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"],
    "高中": ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治"],
}


@app.on_event("startup")
def on_startup() -> None:
    init_database()
    if settings.app_seed_demo_data:
        db = SessionLocal()
        try:
            seed_question_bank(db, reset=False)
        finally:
            db.close()


def _grade_options() -> List[GradeOption]:
    return [GradeOption(**item) for item in GRADE_CATALOG]


def _wrong_question_rows(db: Session, student_id: str) -> List[dict]:
    rows = (
        db.query(WrongQuestionRecord, QuestionBank)
        .join(QuestionBank, WrongQuestionRecord.question_id == QuestionBank.question_id)
        .filter(WrongQuestionRecord.student_id == student_id)
        .order_by(WrongQuestionRecord.last_wrong_at.desc(), WrongQuestionRecord.id.desc())
        .all()
    )
    return [
        {
            "question_id": wrong.question_id,
            "title": question.title,
            "wrong_count": wrong.wrong_count,
            "status": wrong.status,
            "last_wrong_at": wrong.last_wrong_at.isoformat(),
            "root_cause_summary": wrong.root_cause_summary,
            "qwen_summary": wrong.qwen_summary,
        }
        for wrong, question in rows
    ]


def _recent_students(db: Session, limit: int = 8) -> List[dict]:
    students = db.query(Student).order_by(Student.updated_at.desc(), Student.created_at.desc()).limit(limit).all()
    payload = []
    for student in students:
        latest_snapshot = (
            db.query(PortraitSnapshot)
            .filter(PortraitSnapshot.student_id == student.student_id)
            .order_by(PortraitSnapshot.version_number.desc(), PortraitSnapshot.id.desc())
            .first()
        )
        payload.append(
            {
                "student_id": student.student_id,
                "name": student.name,
                "grade": student.grade,
                "has_portrait": latest_snapshot is not None,
                "latest_snapshot_version": latest_snapshot.version_number if latest_snapshot else None,
                "latest_snapshot_at": latest_snapshot.created_at.isoformat() if latest_snapshot else None,
                "created_at": student.created_at.isoformat(),
            }
        )
    payload.sort(key=lambda item: item["latest_snapshot_at"] or item["created_at"], reverse=True)
    return payload


def _ensure_frontend_context_student(db: Session) -> dict:
    recent = _recent_students(db, limit=1)
    if recent and recent[0]["has_portrait"]:
        return recent[0]

    service = ColdStartService(db)
    created = service.create_session(SimpleNamespace(name="演示学生-默认", grade="grade_8"))
    session_id = created["session_id"]
    service.submit_questionnaire(session_id, QUESTIONNAIRE_DEMO_ANSWERS)
    diagnostic_answers = [
        {
            "question_id": item["question_id"],
            "answer_text": DIAGNOSTIC_DEMO_ANSWERS.get(item["question_id"], "A"),
            "duration_seconds": item["target_duration_seconds"] + 5,
        }
        for item in created["diagnostic_questions"]
    ]
    service.submit_diagnostic(session_id, diagnostic_answers)
    service.finalize(session_id, QwenClient(db))
    return _recent_students(db, limit=1)[0]


def _subject_catalog_for_stage(school_type: str) -> List[dict]:
    subjects = SUBJECT_CATALOG.get(school_type, SUBJECT_CATALOG["初中"])
    return [{"name": subject, "icon": _subject_icon(subject), "available": subject == "数学"} for subject in subjects]


def _subject_icon(subject: str) -> str:
    icon_map = {
        "语文": "chinese-icon",
        "数学": "math-icon",
        "英语": "english-icon",
        "物理": "physics-icon",
        "化学": "chemistry-icon",
        "生物": "biology-icon",
        "历史": "history-icon",
        "地理": "geography-icon",
        "政治": "politics-icon",
    }
    return icon_map.get(subject, "course-icon")


def _knowledge_points_for_subject(db: Session, subject: str) -> List[dict]:
    if subject != "数学":
        return [
            {"id": f"{subject}-001", "title": f"{subject}核心基础", "difficulty": "中等", "importance": "重点"},
            {"id": f"{subject}-002", "title": f"{subject}综合应用", "difficulty": "困难", "importance": "重点"},
        ]

    tags = []
    rows = db.query(QuestionBank).filter(QuestionBank.grade == "grade_8").all()
    for row in rows:
        tags.extend(json.loads(row.knowledge_tags_json or "[]"))
    unique_tags = []
    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)
    return [
        {
            "id": f"math-{idx+1:03d}",
            "title": tag,
            "difficulty": "中等" if idx % 3 else "基础",
            "importance": "重点" if idx < 5 else "基础",
        }
        for idx, tag in enumerate(unique_tags[:12])
    ]


def _knowledge_detail(db: Session, subject: str, knowledge: str) -> dict:
    question_rows = db.query(QuestionBank).filter(QuestionBank.grade == "grade_8", QuestionBank.stage == "practice").all()
    matched = [
        row for row in question_rows
        if subject == "数学" and knowledge in json.loads(row.knowledge_tags_json or "[]")
    ]
    matched = matched[:6]
    exercises = []
    for row in matched[:4]:
        exercises.append(
            {
                "type": "choice",
                "difficulty": "easy" if row.difficulty == 1 else "medium" if row.difficulty == 2 else "hard",
                "question": row.stem,
                "options": [option["value"] for option in json.loads(row.options_json or "[]")],
                "answer": row.correct_answer,
                "analysis": row.explanation,
            }
        )
    examples = [
        {
            "title": row.title,
            "difficulty": "基础" if row.difficulty == 1 else "中等" if row.difficulty == 2 else "困难",
            "question": row.stem,
            "analysis": row.explanation,
        }
        for row in matched[:3]
    ]
    videos = [
        {
            "title": f"{knowledge}基础讲解",
            "description": f"帮助学生理解“{knowledge}”的核心概念与应用方式。",
            "duration": "15:00",
            "views": "平台推荐",
        },
        {
            "title": f"{knowledge}进阶题型",
            "description": f"围绕“{knowledge}”常见综合题型展开拆解。",
            "duration": "20:00",
            "views": "平台推荐",
        },
    ]
    return {
        "knowledge": knowledge,
        "difficulty": "中等",
        "importance": "重点",
        "frequency": "高频考点" if subject == "数学" else "核心知识点",
        "concept_explanation": f"“{knowledge}”是{subject}中的关键知识点，系统会围绕概念理解、基础运算和综合应用来构建训练。",
        "formula_derivation": f"对于“{knowledge}”，平台会优先强调概念来源、推导逻辑和易错条件，帮助学生不止会做题，还能理解为什么这样做。",
        "application_scenarios": f"“{knowledge}”常见于课堂例题、综合练习和考试情境中，适合通过多轮训练逐步稳定掌握。",
        "examples": examples,
        "exercises": exercises,
        "videos": videos,
        "ai_recommendation": f"根据当前题库与学生常见薄弱点，建议优先从“{knowledge}”的基础应用题开始，再逐步过渡到综合题。",
        "ai_recommend_cards": [
            {"title": "优先练基础题", "description": f"先建立对“{knowledge}”的稳定理解。"},
            {"title": "关注易错点", "description": "重点区分概念、条件和解题步骤中的易混部分。"},
        ],
    }


def _learning_rhythm(student_id: str, db: Session, latest_recommendation, weekly_target_questions: int) -> dict:
    today = datetime.utcnow().date()
    practice_rows = db.query(PracticeAnswer).filter(PracticeAnswer.student_id == student_id).all()
    snapshot_rows = db.query(PortraitSnapshot).filter(PortraitSnapshot.student_id == student_id).all()

    practice_counts = {}
    activity_counts = {}

    for row in practice_rows:
        day = row.created_at.date()
        practice_counts[day] = practice_counts.get(day, 0) + 1
        activity_counts[day] = activity_counts.get(day, 0) + 1

    for row in snapshot_rows:
        day = row.created_at.date()
        activity_counts[day] = max(activity_counts.get(day, 0), 1)

    target_questions = max(4, weekly_target_questions)

    week_start = today - timedelta(days=6)
    completed_this_week = sum(count for day, count in practice_counts.items() if day >= week_start)
    remaining_questions = max(0, target_questions - completed_this_week)
    if completed_this_week >= target_questions:
        weekly_status = "completed"
    elif completed_this_week >= max(4, target_questions // 2):
        weekly_status = "on_track"
    else:
        weekly_status = "behind"

    streak_days = 0
    cursor = today
    while activity_counts.get(cursor, 0) > 0:
        streak_days += 1
        cursor = cursor - timedelta(days=1)

    heatmap = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        count = activity_counts.get(day, 0)
        if count == 0:
            status = "none"
        elif count == 1:
            status = "low"
        elif count <= 3:
            status = "medium"
        else:
            status = "high"
        heatmap.append(
            {
                "date": day.isoformat(),
                "label": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day.weekday()],
                "count": count,
                "status": status,
            }
        )

    return {
        "weekly_goal": {
            "target_questions": target_questions,
            "completed_this_week": completed_this_week,
            "remaining_questions": remaining_questions,
            "status": weekly_status,
        },
        "streak_days": streak_days,
        "learning_heatmap": heatmap,
    }


def _weekly_report(latest_payload: dict, latest_recommendation, recent_wrong_questions: list, rhythm: dict) -> dict:
    weak_dimension = min(latest_payload["dimensions"], key=lambda item: item["score"])
    strong_dimension = max(latest_payload["dimensions"], key=lambda item: item["score"])
    weekly_goal = rhythm["weekly_goal"]
    if weekly_goal["status"] == "completed":
        headline = "本周学习目标已完成"
    elif weekly_goal["status"] == "on_track":
        headline = "本周学习节奏整体稳定"
    else:
        headline = "本周仍需尽快补足训练节奏"

    summary = (
        f"当前优势维度是 {strong_dimension['dimension_name']}，"
        f"最需要关注的是 {weak_dimension['dimension_name']}。"
        f"本周已完成 {weekly_goal['completed_this_week']} 题，"
        f"连续学习 {rhythm['streak_days']} 天。"
    )
    highlights = [
        f"训练重点：{'、'.join(latest_payload['training_focus'][:3]) or '暂无'}",
        f"待关注知识点：{'、'.join([item['knowledge_tag'] for item in latest_payload['knowledge_matrix'] if item['needs_attention']][:3]) or '暂无'}",
        f"错题回流数：{len(recent_wrong_questions)}",
    ]
    if latest_recommendation:
        highlights.append(
            f"当前训练进度：{latest_recommendation['progress']['completed_questions']}/{latest_recommendation['progress']['total_questions']} 题"
        )
    return {"headline": headline, "summary": summary, "highlights": highlights}


def _lifetime_stats(student_id: str, db: Session, streak_days: int) -> dict:
    practice_rows = db.query(PracticeAnswer).filter(PracticeAnswer.student_id == student_id).all()
    diagnostic_rows = db.query(DiagnosticAnswer).filter(DiagnosticAnswer.student_id == student_id).all()
    total_seconds = sum(row.duration_seconds for row in practice_rows) + sum(row.duration_seconds for row in diagnostic_rows)
    days = set(row.created_at.date() for row in practice_rows)
    days.update(row.created_at.date() for row in diagnostic_rows)
    achievements = 0
    if streak_days >= 3:
        achievements += 1
    if len(practice_rows) >= 10:
        achievements += 1
    if len(practice_rows) >= 30:
        achievements += 1
    return {
        "total_study_hours": round(total_seconds / 3600, 1),
        "study_days": len(days),
        "total_practice_count": len(practice_rows),
        "achievements_count": achievements,
    }


def _build_workbench_response(student_id: str, db: Session) -> DashboardResponse:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    portrait_service = PortraitService(db)
    latest = portrait_service.get_latest_snapshot(student_id)
    if latest is None:
        raise HTTPException(status_code=404, detail="portrait snapshot not found")
    latest_payload = portrait_service.snapshot_to_response(latest)
    previous = portrait_service.get_previous_snapshot(student_id, latest.snapshot_id)
    previous_payload = portrait_service.snapshot_to_response(previous) if previous else None
    ai_service = AIRunService(db)
    latest_ai_run = ai_service.get_latest_run(student_id)
    recommendation_service = RecommendationService(db)
    latest_recommendation = recommendation_service.latest_summary(student_id)
    recent_wrong_questions = [WrongQuestionResponse(**item) for item in _wrong_question_rows(db, student_id)[:6]]
    weak_dimension = min(latest_payload["dimensions"], key=lambda item: item["score"])
    strong_dimension = max(latest_payload["dimensions"], key=lambda item: item["score"])
    cards = [
        DashboardCard(label="画像版本", value=f"V{latest_payload['version_number']}", hint=latest_payload["source_stage"]),
        DashboardCard(label="当前短板", value=weak_dimension["dimension_name"], hint=percent(weak_dimension["score"])),
        DashboardCard(label="当前优势", value=strong_dimension["dimension_name"], hint=percent(strong_dimension["score"])),
        DashboardCard(
            label="薄弱知识点数",
            value=str(sum(1 for item in latest_payload["knowledge_matrix"] if item["needs_attention"])),
            hint="用于驱动训练方案配比",
        ),
    ]
    today_suggestions = [
        {
            "title": "先完成当前训练重点",
            "body": "、".join(latest_payload["training_focus"][:3]) or "先从当前最弱维度开始练习。",
            "priority": "high",
        },
        {
            "title": "优先关注薄弱知识点",
            "body": "、".join([item["knowledge_tag"] for item in latest_payload["knowledge_matrix"] if item["needs_attention"]][:3]) or "当前暂无明显薄弱知识点。",
            "priority": "medium",
        },
    ]
    if latest_recommendation:
        progress = latest_recommendation["progress"]
        today_suggestions.append(
            {
                "title": "继续当前训练批次",
                "body": f"已完成 {progress['completed_questions']}/{progress['total_questions']} 题，预计还需 {progress['estimated_minutes_remaining']} 分钟。",
                "priority": "high" if progress["status"] == "in_progress" else "low",
            }
        )

    pending_alerts = []
    if recent_wrong_questions:
        pending_alerts.append(
            {
                "title": "存在待回流错题",
                "body": f"当前有 {len(recent_wrong_questions)} 道题需要回看和再次练习。",
                "severity": "high",
            }
        )
    if weak_dimension["score"] < 60:
        pending_alerts.append(
            {
                "title": "核心维度仍有波动",
                "body": f"{weak_dimension['dimension_name']} 当前仅 {round(weak_dimension['score'])} 分，建议优先训练。",
                "severity": "medium",
            }
        )
    if latest_ai_run and latest_ai_run.fallback_used:
        pending_alerts.append(
            {
                "title": "最近一次智能分析触发回退",
                "body": latest_ai_run.error_summary or "当前使用规则回退结果。",
                "severity": "low",
            }
        )

    recent_activities = [
        {
            "title": f"成长画像更新到 V{latest_payload['version_number']}",
            "body": latest_payload["portrait_summary"],
            "occurred_at": latest_payload["created_at"],
            "activity_type": "snapshot",
        }
    ]
    if latest_recommendation:
        recent_activities.append(
            {
                "title": "新的训练方案已生成",
                "body": latest_recommendation["overall_commentary"] or "平台已根据当前画像生成训练方案。",
                "occurred_at": latest_recommendation.get("created_at", latest_payload["created_at"]),
                "activity_type": "plan",
            }
        )
    if latest_ai_run:
        recent_activities.append(
            {
                "title": f"智能分析{ '完成' if latest_ai_run.success else '回退' }",
                "body": latest_ai_run.analysis_summary or latest_ai_run.error_summary or "平台已记录本次分析结果。",
                "occurred_at": latest_ai_run.created_at.isoformat(),
                "activity_type": "ai",
            }
        )
    rhythm = _learning_rhythm(student_id, db, latest_recommendation, student.weekly_target_questions)
    weekly_report = _weekly_report(latest_payload, latest_recommendation, recent_wrong_questions, rhythm)
    lifetime_stats = _lifetime_stats(student_id, db, rhythm["streak_days"])

    return DashboardResponse(
        student_id=student_id,
        student_name=student.name,
        grade=student.grade,
        cards=cards,
        latest_snapshot=latest_payload,
        previous_snapshot=previous_payload,
        latest_recommendation=latest_recommendation,
        recent_wrong_questions=recent_wrong_questions,
        latest_ai_run=ai_service.to_response(latest_ai_run) if latest_ai_run else None,
        today_suggestions=today_suggestions,
        pending_alerts=pending_alerts,
        recent_activities=recent_activities,
        weekly_goal=rhythm["weekly_goal"],
        streak_days=rhythm["streak_days"],
        learning_heatmap=rhythm["learning_heatmap"],
        weekly_report=weekly_report,
        lifetime_stats=lifetime_stats,
    )


@app.get("/")
def root():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE), headers={"Cache-Control": "no-store, max-age=0"})
    return {"message": "frontend not found"}


@app.get("/index.html")
def index_html():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE), headers={"Cache-Control": "no-store, max-age=0"})
    raise HTTPException(status_code=404, detail="frontend not found")


@app.get("/api/ui/context")
def ui_context(db: Session = Depends(get_db)):
    current = _ensure_frontend_context_student(db)
    return {"current_student": current}


@app.post("/api/ai/chat", response_model=AIChatResponse)
def ai_chat(payload: AIChatRequest, db: Session = Depends(get_db)):
    reply = QwenClient(db).companion_reply(
        message=payload.message,
        subject=payload.subject,
        grade=payload.grade,
        custom_system_prompt=payload.custom_system_prompt,
    )
    return AIChatResponse(reply=reply)


@app.post("/api/ai/hotspot-questions", response_model=HotspotQuestionsResponse)
def ai_hotspot_questions(payload: dict, db: Session = Depends(get_db)):
    subject = payload.get("subject", "")
    grade = payload.get("grade", "")
    knowledge = payload.get("knowledge", "")
    count = int(payload.get("count", 3))
    questions, ai_status = QwenClient(db).hotspot_questions_with_meta(subject=subject, grade=grade, knowledge=knowledge, count=count)
    return HotspotQuestionsResponse(questions=questions, ai_status=ai_status)


@app.get("/api/ui/subjects")
def ui_subjects(school_type: str = "初中"):
    return {"school_type": school_type, "subjects": _subject_catalog_for_stage(school_type)}


@app.get("/api/ui/knowledge-points")
def ui_knowledge_points(subject: str = "数学", db: Session = Depends(get_db)):
    return {"subject": subject, "knowledge_points": _knowledge_points_for_subject(db, subject)}


@app.get("/api/ui/knowledge-detail")
def ui_knowledge_detail(subject: str = "数学", knowledge: str = "", db: Session = Depends(get_db)):
    target = knowledge or "一次函数"
    return _knowledge_detail(db, subject, target)


@app.get("/api/ui/modeling-basis")
def ui_modeling_basis(db: Session = Depends(get_db)):
    return UIDashboardService(db).build_modeling_basis()


@app.get("/api/students/{student_id}/analysis-dashboard")
def analysis_dashboard(student_id: str, range: str = "month", db: Session = Depends(get_db)):
    return UIDashboardService(db).build_analysis_dashboard(student_id, range)


@app.get("/api/students/{student_id}/personal-dashboard")
def personal_dashboard(student_id: str, db: Session = Depends(get_db)):
    return UIDashboardService(db).build_personal_dashboard(student_id)


@app.get("/api/students/{student_id}/portrait-modeling")
def portrait_modeling(student_id: str, db: Session = Depends(get_db)):
    return UIDashboardService(db).build_portrait_modeling(student_id)


@app.get("/styles.css")
def styles():
    file_path = FRONTEND_DIR / "styles.css"
    if file_path.exists():
        return FileResponse(str(file_path), media_type="text/css", headers={"Cache-Control": "no-store, max-age=0"})
    raise HTTPException(status_code=404, detail="styles not found")


@app.get("/app.js")
def app_js():
    file_path = FRONTEND_DIR / "app.js"
    if file_path.exists():
        return FileResponse(str(file_path), media_type="application/javascript", headers={"Cache-Control": "no-store, max-age=0"})
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta/grades", response_model=GradeCatalogResponse)
def grade_catalog():
    active_grade = next((item["label"] for item in GRADE_CATALOG if item["active"]), "初二")
    return GradeCatalogResponse(grades=_grade_options(), active_grade=active_grade)


@app.get("/api/meta/ai-status", response_model=AICapabilityResponse)
def ai_status(db: Session = Depends(get_db)):
    return AICapabilityResponse(**QwenClient(db).capability_status())


@app.get("/api/system/question-bank/stats", response_model=QuestionBankStatsResponse)
def question_bank_stats(db: Session = Depends(get_db)):
    total = db.query(QuestionBank).count()
    diagnostic_count = db.query(QuestionBank).filter(QuestionBank.stage == "diagnostic").count()
    practice_count = db.query(QuestionBank).filter(QuestionBank.stage == "practice").count()
    return QuestionBankStatsResponse(total_questions=total, diagnostic_count=diagnostic_count, practice_count=practice_count)


@app.get("/api/students/recent", response_model=RecentStudentsResponse)
def recent_students(db: Session = Depends(get_db)):
    return RecentStudentsResponse(students=_recent_students(db))


@app.post("/api/students/{student_id}/weekly-goal", response_model=WeeklyGoalResponse)
def update_weekly_goal(student_id: str, payload: WeeklyGoalUpdateRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    student.weekly_target_questions = max(4, min(payload.target_questions, 60))
    db.commit()
    latest_recommendation = RecommendationService(db).latest_summary(student_id)
    rhythm = _learning_rhythm(student_id, db, latest_recommendation, student.weekly_target_questions)
    return WeeklyGoalResponse(**rhythm["weekly_goal"])


@app.post("/api/cold-start/sessions", response_model=ColdStartSessionResponse)
def create_cold_start_session(payload: ColdStartSessionCreateRequest, db: Session = Depends(get_db)):
    service = ColdStartService(db)
    try:
        return ColdStartSessionResponse(**service.create_session(payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/cold-start/{session_id}/questionnaire", response_model=QuestionnaireSubmitResponse)
def submit_questionnaire(session_id: str, payload: QuestionnaireSubmitRequest, db: Session = Depends(get_db)):
    service = ColdStartService(db)
    try:
        return QuestionnaireSubmitResponse(**service.submit_questionnaire(session_id, [item.dict() for item in payload.answers]))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/cold-start/{session_id}/diagnostic/submit", response_model=DiagnosticSubmitResponse)
def submit_diagnostic(session_id: str, payload: DiagnosticSubmitRequest, db: Session = Depends(get_db)):
    service = ColdStartService(db)
    try:
        return DiagnosticSubmitResponse(**service.submit_diagnostic(session_id, [item.dict() for item in payload.answers]))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/cold-start/{session_id}/finalize", response_model=ColdStartFinalizeResponse)
def finalize_cold_start(session_id: str, db: Session = Depends(get_db)):
    service = ColdStartService(db)
    ai_runs = AIRunService(db)
    try:
        session, snapshot, ai_run = service.finalize(session_id, QwenClient(db))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ColdStartFinalizeResponse(
        session_id=session.session_id,
        student_id=session.student_id,
        snapshot=PortraitService(db).snapshot_to_response(snapshot),
        ai_status=ai_runs.to_status(ai_run),
    )


@app.post("/api/ui/cold-start/complete", response_model=UIColdStartCompleteResponse)
def complete_ui_cold_start(payload: UIColdStartCompleteRequest, db: Session = Depends(get_db)):
    service = ColdStartService(db)
    ai_runs = AIRunService(db)
    try:
        if payload.session_id:
            session_id = payload.session_id
            session_payload = {
                "session_id": session_id,
                "student_name": payload.name.strip(),
                "grade": payload.grade,
            }
        else:
            session_payload = service.create_session(payload)
            session_id = session_payload["session_id"]
        service.submit_questionnaire(session_id, [item.dict() for item in payload.questionnaire_answers])
        service.submit_diagnostic(session_id, [item.dict() for item in payload.diagnostic_answers])
        session, snapshot, ai_run = service.finalize(session_id, QwenClient(db))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return UIColdStartCompleteResponse(
        session_id=session.session_id,
        student_id=session.student_id,
        student_name=session_payload["student_name"],
        grade=session_payload["grade"],
        snapshot=PortraitService(db).snapshot_to_response(snapshot),
        ai_status=ai_runs.to_status(ai_run),
    )


@app.get("/api/students/{student_id}/portrait/latest", response_model=PortraitLatestResponse)
def portrait_latest(student_id: str, db: Session = Depends(get_db)):
    service = PortraitService(db)
    snapshot = service.get_latest_snapshot(student_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="portrait snapshot not found")
    return PortraitLatestResponse(student_id=student_id, snapshot=service.snapshot_to_response(snapshot))


@app.get("/api/students/{student_id}/portrait/history", response_model=PortraitHistoryResponse)
def portrait_history(student_id: str, db: Session = Depends(get_db)):
    service = PortraitService(db)
    snapshots = service.get_snapshot_history(student_id)
    return PortraitHistoryResponse(
        student_id=student_id,
        snapshots=[service.snapshot_to_response(snapshot) for snapshot in snapshots],
    )


@app.get("/api/students/{student_id}/wrong-questions", response_model=List[WrongQuestionResponse])
def wrong_questions(student_id: str, db: Session = Depends(get_db)):
    return [WrongQuestionResponse(**item) for item in _wrong_question_rows(db, student_id)]


@app.post("/api/practice/recommendations", response_model=RecommendationResponse)
def generate_recommendations(payload: RecommendationRequest, db: Session = Depends(get_db)):
    service = RecommendationService(db)
    ai_runs = AIRunService(db)
    try:
        batch, items, snapshot_payload = service.generate(payload.student_id, payload.requested_count, payload.training_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    student = db.query(Student).filter(Student.student_id == payload.student_id).first()
    ai_output, ai_run = QwenClient(db).explain_recommendations(
        student_id=payload.student_id,
        student_name=student.name if student else "学生",
        snapshot_payload=snapshot_payload,
        recommendation_items=items,
    )
    service.apply_ai_output(batch.batch_id, ai_output, ai_run.run_id)
    batch = db.query(RecommendationBatch).filter(RecommendationBatch.batch_id == batch.batch_id).first()
    response_payload = service.batch_to_response(batch)
    return RecommendationResponse(
        student_id=payload.student_id,
        batch_id=batch.batch_id,
        training_mode=response_payload["training_mode"],
        training_mode_label=response_payload["training_mode_label"],
        batch_goal=response_payload["batch_goal"],
        batch_tags=response_payload["batch_tags"],
        difficulty_distribution=response_payload["difficulty_distribution"],
        type_distribution=response_payload["type_distribution"],
        knowledge_distribution=response_payload["knowledge_distribution"],
        training_focus=response_payload["training_focus"],
        overall_commentary=response_payload["overall_commentary"],
        progress=response_payload["progress"],
        items=response_payload["items"],
        ai_status=ai_runs.to_status(ai_run),
        created_at=batch.created_at.isoformat(),
    )


@app.post("/api/practice/answers", response_model=PracticeAnswerResponse)
def submit_practice_answer(payload: PracticeAnswerRequest, db: Session = Depends(get_db)):
    batch = db.query(RecommendationBatch).filter(RecommendationBatch.batch_id == payload.batch_id).first()
    if batch is None or batch.student_id != payload.student_id:
        raise HTTPException(status_code=404, detail="recommendation batch not found")
    question = db.query(QuestionBank).filter(QuestionBank.question_id == payload.question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")
    service = PracticeService(db)
    ai_runs = AIRunService(db)
    try:
        result = service.submit_answer(
            student_id=payload.student_id,
            batch=batch,
            question=question,
            answer_text=payload.answer_text,
            duration_seconds=payload.duration_seconds,
            qwen_client=QwenClient(db),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return PracticeAnswerResponse(
        student_id=result["student_id"],
        batch_id=result["batch_id"],
        question_id=result["question_id"],
        is_correct=result["is_correct"],
        correct_answer=result["correct_answer"],
        reference_explanation=result["reference_explanation"],
        feedback_summary=result["feedback_summary"],
        next_steps=result["next_steps"],
        dimension_deltas=result["dimension_deltas"],
        snapshot=result["snapshot"],
        ai_status=ai_runs.to_status(result["ai_run"]),
    )


@app.get("/api/students/{student_id}/ai-runs", response_model=AIAnalysisRunsResponse)
def ai_runs(student_id: str, db: Session = Depends(get_db)):
    service = AIRunService(db)
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    return AIAnalysisRunsResponse(student_id=student_id, runs=[service.to_response(run) for run in service.get_recent_runs(student_id)])


@app.get("/api/students/{student_id}/dashboard", response_model=DashboardResponse)
def dashboard(student_id: str, db: Session = Depends(get_db)):
    return _build_workbench_response(student_id, db)


@app.get("/api/students/{student_id}/workbench", response_model=DashboardResponse)
def workbench(student_id: str, db: Session = Depends(get_db)):
    return _build_workbench_response(student_id, db)
