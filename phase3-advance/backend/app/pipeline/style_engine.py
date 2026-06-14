"""
Style Generator Engine - Dynamic template system for Word/Excel/PPT.
Supports: user-defined styles, preference learning, web template search, built-in presets.
"""
import re, json, os
from typing import Dict, Any, Optional, Tuple
from loguru import logger



# ═══════════════════════════════════════════
# BUILT-IN TEMPLATE LIBRARY (6 presets)
# ═══════════════════════════════════════════

PRESET_TEMPLATES = {
    "学术严谨风": {
        "keywords": ["学术", "严谨", "论文", "答辩", "研究", "正式", "学术风", "学术蓝"],
        "word": {
            "theme": "academic",
            "fonts": {"title": "黑体", "h1": "黑体", "h2": "黑体", "body": "宋体", "size_title": 22, "size_h1": 16, "size_h2": 14, "size_body": 12},
            "colors": {"title": "1A3A5C", "h1": "1A3A5C", "h2": "2C5F8A", "accent": "C49A2B", "cover_bg": "1A3A5C", "cover_text": "FFFFFF"},
            "spacing": {"line": 1.5, "indent": True, "title_before": 24, "h1_before": 18, "h2_before": 12},
        },
        "excel": {
            "theme": "professional",
            "fonts": {"header": "黑体", "data": "宋体"},
            "colors": {"header_bg": "1A3A5C", "header_fg": "FFFFFF", "alt1": "FFFFFF", "alt2": "E8EDF2", "border": "B8CCE4"},
        },
        "ppt": {
            "theme": "academic_blue",
            "fonts": {"title": "黑体", "body": "微软雅黑"},
            "colors": {"bg": "1A3A5C", "accent": "C49A2B", "text_light": "FFFFFF", "text_dark": "1F2937"},
        },
    },
    "商务专业风": {
        "keywords": ["商务", "专业", "商业", "企业", "汇报", "职场", "商务风", "商务蓝", "商业报告"],
        "word": {
            "theme": "business",
            "fonts": {"title": "微软雅黑", "h1": "微软雅黑", "h2": "微软雅黑", "body": "微软雅黑", "size_title": 20, "size_h1": 15, "size_h2": 13, "size_body": 11},
            "colors": {"title": "1E3A5F", "h1": "1E3A5F", "h2": "34495E", "accent": "2980B9", "cover_bg": "1E3A5F", "cover_text": "FFFFFF"},
            "spacing": {"line": 1.3, "indent": True, "title_before": 20, "h1_before": 14, "h2_before": 10},
        },
        "excel": {
            "theme": "corporate",
            "fonts": {"header": "微软雅黑", "data": "微软雅黑"},
            "colors": {"header_bg": "002060", "header_fg": "FFFFFF", "alt1": "FFFFFF", "alt2": "E6EDF5", "border": "B8CCE4"},
        },
        "ppt": {
            "theme": "elegant_gray",
            "fonts": {"title": "微软雅黑", "body": "微软雅黑"},
            "colors": {"bg": "2D3436", "accent": "0984E3", "text_light": "FFFFFF", "text_dark": "2D3436"},
        },
    },
    "简约现代风": {
        "keywords": ["简约", "现代", "极简", "清新", "简洁", "白色", "纯净", "现代风", "简约风"],
        "word": {
            "theme": "modern",
            "fonts": {"title": "微软雅黑", "h1": "微软雅黑", "h2": "微软雅黑", "body": "微软雅黑", "size_title": 24, "size_h1": 16, "size_h2": 14, "size_body": 11},
            "colors": {"title": "2563EB", "h1": "1E40AF", "h2": "3B82F6", "accent": "F59E0B", "cover_bg": "FFFFFF", "cover_text": "2563EB"},
            "spacing": {"line": 1.5, "indent": False, "title_before": 28, "h1_before": 20, "h2_before": 14},
        },
        "excel": {
            "theme": "professional",
            "fonts": {"header": "微软雅黑", "data": "微软雅黑"},
            "colors": {"header_bg": "2563EB", "header_fg": "FFFFFF", "alt1": "FFFFFF", "alt2": "EFF6FF", "border": "BFDBFE"},
        },
        "ppt": {
            "theme": "modern_clean",
            "fonts": {"title": "微软雅黑", "body": "微软雅黑"},
            "colors": {"bg": "FFFFFF", "accent": "2563EB", "text_light": "FFFFFF", "text_dark": "1E293B"},
        },
    },
    "科技感": {
        "keywords": ["科技", "科技感", "未来", "数字", "智能", "AI", "tech", "技术"],
        "word": {
            "theme": "modern",
            "fonts": {"title": "微软雅黑", "h1": "微软雅黑", "h2": "微软雅黑", "body": "微软雅黑", "size_title": 24, "size_h1": 16, "size_h2": 14, "size_body": 11},
            "colors": {"title": "00B4D8", "h1": "0077B6", "h2": "00B4D8", "accent": "48CAE4", "cover_bg": "03045E", "cover_text": "FFFFFF"},
            "spacing": {"line": 1.4, "indent": False, "title_before": 24, "h1_before": 16, "h2_before": 12},
        },
        "excel": {
            "theme": "professional",
            "fonts": {"header": "微软雅黑", "data": "微软雅黑"},
            "colors": {"header_bg": "0077B6", "header_fg": "FFFFFF", "alt1": "FFFFFF", "alt2": "E0F2FE", "border": "BAE6FD"},
        },
        "ppt": {
            "theme": "academic_blue",
            "fonts": {"title": "微软雅黑", "body": "微软雅黑"},
            "colors": {"bg": "03045E", "accent": "00B4D8", "text_light": "FFFFFF", "text_dark": "1E293B"},
        },
    },
    "中国风": {
        "keywords": ["中国风", "中国", "传统", "古典", "国风", "古风", "中式"],
        "word": {
            "theme": "academic",
            "fonts": {"title": "黑体", "h1": "黑体", "h2": "楷体", "body": "宋体", "size_title": 22, "size_h1": 16, "size_h2": 14, "size_body": 12},
            "colors": {"title": "8B0000", "h1": "8B0000", "h2": "B22222", "accent": "DAA520", "cover_bg": "8B0000", "cover_text": "FFD700"},
            "spacing": {"line": 1.6, "indent": True, "title_before": 24, "h1_before": 18, "h2_before": 12},
        },
        "excel": {
            "theme": "professional",
            "fonts": {"header": "黑体", "data": "宋体"},
            "colors": {"header_bg": "8B0000", "header_fg": "FFD700", "alt1": "FFFFFF", "alt2": "FFF5F5", "border": "FECACA"},
        },
        "ppt": {
            "theme": "academic_blue",
            "fonts": {"title": "黑体", "body": "宋体"},
            "colors": {"bg": "8B0000", "accent": "DAA520", "text_light": "FFD700", "text_dark": "2D1810"},
        },
    },
    "清新自然风": {
        "keywords": ["清新", "自然", "绿色", "环保", "生态", "健康", "温暖", "柔和"],
        "word": {
            "theme": "modern",
            "fonts": {"title": "微软雅黑", "h1": "微软雅黑", "h2": "微软雅黑", "body": "微软雅黑", "size_title": 22, "size_h1": 16, "size_h2": 14, "size_body": 11},
            "colors": {"title": "059669", "h1": "047857", "h2": "059669", "accent": "F59E0B", "cover_bg": "ECFDF5", "cover_text": "059669"},
            "spacing": {"line": 1.5, "indent": True, "title_before": 22, "h1_before": 16, "h2_before": 12},
        },
        "excel": {
            "theme": "professional",
            "fonts": {"header": "微软雅黑", "data": "微软雅黑"},
            "colors": {"header_bg": "059669", "header_fg": "FFFFFF", "alt1": "FFFFFF", "alt2": "ECFDF5", "border": "A7F3D0"},
        },
        "ppt": {
            "theme": "modern_clean",
            "fonts": {"title": "微软雅黑", "body": "微软雅黑"},
            "colors": {"bg": "ECFDF5", "accent": "059669", "text_light": "FFFFFF", "text_dark": "064E3B"},
        },
    },
}


class StyleEngine:
    """
    Dynamic style generator for document templates.
    Priority: user-specified → preference learning → web search → built-in presets.
    """

    def __init__(self):
        self.presets = PRESET_TEMPLATES
        self._preference_cache = {}

    def resolve_style(self, message: str, user_prefs: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Resolve the best style config for a given user message and preferences.

        Args:
            message: User input message
            user_prefs: User preference dict from memory (tone_style, learned_facts, etc.)

        Returns:
            Style config dict with word/excel/ppt sections
        """
        # Priority 1: User-specified style keywords in message
        style_name, style_config = self._match_user_keywords(message)
        if style_config:
            logger.info(f"🎨 Matched user style: {style_name}")
            return {"style_name": style_name, "source": "user_specified", **style_config}

        # Priority 2: User preference from memory
        pref_style = self._get_preference_style(user_prefs)
        if pref_style:
            style_name, style_config = self._match_user_keywords(pref_style)
            if style_config:
                logger.info(f"🎨 Using preference style: {style_name}")
                return {"style_name": style_name, "source": "preference", **style_config}

        # Priority 3: Try web search for template reference (graceful fallback)
        web_style = self._try_web_search(message)
        if web_style:
            style_name, style_config = self._match_user_keywords(web_style)
            if style_config:
                logger.info(f"🎨 Using web-searched style: {style_name}")
                return {"style_name": style_name, "source": "web_search", **style_config}

        # Priority 4: Default to "商务专业风" (most universal)
        default = self.presets.get("商务专业风")
        logger.info("🎨 Using default style: 商务专业风")
        return {"style_name": "商务专业风", "source": "default", **default}

    def _match_user_keywords(self, text: str) -> Tuple[str, Optional[Dict]]:
        """Match user text against preset template keywords."""
        if not text:
            return ("", None)
        text_lower = text.lower()

        # Score each preset by keyword matches
        best_score = 0
        best_name = ""
        best_config = None

        for name, config in self.presets.items():
            keywords = config.get("keywords", [])
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            # Exact style name match gets bonus
            if name.lower() in text_lower:
                score += 5
            if score > best_score:
                best_score = score
                best_name = name
                best_config = config

        if best_score >= 1:
            return (best_name, best_config)

        # Check for custom color specification
        color_match = re.search(r'#([0-9A-Fa-f]{6})', text)
        if color_match:
            # Use modern style as base, customize with user color
            custom = self._customize_color("简约现代风", f"#{color_match.group(1)}")
            return ("自定义配色", custom)

        # Check for general style hints
        if any(w in text_lower for w in ["蓝色", "blue"]):
            return self._match_user_keywords("商务")
        if any(w in text_lower for w in ["红色", "red"]):
            return ("中国风", self.presets.get("中国风"))
        if any(w in text_lower for w in ["绿色", "green"]):
            return ("清新自然风", self.presets.get("清新自然风"))
        if any(w in text_lower for w in ["黑色", "暗色", "dark"]):
            return ("商务专业风", self.presets.get("商务专业风"))

        return ("", None)

    def _customize_color(self, base_name: str, primary_color: str) -> Optional[Dict]:
        """Create a customized style based on an existing preset with a new primary color."""
        base = self.presets.get(base_name)
        if not base:
            return None

        import copy
        custom = copy.deepcopy(base)
        hex_color = primary_color.lstrip("#")

        # Update all color references to use the custom primary color
        def update_colors(section, key):
            if section and isinstance(section, dict):
                for k, v in section.items():
                    if k.endswith("bg") or k == "title" or k == "h1" or k == "header_bg":
                        if isinstance(v, str) and len(v) == 6:
                            section[k] = hex_color

        update_colors(custom.get("word", {}).get("colors"), "title")
        update_colors(custom.get("excel", {}).get("colors"), "header_bg")
        update_colors(custom.get("ppt", {}).get("colors"), "bg")

        custom["keywords"] = [f"自定义配色 #{primary_color}"]
        return custom

    def _get_preference_style(self, user_prefs: Optional[Dict]) -> Optional[str]:
        """Extract preferred style from user preferences."""
        if not user_prefs:
            return None

        # Check learned_facts for style hints
        facts = user_prefs.get("learned_facts", "")
        if facts:
            try:
                if isinstance(facts, str):
                    facts_list = json.loads(facts)
                else:
                    facts_list = facts
                for fact in facts_list:
                    for name in PRESET_TEMPLATES.keys():
                        if name in str(fact):
                            return name
            except:
                pass

        # Check tone_style mapping
        tone_map = {
            "formal": "学术严谨风",
            "concise": "简约现代风",
            "friendly": "清新自然风",
            "detailed": "商务专业风",
            "humorous": "简约现代风",
        }
        tone = user_prefs.get("tone_style", "")
        if tone in tone_map:
            return tone_map[tone]

        # Check like/dislike ratio for learning
        likes = user_prefs.get("like_count", 0)
        dislikes = user_prefs.get("dislike_count", 0)
        if likes > dislikes and likes > 3:
            # User has strong positive history, return most professional
            return "商务专业风"
        elif dislikes > likes and dislikes > 3:
            # User has negative history, try alternate
            return "简约现代风"

        return None

    def _try_web_search(self, message: str) -> Optional[str]:
        """
        Try to search for template style references online.
        Falls back gracefully if network unavailable.
        """
        try:
            import httpx
            # Try to extract searchable keywords
            keywords = []
            for name, config in PRESET_TEMPLATES.items():
                for kw in config.get("keywords", []):
                    if kw in message:
                        keywords.append(kw)
            if not keywords:
                return None

            search_query = f"{' '.join(keywords)} 模板配色方案 site:officeplus.cn OR site:canva.cn"
            resp = httpx.get(
                "https://api.duckduckgo.com/",
                params={"q": search_query, "format": "json", "no_html": 1},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Extract style-related snippets
                snippets = []
                for topic in data.get("RelatedTopics", [])[:3]:
                    text = topic.get("Text", "")
                    # Look for color/customization hints
                    for name in PRESET_TEMPLATES.keys():
                        if name in text:
                            return name
                    snippets.append(text)
                return " ".join(snippets[:2])
        except Exception as e:
            logger.debug(f"Web template search skipped: {e}")

        return None

    def learn_from_feedback(self, style_name: str, feedback_type: str, db_session):
        """
        Update user preferences based on like/dislike feedback.
        style_name: The style name used for the generated file
        feedback_type: "like" or "dislike"
        """
        try:
            from app.models import Preference
            pref = db_session.query(Preference).filter(Preference.user_id == "default_user").first()
            if not pref:
                return

            if feedback_type == "like":
                pref.like_count += 1
                # Add this style to learned facts
                facts = []
                if pref.learned_facts:
                    try: facts = json.loads(pref.learned_facts)
                    except: pass
                fact_entry = f"喜欢{style_name}风格的文件"
                if fact_entry not in facts:
                    facts.append(fact_entry)
                    pref.learned_facts = json.dumps(facts, ensure_ascii=False)
            elif feedback_type == "dislike":
                pref.dislike_count += 1

            pref.updated_at = __import__('datetime').datetime.now()
            db_session.commit()
            logger.info(f"📝 Style preference learned: {style_name} → {feedback_type}")
        except Exception as e:
            logger.warning(f"Preference learning failed: {e}")

    def apply_to_prompt(self, style_config: Dict[str, Any], generation_type: str, base_prompt: str) -> str:
        """
        Enhance a generation prompt with style-specific instructions.
        generation_type: "word", "excel", or "ppt"
        """
        style_name = style_config.get("style_name", "默认")
        type_config = style_config.get(generation_type, {})

        if not type_config:
            return base_prompt

        colors = type_config.get("colors", {})
        fonts = type_config.get("fonts", {})

        style_instruction = f"\n\n【样式要求 - {style_name}】\n"
        if colors:
            style_instruction += f"配色：主色调 {colors.get('title', colors.get('header_bg',''))}，点缀色 {colors.get('accent','')}。\n"
        if fonts:
            font_list = [v for k, v in fonts.items() if k not in ("size_title", "size_h1", "size_h2", "size_body")]
            style_instruction += f"字体：{', '.join(set(font_list))}。\n"

        return base_prompt + style_instruction