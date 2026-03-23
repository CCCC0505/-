from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Tuple

from backend.seed_data import COGNITIVE_LEVEL_META, DIMENSION_META, QUESTIONNAIRE_QUESTIONS
from backend.services.common import clamp, level_label, mean, safe_round


DIFFICULTY_FACTORS = {1: 0.95, 2: 1.00, 3: 1.08, 4: 1.15}
COGNITIVE_FACTORS = {"remember": 0.94, "understand": 1.00, "apply": 1.06, "analyze": 1.12}
KNOWLEDGE_ALERT_THRESHOLD = 55.0
COGNITIVE_ALERT_THRESHOLD = 58.0

QUESTIONNAIRE_LOOKUP = {item["code"]: item for item in QUESTIONNAIRE_QUESTIONS}
DIMENSION_LOOKUP = {item["code"]: item["name"] for item in DIMENSION_META}
COGNITIVE_LOOKUP = {item["code"]: item["name"] for item in COGNITIVE_LEVEL_META}


def target_speed_factor(duration_seconds: float, target_duration_seconds: int) -> float:
    if target_duration_seconds <= 0:
        return 1.0
    ratio = duration_seconds / float(target_duration_seconds)
    if 0.7 <= ratio <= 1.3:
        return 1.0
    if 0.5 <= ratio <= 1.6:
        return 0.93
    return 0.86


def map_questionnaire_answers(answer_pairs: Iterable[Tuple[str, str]]) -> List[Dict[str, object]]:
    records = []
    for question_code, answer_value in answer_pairs:
        question = QUESTIONNAIRE_LOOKUP.get(question_code)
        if question is None:
            continue
        option = next((item for item in question["options"] if item["value"] == answer_value), None)
        if option is None:
            continue
        records.append(
            {
                "trait_code": question["trait_code"],
                "trait_name": question["trait_name"],
                "trait_value": float(option["score"]),
                "trait_label": option["trait_label"],
                "source": "questionnaire",
            }
        )
    return records


def trait_index(trait_records: List[Dict[str, object]]) -> Dict[str, float]:
    base = {item["trait_code"]: float(item["trait_value"]) for item in trait_records}
    base["stability_index"] = mean(
        [
            base.get("practice_pace", 65),
            base.get("review_habit", 65),
            base.get("confidence_level", 65),
            base.get("help_seeking", 65),
        ],
        default=65,
    )
    base["strategy_index"] = mean(
        [
            base.get("challenge_threshold", 65),
            base.get("help_seeking", 65),
            base.get("learning_preference", 65),
        ],
        default=65,
    )
    return base


def build_initial_snapshot(
    diagnostic_answers: List[Dict[str, object]],
    question_lookup: Dict[str, Dict[str, object]],
    trait_records: List[Dict[str, object]],
) -> Dict[str, object]:
    dimension_hits = {item["code"]: 0.0 for item in DIMENSION_META}
    dimension_max = {item["code"]: 0.0 for item in DIMENSION_META}
    dimension_evidence = {item["code"]: [] for item in DIMENSION_META}
    knowledge_hits: Dict[str, float] = {}
    knowledge_max: Dict[str, float] = {}
    knowledge_evidence: Dict[str, List[str]] = {}
    cognitive_hits = {item["code"]: 0.0 for item in COGNITIVE_LEVEL_META}
    cognitive_max = {item["code"]: 0.0 for item in COGNITIVE_LEVEL_META}
    cognitive_evidence = {item["code"]: [] for item in COGNITIVE_LEVEL_META}

    for answer in diagnostic_answers:
        question = question_lookup.get(str(answer["question_id"]))
        if question is None:
            continue
        difficulty_factor = DIFFICULTY_FACTORS.get(int(question["difficulty"]), 1.0)
        cognitive_factor = COGNITIVE_FACTORS.get(str(question["cognitive_level"]), 1.0)
        speed_factor = target_speed_factor(float(answer["duration_seconds"]), int(question["target_duration_seconds"]))
        base = (1.0 if answer["is_correct"] else 0.0) * difficulty_factor * cognitive_factor * speed_factor
        max_base = difficulty_factor * cognitive_factor

        for dimension_code, weight in question["dimension_weights"].items():
            dimension_hits[dimension_code] += base * float(weight)
            dimension_max[dimension_code] += max_base * float(weight)
            if not answer["is_correct"]:
                dimension_evidence[dimension_code].append(f"{question['title']} 未答对")
            elif speed_factor < 0.95:
                dimension_evidence[dimension_code].append(f"{question['title']} 用时偏离目标")

        for tag in question["knowledge_tags"]:
            knowledge_hits[tag] = knowledge_hits.get(tag, 0.0) + base
            knowledge_max[tag] = knowledge_max.get(tag, 0.0) + max_base
            if not answer["is_correct"]:
                knowledge_evidence.setdefault(tag, []).append(f"{question['title']} 暴露薄弱点")

        level_code = str(question["cognitive_level"])
        cognitive_hits[level_code] += base
        cognitive_max[level_code] += max_base
        if not answer["is_correct"]:
            cognitive_evidence[level_code].append(f"{question['title']} 未完成该层级要求")

    indices = trait_index(trait_records)
    dimensions = []
    for item in DIMENSION_META:
        code = item["code"]
        raw_score = 100.0 * dimension_hits[code] / dimension_max[code] if dimension_max[code] else 0.0
        if code == "learning_stability":
            raw_score = raw_score * 0.75 + indices["stability_index"] * 0.25
        if code == "logical_reasoning":
            raw_score = raw_score * 0.9 + indices["strategy_index"] * 0.1
        score = clamp(safe_round(raw_score, 2), 0.0, 100.0)
        dimensions.append(
            {
                "dimension_code": code,
                "dimension_name": item["name"],
                "score": score,
                "level": level_label(score),
                "evidence": list(dict.fromkeys(dimension_evidence[code]))[:3],
            }
        )

    knowledge_matrix = []
    for tag, max_value in knowledge_max.items():
        score = 100.0 * knowledge_hits.get(tag, 0.0) / max_value if max_value else 0.0
        score = clamp(safe_round(score, 2), 0.0, 100.0)
        knowledge_matrix.append(
            {
                "knowledge_tag": tag,
                "mastery_score": score,
                "needs_attention": score < KNOWLEDGE_ALERT_THRESHOLD,
                "evidence": knowledge_evidence.get(tag, [])[:3],
            }
        )
    knowledge_matrix.sort(key=lambda item: item["mastery_score"])

    cognitive_diagnosis = []
    for item in COGNITIVE_LEVEL_META:
        code = item["code"]
        score = 100.0 * cognitive_hits[code] / cognitive_max[code] if cognitive_max[code] else 0.0
        score = clamp(safe_round(score, 2), 0.0, 100.0)
        cognitive_diagnosis.append(
            {
                "level_code": code,
                "level_name": item["name"],
                "accuracy": score,
                "needs_attention": score < COGNITIVE_ALERT_THRESHOLD,
                "evidence": cognitive_evidence[code][:3],
            }
        )

    dimensions.sort(key=lambda item: item["score"])
    training_focus = build_training_focus(dimensions, knowledge_matrix)
    risk_flags = build_risk_flags(dimensions, knowledge_matrix, trait_records)
    fallback = build_rule_commentary(dimensions, knowledge_matrix, trait_records)
    return {
        "dimensions": dimensions,
        "knowledge_matrix": knowledge_matrix,
        "cognitive_diagnosis": cognitive_diagnosis,
        "learner_traits": trait_records,
        "training_focus": training_focus,
        "risk_flags": risk_flags,
        "fallback_summary": fallback["portrait_summary"],
        "fallback_commentary": fallback["teacher_commentary"],
    }


def build_training_focus(dimensions: List[Dict[str, object]], knowledge_matrix: List[Dict[str, object]]) -> List[str]:
    focus = []
    for item in dimensions[:2]:
        focus.append(f"优先修复 {item['dimension_name']}")
    for item in knowledge_matrix[:2]:
        focus.append(f"补强知识点：{item['knowledge_tag']}")
    return list(dict.fromkeys(focus))[:4]


def build_risk_flags(
    dimensions: List[Dict[str, object]],
    knowledge_matrix: List[Dict[str, object]],
    trait_records: List[Dict[str, object]],
) -> List[str]:
    flags = []
    trait_scores = trait_index(trait_records)
    if dimensions and float(dimensions[0]["score"]) < 45:
        flags.append(f"{dimensions[0]['dimension_name']} 处于预警区间")
    weak_knowledge = [item["knowledge_tag"] for item in knowledge_matrix if item["needs_attention"]]
    if len(weak_knowledge) >= 3:
        flags.append("基础知识点薄弱面较广，建议降低初始训练跨度")
    if trait_scores.get("confidence_level", 65) < 50:
        flags.append("遇到数学任务时容易紧张，需要更温和的反馈节奏")
    if trait_scores.get("review_habit", 65) < 45:
        flags.append("错题复盘习惯偏弱，后续需强化回看机制")
    return list(dict.fromkeys(flags))[:4]


def build_rule_commentary(
    dimensions: List[Dict[str, object]],
    knowledge_matrix: List[Dict[str, object]],
    trait_records: List[Dict[str, object]],
) -> Dict[str, str]:
    low_dimensions = "、".join(item["dimension_name"] for item in dimensions[:2]) or "整体能力"
    high_dimension = dimensions[-1]["dimension_name"] if dimensions else "暂无明显优势"
    weak_tags = "、".join(item["knowledge_tag"] for item in knowledge_matrix[:2]) or "暂无"
    trait_scores = trait_index(trait_records)
    confidence_text = "信心较强" if trait_scores.get("confidence_level", 65) >= 75 else "需要更多正向反馈"
    portrait_summary = (
        f"当前画像显示，学生的主要关注点集中在 {low_dimensions}，"
        f"相对优势在 {high_dimension}。知识点上需要优先补强 {weak_tags}。"
    )
    teacher_commentary = (
        f"建议先用低门槛、小步快跑的训练修复 {low_dimensions}，"
        f"再把 {high_dimension} 作为稳态支点往上带。当前学习状态上，{confidence_text}。"
    )
    return {"portrait_summary": portrait_summary, "teacher_commentary": teacher_commentary}


def snapshot_to_maps(snapshot: Dict[str, object]) -> Dict[str, Dict[str, Dict[str, object]]]:
    return {
        "dimensions": {item["dimension_code"]: deepcopy(item) for item in snapshot["dimensions"]},
        "knowledge": {item["knowledge_tag"]: deepcopy(item) for item in snapshot["knowledge_matrix"]},
        "cognitive": {item["level_code"]: deepcopy(item) for item in snapshot["cognitive_diagnosis"]},
        "traits": {item["trait_code"]: deepcopy(item) for item in snapshot["learner_traits"]},
    }


def update_snapshot_from_practice(
    current_snapshot: Dict[str, object],
    question_payload: Dict[str, object],
    is_correct: bool,
    duration_seconds: float,
) -> Dict[str, object]:
    maps = snapshot_to_maps(current_snapshot)
    difficulty_factor = DIFFICULTY_FACTORS.get(int(question_payload["difficulty"]), 1.0)
    speed_factor = target_speed_factor(float(duration_seconds), int(question_payload["target_duration_seconds"]))
    delta = (8.0 if is_correct else -6.5) * difficulty_factor * speed_factor

    for dimension_code, weight in question_payload["dimension_weights"].items():
        row = maps["dimensions"][dimension_code]
        row["score"] = clamp(float(row["score"]) + delta * float(weight), 0.0, 100.0)
        row["level"] = level_label(float(row["score"]))
        if not is_correct:
            row["evidence"] = list(dict.fromkeys([f"{question_payload['title']} 练习未答对"] + row["evidence"]))[:3]

    for tag in question_payload["knowledge_tags"]:
        row = maps["knowledge"].setdefault(
            tag,
            {
                "knowledge_tag": tag,
                "mastery_score": 60.0,
                "needs_attention": False,
                "evidence": [],
            },
        )
        row["mastery_score"] = clamp(float(row["mastery_score"]) + (9.0 if is_correct else -7.0), 0.0, 100.0)
        row["needs_attention"] = float(row["mastery_score"]) < KNOWLEDGE_ALERT_THRESHOLD
        if not is_correct:
            row["evidence"] = list(dict.fromkeys([f"{question_payload['title']} 再次出错"] + row["evidence"]))[:3]

    level_code = question_payload["cognitive_level"]
    level_row = maps["cognitive"].setdefault(
        level_code,
        {
            "level_code": level_code,
            "level_name": COGNITIVE_LOOKUP[level_code],
            "accuracy": 60.0,
            "needs_attention": False,
            "evidence": [],
        },
    )
    level_row["accuracy"] = clamp(float(level_row["accuracy"]) + (7.0 if is_correct else -5.5), 0.0, 100.0)
    level_row["needs_attention"] = float(level_row["accuracy"]) < COGNITIVE_ALERT_THRESHOLD

    confidence = maps["traits"].get("confidence_level")
    if confidence:
        confidence["trait_value"] = clamp(float(confidence["trait_value"]) + (3.0 if is_correct else -2.0), 0.0, 100.0)
        confidence["trait_label"] = "信心较强" if float(confidence["trait_value"]) >= 75 else "信心平稳" if float(confidence["trait_value"]) >= 55 else "信心偏弱"
    pace = maps["traits"].get("practice_pace")
    if pace and speed_factor < 0.9:
        pace["trait_value"] = clamp(float(pace["trait_value"]) - 1.5, 0.0, 100.0)

    dimensions = sorted(maps["dimensions"].values(), key=lambda item: float(item["score"]))
    knowledge_matrix = sorted(maps["knowledge"].values(), key=lambda item: float(item["mastery_score"]))
    cognitive_diagnosis = list(maps["cognitive"].values())
    learner_traits = list(maps["traits"].values())
    training_focus = build_training_focus(dimensions, knowledge_matrix)
    risk_flags = build_risk_flags(dimensions, knowledge_matrix, learner_traits)
    fallback = build_rule_commentary(dimensions, knowledge_matrix, learner_traits)
    return {
        "dimensions": dimensions,
        "knowledge_matrix": knowledge_matrix,
        "cognitive_diagnosis": cognitive_diagnosis,
        "learner_traits": learner_traits,
        "training_focus": training_focus,
        "risk_flags": risk_flags,
        "fallback_summary": fallback["portrait_summary"],
        "fallback_commentary": fallback["teacher_commentary"],
    }


def summarize_snapshot_delta(previous_snapshot: Dict[str, object], new_snapshot: Dict[str, object]) -> List[str]:
    previous_dimensions = {item["dimension_code"]: float(item["score"]) for item in previous_snapshot["dimensions"]}
    summary = []
    for row in new_snapshot["dimensions"]:
        old_score = previous_dimensions.get(row["dimension_code"], float(row["score"]))
        diff = float(row["score"]) - old_score
        if abs(diff) >= 2:
            direction = "上升" if diff > 0 else "下降"
            summary.append(f"{row['dimension_name']} {direction} {abs(round(diff, 1))} 分")
    return summary[:4]
