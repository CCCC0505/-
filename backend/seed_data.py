from __future__ import annotations

from typing import Dict, List, Tuple


GRADE_CATALOG = [
    {"code": "grade_7", "label": "初一", "active": False, "status": "coming_soon"},
    {"code": "grade_8", "label": "初二", "active": True, "status": "active"},
    {"code": "grade_9", "label": "初三", "active": False, "status": "coming_soon"},
]


DIMENSION_META = [
    {"code": "calculation_accuracy", "name": "计算准确性"},
    {"code": "knowledge_mastery", "name": "知识点掌握度"},
    {"code": "logical_reasoning", "name": "逻辑策略"},
    {"code": "cognitive_performance", "name": "认知层级表现"},
    {"code": "learning_stability", "name": "学习稳定性"},
]


COGNITIVE_LEVEL_META = [
    {"code": "remember", "name": "记忆识别"},
    {"code": "understand", "name": "理解迁移"},
    {"code": "apply", "name": "应用求解"},
    {"code": "analyze", "name": "分析建模"},
]


QUESTIONNAIRE_QUESTIONS = [
    {
        "code": "difficulty_preference",
        "title": "你更喜欢怎样的题目难度？",
        "prompt": "这决定系统给你的起始挑战阈值。",
        "trait_code": "challenge_threshold",
        "trait_name": "挑战阈值",
        "options": [
            {"value": "steady", "label": "先稳住基础", "score": 42, "trait_label": "偏稳妥"},
            {"value": "balanced", "label": "稳步进阶", "score": 68, "trait_label": "均衡推进"},
            {"value": "challenge", "label": "更想挑战", "score": 84, "trait_label": "挑战驱动"},
        ],
    },
    {
        "code": "practice_pace",
        "title": "做题节奏更像哪一种？",
        "prompt": "这会影响学习稳定性的建模。",
        "trait_code": "practice_pace",
        "trait_name": "练习节奏",
        "options": [
            {"value": "slow", "label": "慢一点更安心", "score": 58, "trait_label": "稳慢型"},
            {"value": "steady", "label": "稳步推进", "score": 72, "trait_label": "稳健型"},
            {"value": "fast", "label": "快节奏推进", "score": 81, "trait_label": "高节奏型"},
        ],
    },
    {
        "code": "review_habit",
        "title": "做错题后你通常会怎么处理？",
        "prompt": "这会进入错题回流和稳定性建模。",
        "trait_code": "review_habit",
        "trait_name": "错题复盘习惯",
        "options": [
            {"value": "rarely", "label": "很少回看", "score": 36, "trait_label": "复盘弱"},
            {"value": "sometimes", "label": "偶尔回看", "score": 64, "trait_label": "复盘中"},
            {"value": "always", "label": "会主动总结", "score": 88, "trait_label": "复盘强"},
        ],
    },
    {
        "code": "confidence_level",
        "title": "遇到数学题时你的心理状态更像哪一种？",
        "prompt": "这会影响教师点评的语气和风险标记。",
        "trait_code": "confidence_level",
        "trait_name": "数学自信度",
        "options": [
            {"value": "anxious", "label": "容易紧张", "score": 44, "trait_label": "信心偏弱"},
            {"value": "stable", "label": "比较稳定", "score": 70, "trait_label": "信心平稳"},
            {"value": "confident", "label": "比较自信", "score": 86, "trait_label": "信心较强"},
        ],
    },
    {
        "code": "help_seeking",
        "title": "卡住时你一般会怎么做？",
        "prompt": "这会进入策略和稳定性建模。",
        "trait_code": "help_seeking",
        "trait_name": "求助倾向",
        "options": [
            {"value": "avoid", "label": "常常自己扛着", "score": 48, "trait_label": "求助不足"},
            {"value": "balanced", "label": "先想再求助", "score": 78, "trait_label": "求助平衡"},
            {"value": "quick", "label": "卡住就会问", "score": 66, "trait_label": "求助及时"},
        ],
    },
    {
        "code": "learning_preference",
        "title": "你更喜欢哪种学习方式？",
        "prompt": "这会影响训练重点与点评表达。",
        "trait_code": "learning_preference",
        "trait_name": "学习偏好",
        "options": [
            {"value": "examples", "label": "例题带练", "score": 68, "trait_label": "例题驱动"},
            {"value": "steps", "label": "看步骤讲解", "score": 74, "trait_label": "步骤驱动"},
            {"value": "trial", "label": "先自己做再对答案", "score": 80, "trait_label": "主动试错型"},
        ],
    },
]


def weights(calc: float, knowledge: float, logic: float, cognitive: float, stability: float) -> Dict[str, float]:
    return {
        "calculation_accuracy": calc,
        "knowledge_mastery": knowledge,
        "logical_reasoning": logic,
        "cognitive_performance": cognitive,
        "learning_stability": stability,
    }


def mcq_options(values: List[str], correct_index: int) -> Tuple[List[Dict[str, str]], str]:
    labels = ["A", "B", "C", "D"]
    options = [{"label": labels[idx], "value": str(value)} for idx, value in enumerate(values)]
    return options, labels[correct_index]


def question(
    question_id: str,
    stage: str,
    title: str,
    stem: str,
    option_values: List[str],
    correct_index: int,
    explanation: str,
    difficulty: int,
    target_duration_seconds: int,
    knowledge_tags: List[str],
    cognitive_level: str,
    dimension_weights: Dict[str, float],
) -> Dict[str, object]:
    options, correct_answer = mcq_options(option_values, correct_index)
    return {
        "question_id": question_id,
        "grade": "grade_8",
        "stage": stage,
        "title": title,
        "stem": stem,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "difficulty": difficulty,
        "target_duration_seconds": target_duration_seconds,
        "knowledge_tags": knowledge_tags,
        "cognitive_level": cognitive_level,
        "dimension_weights": dimension_weights,
        "training_tags": knowledge_tags,
    }


DIAGNOSTIC_QUESTIONS = [
    question("DIAG-001", "diagnostic", "有理数运算 1", "-3 + 7 的结果是？", ["-10", "-4", "4", "10"], 2, "先看符号再做加法，结果是 4。", 1, 45, ["实数运算"], "remember", weights(0.55, 0.25, 0.05, 0.05, 0.10)),
    question("DIAG-002", "diagnostic", "分数加法", "2/3 + 1/6 的结果是？", ["1/2", "5/6", "1", "7/6"], 1, "通分到 6，得到 4/6 + 1/6 = 5/6。", 1, 60, ["分数运算"], "understand", weights(0.48, 0.25, 0.08, 0.07, 0.12)),
    question("DIAG-003", "diagnostic", "解方程 1", "方程 2(x-1)=8 的解是？", ["3", "4", "5", "6"], 2, "先两边除以 2 得 x-1=4，再得到 x=5。", 2, 75, ["一元一次方程"], "apply", weights(0.28, 0.30, 0.20, 0.12, 0.10)),
    question("DIAG-004", "diagnostic", "解方程 2", "方程 3x + 2 = 2x + 9 的解是？", ["5", "6", "7", "8"], 2, "移项得 x=7。", 2, 75, ["一元一次方程"], "apply", weights(0.26, 0.30, 0.22, 0.12, 0.10)),
    question("DIAG-005", "diagnostic", "一次函数代值", "若 y=2x+1，当 x=3 时，y 等于？", ["5", "6", "7", "8"], 2, "把 x=3 代入，得到 y=7。", 2, 75, ["一次函数"], "apply", weights(0.22, 0.32, 0.20, 0.16, 0.10)),
    question("DIAG-006", "diagnostic", "平面直角坐标系", "点 A(2,-1) 位于第几象限？", ["第一象限", "第二象限", "第三象限", "第四象限"], 3, "横坐标正、纵坐标负，在第四象限。", 1, 50, ["平面直角坐标系"], "remember", weights(0.05, 0.38, 0.18, 0.24, 0.15)),
    question("DIAG-007", "diagnostic", "三角形内角和", "一个三角形中两个角分别是 35° 和 65°，第三个角是？", ["70°", "75°", "80°", "90°"], 2, "三角形内角和 180°，所以第三个角是 80°。", 2, 65, ["三角形"], "understand", weights(0.08, 0.30, 0.22, 0.25, 0.15)),
    question("DIAG-008", "diagnostic", "平均数", "数据 2，4，4，5，7 的平均数是？", ["4", "4.2", "4.4", "4.6"], 2, "和为 22，22÷5=4.4。", 2, 70, ["数据统计"], "understand", weights(0.20, 0.26, 0.15, 0.24, 0.15)),
    question("DIAG-009", "diagnostic", "简单概率", "掷一枚均匀硬币，出现正面的概率是？", ["1/4", "1/3", "1/2", "2/3"], 2, "正反两面等可能，概率为 1/2。", 1, 55, ["概率初步"], "remember", weights(0.05, 0.32, 0.25, 0.23, 0.15)),
    question("DIAG-010", "diagnostic", "因式分解", "x²-9 可以分解为？", ["(x-9)(x+1)", "(x-3)(x+3)", "(x-1)(x+9)", "(x-3)²"], 1, "这是平方差公式：x²-3²=(x-3)(x+3)。", 2, 80, ["整式与因式分解"], "understand", weights(0.20, 0.28, 0.20, 0.20, 0.12)),
    question("DIAG-011", "diagnostic", "科学记数法", "0.00036 用科学记数法表示为？", ["3.6×10⁻⁴", "3.6×10⁻³", "36×10⁻⁵", "0.36×10⁻³"], 0, "小数点向右移动 4 位，指数为 -4。", 2, 65, ["科学记数法"], "understand", weights(0.28, 0.28, 0.12, 0.18, 0.14)),
    question("DIAG-012", "diagnostic", "不等式性质", "若 a>b，下列一定成立的是？", ["a-2<b-2", "a+2>b+2", "2a<2b", "-a>-b"], 1, "同向加同一个数，不等号方向不变。", 2, 70, ["不等式"], "understand", weights(0.16, 0.30, 0.26, 0.16, 0.12)),
    question("DIAG-013", "diagnostic", "一次函数反求", "若 y=-x+4，当 y=1 时，x 等于？", ["1", "2", "3", "4"], 2, "把 y=1 代入，得到 -x+4=1，所以 x=3。", 2, 80, ["一次函数"], "apply", weights(0.22, 0.28, 0.24, 0.16, 0.10)),
    question("DIAG-014", "diagnostic", "应用题 1", "一个长方形周长是 20，长是 6，宽是？", ["3", "4", "5", "6"], 1, "2(长+宽)=20，所以长+宽=10，宽=4。", 2, 90, ["列式建模"], "analyze", weights(0.12, 0.24, 0.30, 0.22, 0.12)),
    question("DIAG-015", "diagnostic", "中位数", "数据 1，2，2，4，9 的中位数是？", ["1", "2", "4", "9"], 1, "按从小到大排列后，中间的数是 2。", 1, 50, ["数据统计"], "remember", weights(0.10, 0.28, 0.16, 0.26, 0.20)),
    question("DIAG-016", "diagnostic", "数列观察", "数列 2，5，8，11，… 的第 10 项是？", ["26", "27", "28", "29"], 3, "公差是 3，第 10 项是 2+9×3=29。", 3, 90, ["规律探究"], "analyze", weights(0.14, 0.18, 0.32, 0.24, 0.12)),
    question("DIAG-017", "diagnostic", "一次函数解析式", "一次函数经过点 (0,3) 和 (2,7)，它的解析式是？", ["y=x+3", "y=2x+1", "y=2x+3", "y=3x+1"], 2, "斜率是 (7-3)/(2-0)=2，截距是 3，所以 y=2x+3。", 3, 100, ["一次函数"], "analyze", weights(0.10, 0.24, 0.30, 0.24, 0.12)),
    question("DIAG-018", "diagnostic", "等腰三角形", "等腰三角形的顶角是 40°，每个底角是？", ["50°", "60°", "70°", "80°"], 2, "两个底角相等，(180-40)/2=70。", 2, 70, ["三角形"], "understand", weights(0.10, 0.30, 0.22, 0.24, 0.14)),
    question("DIAG-019", "diagnostic", "折扣问题", "某商品打 8 折后卖 80 元，原价是？", ["90 元", "96 元", "100 元", "120 元"], 2, "80%=0.8，原价为 80÷0.8=100。", 2, 90, ["百分数应用"], "analyze", weights(0.20, 0.22, 0.28, 0.18, 0.12)),
    question("DIAG-020", "diagnostic", "概率应用", "盒中有 3 个红球和 2 个蓝球，任取 1 个是蓝球的概率是？", ["2/3", "2/5", "3/5", "1/5"], 1, "总数是 5 个，蓝球 2 个，概率 2/5。", 2, 60, ["概率初步"], "apply", weights(0.10, 0.28, 0.22, 0.22, 0.18)),
    question("DIAG-021", "diagnostic", "二元一次方程组", "解方程组 x+y=5，x-y=1，则 x 等于？", ["2", "3", "4", "5"], 1, "两式相加得 2x=6，所以 x=3。", 3, 90, ["二元一次方程组"], "apply", weights(0.18, 0.28, 0.24, 0.18, 0.12)),
    question("DIAG-022", "diagnostic", "众数", "数据 1，2，2，3，9 的众数是？", ["1", "2", "3", "9"], 1, "出现次数最多的是 2。", 1, 45, ["数据统计"], "remember", weights(0.08, 0.30, 0.16, 0.24, 0.22)),
    question("DIAG-023", "diagnostic", "绝对值方程", "若 |x-2|=5，x 的取值是？", ["7", "-3", "7 或 -3", "2 或 5"], 2, "绝对值方程有两个解：x-2=5 或 x-2=-5。", 3, 100, ["绝对值"], "analyze", weights(0.14, 0.24, 0.26, 0.24, 0.12)),
    question("DIAG-024", "diagnostic", "勾股定理", "直角三角形两条直角边分别是 3 和 4，斜边长是？", ["4", "5", "6", "7"], 1, "3²+4²=5²，所以斜边长是 5。", 2, 90, ["勾股定理"], "apply", weights(0.20, 0.26, 0.20, 0.20, 0.14)),
]


def build_linear_equation_practice() -> List[Dict[str, object]]:
    rows = []
    for idx in range(12):
        a = 2 + (idx % 3)
        x = 2 + (idx % 5)
        b = 1 + (idx % 4)
        c = a * x + b
        values = [str(x - 1), str(x), str(x + 1), str(x + 2)]
        rows.append(
            question(
                f"PRAC-EQ-{idx + 1:03d}",
                "practice",
                f"方程训练 {idx + 1}",
                f"解方程：{a}x + {b} = {c}",
                values,
                1,
                f"移项并化简后得到 x={x}。",
                1 + idx // 4,
                80,
                ["一元一次方程"],
                "apply" if idx < 8 else "analyze",
                weights(0.28, 0.28, 0.22, 0.12, 0.10),
            )
        )
    return rows


def build_linear_function_practice() -> List[Dict[str, object]]:
    rows = []
    for idx in range(6):
        k = 1 + (idx % 3)
        b = 2 + idx
        x = 2 + idx
        y = k * x + b
        rows.append(
            question(
                f"PRAC-FUNC-{idx + 1:03d}",
                "practice",
                f"函数代值 {idx + 1}",
                f"若 y={k}x+{b}，当 x={x} 时，y 等于？",
                [str(y - 2), str(y - 1), str(y), str(y + 1)],
                2,
                f"把 x={x} 代入即可，得到 y={y}。",
                2,
                85,
                ["一次函数"],
                "apply",
                weights(0.18, 0.30, 0.24, 0.18, 0.10),
            )
        )
    for idx in range(6):
        k = 1 + (idx % 2)
        b = 3 + idx
        x = 2 + idx
        y = k * x + b
        rows.append(
            question(
                f"PRAC-FUNC-{idx + 7:03d}",
                "practice",
                f"函数反求 {idx + 1}",
                f"若 y={k}x+{b}，当 y={y} 时，x 等于？",
                [str(x - 1), str(x), str(x + 1), str(x + 2)],
                1,
                f"代入 y={y} 后解方程，得到 x={x}。",
                2 + idx // 3,
                95,
                ["一次函数"],
                "analyze",
                weights(0.16, 0.28, 0.30, 0.16, 0.10),
            )
        )
    return rows


def build_geometry_practice() -> List[Dict[str, object]]:
    rows = []
    angle_sets = [(35, 65), (40, 55), (25, 75), (48, 62), (30, 80), (22, 78)]
    for idx, (a1, a2) in enumerate(angle_sets, start=1):
        target = 180 - a1 - a2
        rows.append(
            question(
                f"PRAC-GEO-{idx:03d}",
                "practice",
                f"三角形角度 {idx}",
                f"三角形两个内角分别为 {a1}° 和 {a2}°，第三个角是？",
                [str(target - 10) + "°", str(target - 5) + "°", str(target) + "°", str(target + 5) + "°"],
                2,
                f"三角形内角和为 180°，所以第三个角是 {target}°。",
                2,
                75,
                ["三角形"],
                "understand",
                weights(0.08, 0.30, 0.24, 0.24, 0.14),
            )
        )
    base_pairs = [(3, 4), (5, 12), (6, 8), (8, 15), (7, 24), (9, 12)]
    for idx, (a, b) in enumerate(base_pairs, start=7):
        c = int((a * a + b * b) ** 0.5)
        rows.append(
            question(
                f"PRAC-GEO-{idx:03d}",
                "practice",
                f"勾股应用 {idx - 6}",
                f"直角三角形两条直角边长分别为 {a} 和 {b}，斜边长是？",
                [str(c - 1), str(c), str(c + 1), str(c + 2)],
                1,
                f"根据勾股定理可得斜边长为 {c}。",
                2 + (idx - 7) // 3,
                95,
                ["勾股定理"],
                "apply",
                weights(0.18, 0.26, 0.24, 0.18, 0.14),
            )
        )
    return rows


def build_statistics_probability_practice() -> List[Dict[str, object]]:
    rows = []
    data_sets = [
        [2, 3, 5, 6, 9],
        [1, 4, 4, 5, 6],
        [3, 3, 4, 7, 8],
        [2, 6, 6, 7, 9],
        [1, 2, 5, 7, 10],
        [4, 5, 5, 6, 10],
    ]
    for idx, values in enumerate(data_sets, start=1):
        avg = sum(values) / len(values)
        rows.append(
            question(
                f"PRAC-DATA-{idx:03d}",
                "practice",
                f"平均数训练 {idx}",
                f"数据 {values[0]}，{values[1]}，{values[2]}，{values[3]}，{values[4]} 的平均数是？",
                [str(avg - 0.4), str(avg), str(avg + 0.2), str(avg + 0.6)],
                1,
                f"总和除以个数，平均数为 {avg}。",
                2,
                85,
                ["数据统计"],
                "understand",
                weights(0.20, 0.28, 0.14, 0.22, 0.16),
            )
        )
    ball_sets = [(2, 3), (3, 2), (4, 1), (1, 4), (3, 5), (4, 3)]
    for idx, (blue, red) in enumerate(ball_sets, start=7):
        total = blue + red
        rows.append(
            question(
                f"PRAC-DATA-{idx:03d}",
                "practice",
                f"概率训练 {idx - 6}",
                f"盒中有 {blue} 个蓝球和 {red} 个红球，任取 1 个是蓝球的概率是？",
                [f"{blue}/{total + 1}", f"{blue}/{total}", f"{red}/{total}", f"1/{total}"],
                1,
                f"蓝球个数除以总个数，概率是 {blue}/{total}。",
                2 + (idx - 7) // 3,
                80,
                ["概率初步"],
                "apply",
                weights(0.10, 0.28, 0.26, 0.20, 0.16),
            )
        )
    return rows


def build_algebra_misc_practice() -> List[Dict[str, object]]:
    rows = []
    sci_values = [(0.00042, "4.2×10⁻⁴"), (0.0065, "6.5×10⁻³"), (0.0009, "9×10⁻⁴"), (0.054, "5.4×10⁻²"), (0.0081, "8.1×10⁻³"), (0.00072, "7.2×10⁻⁴")]
    for idx, (raw, expected) in enumerate(sci_values, start=1):
        rows.append(
            question(
                f"PRAC-ALG-{idx:03d}",
                "practice",
                f"科学记数法 {idx}",
                f"{raw} 用科学记数法表示为？",
                [expected, expected.replace("10⁻", "10⁻0"), expected.replace("×", ""), expected.replace("⁻", "")],
                0,
                f"按科学记数法规范写为 {expected}。",
                1 + idx // 3,
                60,
                ["科学记数法"],
                "understand",
                weights(0.22, 0.30, 0.14, 0.18, 0.16),
            )
        )
    factor_sets = [(25, 5), (36, 6), (49, 7), (64, 8), (81, 9), (100, 10)]
    for idx, (n, root) in enumerate(factor_sets, start=7):
        rows.append(
            question(
                f"PRAC-ALG-{idx:03d}",
                "practice",
                f"平方根与绝对值 {idx - 6}",
                f"|x-{root}|=0 时，x 的值是？",
                [str(root - 1), str(root), str(root + 1), str(n)],
                1,
                f"绝对值为 0 时，里面的式子必须等于 0，所以 x={root}。",
                2 + (idx - 7) // 3,
                75,
                ["绝对值"],
                "apply",
                weights(0.20, 0.24, 0.24, 0.18, 0.14),
            )
        )
    return rows


def all_questions() -> List[Dict[str, object]]:
    practice = []
    practice.extend(build_linear_equation_practice())
    practice.extend(build_linear_function_practice())
    practice.extend(build_geometry_practice())
    practice.extend(build_statistics_probability_practice())
    practice.extend(build_algebra_misc_practice())
    return DIAGNOSTIC_QUESTIONS + practice
