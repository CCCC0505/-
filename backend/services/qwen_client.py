from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import AIAnalysisRun
from backend.services.common import ensure_dict, ensure_list, json_dumps, make_id


settings = get_settings()


PORTRAIT_OUTPUT_SCHEMA = {
    "portrait_summary": "一句话总结当前学生画像",
    "teacher_commentary": "面向老师/家长的简洁点评",
    "training_focus": ["3-4条训练重点"],
    "risk_flags": ["0-4条风险提醒"],
    "confidence": 0.0,
    "dimension_insights": [
        {"dimension_code": "calculation_accuracy", "diagnosis": "该维度当前表现如何", "evidence": ["证据1", "证据2"]}
    ],
    "knowledge_insights": [
        {"knowledge_tag": "一次函数", "priority": "high", "diagnosis": "该知识点的当前判断"}
    ],
    "cognitive_insights": [
        {"level_code": "apply", "diagnosis": "该认知层级的当前判断"}
    ],
}


class QwenClient:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.client = None
        if settings.qwen_enabled:
            self.client = OpenAI(
                api_key=settings.dashscope_api_key,
                base_url=settings.dashscope_base_url,
                timeout=settings.qwen_timeout_seconds,
            )

    def capability_status(self) -> Dict[str, Any]:
        return {
            "enabled": settings.qwen_enabled,
            "provider": "dashscope",
            "model_name": settings.qwen_model,
            "base_url": settings.dashscope_base_url,
            "message": "已配置 DashScope/Qwen" if settings.qwen_enabled else "未配置 DASHSCOPE_API_KEY，将自动回退到规则输出",
        }

    def portrait_schema_definition(self) -> Dict[str, Any]:
        return {
            "schema_name": "portrait_ai_output_v1",
            "description": "用于把 Qwen 的画像解释输出规范成可落表、可展示、可审计的成长画像结构。",
            "schema": PORTRAIT_OUTPUT_SCHEMA,
            "notes": [
                "前五个字段直接参与画像摘要、教师点评、训练重点、风险提示和可信度展示。",
                "dimension_insights / knowledge_insights / cognitive_insights 用于分析页展示和审计，不覆盖规则分数。",
                "如果模型未返回这些字段，后端会自动按规则画像补齐最小可用结果。",
            ],
        }

    def companion_reply(self, message: str, subject: str = "", grade: str = "", custom_system_prompt: str = "") -> str:
        fallback = self._fallback_companion_reply(message, subject)
        if not settings.qwen_enabled or self.client is None:
            return fallback

        system_prompt = custom_system_prompt or (
            f"你是一位友好的{grade or ''}{subject or ''}学习陪伴助手。"
            "请用简洁、具体、鼓励式语气回答，优先帮助学生理解问题、安排下一步。"
        )
        try:
            response = self.client.chat.completions.create(
                model=settings.qwen_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.5,
            )
            text = (response.choices[0].message.content or "").strip()
            return text or fallback
        except Exception:  # noqa: BLE001
            return fallback

    def hotspot_questions(self, subject: str, grade: str, knowledge: str, count: int = 3) -> List[Dict[str, Any]]:
        return self.hotspot_questions_with_meta(subject, grade, knowledge, count)[0]

    def hotspot_questions_with_meta(self, subject: str, grade: str, knowledge: str, count: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        fallback = self._fallback_hotspot_questions(subject, grade, knowledge, count)
        if not settings.qwen_enabled or self.client is None:
            return fallback, {
                "enabled": settings.qwen_enabled,
                "attempted": False,
                "success": False,
                "fallback_used": True,
                "model_name": settings.qwen_model,
                "message": "未配置 Qwen，已使用备用热点题",
            }

        prompt = (
            f"你是一位{grade}{subject}老师。请围绕“{knowledge}”生成 {count} 道适合学生练习的应用题。"
            "请优先返回 JSON 对象，格式为 {\"questions\":[...]}；如果无法做到，也可以直接返回 JSON 数组。"
            "每个元素包含 id,badge,difficulty,content,tag。"
            "difficulty 仅允许：简单、中等、困难。不要输出任何额外解释。"
        )
        try:
            request_kwargs = {
                "model": settings.qwen_model,
                "messages": [
                    {"role": "system", "content": "你是严格遵守 JSON 输出的教育题目生成助手。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 900,
                "timeout": settings.qwen_timeout_seconds,
            }
            try:
                response = self.client.chat.completions.create(
                    **request_kwargs,
                    response_format={"type": "json_object"},
                )
            except Exception:
                response = self.client.chat.completions.create(**request_kwargs)
            text = (response.choices[0].message.content or "").strip()
            parsed = self._extract_json_array(text)
            if not parsed:
                parsed_object = self._extract_json_object(text)
                if isinstance(parsed_object.get("questions"), list):
                    parsed = parsed_object.get("questions", [])
            normalized = []
            for idx, item in enumerate(parsed[:count], start=1):
                if not isinstance(item, dict):
                    continue
                normalized.append(
                    {
                        "id": str(item.get("id") or f"h{idx:03d}"),
                        "badge": str(item.get("badge") or "AI推荐"),
                        "difficulty": str(item.get("difficulty") or "中等"),
                        "content": str(item.get("content") or ""),
                        "tag": str(item.get("tag") or knowledge),
                    }
                )
            if normalized:
                return normalized, {
                    "enabled": True,
                    "attempted": True,
                    "success": True,
                    "fallback_used": False,
                    "model_name": settings.qwen_model,
                    "message": "已使用 Qwen 生成热点题",
                }
            return fallback, {
                "enabled": True,
                "attempted": True,
                "success": False,
                "fallback_used": True,
                "model_name": settings.qwen_model,
                "message": "Qwen 返回为空，已使用备用热点题",
            }
        except Exception:  # noqa: BLE001
            return fallback, {
                "enabled": True,
                "attempted": True,
                "success": False,
                "fallback_used": True,
                "model_name": settings.qwen_model,
                "message": "Qwen 调用失败，已使用备用热点题",
            }

    def analyze_cold_start(
        self,
        student_id: str,
        student_name: str,
        snapshot_payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], AIAnalysisRun]:
        fallback = {
            "portrait_summary": snapshot_payload["fallback_summary"],
            "teacher_commentary": snapshot_payload["fallback_commentary"],
            "training_focus": snapshot_payload["training_focus"],
            "risk_flags": snapshot_payload["risk_flags"],
            "confidence": 0.0,
            "dimension_insights": self._fallback_dimension_insights(snapshot_payload),
            "knowledge_insights": self._fallback_knowledge_insights(snapshot_payload),
            "cognitive_insights": self._fallback_cognitive_insights(snapshot_payload),
        }
        prompt = (
            "你是一位初中数学教研老师，请根据规则画像输出简洁、可信、可落地的 JSON。\n"
            "只返回 JSON，不要加解释。\n"
            "字段必须严格包含以下键：portrait_summary, teacher_commentary, training_focus, risk_flags, confidence, dimension_insights, knowledge_insights, cognitive_insights。\n"
            f"输出 schema 参考：{json_dumps(self.portrait_schema_definition()['schema'])}\n"
            "其中 dimension_insights 必须使用规则画像中的 dimension_code；knowledge_insights 使用已有 knowledge_tag；cognitive_insights 使用已有 level_code。\n"
            f"学生：{student_name}\n"
            f"规则画像：{json_dumps(self._compact_snapshot_payload(snapshot_payload))}"
        )
        normalized, run = self._run_json_task(
            student_id=student_id,
            stage="cold_start",
            request_type="portrait_summary",
            prompt=prompt,
            fallback=fallback,
            normalizer=self._normalize_cold_start,
        )
        return normalized, run

    def explain_recommendations(
        self,
        student_id: str,
        student_name: str,
        snapshot_payload: Dict[str, Any],
        recommendation_items: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], AIAnalysisRun]:
        fallback = {
            "overall_commentary": self._fallback_recommendation_commentary(snapshot_payload),
            "training_focus": snapshot_payload.get("training_focus", []),
            "item_reasons": [{"question_id": item["question_id"], "reason": item["rule_reason"]} for item in recommendation_items],
            "confidence": 0.0,
        }
        compact_items = [
            {
                "question_id": item["question_id"],
                "title": item["title"],
                "recommendation_type": item["recommendation_type"],
                "rule_reason": item["rule_reason"],
                "priority": item.get("priority"),
                "recommendation_driver": item.get("recommendation_driver"),
                "recommendation_template": item.get("recommendation_template"),
            }
            for item in recommendation_items
        ]
        prompt = (
            "你是一位初中数学老师，请根据学生当前画像和推荐列表输出 JSON。\n"
            "只返回 JSON，不要输出 Markdown。\n"
            "字段必须包含 overall_commentary, training_focus, item_reasons, confidence。\n"
            f"画像摘要：{json_dumps(snapshot_payload)}\n"
            f"推荐列表：{json_dumps(compact_items)}"
        )
        normalized, run = self._run_json_task(
            student_id=student_id,
            stage="recommendation",
            request_type="recommendation_explain",
            prompt=prompt,
            fallback=fallback,
            normalizer=self._normalize_recommendation,
        )
        return normalized, run

    def generate_practice_feedback(
        self,
        student_id: str,
        student_name: str,
        question_payload: Dict[str, Any],
        practice_payload: Dict[str, Any],
        delta_summary: List[str],
    ) -> Tuple[Dict[str, Any], AIAnalysisRun]:
        fallback = {
            "feedback_summary": self._fallback_practice_feedback(practice_payload, delta_summary),
            "mistake_analysis": delta_summary if not practice_payload["is_correct"] else ["本题已答对，可继续保持当前策略。"],
            "next_steps": ["继续完成同类型题训练", "回看本题对应知识点"],
            "confidence": 0.0,
        }
        prompt = (
            "你是一位初中数学老师，请根据学生练习结果输出 JSON。\n"
            "只返回 JSON，不要解释。\n"
            "字段必须包含 feedback_summary, mistake_analysis, next_steps, confidence。\n"
            f"学生：{student_name}\n"
            f"题目信息：{json_dumps(question_payload)}\n"
            f"练习结果：{json_dumps(practice_payload)}\n"
            f"画像变化：{json_dumps(delta_summary)}"
        )
        normalized, run = self._run_json_task(
            student_id=student_id,
            stage="practice",
            request_type="practice_feedback",
            prompt=prompt,
            fallback=fallback,
            normalizer=self._normalize_practice,
        )
        return normalized, run

    def _run_json_task(
        self,
        student_id: str,
        stage: str,
        request_type: str,
        prompt: str,
        fallback: Dict[str, Any],
        normalizer,
    ) -> Tuple[Dict[str, Any], AIAnalysisRun]:
        run = AIAnalysisRun(
            run_id=make_id("airun"),
            student_id=student_id,
            stage=stage,
            request_type=request_type,
            provider="dashscope",
            model_name=settings.qwen_model,
            enabled=settings.qwen_enabled,
            attempted=False,
            success=False,
            fallback_used=True,
            confidence=0.0,
            error_summary="",
            analysis_summary="",
            raw_prompt_summary=prompt[:2000],
            raw_response_text="",
            normalized_output_json=json_dumps({}),
            structured_output_json=json_dumps(fallback),
        )

        if not settings.qwen_enabled or self.client is None:
            run.error_summary = "未配置 DASHSCOPE_API_KEY，已使用规则回退"
            run.analysis_summary = self._summary_from_output(request_type, fallback)
            self.db.add(run)
            self.db.flush()
            return fallback, run

        try:
            run.attempted = True
            request_kwargs = {
                "model": settings.qwen_model,
                "messages": [
                    {"role": "system", "content": "你是严谨的教育分析助手，必须只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 1200,
                "timeout": settings.qwen_timeout_seconds,
            }
            try:
                response = self.client.chat.completions.create(
                    **request_kwargs,
                    response_format={"type": "json_object"},
                )
            except Exception:
                response = self.client.chat.completions.create(**request_kwargs)
            text = response.choices[0].message.content or ""
            run.raw_response_text = text[:8000]
            extracted = self._extract_json_object(text)
            normalized = normalizer(extracted, fallback)
            run.normalized_output_json = json_dumps(extracted)
            run.structured_output_json = json_dumps(normalized)
            run.confidence = float(normalized.get("confidence", 0.0) or 0.0)
            run.success = any(normalized.get(key) for key in fallback.keys() if key != "confidence")
            run.fallback_used = normalized != extracted or run.confidence == 0.0
            run.analysis_summary = self._summary_from_output(request_type, normalized)
            if not run.success:
                run.error_summary = "模型输出为空，已使用规则回退"
                normalized = fallback
                run.structured_output_json = json_dumps(normalized)
            self.db.add(run)
            self.db.flush()
            return normalized, run
        except Exception as exc:  # noqa: BLE001
            run.error_summary = f"Qwen 调用失败：{exc}"
            run.analysis_summary = self._summary_from_output(request_type, fallback)
            self.db.add(run)
            self.db.flush()
            return fallback, run

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        if not text.strip():
            return {}
        fenced = text.strip()
        if "```" in fenced:
            chunks = fenced.split("```")
            fenced = next((chunk for chunk in chunks if "{" in chunk and "}" in chunk), fenced)
            fenced = fenced.replace("json", "", 1).strip()
        start = fenced.find("{")
        if start < 0:
            return {}
        depth = 0
        end = -1
        for idx, char in enumerate(fenced[start:], start=start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        if end < 0:
            return {}
        candidate = fenced[start:end]
        try:
            loaded = json.loads(candidate)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _extract_json_array(self, text: str) -> List[Any]:
        if not text.strip():
            return []
        fenced = text.strip()
        if "```" in fenced:
            chunks = fenced.split("```")
            fenced = next((chunk for chunk in chunks if "[" in chunk and "]" in chunk), fenced)
            fenced = fenced.replace("json", "", 1).strip()
        match = re.search(r"\[[\s\S]*\]", fenced)
        if not match:
            return []
        try:
            loaded = json.loads(match.group(0))
            return loaded if isinstance(loaded, list) else []
        except json.JSONDecodeError:
            return []

    def _normalize_cold_start(self, payload: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        data = ensure_dict(payload)
        portrait_summary = str(data.get("portrait_summary") or fallback["portrait_summary"]).strip()
        teacher_commentary = str(data.get("teacher_commentary") or fallback["teacher_commentary"]).strip()
        training_focus = ensure_list(data.get("training_focus")) or fallback["training_focus"]
        risk_flags = ensure_list(data.get("risk_flags")) or fallback["risk_flags"]
        confidence = self._normalize_confidence(data.get("confidence"))
        dimension_insights = self._normalize_dimension_insights(data.get("dimension_insights"), fallback["dimension_insights"])
        knowledge_insights = self._normalize_knowledge_insights(data.get("knowledge_insights"), fallback["knowledge_insights"])
        cognitive_insights = self._normalize_cognitive_insights(data.get("cognitive_insights"), fallback["cognitive_insights"])
        return {
            "portrait_summary": portrait_summary,
            "teacher_commentary": teacher_commentary,
            "training_focus": [str(item) for item in training_focus][:4],
            "risk_flags": [str(item) for item in risk_flags][:4],
            "confidence": confidence,
            "dimension_insights": dimension_insights,
            "knowledge_insights": knowledge_insights,
            "cognitive_insights": cognitive_insights,
        }

    def _normalize_recommendation(self, payload: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        data = ensure_dict(payload)
        item_reasons_raw = data.get("item_reasons", [])
        item_reasons = []
        if isinstance(item_reasons_raw, dict):
            item_reasons = [{"question_id": key, "reason": value} for key, value in item_reasons_raw.items()]
        else:
            for item in ensure_list(item_reasons_raw):
                if isinstance(item, dict):
                    item_reasons.append(
                        {
                            "question_id": str(item.get("question_id") or item.get("id") or ""),
                            "reason": str(item.get("reason") or item.get("commentary") or ""),
                        }
                    )
        merged = {entry["question_id"]: entry["reason"] for entry in fallback["item_reasons"]}
        for item in item_reasons:
            if item["question_id"] and item["reason"]:
                merged[item["question_id"]] = item["reason"]
        normalized_items = [{"question_id": key, "reason": value} for key, value in merged.items()]
        return {
            "overall_commentary": str(data.get("overall_commentary") or fallback["overall_commentary"]).strip(),
            "training_focus": [str(item) for item in (ensure_list(data.get("training_focus")) or fallback["training_focus"])][:4],
            "item_reasons": normalized_items,
            "confidence": self._normalize_confidence(data.get("confidence")),
        }

    def _normalize_practice(self, payload: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        data = ensure_dict(payload)
        return {
            "feedback_summary": str(data.get("feedback_summary") or fallback["feedback_summary"]).strip(),
            "mistake_analysis": [str(item) for item in (ensure_list(data.get("mistake_analysis")) or fallback["mistake_analysis"])][:4],
            "next_steps": [str(item) for item in (ensure_list(data.get("next_steps")) or fallback["next_steps"])][:4],
            "confidence": self._normalize_confidence(data.get("confidence")),
        }

    def _normalize_confidence(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, str):
            cleaned = value.strip().replace("%", "")
            try:
                value = float(cleaned)
                if value > 1:
                    value /= 100.0
            except ValueError:
                return 0.0
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if number > 1:
            number /= 100.0
        return max(0.0, min(number, 1.0))

    def _summary_from_output(self, request_type: str, output: Dict[str, Any]) -> str:
        if request_type == "portrait_summary":
            return str(output.get("portrait_summary", ""))[:240]
        if request_type == "recommendation_explain":
            return str(output.get("overall_commentary", ""))[:240]
        return str(output.get("feedback_summary", ""))[:240]

    def _fallback_companion_reply(self, message: str, subject: str) -> str:
        if "休息" in message or "累" in message:
            return "已经学习一会儿了，先休息几分钟、活动一下再继续，效率会更高。"
        if "不会" in message or "难" in message:
            return f"先别着急，我们可以把这道{subject or '题'}拆成已知条件、目标和步骤三部分，先找第一步。"
        return "我在这儿。你可以把题目、卡住的步骤或今天的学习计划告诉我，我会帮你一起理清。"

    def _fallback_hotspot_questions(self, subject: str, grade: str, knowledge: str, count: int) -> List[Dict[str, Any]]:
        templates = [
            ("AI推荐", "中等", f"围绕“{knowledge}”设计的一道{grade}{subject}应用题，重点考查知识点在真实情境中的使用。", "真实情境"),
            ("AI推荐", "困难", f"结合综合场景，分析“{knowledge}”在复杂问题中的迁移应用。", "综合拓展"),
            ("AI推荐", "简单", f"从基础情境出发，巩固“{knowledge}”的核心概念和直接应用。", "基础巩固"),
        ]
        result = []
        for idx in range(count):
            badge, difficulty, content, tag = templates[idx % len(templates)]
            result.append({"id": f"h{idx + 1:03d}", "badge": badge, "difficulty": difficulty, "content": content, "tag": tag})
        return result

    def _fallback_recommendation_commentary(self, snapshot_payload: Dict[str, Any]) -> str:
        focus = "、".join(snapshot_payload.get("training_focus", [])[:3]) or "基础修复"
        return f"本轮推荐围绕 {focus} 展开，先补短板，再做同类巩固，最后加入一题提升题观察迁移。"

    def _fallback_practice_feedback(self, practice_payload: Dict[str, Any], delta_summary: List[str]) -> str:
        if practice_payload["is_correct"]:
            return "这道题已经答对，建议继续保持当前节奏，并趁热完成同类型练习。"
        if delta_summary:
            return f"这次练习提示你在 {delta_summary[0]} 上还有波动，建议先回看解题步骤再做同类题。"
        return "这道题还需要回看解题步骤，先把关键知识点重新理顺。"

    def _compact_snapshot_payload(self, snapshot_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "portrait_summary": snapshot_payload.get("portrait_summary"),
            "teacher_commentary": snapshot_payload.get("teacher_commentary"),
            "dimensions": [
                {
                    "dimension_code": item.get("dimension_code"),
                    "dimension_name": item.get("dimension_name"),
                    "score": item.get("score"),
                    "level": item.get("level"),
                }
                for item in snapshot_payload.get("dimensions", [])[:5]
            ],
            "knowledge_matrix": [
                {
                    "knowledge_tag": item.get("knowledge_tag"),
                    "mastery_score": item.get("mastery_score"),
                    "needs_attention": item.get("needs_attention"),
                }
                for item in snapshot_payload.get("knowledge_matrix", [])[:6]
            ],
            "cognitive_diagnosis": [
                {
                    "level_code": item.get("level_code"),
                    "level_name": item.get("level_name"),
                    "accuracy": item.get("accuracy"),
                    "needs_attention": item.get("needs_attention"),
                }
                for item in snapshot_payload.get("cognitive_diagnosis", [])[:4]
            ],
            "learner_traits": [
                {
                    "trait_code": item.get("trait_code"),
                    "trait_name": item.get("trait_name"),
                    "trait_label": item.get("trait_label"),
                    "trait_value": item.get("trait_value"),
                }
                for item in snapshot_payload.get("learner_traits", [])[:6]
            ],
            "training_focus": snapshot_payload.get("training_focus", [])[:4],
            "risk_flags": snapshot_payload.get("risk_flags", [])[:4],
            "fallback_summary": snapshot_payload.get("fallback_summary"),
            "fallback_commentary": snapshot_payload.get("fallback_commentary"),
        }

    def _fallback_dimension_insights(self, snapshot_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "dimension_code": item["dimension_code"],
                "diagnosis": f"{item['dimension_name']} 当前处于 {item['level']}，建议结合后续训练持续观察。",
                "evidence": ensure_list(item.get("evidence"))[:2],
            }
            for item in snapshot_payload.get("dimensions", [])[:5]
        ]

    def _fallback_knowledge_insights(self, snapshot_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = []
        for item in snapshot_payload.get("knowledge_matrix", [])[:6]:
            rows.append(
                {
                    "knowledge_tag": item["knowledge_tag"],
                    "priority": "high" if item["needs_attention"] else "medium",
                    "diagnosis": f"当前掌握度 {round(float(item['mastery_score']))}，{('建议优先补强' if item['needs_attention'] else '可继续巩固')}。",
                }
            )
        return rows

    def _fallback_cognitive_insights(self, snapshot_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "level_code": item["level_code"],
                "diagnosis": f"{item['level_name']} 当前准确率 {round(float(item['accuracy']))}。"
            }
            for item in snapshot_payload.get("cognitive_diagnosis", [])[:4]
        ]

    def _normalize_dimension_insights(self, payload: Any, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for item in ensure_list(payload):
            if not isinstance(item, dict):
                continue
            code = str(item.get("dimension_code") or "").strip()
            diagnosis = str(item.get("diagnosis") or "").strip()
            evidence = [str(value) for value in ensure_list(item.get("evidence")) if str(value).strip()]
            if code and diagnosis:
                rows.append({"dimension_code": code, "diagnosis": diagnosis, "evidence": evidence[:3]})
        return rows or fallback

    def _normalize_knowledge_insights(self, payload: Any, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for item in ensure_list(payload):
            if not isinstance(item, dict):
                continue
            tag = str(item.get("knowledge_tag") or "").strip()
            diagnosis = str(item.get("diagnosis") or "").strip()
            priority = str(item.get("priority") or "medium").strip().lower()
            if tag and diagnosis:
                rows.append({"knowledge_tag": tag, "priority": priority if priority in {"high", "medium", "low"} else "medium", "diagnosis": diagnosis})
        return rows or fallback

    def _normalize_cognitive_insights(self, payload: Any, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for item in ensure_list(payload):
            if not isinstance(item, dict):
                continue
            code = str(item.get("level_code") or "").strip()
            diagnosis = str(item.get("diagnosis") or "").strip()
            if code and diagnosis:
                rows.append({"level_code": code, "diagnosis": diagnosis})
        return rows or fallback
