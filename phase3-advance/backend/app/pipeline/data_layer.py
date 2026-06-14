"""
Layer 2: Data Acquisition Layer - Reliable, Real-time Web Search
Gathers all needed data with smart decision logic, query preservation, result filtering.
"""
import json, os, hashlib, re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from loguru import logger
from openai import OpenAI
from sqlalchemy.orm import Session as DBSession

from app.config import get_settings
from app.models import KnowledgeItem, KnowledgeCache


class DataSources(BaseModel):
    knowledge_results: List[Dict[str, Any]] = []
    web_results: List[Dict[str, Any]] = []
    memory_context: List[Dict[str, Any]] = []
    file_contents: List[Dict[str, Any]] = []
    search_metadata: Dict[str, Any] = {}


class DataAcquisitionLayer:
    """Acquires raw data with smart decision logic."""

    # ═══════════════════════════════════════════
    # REAL-TIME KEYWORDS: skip KB, force web
    # ═══════════════════════════════════════════
    REALTIME_KEYWORDS = [
        "最新", "最近", "近期", "当下", "今年", "今天", "今日", "现在", "目前",
        "实时", "刚刚", "最新消息", "当前",
        "天气", "温度", "气温", "下雨", "晴天", "阴天", "weather", "台风",
        "比分", "比赛", "赛程", "结果", "冠军", "决赛", "小组赛", "淘汰赛",
        "股价", "股票", "行情", "汇率", "金价", "油价",
        "新闻", "头条", "热点", "报道",
        "today", "latest", "recent", "breaking", "live", "score", "stock",
        "几号", "星期几", "日期", "时间",
    ]
    # ═══════════════════════════════════════════
    # Compound entity patterns: never split these
    # ═══════════════════════════════════════════
    COMPOUND_PATTERNS = [
        r'[A-Z\u4e00-\u9fff]{2,}世界杯',   # 美加墨世界杯
        r'\d{4}年世界杯',
        r'[A-Z\u4e00-\u9fff]+奥运会',
        r'[A-Z\u4e00-\u9fff]+联赛',
        r'[A-Z\u4e00-\u9fff]+杯赛',
        r'[A-Z\u4e00-\u9fff]+锦标赛',
        r'[A-Z\u4e00-\u9fff]+大奖赛',
    ]

    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._client = None
        self.model = settings.ai_model_name
        self.kb_url = settings.knowledge_base_url
        self.kb_api_key = settings.knowledge_base_api_key

    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(
                base_url=self._settings.ai_api_base_url,
                api_key=self._settings.ai_api_key or "sk-placeholder",
                timeout=20.0, max_retries=1,
            )
        return self._client

    # ═══════════════════════════════════════════
    # MAIN ACQUIRE - Smart Decision Logic
    # ═══════════════════════════════════════════
    def acquire(self, db: DBSession, intent: Any, user_id: str = "default_user",
                session_id: str = "") -> DataSources:
        logger.info(f"[Layer 2] Acquiring data for: {intent.primary_intent}")
        sources = DataSources()
        now = datetime.now()
        current_time_str = now.strftime("%Y年%m月%d日 %H:%M")
        raw_message = intent.raw_message

        # Step 0: Capture current time
        # Step 1: Load memory context (for multi-turn time-sensitivity)
        if session_id:
            sources.memory_context = self._get_memory_context(db, user_id, session_id)
            logger.info(f"[Layer 2] Memory: {len(sources.memory_context)} items")

        # Step 2: Decision - force web search or KB-first?
        is_context_time_sensitive = self._is_context_time_sensitive(sources.memory_context)
        force_web = self._is_realtime_query(raw_message) or is_context_time_sensitive

        if force_web:
            logger.info("[Layer 2] ⚡ Realtime query detected → DIRECT web search (skip KB)")
            web_query = self._build_smart_query(raw_message, intent.entities, now)
            sources.web_results = self._web_search(db, web_query)
            # Supplement with KB but mark as reference only
            try:
                sources.knowledge_results = self._query_knowledge_base(db, raw_message)
            except:
                pass
        else:
            # KB-first
            sources.knowledge_results = self._query_knowledge_base(db, raw_message)
            logger.info(f"[Layer 2] KB returned {len(sources.knowledge_results)} results")

            # Only web search if user message looks like a real question (not greeting/chat)
            needs_web = self._needs_web_search(raw_message)
            if needs_web:
                if sources.knowledge_results:
                    conflict = self._check_time_conflict(sources.knowledge_results, now)
                    if conflict:
                        logger.info(f"[Layer 2] ⏰ KB stale ({conflict}) → web search")
                        web_query = self._build_smart_query(raw_message, intent.entities, now)
                        sources.web_results = self._web_search(db, web_query)
                    elif len(sources.knowledge_results) < 2:
                        sources.web_results = self._web_search(db, raw_message)
                else:
                    sources.web_results = self._web_search(db, raw_message)
            else:
                logger.info("[Layer 2] Chat/greeting message → skip web search entirely")

        # Metadata
        sources.search_metadata = {
            "kb_query_count": len(sources.knowledge_results),
            "web_query_count": len(sources.web_results),
            "memory_items": len(sources.memory_context),
            "timestamp": now.isoformat(),
            "current_time": current_time_str,
            "force_web_search": force_web,
        }
        return sources

    # ═══════════════════════════════════════════
    # QUERY BUILDING - Preserve compounds, add date
    # ═══════════════════════════════════════════
    def _is_realtime_query(self, message: str) -> bool:
        lower = message.lower()
        return any(kw in lower for kw in self.REALTIME_KEYWORDS)

    def _needs_web_search(self, message: str) -> bool:
        """Only trigger web search for actual questions, not greetings/chit-chat.
        A message needs web search if it has:
        - Real-time keywords (already handled by _is_realtime_query)
        - Question words (什么/怎么/为什么/如何/哪里/多少/哪)
        - Topic nouns longer than 4 characters
        - English questions
        """
        if self._is_realtime_query(message):
            return True
        lower = message.lower().strip()
        # Skip pure greetings / very short / emotional messages
        skip_patterns = [
            "你好", "嗨", "哈喽", "hello", "hi", "hey",
            "谢谢", "感谢", "多谢", "thanks", "thank",
            "再见", "拜拜", "bye", "goodbye",
            "厉害", "牛", "哈哈哈", "笑死", "哭",
            "嗯", "哦", "好", "ok", "好的", "行",
            "不错", "可以", "很棒", "真好",
        ]
        if any(lower == s for s in skip_patterns):
            return False
        if len(lower) <= 3:
            return False
        # Has question indicators → need search
        question_words = ["什么", "怎么", "为什么", "如何", "哪里", "多少",
                           "哪", "谁", "何时", "what", "how", "why",
                           "where", "when", "which", "who"]
        if any(qw in lower for qw in question_words):
            return True
        # Has meaningful topic (longer Chinese text → probably a question)
        chinese_chars = sum(1 for c in lower if '\u4e00' <= c <= '\u9fff')
        if chinese_chars >= 5:
            return True
        # Default: skip web search for chat
        return False

    def _is_context_time_sensitive(self, memory: List[Dict]) -> bool:
        if not memory:
            return False
        indicators = ["最新", "最近", "今天", "天气", "新闻", "比分", "比赛"]
        for item in memory:
            if item.get("type") == "message":
                content = item.get("content", "").lower()
                if any(ti.lower() in content for ti in indicators):
                    return True
        return False

    def _build_smart_query(self, raw_message: str, entities: Dict, now: datetime) -> str:
        """Build search query with precise timestamp injection, sports site scoping,
        and compound entity preservation."""
        msg = raw_message.strip()
        today_str = now.strftime("%Y年%m月%d日")
        year_month = now.strftime("%Y年%m月")

        # ═══ SPORTS DETECTION: team1 vs team2 pattern ═══
        sports_matchup = re.search(
            r'([A-Z\u4e00-\u9fff]{2,6})(?:对|vs\.?|VS\.?|对阵|迎战|战)([A-Z\u4e00-\u9fff]{2,6})',
            msg, re.I
        )
        is_sports = any(w in msg for w in ["比分", "比赛", "赛程", "小组赛",
                                              "淘汰赛", "决赛", "半决赛", "世界杯",
                                              "赢", "输", "进球", "score", "match",
                                              "联赛", "杯", "锦标赛"])
        is_weather = any(w in msg for w in ["天气", "温度", "气温", "下雨", "晴天",
                                              "阴天", "刮风", "台风", "weather"])
        is_stock = any(w in msg for w in ["股价", "股票", "行情", "汇率", "金价", "油价",
                                            "涨", "跌", "收盘"])

        # ━━━ PRECISE TIMESTAMP for real-time queries ━━━
        if is_sports or is_weather or is_stock:
            time_prefix = today_str  # "2026年06月15日"
        else:
            time_prefix = str(now.year) + "年"

        # ━━━ Initialize variables used across blocks ━━━
        compounds = []
        teams = []

        # ━━━ SPORTS: site-scoped + matchup decomposition ━━━
        if is_sports:
            # Extract compound entities
            compounds = []
            for pattern in self.COMPOUND_PATTERNS:
                compounds.extend(re.findall(pattern, msg))
            # T1 vs T2 → extract both team names
            teams = []
            if sports_matchup:
                teams = [sports_matchup.group(1), sports_matchup.group(2)]
            # Build precise sports query
            parts = [time_prefix]
            if compounds:
                parts.append(" ".join(compounds))
            if teams:
                parts.append(f"{teams[0]} {teams[1]}")
            parts.append("比分")
            query = " ".join(parts)
            # Add site-scope for authoritative sports sources
            query = f"{query} site:espn.com OR site:sports.sina.com.cn OR site:fifa.com"
        elif is_weather:
            # Extract city name
            city_match = re.search(
                r'(北京|上海|广州|深圳|杭州|成都|重庆|武汉|南京|天津|西安|长沙|郑州|济南|青岛|大连|厦门|哈尔滨|沈阳|合肥|福州|南昌|昆明|贵阳|南宁|拉萨|乌鲁木齐|呼和浩特|银川|西宁|兰州)',
                msg
            )
            city = city_match.group(1) if city_match else ""
            query = f"{time_prefix} {city} 天气 实时温度" if city else f"{time_prefix} 天气 实时"
        elif is_stock:
            stock_entity = re.search(r'([A-Z\u4e00-\u9fff]{2,10}(?:股份|银行|科技|集团|石油|黄金)?)', msg)
            entity = stock_entity.group(1) if stock_entity else ""
            query = f"{time_prefix} {entity} 股价 实时行情" if entity else f"{time_prefix} 实时股价"
        else:
            # General query: preserve compounds
            compounds = []
            for pattern in self.COMPOUND_PATTERNS:
                compounds.extend(re.findall(pattern, msg))
            if compounds:
                base = " ".join(compounds)
                time_hints = ["比分", "结果", "赛程", "最新", "实时"]
                extra = [w for w in time_hints if w in msg]
                query = f"{time_prefix} {base} {' '.join(extra)}"
            else:
                query = f"{time_prefix} {msg}"
            # If too short, use full message
            if len(query.strip().replace(time_prefix, "").strip()) < 4:
                query = f"{time_prefix} {msg}"

        # ━━━ Wrap compounds in quotes for exact-match search ━━━
        for cp in compounds if 'compounds' in dir() else []:
            if cp and cp in query:
                query = query.replace(cp, f'"{cp}"')
        if teams:
            for t in teams:
                if len(t) >= 2 and t in query:
                    query = query.replace(t, f'"{t}"')

        # ━━━ NEVER use vague year-only queries ━━━
        if query.strip() == f"{now.year}年" or query.strip() == f"{now.year}":
            query = f"{today_str} {msg}"

        # Log to thinking panel
        logger.info(f"[SEARCH_QUERY] '{query}' ← original: '{raw_message[:80]}'")
        return query

    def _check_time_conflict(self, kb_results: List[Dict], now: datetime) -> Optional[str]:
        """Detect stale KB results (>90 days old or wrong year)."""
        if not kb_results:
            return None
        current_year = now.year
        date_pattern = re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})')
        year_pattern = re.compile(r'(?:19|20)(\d{2})年')
        for r in kb_results[:5]:
            content = r.get("content", r.get("snippet", ""))
            if not content:
                continue
            # Year check
            for y_str in year_pattern.findall(content):
                yr = int(f"20{y_str}") if len(y_str) == 2 else int(y_str)
                if yr < current_year - 1:
                    return f"KB year {yr} vs current {current_year}"
            # Date check
            for d in date_pattern.findall(content):
                try:
                    doc_date = datetime(int(d[0]), int(d[1]), int(d[2]))
                    if (now - doc_date).days > 90:
                        return f"KB date {d[0]}-{d[1]}-{d[2]} is {(now-doc_date).days}d old"
                except:
                    pass
        return None

    # ═══════════════════════════════════════════
    # WEB SEARCH - 3-Layer Fallback
    # ═══════════════════════════════════════════
    def _web_search(self, db: DBSession, query: str) -> List[Dict]:
        """3-layer search with 3s total timeout per layer.
        Returns at least a system clock result even on total failure."""
        results = []
        logger.info(f"[SEARCH_QUERY] Actual search query: '{query}'")

        # Layer A: DuckDuckGo Search (ddgs library) — 3s timeout
        try:
            import threading
            ddg_result = []
            exc = []
            def _ddgs():
                try:
                    from ddgs import DDGS
                    with DDGS(timeout=3) as ddgs:
                        raw = list(ddgs.text(query, max_results=5))
                        for r in raw:
                            ddg_result.append({
                                "title": r.get("title", ""),
                                "snippet": r.get("body", ""),
                                "url": r.get("href", ""),
                                "source": "DuckDuckGo",
                                "timestamp": datetime.now().isoformat(),
                            })
                except ImportError:
                    try:
                        from duckduckgo_search import DDGS
                        with DDGS(timeout=3) as ddgs:
                            raw = list(ddgs.text(query, max_results=5))
                            for r in raw:
                                ddg_result.append({
                                    "title": r.get("title", ""),
                                    "snippet": r.get("body", ""),
                                    "url": r.get("href", ""),
                                    "source": "DuckDuckGo",
                                    "timestamp": datetime.now().isoformat(),
                                })
                    except Exception as e2:
                        exc.append(str(e2))
                except Exception as e1:
                    exc.append(str(e1))
            t = threading.Thread(target=_ddgs, daemon=True)
            t.start()
            t.join(timeout=4)
            results = ddg_result
            if results:
                logger.info(f"[SEARCH_RESULT] DDGS: {len(results)} results (fast)")
        except Exception as e:
            logger.debug(f"[SEARCH_DEBUG] DDGS error: {e}")

        # Layer B: Quick DDG JSON API (faster, 3s)
        if not results:
            try:
                import httpx
                resp = httpx.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "kl": "cn-zh"},
                    timeout=3.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for topic in data.get("RelatedTopics", [])[:5]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append({
                                "title": topic.get("FirstURL", ""),
                                "snippet": topic.get("Text", "")[:300],
                                "url": topic.get("FirstURL", ""),
                                "source": "DuckDuckGo-API",
                            })
                    if results:
                        logger.info(f"[SEARCH_RESULT] DDG API: {len(results)} results")
            except Exception as e:
                logger.debug(f"[SEARCH_DEBUG] DDG API: {e}")

        # ━━━ FILTER & CLEAN ━━━
        if results:
            results = self._filter_search_results(results, query)

        # ━━━ SYSTEM CLOCK INJECTION (always included) ━━━
        today_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        for r in results:
            r["query_used"] = query
            r["retrieved_at"] = datetime.now().isoformat()

        # Always prepend system time for date queries
        if any(w in query.lower() for w in ["今天", "日期", "几号", "星期几", "today", "date", "时间"]):
            results.insert(0, {
                "title": "系统时钟",
                "snippet": f"当前精确时间：{today_str}（Asia/Shanghai，系统本地时钟，100%准确）",
                "url": "",
                "source": "system_clock",
            })

        # If completely empty, return time info so chat doesn't go empty
        if not results:
            results.append({
                "title": "系统信息",
                "snippet": f"当前时间：{today_str}。搜索'{query}'暂未返回结果，但我会基于已有知识回复。",
                "url": "",
                "source": "system_clock",
            })

        logger.info(f"[SEARCH_RESULT] Final: {len(results)} results for '{query[:60]}'")
        return results

    def _filter_search_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Filter out ads, spam, dictionary entries, irrelevant content.
        Cross-validate and prefer authoritative sources."""
        filtered = []
        # Noise patterns to reject
        noise_keywords = [
            "广告", "秒杀", "立即购买", "优惠券", "限时抢购", "点击查看",
            "sponsored", "advertisement", "promoted",
        ]
        # Authoritative source patterns
        authority_domains = [
            ".gov.cn", ".edu.cn", "wikipedia.org", "baike.baidu.com",
            "zhihu.com", "people.com.cn", "xinhuanet.com", "bbc.com",
            "reuters.com", "sina.com.cn", "sohu.com", "163.com",
        ]

        for r in results:
            snippet = r.get("snippet", "")
            title = r.get("title", "")
            url = r.get("url", "")
            combined = f"{title} {snippet}".lower()

            # Reject noise
            if any(nk in combined for nk in noise_keywords):
                continue
            # Reject dictionary definitions when searching for real-time/non-definition content
            if any(w in query for w in ["比分", "天气", "新闻", "赛程"]):
                if any(w in combined for w in ["释义", "读音", "部首", "笔画", "例句", "基本解释"]):
                    continue
            # Reject empty/too-short snippets
            if len(snippet.strip()) < 15:
                continue

            # Score by authority
            is_authority = any(ad in url for ad in authority_domains)
            r["_authority"] = is_authority

            # Clean snippet
            r["snippet"] = self._strip_html_tags(snippet)

            filtered.append(r)

        # Sort: authoritative sources first
        filtered.sort(key=lambda x: (not x.get("_authority", False), len(x.get("snippet", "")) < 50))

        return filtered[:8]

    def _strip_html_tags(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text).strip()

    # ═══════════════════════════════════════════
    # SEARCH ENGINES
    # ═══════════════════════════════════════════
    def _search_bing(self, query: str) -> List[Dict]:
        """Bing search with zh-cn locale, 5s timeout."""
        import httpx
        try:
            resp = httpx.get(
                "https://www.bing.com/search",
                params={"q": query, "setlang": "zh-cn", "cc": "cn"},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
                timeout=5.0,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                snippets = re.findall(r'<li class="b_algo"[^>]*>.*?<p[^>]*>(.*?)</p>', resp.text, re.DOTALL)
                results = []
                for s in snippets[:8]:
                    clean = re.sub(r'<[^>]+>', '', s).strip()
                    if clean and len(clean) > 10:
                        results.append({
                            "title": "",
                            "snippet": clean[:600],
                            "url": "",
                            "source": "Bing",
                            "timestamp": datetime.now().isoformat(),
                        })
                return results
        except Exception as e:
            logger.debug(f"[SEARCH_DEBUG] Bing: {e}")
        return []

    def _search_ddg_api(self, query: str) -> List[Dict]:
        """DuckDuckGo JSON API fallback, 5s timeout."""
        import httpx
        try:
            resp = httpx.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "kl": "cn-zh"},
                timeout=5.0,
                verify=False,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for topic in data.get("RelatedTopics", [])[:8]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                            "source": "DuckDuckGo-API",
                            "timestamp": datetime.now().isoformat(),
                        })
                return results
        except Exception as e:
            logger.debug(f"[SEARCH_DEBUG] DDG API: {e}")

        today_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        return [{
            "title": "搜索提示",
            "snippet": f"抱歉，我尝试搜索了「{query}」，但搜索引擎暂不可用。当前本地时间：{today_str}。请稍后重试或更换关键词。",
            "url": "",
            "source": "system",
            "timestamp": today_str,
        }]

    # ═══════════════════════════════════════════
    # KNOWLEDGE BASE - Milvus/ChromaDB/MySQL
    # ═══════════════════════════════════════════
    def _query_knowledge_base(self, db: DBSession, query: str) -> List[Dict]:
        try:
            from app.rag import VectorDBManager, VectorRetriever
            vector_db = VectorDBManager(
                host=os.getenv("MILVUS_HOST", "localhost"),
                port=int(os.getenv("MILVUS_PORT", "19530")),
                collection_name=os.getenv("COLLECTION_NAME", "agent_rag"),
            )
            rag = VectorRetriever(vector_db=vector_db)
            rag_result = rag.query(query, top_k=3)
            if rag_result["from_kb"] and rag_result["answer"]:
                sources = rag_result.get("sources", [])
                return [{
                    "content": rag_result["answer"],
                    "source_url": s.get("source", "RAG知识库") if isinstance(s, dict) else "RAG知识库",
                    "title": "RAG 检索结果",
                    "category": "rag",
                    "tags": "rag",
                    "relevance_score": sources[0].get("score", 0.8) if sources else 0.8,
                } for s in sources[:3]] if sources else [{
                    "content": rag_result["answer"],
                    "source_url": "RAG知识库",
                    "title": "RAG 检索结果",
                    "category": "rag",
                    "tags": "rag",
                    "relevance_score": 0.8,
                }]
        except Exception as e:
            logger.debug(f"RAG query skipped: {e}")

        # MySQL text search
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cached = db.query(KnowledgeCache).filter(
            KnowledgeCache.query_hash == query_hash,
            KnowledgeCache.expires_at > datetime.now(),
        ).first()
        if cached:
            cached.hit_count += 1
            db.commit()
            return json.loads(cached.result_json)

        try:
            results = db.query(KnowledgeItem).filter(
                KnowledgeItem.is_active == True,
                KnowledgeItem.content.contains(query[:100]),
            ).limit(5).all()
            if results:
                for r in results:
                    r.access_count += 1
                db.commit()
                items = [{
                    "id": r.id, "title": r.title, "content": r.content,
                    "source_url": r.source_url, "category": r.category,
                    "tags": r.tags, "relevance_score": r.relevance_score,
                } for r in results]
                cache = KnowledgeCache(
                    query_hash=query_hash, query_text=query[:1000],
                    result_json=json.dumps(items, ensure_ascii=False),
                    expires_at=datetime.now() + timedelta(hours=1),
                )
                db.add(cache)
                db.commit()
                return items
        except Exception as e:
            logger.warning(f"KB query failed: {e}")
        return []

    def _get_memory_context(self, db, user_id, session_id):
        from app.models import Session, Message, Preference
        memory = []
        try:
            session = db.query(Session).filter(Session.id == session_id, Session.is_active == True).first()
            if session and session.context_summary:
                memory.append({"type": "session_summary", "content": session.context_summary})
            messages = db.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.sequence.desc()).limit(20).all()
            for msg in reversed(messages):
                memory.append({"type": "message", "role": msg.role, "content": msg.content, "sequence": msg.sequence})
            prefs = db.query(Preference).filter(Preference.user_id == user_id).first()
            if prefs:
                memory.append({"type": "preferences", "tone_style": prefs.tone_style, "response_length": prefs.response_length})
        except:
            pass
        return memory

    def inject_file_contents(self, sources, file_data):
        sources.file_contents = file_data
        logger.info(f"[Layer 2] Injected {len(file_data)} file contents")