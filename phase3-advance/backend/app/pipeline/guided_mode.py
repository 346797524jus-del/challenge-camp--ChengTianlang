"""
Guided Requirement Mode - Multi-round questioning to clarify user needs before execution.
Inspired by Tongyi Qianwen's "Office Mode" (千问办公模式风格).
"""
import json
from typing import Dict, List, Optional, Any

# ═══════════════════════════════════════════
# GUIDE QUESTION DEFINITIONS
# ═══════════════════════════════════════════

PPT_QUESTIONS = [
    {
        "id": "ppt_purpose",
        "question": "这个PPT的用途是什么？",
        "options": ["📚 学术答辩", "💼 工作汇报", "🚀 产品介绍", "📖 教学课件", "📢 宣传展示", "✨ 其他（请说明）"],
        "field": "purpose",
        "detail": "选择用途后，小石头会为您匹配最合适的模板结构",
    },
    {
        "id": "ppt_style",
        "question": "您希望采用什么风格？",
        "options": ["🎓 学术严谨", "💼 商务专业", "🔮 科技未来", "🌿 清新简约", "🎨 创意活力", "🎯 自定义（请描述）"],
        "field": "style",
        "detail": "风格决定配色、字体和版式",
    },
    {
        "id": "ppt_topic",
        "question": "PPT的主题或标题是什么？",
        "options": [],  # free text
        "field": "topic",
        "detail": "请描述您的PPT主题，越具体效果越好",
    },
    {
        "id": "ppt_pages",
        "question": "大概需要多少页？",
        "options": ["📄 5-10页", "📑 10-15页", "📚 15页以上", "🤖 由你决定"],
        "field": "pages",
        "detail": "页数影响内容深度和结构",
    },
    {
        "id": "ppt_color_logo",
        "question": "是否有特殊的配色偏好或Logo要求？",
        "options": ["⏭️ 跳过/无特殊要求"],
        "field": "color_logo",
        "detail": "可直接回复颜色代码（如#1A3A5C）或上传Logo",
    },
    {
        "id": "ppt_chart",
        "question": "需要包含数据图表吗？",
        "options": ["📊 需要图表", "⏭️ 不需要", "📈 需要，我有数据（请粘贴）"],
        "field": "chart_needed",
        "detail": "如果需要图表，可提供数据让AI自动生成",
    },
]

WORD_QUESTIONS = [
    {
        "id": "word_type",
        "question": "您需要什么类型的Word文档？",
        "options": ["📄 报告", "📝 论文", "📋 简历", "📜 合同", "📖 说明书", "✨ 其他"],
        "field": "doc_type",
    },
    {
        "id": "word_style",
        "question": "文档风格偏好？",
        "options": ["🎓 学术严谨", "💼 商务专业", "🌿 简约清新", "🎨 创意个性"],
        "field": "style",
    },
    {
        "id": "word_topic",
        "question": "请描述文档标题与核心内容",
        "options": [],
        "field": "topic",
    },
    {
        "id": "word_cover",
        "question": "是否需要封面和目录？",
        "options": ["✅ 需要封面+目录", "❌ 不需要，直接正文"],
        "field": "cover_toc",
    },
]

EXCEL_QUESTIONS = [
    {
        "id": "excel_purpose",
        "question": "表格的主要用途是什么？",
        "options": ["📊 数据统计", "💰 财务报表", "📅 日程安排", "✅ 任务清单", "✨ 其他"],
        "field": "purpose",
    },
    {
        "id": "excel_columns",
        "question": "需要哪些列/字段？",
        "options": ["⏭️ 由你推荐合适的列"],
        "field": "columns",
    },
    {
        "id": "excel_chart",
        "question": "是否需要生成图表？",
        "options": ["📊 需要图表", "❌ 不需要"],
        "field": "chart_needed",
    },
]

GENERAL_INTRO_QUESTIONS = [
    {
        "id": "file_type",
        "question": "您需要生成什么类型的文件？",
        "options": ["📊 PPT演示文稿", "📝 Word文档", "📈 Excel表格"],
        "field": "file_type",
        "detail": "选择文件类型后，小石头会针对性地了解您的需求",
    },
]


class GuideState:
    """Tracks the progress of a guided requirement session."""

    STEPS_KEY = "guide_state"

    def __init__(self, file_type: str = ""):
        self.file_type = file_type
        self.current_step = 0
        self.total_steps = 0
        self.questions: List[Dict] = []
        self.answers: Dict[str, str] = {}
        self.status = "active"  # active, confirming, executing, completed, cancelled
        self.confirmed = False

    def init_questions(self, file_type: str):
        """Initialize question list based on file type."""
        self.file_type = file_type
        if file_type == "ppt":
            self.questions = PPT_QUESTIONS
        elif file_type == "word":
            self.questions = WORD_QUESTIONS
        elif file_type == "excel":
            self.questions = EXCEL_QUESTIONS
        self.total_steps = len(self.questions)
        self.current_step = 0

    def get_current_question(self) -> Optional[Dict]:
        """Get the current unanswered question."""
        if self.current_step >= len(self.questions):
            return None
        return self.questions[self.current_step]

    def record_answer(self, answer: str) -> bool:
        """Record user's answer to current question. Returns True if more questions remain."""
        q = self.get_current_question()
        if q:
            self.answers[q["field"]] = answer
            self.current_step += 1
        return self.current_step < len(self.questions)

    def build_summary(self) -> str:
        """Build a confirmation summary from collected answers."""
        ft = self.file_type.upper()
        purpose = self.answers.get("purpose", self.answers.get("doc_type", ""))
        style = self.answers.get("style", "")
        topic = self.answers.get("topic", "")
        pages = self.answers.get("pages", "")

        parts = [f"### ✅ 需求确认\n"]
        parts.append(f"- **文件类型**：{ft}")
        if purpose:
            parts.append(f"- **用途/类型**：{purpose}")
        if style:
            parts.append(f"- **风格偏好**：{style}")
        if topic:
            parts.append(f"- **主题/标题**：{topic}")
        if pages:
            parts.append(f"- **页数/规模**：{pages}")

        # Add any other collected fields
        for k, v in self.answers.items():
            if k not in ["purpose", "doc_type", "style", "topic", "pages"]:
                # Clean up option markers
                clean_v = v.replace("✅ ", "").replace("❌ ", "").replace("⏭️ ", "")
                parts.append(f"- **{k}**：{clean_v}")

        parts.append(f"\n> 💡 以上信息确认无误？回复「**开始生成**」或「**直接做吧**」即可开始。如需修改，回复具体要改的内容。")
        return "\n".join(parts)

    def build_generation_message(self) -> str:
        """Build a complete generation instruction from collected answers."""
        ft = self.file_type
        topic = self.answers.get("topic", "")
        purpose = self.answers.get("purpose", self.answers.get("doc_type", ""))
        style = self.answers.get("style", "")
        pages = self.answers.get("pages", "")

        # Clean helper markers from answers
        def clean(v):
            if not v:
                return ""
            for marker in ["🎓 ", "💼 ", "🔮 ", "🌿 ", "🎨 ", "🎯 ",
                            "📊 ", "📝 ", "📋 ", "📜 ", "📖 ", "📄 ", "📑 ", "📚 ",
                            "🚀 ", "📢 ", "📈 ", "💰 ", "📅 ", "✅ ",
                            "🤖 ", "⏭️ ", "❌ ", "📎 ", "✨ ", "💡 "]:
                v = v.replace(marker, "")
            return v.strip()

        topic = clean(topic)
        purpose = clean(purpose)
        style = clean(style)

        parts = []
        if topic:
            parts.append(topic)
        if purpose:
            parts.append(f"{purpose}")
        if style:
            parts.append(f"{style}风格")
        if pages:
            parts.append(f"{clean(pages)}页")

        combined = " ".join(parts) if parts else "通用文档"
        return f"生成{combined}的{ft.upper()}"

    def to_dict(self) -> Dict:
        return {
            "file_type": self.file_type,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "answers": self.answers,
            "status": self.status,
            "confirmed": self.confirmed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "GuideState":
        try:
            data = json.loads(json_str)
            gs = cls(file_type=data.get("file_type", ""))
            gs.current_step = data.get("current_step", 0)
            gs.total_steps = data.get("total_steps", 0)
            gs.answers = data.get("answers", {})
            gs.status = data.get("status", "active")
            gs.confirmed = data.get("confirmed", False)
            # Rebuild questions list
            if gs.file_type == "ppt":
                gs.questions = PPT_QUESTIONS
            elif gs.file_type == "word":
                gs.questions = WORD_QUESTIONS
            elif gs.file_type == "excel":
                gs.questions = EXCEL_QUESTIONS
            return gs
        except:
            return cls()


def detect_guide_trigger(message: str) -> Optional[str]:
    """
    Detect if the user's message indicates a file creation task that should trigger guided mode.
    Returns the file_type if detected, or None.
    """
    m = message.lower()
    # Check for file creation intent
    has_create_action = any(k in m for k in ["做", "生成", "制作", "创建", "写", "帮我", "搞"])
    if not has_create_action:
        return None

    # Check for specific file types
    has_ppt = any(k in m for k in ["ppt", "演示文稿", "幻灯片"])
    has_word = any(k in m for k in ["word", "文档", "doc", "报告", "简历", "论文", "合同"])
    has_excel = any(k in m for k in ["excel", "表格", "电子表格"])

    if has_ppt:
        return "ppt"
    if has_excel and not has_word:
        return "excel"
    if has_word:
        return "word"

    # Generic "make me a document" - need to ask
    if any(k in m for k in ["文件", "文档", "ppt", "演示", "表格"]) and has_create_action:
        return "unknown"

    return None