"""
Layer 1: Input Understanding Layer  
Analyzes user input + conversation history to determine intent and context.
"""
import json, re
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from loguru import logger
from openai import OpenAI
from app.config import get_settings


class UserIntent(BaseModel):
    primary_intent: str = "chat"
    sub_intents: List[str] = []
    entities: Dict[str, Any] = {}  # relaxed to Any to survive LLM format variations; sanitized downstream
    target_file_types: List[str] = []
    requires_search: bool = False
    requires_file_processing: bool = False
    requires_deep_thinking: bool = False
    tone_hint: str = ""
    complexity: str = "simple"
    raw_message: str = ""
    ppt_purpose: str = ""  # defense, product_intro, teaching, report, general


class SubTask(BaseModel):
    task_id: str
    description: str
    module: str
    dependencies: List[str] = []
    status: str = "pending"


class InputUnderstandingLayer:
    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._client = None
        self.model = settings.ai_model_name
        # Context memory for continuity
        self._session_cache: Dict[str, Dict[str, str]] = {}

    @property
    def client(self):
        if self._client is None:
            api_key = self._settings.ai_api_key
            if not api_key or api_key == "sk-placeholder":
                logger.error("❌ [Layer 1] AI_API_KEY is empty or placeholder! Check .env or config.py")
                api_key = "sk-placeholder"
            self._client = OpenAI(
                base_url=self._settings.ai_api_base_url,
                api_key=api_key,
                timeout=20.0,
                max_retries=1,
            )
        return self._client

    def analyze(self, message: str, deep_thinking: bool = False,
                conversation_context: str = "") -> UserIntent:
        logger.info(f"[Layer 1] Analyzing: {message[:100]}...")

        quick_intent = self._quick_classify(message)
        llm_intent = self._llm_analyze(message)

        # FORCE ROUTING: hardware-level guarantee - quick_classify ALWAYS wins for file ops
        logger.info(f"[Layer 1] quick={quick_intent}, llm={llm_intent.get('primary_intent','?')}")
        if quick_intent != "chat":
            primary = quick_intent
            logger.info(f"[Layer 1] Quick classify overrides LLM: {quick_intent} > {llm_intent.get('primary_intent','')}")
        else:
            primary = llm_intent.get("primary_intent", "chat")
            # Double-check: if LLM says "chat" but message clearly asks for file generation, override
            if primary == "chat":
                forced = self._force_detect(message)
                if forced:
                    primary = forced
                    logger.info(f"[Layer 1] FORCE ROUTED to {primary} (overriding LLM)")
        # Sanitize entities deeply: LLM returns unpredictable nested types
        raw_entities = llm_intent.get("entities", {})
        entities = {}
        if isinstance(raw_entities, dict):
            for k, v in raw_entities.items():
                if isinstance(v, list):
                    entities[str(k)] = ", ".join(str(x) for x in v)  # flatten lists
                elif isinstance(v, (str, int, float, bool)):
                    entities[str(k)] = str(v)
                else:
                    entities[str(k)] = str(v)[:200]
        elif isinstance(raw_entities, list):
            # LLM returned a list for entities field
            pass  # leave empty

        # Detect PPT purpose
        ppt_purpose = ""
        if "ppt" in primary:
            ppt_purpose = llm_intent.get("ppt_purpose", self._detect_ppt_purpose(message, conversation_context))

        return UserIntent(
            primary_intent=primary,
            sub_intents=llm_intent.get("sub_intents", []),
            entities=entities,
            target_file_types=llm_intent.get("target_file_types", []),
            requires_search=llm_intent.get("requires_search", False),
            requires_file_processing=llm_intent.get("requires_file_processing", False),
            requires_deep_thinking=deep_thinking,
            tone_hint=llm_intent.get("tone_hint", "friendly"),
            complexity=llm_intent.get("complexity", "simple"),
            raw_message=message,
            ppt_purpose=ppt_purpose,
        )

    def decompose_for_deep_thinking(self, message, intent) -> List[SubTask]:
        logger.info("[Layer 1] Decomposing...")
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"user","content":f"Decompose: {message} → JSON [{task_id,description,module,dependencies}] only."}],
                temperature=0.3, max_tokens=1000,
            )
            c = resp.choices[0].message.content
            js = c.find("["); je = c.rfind("]")+1
            if js>=0 and je>js:
                return [SubTask(task_id=t["task_id"],description=t["description"],module=t.get("module","general"),dependencies=t.get("dependencies",[])) for t in json.loads(c[js:je])]
        except: pass
        return self._fallback_decompose(intent)

    def _force_detect(self, message: str) -> str:
        """Hard override: if message contains file-generation keywords + format, force the correct intent.
        This runs after both quick and LLM classify, as the ultimate safety net."""
        m = message.lower()
        # Pattern: "换成/改成 + format"
        if any(k in m for k in ["换成","改成","转成","转化为","变成","转为","改成","换为"]):
            if any(k in m for k in ["ppt","演示文稿","幻灯片"]):
                return "create_document_ppt"
            if any(k in m for k in ["word","文档","doc"]):
                return "create_document_word"
            if any(k in m for k in ["excel","表格","电子表格"]):
                return "create_document_excel"
        # Pattern: "生成/制作 + (format|自我介绍) + ppt"
        if any(k in m for k in ["生成","制作","创建","做","写","帮我","帮我做","帮我生成","帮我写","帮我搞"]):
            if any(k in m for k in ["ppt","演示文稿","幻灯片"]):
                return "create_document_ppt"
            if any(k in m for k in ["word","文档","doc"]):
                return "create_document_word"
            if any(k in m for k in ["excel","表格","电子表格"]):
                return "create_document_excel"
            # "生成自我介绍" without format specifier → Word
            if any(k in m for k in ["自我介绍","介绍自己"]):
                return "create_self_intro"
        # Pattern: "ppt格式" or "用ppt" or "以ppt形式"
        if any(k in m for k in ["ppt格式","用ppt","以ppt","ppt形式","ppt版"]):
            return "create_document_ppt"
        if any(k in m for k in ["word格式","用word","以word","word形式","word版"]):
            return "create_document_word"
        if any(k in m for k in ["excel格式","用excel","以excel","excel形式","excel版"]):
            return "create_document_excel"
        return ""

    def _quick_classify(self, message: str) -> str:
        m = message.lower()
        # HIGHEST PRIORITY: format conversion patterns ("换成PPT")
        if any(k in m for k in ["换成","改成","转成","转化为","变成","转为","改为","换为"]):
            if any(k in m for k in ["ppt","演示文稿","幻灯片"]):
                return "create_document_ppt"
            if any(k in m for k in ["word","文档","doc"]):
                return "create_document_word"
            if any(k in m for k in ["excel","表格","电子表格"]):
                return "create_document_excel"
        # Document generation + format
        if any(k in m for k in ["生成","创建","制作","写一","做一个","转成","转换成","改成","变为","转化成","换成","做","写"]):
            if any(k in m for k in ["ppt","演示文稿","幻灯片","presentation"]):
                return "create_document_ppt"
            if any(k in m for k in ["excel","表格","电子表格","xlsx"]):
                return "create_document_excel"
            if any(k in m for k in ["word","文档","doc","docx","报告","简历","论文","合同","说明书","信函","总结"]):
                return "create_document_word"
            # Self-intro + generation verb → Word format
            if any(k in m for k in ["自我介绍","介绍自己","是谁","你是谁"]):
                return "create_self_intro"
        # Format-specifier without generation verb ("ppt格式", "用ppt")
        if any(k in m for k in ["ppt格式","用ppt","以ppt","ppt形式","ppt版"]):
            return "create_document_ppt"
        if any(k in m for k in ["word格式","用word","以word","word形式","word版"]):
            return "create_document_word"
        if any(k in m for k in ["excel格式","用excel","以excel","excel形式","excel版"]):
            return "create_document_excel"
        # Standalone self-intro
        if any(k in m for k in ["自我介绍","介绍自己","你是谁","你的自我介绍"]):
            return "create_self_intro"
        # File operations
        if any(k in m for k in ["上传","文件","处理","清洗","分析数据"]):
            return "file_process"
        # Search
        if any(k in m for k in ["搜索","查找","查一下","天气","新闻","最新"]):
            return "web_search"
        if any(k in m for k in ["分析","总结","摘要","概括"]):
            return "analyze"
        return "chat"

    def _detect_ppt_purpose(self, message: str, context: str = "") -> str:
        """Detect PPT purpose from keywords."""
        combined = (message + " " + context).lower()
        if any(k in combined for k in ["答辩","毕业","论文","学位"]): return "defense"
        if any(k in combined for k in ["产品","介绍","发布","新品"]): return "product_intro"
        if any(k in combined for k in ["教学","课件","课程","培训","学习"]): return "teaching"
        if any(k in combined for k in ["工作","汇报","周报","月报","季度","年度","总结"]): return "report"
        if any(k in combined for k in ["宣传","推广","营销","广告"]): return "promotion"
        if any(k in combined for k in ["简历","自我介绍","个人介绍"]): return "personal_intro"
        return "general"

    def _llm_analyze(self, message: str) -> dict:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role":"system","content":"Return JSON: {primary_intent,sub_intents,entities,target_file_types,requires_search,requires_file_processing,tone_hint,complexity,ppt_purpose}"},
                          {"role":"user","content":message}],
                temperature=0.1, max_tokens=500,
            )
            c = resp.choices[0].message.content
            js = c.find("{"); je = c.rfind("}")+1
            if js>=0 and je>js: return json.loads(c[js:je])
        except: pass
        return {"primary_intent":"chat","complexity":"simple"}

    def _fallback_decompose(self, intent):
        tasks = []
        if intent.requires_search: tasks.append(SubTask(task_id="search_1",description="搜索信息",module="search"))
        tasks.append(SubTask(task_id="generate_1",description="生成回复",module="generation",dependencies=[t.task_id for t in tasks]))
        return tasks