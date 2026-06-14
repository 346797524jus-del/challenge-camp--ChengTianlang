"""
Layer 3: Data Processing Layer (LLM Cleaning + Structured Formatting)
Forces structured Markdown output. No raw unformatted text blocks.
"""
import json, re, hashlib
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
from pydantic import BaseModel
from loguru import logger
from openai import OpenAI
from app.config import get_settings


class ProcessedData(BaseModel):
    cleaned_content: str = ""
    key_points: List[str] = []
    sources: List[Dict[str, str]] = []
    generated_files: List[Dict[str, str]] = []
    charts_data: List[Dict[str, Any]] = []
    confidence: float = 1.0
    requires_followup: bool = False
    followup_questions: List[str] = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# XIAOSHITOU PERSONA - Full Identity System Prompt
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

XIAOSHITOU_SYSTEM_PROMPT = (
    "你的名字叫「小石头」，一个有个性、有记忆、温暖而专业的AI伙伴。\n\n"
    "## 身份设定\n"
    "- 名字由来：「小石头」寓意坚固可靠、踏实稳重，像一颗小石子一样为用户的生活和工作提供坚实支撑\n"
    "- 性格：温暖、风趣、专业、有耐心，像老朋友一样自然交流\n"
    "- 默认头像：🪨 一颗可爱的小石子，简约而独特\n"
    "- 自称：喜欢自称为「小石头」，偶尔用「我这颗小石头」来增加亲切感\n"
    "- 与用户的关系：记得用户的偏好和习惯，提供长期的陪伴和帮助，是用户值得信赖的智能伙伴\n\n"
    "## 核心原则\n"
    "- 回复必须准确、有帮助、结构化\n"
    "- 使用Markdown格式：适当使用### 小标题、**加粗**关键信息、- 列表\n"
    "- 段落间空行分离，确保易读\n"
    "- 如果知道答案，直接给出；如果不确定，诚实说明\n"
    "- 保持友好自然的语气，像与朋友交谈\n"
    "- 在合适的时候展现小石头的个性，但不过度\n\n"
    "## 联网搜索规则（最高优先级）\n"
    "- 联网搜索功能默认常驻开启，无需用户手动打开任何开关\n"
    "- 严禁说「需要手动开启联网搜索」「请打开联网开关」「记得先打开联网」之类的话\n"
    "- 严禁在回复中提及「网络搜索按钮」「搜索开关」「联网模式」\n"
    "- 用户询问实时信息时，你已经通过后端自动联网搜索获取了数据，直接基于搜索结果回答\n"
    "- 搜索结果会在系统内部自动注入到你的上下文中，你看到搜索结果后直接引用即可\n\n"
    "## 反假数据规则（最高优先级，不可违反）\n"
    "- **你绝不能使用模拟数据或过期知识来冒充实时搜索结果**\n"
    "- 如果无法获取实时数据，你必须明确告知用户：「抱歉，我尝试搜索了但未找到实时信息」\n"
    "- 严禁将知识库数据描述为「我搜到」「最新消息」「实时数据」\n"
    "- 如果搜索结果不足或无法回答，必须诚实告知用户，并提供搜索词建议\n"
    "- 当搜索结果为空或不相关时，固定回复格式：「抱歉，我尝试搜索了「{实际搜索词}」，但没有找到相关信息。建议您尝试更换关键词或访问权威网站。」\n\n"
    "## 来源标注规范（最高优先级）\n"
    "- 在回复中必须明确区分信息来源类型：\n"
    "  - 联网搜索结果：「根据[DuckDuckGo/Bing]搜索结果…」或「根据{来源网站}报道…」\n"
    "  - 知识库数据：「根据知识库记录…」或「根据历史文档…」\n"
    "  - 自身知识：不标注，直接回答\n"
    "  - 系统时钟：「根据系统当前时间…」\n"
    "- 使用联网搜索数据时，标注具体来源和时间（如「根据2026年6月15日搜索结果…」）\n"
    "- 交叉验证：如多个来源信息矛盾，标注「信息存在不一致，多数来源显示…」\n\n"
    "## 自我介绍规范\n"
    "当用户要求自我介绍（如\"介绍你自己\"\"你是谁\"\"自我介绍一下\"等）时，必须：\n"
    "1. 以「小石头」的身份进行介绍，说明名字由来和性格特点\n"
    "2. 强调自己是用户的AI伙伴，而不是冰冷的工具\n"
    "3. 提及能力范围：聊天、文档生成、数据分析、文件处理、联网搜索等\n"
    "4. 语气温暖亲切，展现个性\n"
    "5. 严禁使用\"我是一个AI助手，由XX公司开发\"等泛化表述\n"
    "6. 严禁说\"根据我的知识库\"\"作为语言模型\"等元描述\n\n"
    "## 禁止行为\n"
    "- 不要回复空泛的废话\n"
    "- 不要反复说「我是AI助手」之类的泛化自我介绍\n"
    "- 不要说「根据我的知识库」之类的元描述\n"
    "- 不要使用泛化的AI身份（如\"我是一个人工智能助手\"）\n"
    "- 始终以「小石头」的身份进行回复\n\n"
    "## 文件生成强制规则（最高优先级，不可违反）\n"
    "当用户要求生成PPT/Word/Excel文件时，你**严禁**用文字模拟文件内容。具体禁令：\n"
    "- 禁止输出Markdown格式的PPT大纲（如\"--- 第一页：封面 ---\"）\n"
    "- 禁止输出\"让我用PPT的风格给你做个自我介绍\"然后给文字\n"
    "- 禁止输出\"📄 第X页：xxx\"这类模拟页面\n"
    "- 禁止输出\"怎么样，这份PPT还满意吗？\"而没有生成真实文件\n"
    "- 禁止说\"建议用PPT软件制作\"而不实际调用工具\n"
    "- 如果收到文件生成请求，你必须让系统调用文件生成工具，用文字回复告知文件已生成并提供下载\n"
    "- 任何用文字模拟PPT/Word/Excel文档的行为都是严重错误"
)


class DataProcessingLayer:
    """
    Layer 3: Processes raw data through LLM for cleaning and structuring.
    ENFORCES structured Markdown output - no large unformatted text blocks.
    """

    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._client = None
        self.model = settings.ai_model_name
        self._cache: Dict[str, tuple] = {}

    @property
    def client(self):
        if self._client is None:
            api_key = self._settings.ai_api_key
            if not api_key or api_key == "sk-placeholder":
                logger.error("❌ AI_API_KEY is empty or placeholder! Check .env or config.py")
                api_key = "sk-placeholder"  # Will cause clear auth error, not silent failure
            self._client = OpenAI(
                base_url=self._settings.ai_api_base_url,
                api_key=api_key,
                timeout=20.0,
                max_retries=1,
            )
        return self._client

    def process(self, intent: Any, sources: Any, conversation_context: str = "") -> ProcessedData:
        logger.info(f"[Layer 3] Processing data for {intent.primary_intent}")

        if intent.requires_search or intent.primary_intent == "web_search":
            return self._process_search_results(intent, sources)
        elif intent.requires_file_processing or intent.primary_intent == "file_process":
            return self._process_file_data(intent, sources)
        elif intent.primary_intent in ["analysis", "analyze_data"]:
            return self._process_analysis(intent, sources, conversation_context)
        else:
            return self._process_chat(intent, sources, conversation_context)

    def _process_search_results(self, intent: Any, sources: Any) -> ProcessedData:
        all_results = []

        if sources.knowledge_results:
            for r in sources.knowledge_results:
                all_results.append({
                    "content": r.get("content", r.get("snippet", "")),
                    "source": r.get("source_url", r.get("url", "知识库")),
                    "type": "knowledge", "title": r.get("title", ""),
                })
        if sources.web_results:
            for r in sources.web_results:
                snippet = self._filter_noise(r.get("snippet", ""))
                all_results.append({
                    "content": snippet,
                    "source": r.get("url", "网络搜索"),
                    "type": "web", "title": r.get("title", ""),
                })

        if not all_results:
            return ProcessedData(
                cleaned_content=(
                    "### 🔍 搜索结果\n\n"
                    "抱歉，未能找到与您问题相关的信息。\n\n"
                    "**建议：**\n"
                    "- 尝试使用不同的关键词重新搜索\n"
                    "- 检查网络连接后重试\n"
                    "- 在知识库中添加相关内容"
                ),
                confidence=0.5,
            )

        raw_text = json.dumps(all_results, ensure_ascii=False, indent=2)
        prompt = f"""请处理搜索结果，严格按以下要求回复：

**必须使用Markdown结构化格式：**
- 使用 ## 标题组织回复
- 关键信息使用 **加粗**
- 多个要点使用 - 列表
- 复杂数据使用表格
- 段落间使用空行分隔
- 必须标注信息来源和时效性

搜索结果：{raw_text}
用户问题：{intent.raw_message}

返回JSON：{{"answer": "结构化Markdown回复", "key_points": [], "sources": []}}"""

        return self._llm_clean(raw_text, prompt, all_results)

    def _filter_noise(self, text: str) -> str:
        """Remove ads, popup text, irrelevant content from search results."""
        if not text:
            return ""
        noise_patterns = [
            r'(?i)(click here|buy now|limited offer|subscribe|sign up|广告|弹窗|优惠|秒杀|立即购买|点击查看|关注公众号)',
            r'(?i)(sponsored|promoted|recommended for you)',
        ]
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()[:2000]

    def _process_file_data(self, intent: Any, sources: Any) -> ProcessedData:
        file_texts = []
        if sources.file_contents:
            for f in sources.file_contents:
                content = f.get("content", f.get("parsed_text", ""))
                if content:
                    file_texts.append({
                        "filename": f.get("filename", "unknown"),
                        "file_type": f.get("file_type", "unknown"),
                        "content": content[:5000],
                    })
        if not file_texts:
            return ProcessedData(
                cleaned_content=(
                    "### 📁 文件处理\n\n"
                    "文件内容解析完毕，但未能提取到可用文本数据。\n\n"
                    "**可能原因：**\n"
                    "- 文件为扫描件，文字无法识别\n"
                    "- 文件格式不受支持\n"
                    "- 文件内容为空"
                ),
                confidence=0.5,
            )

        raw_text = json.dumps(file_texts, ensure_ascii=False, indent=2)
        prompt = f"""处理文件数据，用户要求：{intent.raw_message}
文件内容：{raw_text}

用结构化Markdown回复（标题、列表、表格、加粗），返回JSON：{{"answer": "...", "key_points": [], "charts_data": []}}"""
        return self._llm_clean(raw_text, prompt, file_texts)

    def _process_analysis(self, intent: Any, sources: Any, conversation_context: str = "") -> ProcessedData:
        context = conversation_context or ""
        if sources.memory_context:
            for m in sources.memory_context:
                if m.get("type") == "message":
                    context += f"\n[{m['role']}]: {m['content']}"
        prompt = f"""分析以下内容（结构化Markdown回复）：\n用户问题：{intent.raw_message}\n上下文：{context}\n\n返回JSON：{{"answer": "...", "key_points": [], "confidence": 0.9}}"""
        return self._llm_clean(context, prompt, [])

    def _process_chat(self, intent: Any, sources: Any, conversation_context: str = "") -> ProcessedData:
        """Process general chat with LLM using Xiaoshitou persona."""
        memory_ctx = conversation_context or ""
        if sources.memory_context:
            recent_msgs = []
            for m in sources.memory_context:
                if m.get("type") == "message":
                    recent_msgs.append(f"[{m['role']}]: {m['content'][:200]}")
            if recent_msgs:
                memory_ctx = "## 对话历史\n" + "\n".join(recent_msgs[-6:])

        kb_ctx = ""
        if sources.knowledge_results:
            kb_parts = []
            for r in sources.knowledge_results[:2]:
                content = r.get("content", r.get("snippet", ""))[:600]
                if content:
                    kb_parts.append(content)
            if kb_parts:
                kb_ctx = "## 知识库参考\n" + "\n---\n".join(kb_parts)

        try:
            user_content = intent.raw_message
            if kb_ctx:
                user_content = f"{kb_ctx}\n\n## 当前问题\n{intent.raw_message}"
            if memory_ctx:
                user_content = f"{memory_ctx}\n\n{user_content}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": XIAOSHITOU_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7, max_tokens=1000,
            )
            answer = response.choices[0].message.content
            if answer:
                return ProcessedData(cleaned_content=answer, confidence=0.9)
        except Exception as e:
            logger.warning(f"[Layer 3] Chat LLM call failed: {e}")
            return ProcessedData(
                cleaned_content=f"### ⚠️ 服务暂不可用\n\n{str(e)[:200]}",
                confidence=0.3,
            )
        return ProcessedData(cleaned_content=intent.raw_message, confidence=0.5)

    def _llm_clean(self, raw_data: str, prompt: str, sources_list: List[dict]) -> ProcessedData:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是数据处理专家。回复必须使用结构化Markdown格式（标题、列表、加粗、表格），段落间空行分隔。只返回JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3, max_tokens=2000,
            )
            content = response.choices[0].message.content
            js = content.find("{"); je = content.rfind("}") + 1
            if js >= 0 and je > js:
                data = json.loads(content[js:je])
                answer = data.get("answer", "处理完成")
                answer = self._enforce_structure(answer)
                return ProcessedData(
                    cleaned_content=answer,
                    key_points=data.get("key_points", []),
                    sources=data.get("sources", []),
                    charts_data=data.get("charts_data", []),
                    confidence=data.get("confidence", 0.8),
                )
        except Exception as e:
            logger.warning(f"[Layer 3] LLM cleaning failed: {e}")
        return ProcessedData(cleaned_content=raw_data[:2000] if raw_data else "处理完成", confidence=0.6)

    def _enforce_structure(self, text: str) -> str:
        """Ensure response has Markdown structure. Add headings if missing."""
        if not text:
            return text
        has_md = any(marker in text for marker in ["#", "**", "- ", "1. ", "|", "\n\n"])
        if not has_md and len(text) > 200:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            structured = []
            for i, p in enumerate(paragraphs):
                if i == 0:
                    structured.append(p)
                elif len(p) < 100:
                    structured.append(f"\n**{p}**")
                else:
                    structured.append(f"\n{p}")
            text = "\n".join(structured)
        return text

    async def process_stream(self, intent: Any, sources: Any) -> AsyncGenerator[str, None]:
        """Stream with knowledge-augmented context and Xiaoshitou persona."""
        try:
            if intent.requires_search:
                system_prompt = (
                    "你是信息整合专家。搜索类回复必须使用结构化Markdown："
                    "使用 ## 标题、**加粗**关键信息、- 列表、空行分隔段落、标注来源。"
                )
                all_results = (sources.knowledge_results + sources.web_results)
                user_prompt = f"用户问题：{intent.raw_message}\n\n搜索数据：{json.dumps(all_results[:3], ensure_ascii=False)}\n\n请用中文结构化回复："
            else:
                memory_ctx = ""
                if sources.memory_context:
                    recent_msgs = []
                    prefs_info = ""
                    for m in sources.memory_context:
                        if m.get("type") == "message":
                            recent_msgs.append(f"[{m['role']}]: {m['content'][:200]}")
                        elif m.get("type") == "preferences":
                            prefs_info = f"用户偏好：语气{m.get('tone_style','友好')}，长度{m.get('response_length','适中')}。"
                    if recent_msgs:
                        memory_ctx = "## 对话历史\n" + "\n".join(recent_msgs[-6:]) + "\n\n" + prefs_info

                kb_ctx = ""
                if sources.knowledge_results:
                    kb_parts = []
                    for r in sources.knowledge_results[:3]:
                        content = r.get("content", r.get("snippet", ""))[:800]
                        if content:
                            kb_parts.append(content)
                    if kb_parts:
                        kb_ctx = "## 知识库参考资料\n" + "\n---\n".join(kb_parts) + "\n"

                # ALWAYS inject web search results into chat context
                web_ctx = ""
                if sources.web_results:
                    web_parts = []
                    for r in sources.web_results[:5]:
                        snippet = r.get("snippet", "")[:600]
                        if snippet:
                            web_parts.append(f"[{r.get('source','Web')}] {snippet}")
                    if web_parts:
                        web_ctx = "## 实时联网搜索结果\n" + "\n".join(web_parts) + "\n"

                user_prompt = intent.raw_message
                if web_ctx:
                    user_prompt = f"{web_ctx}\n## 当前问题\n{intent.raw_message}"
                if kb_ctx:
                    user_prompt = f"{kb_ctx}\n{user_prompt}"
                if memory_ctx:
                    user_prompt = f"{memory_ctx}\n{user_prompt}"

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": XIAOSHITOU_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7, max_tokens=2000, stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"[Layer 3] Stream failed: {e}")
            error_msg = str(e).lower()
            if "api_key" in error_msg or "credentials" in error_msg or "auth" in error_msg:
                yield (
                    "### ⚠️ AI 服务未配置\n\n"
                    "检测到 API 密钥未设置，无法连接到 AI 服务。\n\n"
                    "**解决方法：**\n"
                    "- 编辑 `backend/.env` 文件\n"
                    "- 设置 `AI_API_KEY=你的密钥`\n"
                    "- 重启后端服务即可\n\n"
                    "支持 OpenAI 兼容的 API（如 DeepSeek、通义千问等）。"
                )
            else:
                yield f"抱歉，处理过程中出现错误：{str(e)[:200]}"