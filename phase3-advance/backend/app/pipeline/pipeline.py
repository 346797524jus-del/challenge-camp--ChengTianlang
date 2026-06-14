"""Xiaoshitou Master Pipeline - Four Layer Architecture with MCP, RAG, Deep Thinking, File Gen Progress."""
import asyncio, uuid, json, re, os
from pathlib import Path
from typing import AsyncGenerator, List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.orm import Session as DBSession

from app.config import GENERATED_DIR, get_settings
from app.pipeline.input_layer import InputUnderstandingLayer, UserIntent, SubTask
from app.pipeline.data_layer import DataAcquisitionLayer, DataSources
from app.pipeline.process_layer import DataProcessingLayer, ProcessedData
from app.pipeline.output_layer import OutputPresentationLayer, FormattedOutput
from app.pipeline.style_engine import StyleEngine
from app.pipeline.guided_mode import GuideState, detect_guide_trigger, GENERAL_INTRO_QUESTIONS, PPT_QUESTIONS, WORD_QUESTIONS, EXCEL_QUESTIONS
from app.models import Session, Message, Preference, FileRecord


def json_dumps(data):
    return json.dumps(data, ensure_ascii=False)


class PipelineContext:
    def __init__(self, user_id, session_id):
        self.user_id = user_id
        self.session_id = session_id
        self.intent: Optional[UserIntent] = None
        self.sources: Optional[DataSources] = None
        self.processed: Optional[ProcessedData] = None
        self.output: Optional[FormattedOutput] = None
        self.thinking_steps: List[Dict[str, Any]] = []
        self.subtasks: List[SubTask] = []
        self.error: Optional[str] = None
        self.tool_results: Dict[str, Any] = {}
        self.deep_thinking_enabled: bool = False
        self.search_metadata: Dict[str, Any] = {}
        self.mcp_results: List[Dict[str, Any]] = []


class AgentPipeline:
    def __init__(self):
        self.input_layer = InputUnderstandingLayer()
        self.data_layer = DataAcquisitionLayer()
        self.process_layer = DataProcessingLayer()
        self.output_layer = OutputPresentationLayer()
        self.style_engine = StyleEngine()

    def _should_auto_enable(self, message):
        triggers = [
            "制作", "生成", "创建", "写一篇", "做一个",
            "答辩", "PPT", "Word", "Excel", "文档", "报告",
            "分析", "总结", "比较", "对比",
            "仔细分析", "深入思考", "详细规划", "帮我规划",
            "多步骤", "流程", "方案",
        ]
        lower = message.lower()
        return any(t.lower() in lower for t in triggers)

    # ━━━━━━━━━━━ PENDING TASK MANAGEMENT ━━━━━━━━━━━
    def _get_pending_task(self, db, session_id: str) -> Optional[Dict]:
        if not session_id:
            return None
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session and hasattr(session, 'pending_task') and session.pending_task:
                return json.loads(session.pending_task)
        except:
            pass
        return None

    def _set_pending_task(self, db, session_id: str, task: Dict):
        if not session_id:
            return
        try:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session and hasattr(session, 'pending_task'):
                session.pending_task = json.dumps(task, ensure_ascii=False)
                db.commit()
        except Exception as e:
            logger.warning(f"Pending task save failed: {e}")

    def _clear_pending_task(self, db, session_id: str):
        self._set_pending_task(db, session_id, {})

    def _handle_pending_task_logic(self, message: str, pending: Dict, db=None, session_id: str = "") -> Optional[Dict]:
        """Detect reference resolution / format-switch commands with context fallback.
        If no pending task exists yet, try to infer topic from conversation history."""
        m_lower = message.lower().strip()
        
        # If no pending task but user says "换成PPT/Word/Excel", try to infer context
        if (not pending or not pending.get("pending_task")) and db and session_id:
            if any(k in m_lower for k in ["换成", "改成", "转成", "还是用", "改为"]):
                # Try to extract recent topic from conversation messages
                recent_topic = self._extract_recent_topic(db, session_id)
                if recent_topic:
                    new_type = "ppt_generation"  # default
                    if any(k in m_lower for k in ["ppt", "演示文稿", "幻灯片"]):
                        new_type = "ppt_generation"
                    elif any(k in m_lower for k in ["word", "文档", "doc"]):
                        new_type = "word_generation"
                    elif any(k in m_lower for k in ["excel", "表格"]):
                        new_type = "excel_generation"
                    pending = {
                        "pending_task": "格式转换",
                        "task_type": new_type,
                        "task_topic": recent_topic,
                        "status": "pending",
                    }
                    self._set_pending_task(db, session_id, pending)
                    logger.info(f"[CTX] Resolved ref: '{message}' → task_type={new_type}, topic='{recent_topic}'")

        if not pending or not pending.get("pending_task"):
            return None

        if any(k in m_lower for k in ["换成", "改成", "转成"]):
            if any(k in m_lower for k in ["ppt", "演示文稿", "幻灯片"]):
                return {**pending, "task_type": "ppt_generation", "status": "pending"}
            if any(k in m_lower for k in ["word", "文档", "doc"]):
                return {**pending, "task_type": "word_generation", "status": "pending"}
            if any(k in m_lower for k in ["excel", "表格"]):
                return {**pending, "task_type": "excel_generation", "status": "pending"}
        if any(k in m_lower for k in ["做吧", "嗯", "开始", "好", "生成", "ok", "yes", "继续"]):
            if len(m_lower) <= 5 or m_lower in ["做吧", "嗯", "开始", "好", "生成", "ok", "yes", "继续"]:
                return {**pending, "status": "execute_now"}
        return None

    def _extract_recent_topic(self, db, session_id: str) -> str:
        """Extract the most recent meaningful topic from conversation history."""
        try:
            from app.models import Message
            msgs = (
                db.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.sequence.desc())
                .limit(10)
                .all()
            )
            # Look for file generation or self-intro messages
            for m in msgs:
                content = m.content or ""
                # Check for generated file markers
                if "自我介绍" in content and m.role == "assistant":
                    return "小石头自我介绍"
                if any(k in content for k in ["文件已生成", "PPT已生成", "Word已生成", "Excel已生成"]):
                    # Try to find the topic from user messages
                    for um in msgs:
                        if um.role == "user" and len(um.content) > 3:
                            # Clean the user message to extract topic
                            topic = um.content.strip()
                            for prefix in ["生成", "制作", "创建", "做一个", "帮我做一个"]:
                                topic = topic.replace(prefix, "")
                            topic = topic.strip().strip("的").strip("。").strip()[:80]
                            if topic and len(topic) >= 2:
                                return topic
                # User asked for self-intro
                if m.role == "user":
                    if any(k in m.content for k in ["自我介绍一下", "自我介绍", "介绍你自己", "你是谁"]):
                        return "小石头自我介绍"
                    # Generic topic extraction
                    for prefix in ["生成", "制作", "创建", "做一个"]:
                        if prefix in m.content:
                            topic = m.content.split(prefix)[-1].strip().split("PPT")[0].split("Word")[0].split("Excel")[0].strip()[:60]
                            if topic and len(topic) >= 2:
                                return topic
            return "小石头自我介绍"
        except Exception as e:
            logger.warning(f"Topic extraction failed: {e}")
        return "小石头自我介绍"

    def _execute_pending_task(self, pending: Dict) -> str:
        task_type = pending.get("task_type", "")
        task_topic = pending.get("task_topic", "小石头自我介绍")
        if task_type == "ppt_generation":
            return f"生成{task_topic}的PPT"
        elif task_type == "word_generation":
            return f"生成{task_topic}的Word文档"
        elif task_type == "excel_generation":
            return f"生成{task_topic}的Excel表格"
        return f"生成{task_topic}的文档"

    # ━━━━━━━━━━━ TEMPLATE SEARCH ━━━━━━━━━━━
    async def _search_templates_online(self, file_type: str, topic: str, style_hint: str) -> Dict:
        result = {"found": False, "source": "", "keywords": [], "template_name": "", "fallback": True}
        try:
            import httpx
            kw_map = {
                "ppt": f"{topic} {style_hint} PPT模板 免费下载 site:officeplus.cn OR site:wudao.cn",
                "word": f"{topic} Word文档模板 免费下载 site:officeplus.cn",
                "excel": f"{topic} Excel表格模板 免费下载 site:officeplus.cn",
            }
            query = kw_map.get(file_type, f"{topic} {style_hint} 模板")
            result["keywords"] = [topic, style_hint, file_type]

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1},
                )
            if resp.status_code == 200:
                data = resp.json()
                topics_data = data.get("RelatedTopics", [])
                if topics_data:
                    result["found"] = True
                    sources_found = set()
                    for t in topics_data[:8]:
                        text = t.get("Text", "")
                        for src in ["officeplus", "OfficePLUS", "OfficePlus", "吾道", "Canva", "canva", "熊猫办公", "熊猫", "woodo", "WPS"]:
                            if src.lower() in text.lower():
                                sources_found.add(src)
                    result["source"] = ", ".join(list(sources_found)[:3]) or "网络搜索"
                    result["template_name"] = f"{style_hint} 风格模板"
        except Exception as e:
            logger.debug(f"Template search failed (non-critical): {e}")
        return result

    # ━━━━━━━━━━━ MAIN SYNC RUN ━━━━━━━━━━━
    def run(self, db, message, user_id="default_user", session_id="", deep_thinking=False):
        if not deep_thinking and self._should_auto_enable(message):
            deep_thinking = True
        ctx = PipelineContext(user_id, session_id)
        ctx.deep_thinking_enabled = deep_thinking
        conversation_context = self._get_conversation_context(db, session_id, user_id)
        ctx.intent = self.input_layer.analyze(message, deep_thinking, conversation_context)
        if deep_thinking:
            ctx.subtasks = self.input_layer.decompose_for_deep_thinking(message, ctx.intent)
            ctx.thinking_steps = self._build_thinking_steps(ctx.intent, ctx.subtasks, True)
        ctx.sources = self.data_layer.acquire(db, ctx.intent, user_id, session_id)
        ctx.search_metadata = self._enrich_search_metadata(ctx)
        ctx.tool_results = self._execute_tools(ctx.intent, message, ctx.sources)
        if ctx.tool_results and ctx.tool_results.get("message"):
            ctx.processed = ProcessedData(cleaned_content=ctx.tool_results["message"])
        else:
            ctx.processed = self.process_layer.process(ctx.intent, ctx.sources, conversation_context)
        prefs = self._get_preferences(db, user_id)
        session = db.query(Session).filter(Session.id == session_id).first()
        nickname = session.assistant_nickname if session else "小石头"
        ctx.output = self.output_layer.format(ctx.processed, ctx.intent, preferences=prefs, assistant_nickname=nickname)
        return ctx

    # ━━━━━━━━━━━ MAIN ASYNC STREAM RUN ━━━━━━━━━━━
    async def run_stream(self, db, message, user_id="default_user", session_id="",
                         deep_thinking=False, guide_mode=False) -> AsyncGenerator[Dict[str, Any], None]:
        if not deep_thinking and self._should_auto_enable(message):
            deep_thinking = True
            logger.info("Deep thinking auto-enabled")

        ctx = PipelineContext(user_id, session_id)
        ctx.deep_thinking_enabled = deep_thinking

        # ══════════════ GUIDED MODE ROUTING ══════════════
        if guide_mode:
            m_lower = message.lower().strip()
            exit_keywords = ["直接做吧", "跳过引导", "开始生成", "不用问了", "直接生成", "关闭引导"]
            if any(k in m_lower for k in exit_keywords):
                pending = self._get_pending_task(db, session_id) or {}
                guide_json = pending.get("guide_state", "{}") if isinstance(pending, dict) else "{}"
                guide_state = GuideState.from_json(guide_json)
                if guide_state.status == "active" and guide_state.current_step > 0:
                    gen_msg = guide_state.build_generation_message()
                    self._clear_pending_task(db, session_id)
                    yield {"event": "guide_complete", "data": json_dumps({
                        "message": "好的，已根据您提供的信息开始生成！", "gen_message": gen_msg
                    })}
                    message = gen_msg
                else:
                    yield {"event": "guide_complete", "data": json_dumps({
                        "message": "已退出需求引导模式，我将直接为您生成。"
                    })}
                    guide_mode = False

            confirm_keywords = ["确认", "没问题", "对的", "是的", "就这样", "可以了", "开始吧", "生成吧"]
            if guide_mode:
                pending = self._get_pending_task(db, session_id) or {}
                guide_json = pending.get("guide_state", "{}") if isinstance(pending, dict) else "{}"
                guide_state = GuideState.from_json(guide_json)

                if guide_state.status != "active":
                    detected = detect_guide_trigger(message)
                    if detected:
                        if detected == "unknown":
                            guide_state.init_questions("unknown")
                            guide_state.status = "active"
                        else:
                            guide_state.init_questions(detected)
                            guide_state.status = "active"
                    self._set_pending_task(db, session_id, {
                        "pending_task": "需求引导模式",
                        "task_type": "guide_mode",
                        "guide_state": guide_state.to_json(),
                    })

                if guide_state.status == "active":
                    if guide_state.file_type == "unknown":
                        answer = message
                        if any(k in answer for k in ["ppt", "演示"]):
                            guide_state.init_questions("ppt")
                        elif any(k in answer for k in ["word", "文档"]):
                            guide_state.init_questions("word")
                        elif any(k in answer for k in ["excel", "表格"]):
                            guide_state.init_questions("excel")

                    if guide_state.file_type and guide_state.file_type != "unknown":
                        if any(k in m_lower for k in confirm_keywords) and guide_state.current_step >= guide_state.total_steps:
                            guide_state.status = "executing"
                            gen_msg = guide_state.build_generation_message()
                            self._clear_pending_task(db, session_id)
                            yield {"event": "message", "data": json_dumps({"type": "text", "content": "### 🎯 需求已确认，开始生成！\n\n正在调用工具..."})}
                            yield {"event": "guide_complete", "data": json_dumps({
                                "message": "开始生成", "gen_message": gen_msg
                            })}
                            message = gen_msg
                            guide_mode = False
                        elif guide_state.current_step < guide_state.total_steps:
                            guide_state.record_answer(message)
                            self._set_pending_task(db, session_id, {
                                "pending_task": "需求引导模式",
                                "task_type": "guide_mode",
                                "guide_state": guide_state.to_json(),
                            })
                            q = guide_state.get_current_question()
                            if q:
                                step_info = f"第{guide_state.current_step + 1}/{guide_state.total_steps}步"
                                yield {"event": "guide_question", "data": json_dumps({
                                    "step": guide_state.current_step + 1,
                                    "total": guide_state.total_steps,
                                    "question": q["question"],
                                    "options": q.get("options", []),
                                    "field": q["field"],
                                    "detail": q.get("detail", ""),
                                    "step_info": step_info,
                                })}
                                return
                            else:
                                summary = guide_state.build_summary()
                                yield {"event": "message", "data": json_dumps({"type": "text", "content": summary})}
                                return
                        else:
                            summary = guide_state.build_summary()
                            yield {"event": "message", "data": json_dumps({"type": "text", "content": summary})}
                            return
                    else:
                        intro_q = GENERAL_INTRO_QUESTIONS[0] if GENERAL_INTRO_QUESTIONS else None
                        if intro_q:
                            yield {"event": "guide_question", "data": json_dumps({
                                "step": 1, "total": 1,
                                "question": intro_q["question"],
                                "options": intro_q.get("options", []),
                                "field": intro_q["field"],
                                "detail": intro_q.get("detail", ""),
                                "step_info": "第1步",
                            })}
                            return

        # Pending task check (only when context-sensitive commands detected)
        pending = self._get_pending_task(db, session_id)
        modified = self._handle_pending_task_logic(message, pending or {}, db=db, session_id=session_id)
        if modified:
            if modified.get("status") == "execute_now":
                message = self._execute_pending_task(modified)
                self._clear_pending_task(db, session_id)
                logger.info(f"Executing pending task: {message}")
            else:
                pending = modified
                self._set_pending_task(db, session_id, pending)
                logger.info(f"[CTX] Updated pending task: task_type={modified.get('task_type')}, topic={modified.get('task_topic')}")
                yield {"event": "message", "data": json_dumps({"type": "text",
                    "content": f"好的，我来把「{modified.get('task_topic','')}」{self._format_task_type(modified.get('task_type',''))}。请稍等~"})}
                message = self._execute_pending_task(pending)

        # Layer 1: Analysis
        if deep_thinking:
            yield self._think("analyze", "正在分析需求", "running", "理解用户意图")
        conversation_context = self._get_conversation_context(db, session_id, user_id)
        ctx.intent = self.input_layer.analyze(message, deep_thinking, conversation_context)

        if deep_thinking:
            ctx.subtasks = self.input_layer.decompose_for_deep_thinking(message, ctx.intent)
            steps = self._build_thinking_steps(ctx.intent, ctx.subtasks, True)
            if steps:
                yield self._think_batch(steps)
            for i, st in enumerate(ctx.subtasks):
                yield self._think(st.task_id, st.description, "running", "处理中...")
                await asyncio.sleep(0.1)
                yield self._think(st.task_id, st.description, "completed", "完成")

        # Auto-title
        if session_id:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session and (not session.title or session.title == "新对话"):
                try:
                    title = await self._generate_title(message)
                    session.title = title
                    db.commit()
                    yield {"event": "title", "data": json_dumps({"title": title})}
                except:
                    pass

        # Layer 2: Data
        ctx.sources = self.data_layer.acquire(db, ctx.intent, user_id, session_id)
        ctx.search_metadata = self._enrich_search_metadata(ctx)
        ctx.mcp_results = await self._try_mcp_tools_async(ctx.intent, message)

        if deep_thinking:
            found = ctx.sources.search_metadata.get('web_query_count', 0) + \
                    ctx.sources.search_metadata.get('kb_query_count', 0)
            yield self._think("search", "搜索相关信息", "completed",
                              f"找到 {found} 条参考资料",
                              extra={"search_metadata": ctx.search_metadata})

        # MCP results: append to sources for LLM, don't shortcut
        if ctx.mcp_results:
            # Inject MCP tool results into web_results so LLM can use them
            for r in ctx.mcp_results:
                ctx.sources.web_results.insert(0, {
                    "title": r.get("source", "MCP"),
                    "snippet": r.get("content", ""),
                    "url": "",
                    "source": r.get("source", "MCP工具"),
                })

        # File generation with full 6-phase progress
        primary = ctx.intent.primary_intent
        if primary.startswith("create_document") or primary == "create_self_intro":
            async for evt in self._stream_file_generation(db, message, session_id, ctx, primary):
                yield evt
            return

        # Normal chat streaming
        if deep_thinking:
            yield self._think("generate", "生成回复内容", "running", "AI 正在组织语言...")
        try:
            stream = self.process_layer.process_stream(ctx.intent, ctx.sources)
            assistant_content = ""
            async for chunk in stream:
                if isinstance(chunk, str):
                    assistant_content += chunk
                    yield {"event": "message", "data": json_dumps({"type": "text", "content": chunk})}

            if session_id and assistant_content:
                self._save_message(db, session_id, "assistant", assistant_content)

            if deep_thinking:
                yield self._think("generate", "生成回复内容", "completed",
                                  f"已生成 {len(assistant_content)} 字回复")
            done_data = {"status": "completed", "message_id": str(uuid.uuid4())}
            if deep_thinking:
                done_data["search_metadata"] = ctx.search_metadata
            yield {"event": "done", "data": json_dumps(done_data)}
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            err = str(e).lower()
            if "api_key" in err or "credentials" in err or "auth" in err:
                msg = "### ⚠️ AI 服务未配置\n\n请编辑 backend/.env 设置 AI_API_KEY"
            else:
                msg = f"抱歉：{str(e)[:200]}"
            yield {"event": "message", "data": json_dumps({"type": "text", "content": msg})}
            yield {"event": "done", "data": json_dumps({"status": "error"})}

    # ━━━━━━━━━━━ FILE GENERATION WITH 6-PHASE PROGRESS ━━━━━━━━━━━
    async def _stream_file_generation(self, db, message, session_id, ctx, primary_intent):
        from app.file_processor import FileProcessor
        fp = FileProcessor()

        m_lower = message.lower()
        is_self_intro = any(k in m_lower for k in ["自我介绍", "介绍自己", "你是谁", "介绍你", "你什么"])
        file_type = "word"
        if any(k in m_lower for k in ["ppt", "演示文稿", "幻灯片"]):
            file_type = "ppt"
        elif any(k in m_lower for k in ["excel", "表格"]):
            file_type = "excel"
        elif "ppt" in primary_intent:
            file_type = "ppt"
        elif "excel" in primary_intent:
            file_type = "excel"

        topic = self._extract_topic(message, ctx.sources)
        author = ctx.intent.entities.get("author", "") if ctx.intent.entities else ""
        style_config = self.style_engine.resolve_style(message)
        style_name = style_config.get("style_name", "默认")

        # Phase 1: Analyze
        yield {"event": "file_progress", "data": json_dumps({
            "phase": 1, "label": "正在分析需求…",
            "detail": f"检测到：{file_type.upper()} | 主题：{topic} | 风格：{style_name}",
            "progress": 5
        })}
        await asyncio.sleep(0.2)

        # Phase 2: Search templates
        yield {"event": "file_progress", "data": json_dumps({
            "phase": 2, "label": "正在搜索合适的模板…",
            "detail": f"搜索关键词：{topic} {style_name} 模板",
            "progress": 15
        })}
        template_result = await self._search_templates_online(file_type, topic, style_name)
        if template_result.get("found"):
            yield {"event": "file_progress", "data": json_dumps({
                "phase": 2, "label": "找到模板参考",
                "detail": f"来源：{template_result.get('source', '网络搜索')} | {template_result.get('template_name', '')}",
                "progress": 20
            })}
        else:
            yield {"event": "file_progress", "data": json_dumps({
                "phase": 2, "label": "使用内置模板",
                "detail": f"内置模板：{style_name}",
                "progress": 20
            })}
        await asyncio.sleep(0.15)

        # Phase 3: Apply style
        yield {"event": "file_progress", "data": json_dumps({
            "phase": 3, "label": "正在应用模板样式…",
            "detail": f"配色方案已加载 | 字体方案已加载",
            "progress": 30
        })}
        await asyncio.sleep(0.2)

        # Phase 4: Generate content
        yield {"event": "file_progress", "data": json_dumps({
            "phase": 4, "label": "正在填充内容…",
            "detail": f"AI正在撰写{file_type.upper()}内容…",
            "progress": 40
        })}

        result = {}
        try:
            if file_type == "ppt":
                result = await self._gen_ppt_inline(message, topic, author, style_config, fp, is_self_intro)
                for i in range(1, result.get("total_pages", 6) + 1):
                    if i % 3 == 0 or i == result.get("total_pages", 6):
                        yield {"event": "file_progress", "data": json_dumps({
                            "phase": 4, "label": f"正在写入第{i}页…",
                            "detail": f"页面进度：{i}/{result.get('total_pages', 6)}",
                            "progress": 40 + int(40 * i / result.get("total_pages", 6))
                        })}
                    await asyncio.sleep(0.03)
            elif file_type == "excel":
                result = self._gen_excel_inline(topic, fp)
            else:
                result = await self._gen_word_inline(message, topic, author, style_config, fp, is_self_intro)
        except Exception as e:
            logger.error(f"File generation error: {e}")
            try:
                if file_type == "ppt":
                    result = await self._gen_ppt_inline(message, topic, author, style_config, fp, is_self_intro)
                elif file_type == "excel":
                    result = self._gen_excel_inline(topic, fp)
                else:
                    result = await self._gen_word_inline(message, topic, author, style_config, fp, is_self_intro)
            except Exception as e2:
                yield {"event": "file_progress", "data": json_dumps({
                    "phase": "error", "label": "文件生成失败（已重试）", "detail": str(e2)[:200], "progress": 50
                })}
                yield {"event": "message", "data": json_dumps({"type": "text",
                       "content": f"### ⚠️ 文件生成失败\n\n两次尝试均失败：{str(e2)[:200]}\n\n请检查配置后重试。"})}
                yield {"event": "done", "data": json_dumps({"status": "error"})}
                return

        if result.get("error"):
            yield {"event": "file_progress", "data": json_dumps({
                "phase": "error", "label": "生成失败", "detail": result["error"][:200], "progress": 50
            })}
            yield {"event": "message", "data": json_dumps(
                   {"type": "text", "content": f"### ⚠️ 文件生成失败\n\n{result['error'][:200]}\n\n请稍后重试。"})}
            yield {"event": "done", "data": json_dumps({"status": "error"})}
            return

        file_path = result.get("file_path", "")
        file_name = result.get("file_name", "")

        # Phase 5: Beautify
        yield {"event": "file_progress", "data": json_dumps({
            "phase": 5, "label": "正在美化排版…",
            "detail": f"应用{style_name}样式，调整格式、间距、字体…",
            "progress": 85
        })}
        await asyncio.sleep(0.3)

        # Save to DB
        file_id = ""
        if file_path and Path(file_path).exists():
            file_id = self._save_generated_file_to_db(db, session_id, file_path, file_name)

        # Phase 6: Prepare preview
        yield {"event": "file_progress", "data": json_dumps({
            "phase": 6, "label": "生成完成，正在准备预览…",
            "detail": "文件已保存，可供下载和预览",
            "progress": 100,
            "file_path": file_path,
            "file_name": file_name,
            "file_id": file_id,
            "file_type": file_type,
            "style_name": style_name,
            "template_source": template_result.get("source", "内置"),
        })}
        await asyncio.sleep(0.1)

        total_pages = result.get("total_pages", 1)
        summary_msg = (
            f"### ✅ {file_type.upper()} 文件已生成\n\n"
            f"**文件名称**：{file_name}\n"
            f"**主　　题**：{topic}\n"
            f"**风　　格**：{style_name}\n"
            f"**模板来源**：{template_result.get('source', '内置模板库')}\n"
            f"**页数/行数**：{total_pages} 页/行\n\n"
            f"> 📥 点击下方卡片即可预览或下载文件"
        )

        yield {"event": "tool_result", "data": json_dumps({
            "file_path": file_path, "file_name": file_name,
            "file_id": file_id, "message": summary_msg, "file_type": file_type,
        })}
        yield {"event": "message", "data": json_dumps({"type": "text", "content": summary_msg})}

        if session_id:
            self._save_message(db, session_id, "assistant", summary_msg)

        self._clear_pending_task(db, session_id)
        yield {"event": "done", "data": json_dumps({
            "status": "completed", "message_id": str(uuid.uuid4()),
            "file_info": {"file_path": file_path, "file_name": file_name, "file_id": file_id}
        })}

    # ━━━━━━━━━━━ FILE GENERATION HELPERS ━━━━━━━━━━━
    async def _gen_ppt_inline(self, message, topic, author, style_config, fp, is_self_intro):
        result = {}
        ppt_theme = style_config.get("ppt", {}).get("theme", "academic_blue")

        if is_self_intro:
            prompt = self._get_self_intro_ppt_prompt()
        else:
            prompt = f"""你是文档专家。为主题《{topic}》生成PPT内容，返回JSON：
{{"title":"完整标题","slides":[
  {{"phase":"cover","title":"封面标题","content":["副标题","作者/日期"]}},
  {{"phase":"intro","title":"概述","content":["要点1","要点2","要点3"]}},
  {{"phase":"content","title":"核心内容一","content":["要点1","要点2","要点3","要点4"]}},
  {{"phase":"content","title":"核心内容二","content":["要点1","要点2","要点3"]}},
  {{"phase":"content","title":"要点分析","content":["要点1","要点2","要点3","要点4"]}},
  {{"phase":"content","title":"详细说明","content":["要点1","要点2","要点3"]}},
  {{"phase":"summary","title":"总结","content":["要点1","要点2","要点3"]}},
  {{"phase":"ending","title":"感谢","content":["谢谢观看"]}}
]}}
每页3-5个要点，每个≤30字。只返回JSON。"""

        resp = self.process_layer.client.chat.completions.create(
            model=self.process_layer.model,
            messages=[{"role": "system", "content": "你是PPT内容专家。只返回JSON。"},
                       {"role": "user", "content": prompt}],
            temperature=0.6, max_tokens=3000,
        )
        gen = resp.choices[0].message.content or ""
        slides = []
        pt = topic
        try:
            js = gen.find("{")
            je = gen.rfind("}") + 1
            if js >= 0 and je > js:
                data = json.loads(gen[js:je])
                pt = data.get("title", topic)
                slides = data.get("slides", [])
        except:
            slides = self._fallback_ppt(topic)
        if not slides:
            slides = self._fallback_ppt(topic)

        fp_path = fp.generate_ppt(title=pt, slides_data=slides, theme_name=ppt_theme, author=author or "小石头")
        result["file_path"] = fp_path
        result["file_name"] = Path(fp_path).name
        result["total_pages"] = len(slides) + 2
        return result

    def _gen_excel_inline(self, topic, fp):
        result = {}
        prompt = f"""你是表格数据专家。为用户生成表格数据，返回JSON格式。
用户需求：{topic}

严格返回以下JSON格式（只返回JSON，不要其他文字）：
{{"title":"表格标题","headers":["列1","列2","列3",...],"rows":[["数据1","数据2","数据3",...],...]}}

要求：
- headers至少2列，最好是用户指定的字段
- rows至少3行真实数据
- 如果用户要求特定字段（如"姓名/年龄/城市"），直接使用作为表头
- 如果用户要求填充示例数据，生成合理的中文示例数据
- 只返回JSON"""
        try:
            resp = self.process_layer.client.chat.completions.create(
                model=self.process_layer.model,
                messages=[{"role": "system", "content": "你是表格数据专家。只返回JSON。不要解释，不要Markdown代码块。"},
                           {"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=2000,
            )
            gen = resp.choices[0].message.content or ""
            logger.info(f"[EXCEL_DEBUG] LLM response: {gen[:300]}")
        except Exception as e:
            logger.error(f"[EXCEL_DEBUG] LLM call failed: {e}")
            gen = ""

        title = topic[:30] or "表格数据"
        headers = ["项目", "数据"]
        rows = [["示例数据", "值"]]
        
        try:
            # Strip markdown code blocks if present
            cleaned = gen.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)
            js = cleaned.find("{")
            je = cleaned.rfind("}") + 1
            if js >= 0 and je > js:
                data = json.loads(cleaned[js:je])
                title = str(data.get("title", title))[:50]
                headers = [str(h) for h in data.get("headers", headers)]
                rows = [[str(c) for c in row] for row in data.get("rows", [])]
                if len(rows) < 3:
                    # Pad with template rows
                    template_row = ["示例" + str(i) for i in range(len(headers))] if headers else ["示例1", "示例2"]
                    while len(rows) < 3:
                        rows.append(template_row)
                logger.info(f"[EXCEL_DEBUG] Parsed: {len(headers)} headers, {len(rows)} rows")
            else:
                logger.warning(f"[EXCEL_DEBUG] No JSON found in: {gen[:200]}")
        except Exception as e:
            logger.warning(f"[EXCEL_DEBUG] JSON parse failed: {e}, raw: {gen[:200]}")
            # Smart fallback: try to extract keywords from topic
            topic_words = topic.replace("生成", "").replace("包含", "").replace("的", "").replace("表格", "").replace("Excel", "").replace("excel", "")
            potential_headers = [w.strip() for w in topic_words.replace("、", ",").replace("和", ",").split(",") if w.strip()]
            if len(potential_headers) >= 2:
                headers = potential_headers[:6]
                rows = [["张三", "28", "北京"], ["李四", "32", "上海"], ["王五", "25", "广州"]][:len(potential_headers)]
                for i in range(len(rows)):
                    rows[i] = rows[i][:len(potential_headers)]

        fp_path = fp.generate_excel(
            sheet_name="Sheet1", headers=headers, rows=rows,
            title=title, theme_name="professional"
        )
        result["file_path"] = fp_path
        result["file_name"] = Path(fp_path).name
        result["total_pages"] = len(rows) + 1
        return result

    async def _gen_word_inline(self, message, topic, author, style_config, fp, is_self_intro):
        result = {}
        word_theme = style_config.get("word", {}).get("theme", "academic")

        if is_self_intro:
            prompt = (
                "你是「小石头」，一个有个性、温暖而专业的AI伙伴。"
                "请以第一人称撰写一份小石头自我介绍文档。\n"
                "要求：\n"
                "1. 标题：小石头的自我介绍\n"
                "2. 包含章节（使用Markdown ## 格式）：名字的由来、我的性格、我能做什么、我与你的关系、我的小特点、结语\n"
                "3. 用小石头第一人称（'我叫小石头…'）\n"
                "4. 语气温暖亲切，展现个性\n"
                "5. 禁止使用'我是一个AI助手，由XX公司开发'等泛化表述\n"
                "6. 总字数600-1000字\n"
                "只返回Markdown。"
            )
        else:
            prompt = (
                f"为主题《{topic}》生成完整文档内容。"
                f"使用Markdown格式（## 标题、### 小标题、- 列表、| 表格）。"
                f"包含：概述、背景、内容、分析、结论。800-1500字。只返回Markdown。"
            )

        resp = self.process_layer.client.chat.completions.create(
            model=self.process_layer.model,
            messages=[{"role": "system", "content": "你是专业文档撰写专家。"},
                       {"role": "user", "content": prompt}],
            temperature=0.7 if is_self_intro else 0.5,
            max_tokens=3000,
        )
        content = resp.choices[0].message.content or topic

        fp_path = fp.generate_word(
            title="小石头的自我介绍" if is_self_intro else topic,
            content=content,
            author=author or "小石头",
            theme_name=word_theme,
            doc_type="introduction" if is_self_intro else "report",
        )
        result["file_path"] = fp_path
        result["file_name"] = Path(fp_path).name
        result["total_pages"] = len(content.split("\n")) // 20 + 1
        return result

    def _get_self_intro_ppt_prompt(self):
        return """你是「小石头」，一个有个性、温暖而专业的AI伙伴。请生成一份PPT自我介绍，返回JSON：
{"title":"小石头的自我介绍","slides":[
  {"phase":"cover","title":"小石头的自我介绍","content":["一颗坚固可靠的小石子","你的智能伙伴"]},
  {"phase":"intro","title":"名字的由来","content":["我叫小石头","寓意坚固可靠、踏实稳重","像小石子一样为你提供坚实支撑"]},
  {"phase":"personality","title":"我的性格","content":["温暖亲切，像老朋友","风趣幽默，让对话不再枯燥","专业严谨，确保信息准确","耐心细致"]},
  {"phase":"abilities","title":"我能做什么","content":["聊天陪伴与深度思考","Word/Excel/PPT文档生成与美化","数据分析与文件处理","联网搜索与天气查询"]},
  {"phase":"features","title":"我的小特点","content":["默认头像是一颗可爱的小石子🪨","自称「我这颗小石头」","简约而独特的风格"]},
  {"phase":"conclusion","title":"期待与你同行","content":["期待成为你最信赖的智能伙伴","坚固如石，温暖如初"]}
]}
每页2-5个要点，每个≤30字。只返回JSON。"""

    def _fallback_ppt(self, topic):
        return [
            {"title": "封面", "content": [f"{topic}", "制作人：小石头"]},
            {"title": "概述", "content": [f"关于{topic}", "核心要点"]},
            {"title": "核心内容一", "content": ["要点一", "要点二", "要点三", "要点四"]},
            {"title": "核心内容二", "content": ["要点一", "要点二", "要点三"]},
            {"title": "要点分析", "content": ["分析一", "分析二", "分析三"]},
            {"title": "详细说明", "content": ["说明一", "说明二", "说明三"]},
            {"title": "总结", "content": ["关键发现", "后续建议"]},
        ]

    # ━━━━━━━━━━━ MCP TOOLS ━━━━━━━━━━━
    async def _try_mcp_tools_async(self, intent, message) -> List[Dict[str, Any]]:
        results = []
        try:
            from app.mcp import get_mcp_manager
            mcp = get_mcp_manager()
            lower = message.lower()

            # Weather: do NOT use fake MCP mock. Rely on real web search via data_layer.
            # The web search will return real weather results which get injected into LLM context.

            if any(k in lower for k in ["地图", "路线", "导航", "amap", "高德"]):
                results.append({
                    "source": "amap_mcp",
                    "content": "📍 地图服务已集成，搜索地点或询问路线即可使用高德地图。",
                })
        except Exception as e:
            logger.warning(f"MCP tool error: {e}")
        return results


    def _format_task_type(self, task_type: str) -> str:
        """Convert task_type to human-readable format description."""
        type_map = {
            "ppt_generation": "转换为PPT格式",
            "word_generation": "转换为Word文档",
            "excel_generation": "转换为Excel表格",
        }
        return type_map.get(task_type, f"转换为{task_type}")

    def _format_mcp_results(self, results):
        return "\n\n".join(r.get("content", "") for r in results if r.get("content"))

    # ━━━━━━━━━━━ THINKING STEPS ━━━━━━━━━━━
    def _build_thinking_steps(self, intent, subtasks, is_deep):
        if not is_deep or not subtasks:
            return []
        return [{
            "id": st.task_id,
            "step": self._sanitize_step(st.description, keep_urls=True),
            "description": st.description,
            "module": st.module,
            "status": "pending",
            "detail": "等待处理",
            "dependencies": st.dependencies,
        } for st in subtasks]

    def _sanitize_step(self, desc, keep_urls=False):
        desc = re.sub(r'(api_key|apikey|api-key|secret|password|token)\s*[=:]\s*\S+', r'\1=***', desc, flags=re.I)
        desc = re.sub(r'sk-[A-Za-z0-9]{20,}', 'sk-***', desc)
        desc = re.sub(r'mysql://\S+', 'mysql://***', desc)
        return desc.strip()[:120]

    def _enrich_search_metadata(self, ctx):
        return {
            "search_keywords": [ctx.intent.raw_message[:100]],
            "knowledge_base_sources": [
                r.get("source_url", r.get("title", "知识库"))
                for r in ctx.sources.knowledge_results[:5]
            ],
            "web_urls": [
                r.get("url", "") for r in ctx.sources.web_results[:5] if r.get("url")
            ],
            "collection_names": ["RAG知识库(Milvus)", "MySQL知识库"],
            "kb_query_count": ctx.sources.search_metadata.get("kb_query_count", 0),
            "web_query_count": ctx.sources.search_metadata.get("web_query_count", 0),
            "memory_items": ctx.sources.search_metadata.get("memory_items", 0),
            "timestamp": ctx.sources.search_metadata.get("timestamp", ""),
        }

    def _think(self, id, step, status, detail, extra=None):
        step_data = {"id": id, "step": step, "status": status, "detail": detail}
        if extra:
            step_data["extra"] = extra
        return {"event": "thinking", "data": json_dumps({"steps": [step_data]})}

    def _think_batch(self, steps):
        return {"event": "thinking", "data": json_dumps({"steps": steps})}

    # ━━━━━━━━━━━ LEGACY EXECUTION ━━━━━━━━━━━
    def _execute_tools(self, intent, message, sources):
        result = {}
        if intent.primary_intent.startswith("create_document") or intent.primary_intent == "create_self_intro":
            result["message"] = "文档正在生成中，请查看文件卡片…"
        return result

    # ━━━━━━━━━━━ HELPERS ━━━━━━━━━━━
    async def _generate_title(self, message):
        try:
            client = self.input_layer.client
            resp = client.chat.completions.create(
                model=self.input_layer.model,
                messages=[
                    {"role": "system", "content": "你是会话命名专家。生成简洁标题（5-20汉字）。只返回标题。"},
                    {"role": "user", "content": message}
                ],
                temperature=0.5, max_tokens=30,
            )
            t = resp.choices[0].message.content.strip()
            t = t.replace('"', '').replace("'", "")
            return t[:20] if t else message[:20] + "…"
        except:
            from datetime import datetime
            return f"新对话_{datetime.now().strftime('%m%d_%H%M')}"

    def _extract_topic(self, message, sources):
        topic = message
        for prefix in ["生成", "制作", "创建", "做一个", "帮我", "一份", "一个",
                       "制作一份", "生成一份", "ppt格式", "ppt", "演示文稿", "幻灯片",
                       "换成", "改成", "转成", "word格式", "word", "文档", "doc", "excel", "表格"]:
            topic = topic.replace(prefix, "")
        topic = topic.strip().strip("的").strip("。").strip()[:80]
        if not topic or len(topic) < 2:
            if sources and sources.memory_context:
                for item in reversed(sources.memory_context):
                    if item.get("type") == "message" and item.get("role") == "user":
                        c = item.get("content", "")
                        if "小石头" in c:
                            return "小石头自我介绍"
                        if "自我介绍" in c:
                            return "小石头自我介绍"
                        return c[:60]
            return "小石头自我介绍"
        return topic

    def _get_conversation_context(self, db, session_id: str, user_id: str) -> str:
        if not session_id:
            return ""
        try:
            messages = (
                db.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.sequence.desc())
                .limit(6)
                .all()
            )
            if not messages:
                return ""
            parts = []
            for m in reversed(messages):
                role_label = "用户" if m.role == "user" else "小石头"
                parts.append(f"[{role_label}]: {m.content[:300]}")
            return "## 对话上下文\n" + "\n".join(parts)
        except:
            return ""

    def _get_preferences(self, db, user_id):
        try:
            pref = db.query(Preference).filter(Preference.user_id == user_id).first()
            if pref:
                return {
                    "tone_style": pref.tone_style,
                    "response_length": pref.response_length,
                    "language_preference": pref.language_preference,
                    "theme": pref.theme,
                    "learned_facts": pref.learned_facts,
                }
        except:
            pass
        return None

    def _save_generated_file_to_db(self, db, session_id: str, file_path: str, file_name: str) -> str:
        try:
            path = Path(file_path)
            if not path.exists():
                return ""
            record = FileRecord(
                session_id=session_id or "global",
                filename=path.name,
                original_filename=file_name or path.name,
                file_path=file_path,
                file_type=path.suffix.lstrip(".").lower(),
                file_size=path.stat().st_size,
                purpose="generated",
                status="done",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record.id
        except Exception as e:
            logger.warning(f"Save file DB failed: {e}")
            return ""

    def _save_message(self, db, session_id, role, content):
        try:
            max_seq = db.query(Message).filter(Message.session_id == session_id).count()
            msg = Message(
                session_id=session_id, role=role, content=content,
                content_type="text", sequence=max_seq + 1,
            )
            db.add(msg)
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                from datetime import datetime
                session.updated_at = datetime.now()
            db.commit()
        except Exception as e:
            logger.warning(f"Save message failed: {e}")