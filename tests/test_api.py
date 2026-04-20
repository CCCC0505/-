import os
from pathlib import Path

DB_PATH = Path("test_grade8_demo.db")
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["APP_SEED_DEMO_DATA"] = "true"
os.environ["DASHSCOPE_API_KEY"] = ""

from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Base, SessionLocal, engine
from backend.models import QuestionBank
from backend.services.bootstrap import seed_question_bank


QUESTIONNAIRE_PAYLOAD = {
    "answers": [
        {"question_code": "difficulty_preference", "answer_value": "balanced"},
        {"question_code": "practice_pace", "answer_value": "steady"},
        {"question_code": "review_habit", "answer_value": "sometimes"},
        {"question_code": "confidence_level", "answer_value": "stable"},
        {"question_code": "help_seeking", "answer_value": "balanced"},
        {"question_code": "learning_preference", "answer_value": "trial"},
    ]
}

DIAGNOSTIC_ANSWERS = {
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


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_question_bank(db, reset=True)
    finally:
        db.close()


def make_client():
    reset_db()
    return TestClient(app)


def build_diagnostic_payload(client):
    session = client.post("/api/cold-start/sessions", json={"name": "测试学生", "grade": "grade_8"}).json()
    diagnostic_questions = session["diagnostic_questions"]
    answers = []
    for item in diagnostic_questions:
        answers.append(
            {
                "question_id": item["question_id"],
                "answer_text": DIAGNOSTIC_ANSWERS[item["question_id"]],
                "duration_seconds": item["target_duration_seconds"] + 6,
            }
        )
    return session, {"answers": answers}


def complete_cold_start(client):
    session, diagnostic_payload = build_diagnostic_payload(client)
    session_id = session["session_id"]
    questionnaire_response = client.post(f"/api/cold-start/{session_id}/questionnaire", json=QUESTIONNAIRE_PAYLOAD)
    assert questionnaire_response.status_code == 200
    diagnostic_response = client.post(f"/api/cold-start/{session_id}/diagnostic/submit", json=diagnostic_payload)
    assert diagnostic_response.status_code == 200
    finalize_response = client.post(f"/api/cold-start/{session_id}/finalize", json={})
    assert finalize_response.status_code == 200
    return finalize_response.json()


def answer_one_recommendation_wrong(client, student_id):
    recommendation_response = client.post("/api/practice/recommendations", json={"student_id": student_id, "requested_count": 5})
    assert recommendation_response.status_code == 200
    recommendation_payload = recommendation_response.json()
    first_item = recommendation_payload["items"][0]
    db = SessionLocal()
    try:
        question = db.query(QuestionBank).filter(QuestionBank.question_id == first_item["question_id"]).first()
        wrong_answer = next(option["label"] for option in first_item["options"] if option["label"] != question.correct_answer)
    finally:
        db.close()

    practice_response = client.post(
        "/api/practice/answers",
        json={
            "student_id": student_id,
            "batch_id": recommendation_payload["batch_id"],
            "question_id": first_item["question_id"],
            "answer_text": wrong_answer,
            "duration_seconds": 95,
        },
    )
    assert practice_response.status_code == 200
    return recommendation_payload, practice_response.json()


def test_question_bank_seed_counts():
    with make_client() as client:
        index_response = client.get("/index.html")
        assert index_response.status_code == 200
        response = client.get("/api/system/question-bank/stats")
        assert response.status_code == 200
        payload = response.json()
        assert payload["diagnostic_count"] == 24
        assert payload["practice_count"] == 60
        assert payload["total_questions"] == 84


def test_ui_subjects_and_knowledge_points_focus_on_math():
    with make_client() as client:
        subjects_response = client.get("/api/ui/subjects?school_type=初中")
        assert subjects_response.status_code == 200
        subjects_payload = subjects_response.json()
        assert subjects_payload["school_type"] == "初中"
        subjects = subjects_payload["subjects"]
        assert any(item["name"] == "数学" and item["available"] is True for item in subjects)
        assert all(item["available"] is False for item in subjects if item["name"] != "数学")

        math_points_response = client.get("/api/ui/knowledge-points?subject=数学")
        assert math_points_response.status_code == 200
        math_points_payload = math_points_response.json()
        assert math_points_payload["knowledge_points"]

        physics_points_response = client.get("/api/ui/knowledge-points?subject=物理")
        assert physics_points_response.status_code == 200
        physics_points_payload = physics_points_response.json()
        assert physics_points_payload["knowledge_points"] == []
        assert "后续开放" in physics_points_payload["message"]


def test_full_cold_start_flow_creates_snapshot_and_ai_run():
    with make_client() as client:
        finalize_payload = complete_cold_start(client)
        snapshot = finalize_payload["snapshot"]
        assert len(snapshot["dimensions"]) == 5
        assert len(snapshot["knowledge_matrix"]) >= 5
        assert snapshot["summary_card"]["headline"]
        assert finalize_payload["ai_status"]["fallback_used"] is True
        assert finalize_payload["ai_status"]["success"] is False

        student_id = finalize_payload["student_id"]
        latest_response = client.get(f"/api/students/{student_id}/portrait/latest")
        assert latest_response.status_code == 200
        history_response = client.get(f"/api/students/{student_id}/portrait/history")
        assert history_response.status_code == 200
        assert len(history_response.json()["snapshots"]) == 1
        ai_runs_response = client.get(f"/api/students/{student_id}/ai-runs")
        assert ai_runs_response.status_code == 200
        assert len(ai_runs_response.json()["runs"]) == 1
        recent_students = client.get("/api/students/recent")
        assert recent_students.status_code == 200
        assert recent_students.json()["students"]
        hotspot_response = client.post("/api/ai/hotspot-questions", json={"subject": "数学", "grade": "初中二年级", "knowledge": "一次函数", "count": 3})
        assert hotspot_response.status_code == 200
        hotspot_payload = hotspot_response.json()
        assert len(hotspot_payload["questions"]) == 3
        assert "ai_status" in hotspot_payload


def test_recommendation_and_practice_update_create_new_snapshot():
    with make_client() as client:
        finalize_payload = complete_cold_start(client)
        student_id = finalize_payload["student_id"]

        recommendation_response = client.post("/api/practice/recommendations", json={"student_id": student_id, "requested_count": 9})
        assert recommendation_response.status_code == 200
        recommendation_payload = recommendation_response.json()
        categories = {item["recommendation_type"] for item in recommendation_payload["items"]}
        assert {"补弱题", "巩固题", "提升题"}.issubset(categories)
        assert recommendation_payload["ai_status"]["fallback_used"] is True
        assert recommendation_payload["training_mode"] == "balanced"
        assert recommendation_payload["training_mode_label"]
        assert recommendation_payload["batch_goal"]
        assert recommendation_payload["fusion_formula"]
        assert recommendation_payload["overall_reason_template"]
        assert isinstance(recommendation_payload["batch_tags"], list)
        assert recommendation_payload["difficulty_distribution"]
        assert recommendation_payload["type_distribution"]
        assert recommendation_payload["knowledge_distribution"]
        assert recommendation_payload["progress"]["total_questions"] == 9
        assert recommendation_payload["progress"]["completed_questions"] == 0
        assert recommendation_payload["items"][0]["priority"] > 0
        assert recommendation_payload["items"][0]["recommendation_driver"]
        assert recommendation_payload["items"][0]["recommendation_template"]
        assert recommendation_payload["items"][0]["forgetting_risk"] >= 0
        assert recommendation_payload["items"][0]["long_term_mastery"] >= 0
        weakness_response = client.post("/api/practice/recommendations", json={"student_id": student_id, "requested_count": 5, "training_mode": "weakness"})
        challenge_response = client.post("/api/practice/recommendations", json={"student_id": student_id, "requested_count": 5, "training_mode": "challenge"})
        assert weakness_response.status_code == 200
        assert challenge_response.status_code == 200
        weakness_payload = weakness_response.json()
        challenge_payload = challenge_response.json()
        weakness_types = [item["recommendation_type"] for item in weakness_payload["items"]]
        challenge_types = [item["recommendation_type"] for item in challenge_payload["items"]]
        assert weakness_types.count("补弱题") >= challenge_types.count("补弱题")
        assert challenge_types.count("提升题") >= weakness_types.count("提升题")

        first_item = recommendation_payload["items"][0]
        db = SessionLocal()
        try:
            question = db.query(QuestionBank).filter(QuestionBank.question_id == first_item["question_id"]).first()
            wrong_answer = next(option["label"] for option in first_item["options"] if option["label"] != question.correct_answer)
        finally:
            db.close()

        practice_response = client.post(
            "/api/practice/answers",
            json={
                "student_id": student_id,
                "batch_id": recommendation_payload["batch_id"],
                "question_id": first_item["question_id"],
                "answer_text": wrong_answer,
                "duration_seconds": 95,
            },
        )
        assert practice_response.status_code == 200
        practice_payload = practice_response.json()
        assert practice_payload["is_correct"] is False
        assert practice_payload["snapshot"]["version_number"] == 2
        assert practice_payload["ai_status"]["fallback_used"] is True
        assert practice_payload["dimension_deltas"]

        history_response = client.get(f"/api/students/{student_id}/portrait/history")
        assert len(history_response.json()["snapshots"]) == 2
        wrong_questions_response = client.get(f"/api/students/{student_id}/wrong-questions")
        assert wrong_questions_response.status_code == 200
        assert len(wrong_questions_response.json()) == 1
        dashboard_response = client.get(f"/api/students/{student_id}/dashboard")
        assert dashboard_response.status_code == 200
        dashboard_payload = dashboard_response.json()
        assert dashboard_payload["latest_recommendation"] is not None
        assert dashboard_payload["latest_recommendation"]["batch_goal"]
        assert dashboard_payload["latest_recommendation"]["difficulty_distribution"]
        assert "progress" in dashboard_payload["latest_recommendation"]
        assert dashboard_payload["today_suggestions"]
        assert "pending_alerts" in dashboard_payload
        assert "weekly_goal" in dashboard_payload
        assert "weekly_report" in dashboard_payload
        assert "streak_days" in dashboard_payload
        assert "learning_heatmap" in dashboard_payload
        workbench_response = client.get(f"/api/students/{student_id}/workbench")
        assert workbench_response.status_code == 200
        workbench_payload = workbench_response.json()
        assert workbench_payload["today_suggestions"]
        assert "recent_activities" in workbench_payload
        assert workbench_payload["weekly_goal"]["target_questions"] >= 9
        assert workbench_payload["weekly_report"]["headline"]
        update_goal_response = client.post(f"/api/students/{student_id}/weekly-goal", json={"target_questions": 18})
        assert update_goal_response.status_code == 200
        assert update_goal_response.json()["target_questions"] == 18
        analysis_response = client.get(f"/api/students/{student_id}/analysis-dashboard?range=month")
        assert analysis_response.status_code == 200
        analysis_payload = analysis_response.json()
        assert analysis_payload["charts"]["progress"]["labels"]
        assert analysis_payload["knowledge_tracking"]["top_review"]
        assert analysis_payload["knowledge_tracking"]["knowledge_states"]
        assert analysis_payload["knowledge_tracking"]["sequence_rows"]
        assert analysis_payload["knowledge_tracking"]["top_review"][0]["risk_level"] in {"高遗忘风险", "中遗忘风险", "低遗忘风险"}
        assert {
            "student_id",
            "question_id",
            "knowledge_tag",
            "created_at",
            "is_correct",
            "duration_seconds",
            "difficulty",
            "snapshot_version",
        }.issubset(analysis_payload["knowledge_tracking"]["sequence_rows"][0].keys())
        assert analysis_payload["modeling_basis"]["references"]
        assert analysis_payload["modeling_basis"]["upgrade_scope"]["long_term_model"] == "轻量 KT"
        assert analysis_payload["recommendation_upgrade"]["scheme_results"]
        assert analysis_payload["recommendation_upgrade"]["formula"]
        assert analysis_payload["defense_assets"]["one_minute_script"]
        assert analysis_payload["emotion_support"]["status"] in {"稳定", "轻度挫败风险", "建议鼓励"}
        assert analysis_payload["portrait_modeling"]["algorithm_pipeline"]
        portrait_modeling = client.get(f"/api/students/{student_id}/portrait-modeling")
        assert portrait_modeling.status_code == 200
        assert portrait_modeling.json()["ai_output_schema"]["schema_name"] == "portrait_ai_output_v1"
        personal_response = client.get(f"/api/students/{student_id}/personal-dashboard")
        assert personal_response.status_code == 200
        personal_payload = personal_response.json()
        assert personal_payload["learning_report"]["chart"]["labels"]
        assert personal_payload["practice_records"]
        modeling_basis = client.get("/api/ui/modeling-basis")
        assert modeling_basis.status_code == 200
        assert modeling_basis.json()["dimension_mapping"]
        session, diagnostic_payload = build_diagnostic_payload(client)
        session_id = session["session_id"]
        quick_complete = client.post(
            "/api/ui/cold-start/complete",
            json={
                "name": session["student_name"],
                "grade": "grade_8",
                "session_id": session_id,
                "questionnaire_answers": QUESTIONNAIRE_PAYLOAD["answers"],
                "diagnostic_answers": diagnostic_payload["answers"],
            },
        )
        assert quick_complete.status_code == 200
        assert quick_complete.json()["snapshot"]["version_number"] == 1


def test_wrong_questions_returns_one_record_after_wrong_answer():
    with make_client() as client:
        finalize_payload = complete_cold_start(client)
        student_id = finalize_payload["student_id"]

        recommendation_payload, practice_payload = answer_one_recommendation_wrong(client, student_id)
        assert practice_payload["is_correct"] is False

        wrong_questions_response = client.get(f"/api/students/{student_id}/wrong-questions")
        assert wrong_questions_response.status_code == 200
        wrong_questions = wrong_questions_response.json()
        assert len(wrong_questions) == 1
        row = wrong_questions[0]
        assert row["question_id"] == recommendation_payload["items"][0]["question_id"]
        assert row["status"] == "open"
        assert row["difficulty"] in {"easy", "medium", "hard"}
        assert isinstance(row["knowledge_tags"], list)
        assert row["knowledge_tags"]
        assert row["explanation"]
        assert row["stem"]
