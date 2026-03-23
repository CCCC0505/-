# 初中数学智能学习平台

这是一个围绕“诊断建档 -> 成长画像 -> 个性训练 -> 智能分析”构建的学习平台原型。当前版本聚焦初二数学场景，用更稳定的规则建模和更透明的智能分析，帮助老师与学生快速看清当前状态、训练方向与变化轨迹。

当前版本只保留核心能力：

- 学生建档
- 6 题冷启动问卷
- 24 题诊断卷
- 五维画像建模
- 历史画像快照
- 三类推荐题
- 练习后画像更新
- AI 调用记录与规则回退

当前版本明确不做：

- 登录鉴权
- 教师端 / 管理端
- 多学校部署
- 多年级完整题库
- 模型训练或微调
- 商业化模块
- 独立情感计算系统

## 1. 技术栈

- 后端：FastAPI + SQLAlchemy + MySQL
- 前端：原生 `HTML + CSS + JavaScript`
- AI 接口：DashScope 兼容 OpenAI 协议的 Qwen

前端文件是独立拆分的：

- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`

## 2. 目录结构

```text
backend/
  app.py
  config.py
  database.py
  models.py
  schemas.py
  seed_data.py
  scripts/bootstrap_demo.py
  services/
    ai_run_service.py
    bootstrap.py
    cold_start_service.py
    common.py
    modeling.py
    portrait_service.py
    practice_service.py
    qwen_client.py
    recommendation_service.py
frontend/
  index.html
  styles.css
  app.js
tests/
  test_api.py
```

## 3. 启动方式

### 3.1 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 3.2 配置环境变量

参考 [\.env.example](/C:/Users/lenovo/Desktop/大创-rebulid/.env.example)。

默认 MySQL 配置：

```env
DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3306/grade8_ai_demo?charset=utf8mb4
```

### 3.3 初始化数据库与题库

```powershell
python -m backend.scripts.bootstrap_demo --reset
```

### 3.4 启动服务

```powershell
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### 3.5 一键启动

项目根目录提供了一个 Windows 双击启动脚本：

- [一键启动答辩系统.bat](/C:/Users/lenovo/Desktop/大创-rebulid/一键启动答辩系统.bat)

作用：

- 自动寻找可用的 Python 虚拟环境
- 启动 `uvicorn`
- 自动打开浏览器首页

默认优先使用：

1. 当前项目下的 `.\.venv\Scripts\python.exe`
2. 若不存在，则回退到旧项目虚拟环境
   `C:\Users\lenovo\Desktop\DC大创代码\.venv\Scripts\python.exe`

启动后访问：

- 首页：[http://127.0.0.1:8000](http://127.0.0.1:8000)
- API 文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 4. V1 功能闭环

完整演示链路如下：

1. 创建学生
2. 提交 6 个问卷题
3. 提交 24 道诊断题
4. 规则引擎生成首版画像
5. Qwen 输出画像摘要与教师点评
6. 保存 `V1` 画像快照
7. 基于画像生成补弱题 / 巩固题 / 提升题
8. 提交练习答案
9. 规则增量更新画像并保存 `V2 / V3...`
10. 记录 AI 成功 / 失败 / 回退状态

## 5. 题库范围

当前题库规模固定为：

- 诊断题：24
- 练习题：60
- 总题量：84

当前只开放 `初二`。

首页会展示 `初一 / 初二 / 初三` 的入口，但只有初二允许完整进入流程，其余年级用于答辩展示“后续扩展方向”。

## 6. 建模方法说明

这一部分是本项目最重要的技术说明。代码实现对应文件为 [modeling.py](/C:/Users/lenovo/Desktop/大创-rebulid/backend/services/modeling.py)。

### 6.1 五维核心画像

系统固定使用 5 个核心维度：

1. `calculation_accuracy`
   计算准确性
2. `knowledge_mastery`
   知识点掌握度
3. `logical_reasoning`
   逻辑策略
4. `cognitive_performance`
   认知层级表现
5. `learning_stability`
   学习稳定性

### 6.2 冷启动问卷的 6 个特征

问卷不会直接生成五维分数，而是先映射为学习者特征：

1. `challenge_threshold`
   挑战阈值
2. `practice_pace`
   练习节奏
3. `review_habit`
   错题复盘习惯
4. `confidence_level`
   数学自信度
5. `help_seeking`
   求助倾向
6. `learning_preference`
   学习偏好

这些特征主要用于：

- 修正 `learning_stability`
- 轻度修正 `logical_reasoning`
- 生成风险标记
- 影响教师点评语气

### 6.3 诊断题建模参数

每道诊断题都带有固定元数据：

- `difficulty`
  难度等级
- `target_duration_seconds`
  目标作答时长
- `knowledge_tags`
  知识点标签
- `cognitive_level`
  认知层级
- `dimension_weights`
  该题对五维画像的影响权重

### 6.4 难度系数

代码中的默认参数如下：

```text
DIFFICULTY_FACTORS = {
  1: 0.95,
  2: 1.00,
  3: 1.08,
  4: 1.15
}
```

含义：

- 难度越高，答对后贡献越大
- 同时也会抬高该题的满分基线

### 6.5 认知层级系数

```text
COGNITIVE_FACTORS = {
  remember: 0.94,
  understand: 1.00,
  apply: 1.06,
  analyze: 1.12
}
```

含义：

- 分析层级题在画像中权重更高
- 记忆识别层级题贡献相对更低

### 6.6 作答速度系数

基于“实际耗时 / 目标耗时”的比例计算：

- `0.7 ~ 1.3`：`1.00`
- `0.5 ~ 1.6`：`0.93`
- 其余：`0.86`

这部分主要进入：

- `learning_stability`
- 每题的总得分贡献

### 6.7 冷启动画像评分公式

对每道诊断题，先计算：

```text
base_score = correctness * difficulty_factor * cognitive_factor * speed_factor
max_base   = 1.0 * difficulty_factor * cognitive_factor
```

其中：

- `correctness = 1` 表示答对
- `correctness = 0` 表示答错

然后按题目的 `dimension_weights` 分摊到五个维度：

```text
dimension_hit += base_score * weight
dimension_max += max_base * weight
dimension_score = 100 * dimension_hit / dimension_max
```

### 6.8 问卷对画像的修正

问卷不会直接决定全部分数，只做有限修正：

- `learning_stability = 0.75 * 诊断得分 + 0.25 * stability_index`
- `logical_reasoning = 0.90 * 诊断得分 + 0.10 * strategy_index`

其中：

- `stability_index = 平均(practice_pace, review_habit, confidence_level, help_seeking)`
- `strategy_index = 平均(challenge_threshold, help_seeking, learning_preference)`

这样做的原因是：

- 保证五维画像仍以真实题目表现为主
- 又能让问卷在“学习行为风格”上发挥作用

### 6.9 知识点矩阵建模

对每个知识点标签：

```text
knowledge_score = 100 * tag_hit / tag_max
```

若得分低于 `55`，标记为 `needs_attention = true`。

### 6.10 认知层级建模

对每个认知层级：

```text
cognitive_score = 100 * level_hit / level_max
```

若得分低于 `58`，标记为 `needs_attention = true`。

### 6.11 训练重点生成规则

训练重点由两部分组成：

- 最低的 2 个维度
- 最弱的 2 个知识点

拼接后形成 `training_focus`，最多保留 4 条。

### 6.12 风险标记生成规则

当前版本会触发的风险规则包括：

- 最弱维度低于 45 分
- 薄弱知识点数量过多
- 自信度低于 50
- 错题复盘习惯低于 45

### 6.13 推荐建模参数

推荐不是随机抽题，而是对每道练习题打分后再分桶选择。

单题分数由以下部分构成：

```text
rank_score =
  0.38 * dimension_need +
  0.34 * knowledge_need +
  decline_bonus +
  difficulty_fit +
  wrong_bonus +
  novelty_bonus
```

其中：

- `dimension_need`
  该题涉及维度的当前薄弱程度
- `knowledge_need`
  该题涉及知识点的当前薄弱程度
- `decline_bonus`
  与上一版快照相比，若相关维度下降，则提高推荐权重
- `difficulty_fit`
  当前能力与题目难度是否匹配
- `wrong_bonus`
  若命中当前错题回流，则增加权重
- `novelty_bonus`
  未做过的题获得正向加成，已做过的题获得惩罚

### 6.14 三类题划分规则

根据当前薄弱程度与题目难度划分：

- `补弱题`
  当前明显薄弱或题目难度较低
- `巩固题`
  中间层，用于稳定正确率
- `提升题`
  难度更高，用于拉高迁移与上限

默认按 `requested_count` 做 1:1:1 配比。

### 6.15 练习后的增量更新

练习提交后，不会覆盖旧画像，而是生成新快照。

增量更新核心规则：

- 答对：相关维度与知识点上调
- 答错：相关维度与知识点下调
- 高难题答对：对自信度有小幅加成
- 明显超时：对练习节奏有小幅扣减

典型增量参数：

```text
delta = (答对 +8 / 答错 -6.5) * difficulty_factor * speed_factor
```

知识点默认：

- 答对 `+9`
- 答错 `-7`

认知层级默认：

- 答对 `+7`
- 答错 `-5.5`

## 7. AI 输出契约

### 7.1 冷启动画像 AI 输出

```json
{
  "portrait_summary": "string",
  "teacher_commentary": "string",
  "training_focus": ["string"],
  "risk_flags": ["string"],
  "confidence": 0.0
}
```

### 7.2 推荐解释 AI 输出

```json
{
  "overall_commentary": "string",
  "training_focus": ["string"],
  "item_reasons": [
    {
      "question_id": "string",
      "reason": "string"
    }
  ],
  "confidence": 0.0
}
```

### 7.3 练习反馈 AI 输出

```json
{
  "feedback_summary": "string",
  "mistake_analysis": ["string"],
  "next_steps": ["string"],
  "confidence": 0.0
}
```

## 8. AI 回退策略

V1 的 AI 设计不是“全成全败”，而是“能用多少用多少”。

流程固定为：

1. 请求 Qwen
2. 提取 JSON
3. 做宽容归一化
4. 用本地 fallback 填补缺失字段
5. 无论成功还是失败，都记录 `ai_analysis_runs`

当没有配置 `DASHSCOPE_API_KEY` 时：

- 系统仍然能完整运行
- 画像、推荐、练习反馈都走规则回退
- 前端会明确显示“规则回退”，不会静默假装 AI 成功

## 9. API 概览

核心接口如下：

- `GET /api/meta/grades`
- `GET /api/meta/ai-status`
- `GET /api/system/question-bank/stats`
- `POST /api/cold-start/sessions`
- `POST /api/cold-start/{session_id}/questionnaire`
- `POST /api/cold-start/{session_id}/diagnostic/submit`
- `POST /api/cold-start/{session_id}/finalize`
- `GET /api/students/{student_id}/dashboard`
- `GET /api/students/{student_id}/portrait/latest`
- `GET /api/students/{student_id}/portrait/history`
- `GET /api/students/{student_id}/wrong-questions`
- `POST /api/practice/recommendations`
- `POST /api/practice/answers`
- `GET /api/students/{student_id}/ai-runs`

## 10. 测试

运行测试：

```powershell
python -m pytest -q
```

当前测试重点覆盖：

- 题库初始化数量
- 冷启动闭环
- 画像快照生成
- 推荐三分组
- 练习后新快照生成
- AI 未配置时的规则回退链路

## 11. 当前版本的取舍说明

这次重写刻意做了两个取舍：

1. 不沿用旧 UI，也不沿用旧的单文件前端结构
   这次前端拆成独立的 `HTML / CSS / JS`，页面结构更适合继续维护。
2. 不保留旧框架里的大而全表层
   只保留“冷启动、画像、推荐、练习、AI 记录”这些真正影响演示价值的核心能力。

如果后续继续扩展，建议优先做：

- 初一 / 初三题库
- 教师端观察页
- 更细粒度的知识追踪
- 更稳的 Qwen 提示词与归一化策略
