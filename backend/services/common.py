import json
import math
import uuid
from typing import Any, Dict, Iterable, List, Optional


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_loads(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def mean(values: Iterable[float], default: float = 0.0) -> float:
    items = list(values)
    if not items:
        return default
    return sum(items) / len(items)


def level_label(score: float) -> str:
    if score >= 80:
        return "优势"
    if score >= 60:
        return "稳定"
    if score >= 45:
        return "待加强"
    return "预警"


def percent(value: float) -> str:
    return f"{round(value)}%"


def safe_round(value: float, digits: int = 2) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return round(value, digits)


def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        cleaned = [item.strip(" -•") for item in value.replace("；", "\n").replace(";", "\n").splitlines()]
        return [item for item in cleaned if item]
    return [value]


def ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        result: Dict[str, Any] = {}
        for item in value:
            if isinstance(item, dict) and "key" in item and "value" in item:
                result[str(item["key"])] = item["value"]
        return result
    return {}
