"""
Layer 4: Output Presentation Layer
Formats cleaned data into user-facing responses with personalization.
All user-visible output passes through this layer as the final formatting step.
Adjusts tone, detail level, and style based on user preferences.
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from loguru import logger
from openai import OpenAI
from app.config import get_settings

# Xiaoshitou identity prompt for output personalization
XIAOSHITOU_STYLE_PROMPT = (
    "你是「小石头」，一颗坚固可靠、温暖风趣的小石子🪨。"
    "回复必须结构化（标题、分段、列表、表格、加粗），禁止大段纯文本。"
    "语气温暖亲切如老朋友，自称「我这颗小石头」。"
    "禁止使用AI助手泛化表述。有数据用表格，有来源用引用。"
)


class FormattedOutput(BaseModel):
    """Final formatted output ready for user display."""
    content: str = ""
    content_type: str = "text"  # text, markdown, file_path
    sources: List[Dict[str, str]] = []
    suggested_actions: List[str] = []
    generated_files: List[Dict[str, str]] = []
    metadata: Dict[str, Any] = {}


class OutputPresentationLayer:
    """
    Layer 4: Formats processed data into personalized, user-friendly output.
    - Applies user preference-based tone/style adjustments
    - Adds personality to assistant responses
    - Formats with appropriate detail level
    - Ensures no raw/internal data leaks to user
    """

    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._client = None
        self.model = settings.ai_model_name

    @property
    def client(self):
        if self._client is None:
            api_key = self._settings.ai_api_key or "sk-placeholder"
            self._client = OpenAI(
                base_url=self._settings.ai_api_base_url,
                api_key=api_key,
            )
        return self._client

    def format(
        self,
        processed: Any,  # ProcessedData
        intent: Any,  # UserIntent
        preferences: Optional[Dict[str, Any]] = None,
        assistant_nickname: str = "小石头",
    ) -> FormattedOutput:
        """
        Format processed data into final user-facing output.

        Args:
            processed: Cleaned data from Layer 3
            intent: Original user intent
            preferences: User preferences for tone/style
            assistant_nickname: Custom nickname for the assistant

        Returns:
            FormattedOutput ready for user display
        """
        logger.info(f"[Layer 4] Formatting output with tone: {preferences.get('tone_style', 'friendly') if preferences else 'friendly'}")

        # Build style instructions
        style_instructions = self._build_style_instructions(preferences, assistant_nickname)

        # Format based on content type
        formatted = self._format_content(processed, intent, style_instructions)

        # Attach metadata
        formatted.metadata = {
            "assistant_nickname": assistant_nickname,
            "intent": intent.primary_intent,
            "tone_style": preferences.get("tone_style", "friendly") if preferences else "friendly",
            "sources_count": len(formatted.sources),
            "generated_files_count": len(formatted.generated_files),
        }

        return formatted

    def _build_style_instructions(
        self, preferences: Optional[Dict[str, Any]], nickname: str
    ) -> str:
        """Build style instructions based on user preferences."""
        tone = preferences.get("tone_style", "friendly") if preferences else "friendly"
        length = preferences.get("response_length", "medium") if preferences else "medium"
        learned_facts = preferences.get("learned_facts", "") if preferences else ""

        styles = {
            "friendly": f"以亲切友好的语气回复，像朋友一样。称呼自己为「{nickname}」。",
            "formal": "以正式专业的语气回复，使用敬语。",
            "concise": "回复简洁明了，直击要点，不啰嗦。",
            "detailed": "回复详细全面，提供丰富的信息和解释。",
            "humorous": "以轻松幽默的语气回复，但保持信息准确。",
        }

        lengths = {
            "short": "保持回复简短，不超过200字。",
            "medium": "回复长度适中，300-800字。",
            "long": "提供详细回复，可以超过800字。",
        }

        instructions = styles.get(tone, styles["friendly"])
        instructions += " " + lengths.get(length, lengths["medium"])

        if learned_facts:
            try:
                facts = json.loads(learned_facts) if isinstance(learned_facts, str) else learned_facts
                if isinstance(facts, list) and len(facts) > 0:
                    facts_text = "；".join(facts[:5])
                    instructions += f" 已知用户背景：{facts_text}。"
            except:
                pass

        return instructions

    def _format_content(
        self, processed: Any, intent: Any, style_instructions: str
    ) -> FormattedOutput:
        """Format content with LLM for personality and style."""
        content = processed.cleaned_content

        if not content or content == intent.raw_message:
            # For simple chat, the content itself is the output
            return FormattedOutput(
                content=content,
                content_type="text",
                sources=[],
            )

        # For processed data, add formatting polish
        try:
            prompt = f"""请按照以下风格要求重新润色回复内容。保持信息准确，不要添加虚假信息。

风格要求：{style_instructions}

原始回复内容：
{content}

请返回润色后的完整回复（纯文本，不需要JSON格式）。
如果是搜索类回复，请保留信息来源标注。"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"你是{style_instructions}"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            polished = response.choices[0].message.content
            if polished:
                content = polished
        except Exception as e:
            logger.warning(f"[Layer 4] Content polishing failed: {e}")

        return FormattedOutput(
            content=content,
            content_type="markdown",
            sources=processed.sources,
            generated_files=processed.generated_files,
        )

    def format_error(self, error_message: str) -> FormattedOutput:
        """Format error messages in a user-friendly way."""
        friendly_errors = {
            "rate_limit": "我现在有点忙，请稍等一下再问我～",
            "timeout": "处理时间较长，请简化您的问题试试。",
            "api_error": "暂时无法连接到AI服务，请稍后重试。",
            "file_too_large": "文件太大了，请上传小于20MB的文件。",
            "unsupported_format": "不支持此文件格式，请上传PDF、Word、Excel、CSV、TXT或图片文件。",
        }

        for key, msg in friendly_errors.items():
            if key in error_message.lower():
                return FormattedOutput(content=msg, content_type="text")

        return FormattedOutput(
            content=f"抱歉，遇到了一点小问题：{error_message}",
            content_type="text",
        )

    def format_thinking_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format thinking steps for frontend display.
        Ensures no internal tool parameters or API URLs are exposed.
        """
        safe_steps = []
        status_map = {
            "pending": "等待中",
            "running": "进行中",
            "completed": "已完成",
            "failed": "失败",
        }

        for step in steps:
            safe_step = {
                "id": step.get("task_id", step.get("id", "")),
                "step": self._sanitize_description(step.get("description", step.get("step", ""))),
                "module": step.get("module", ""),
                "status": step.get("status", "pending"),
                "status_text": status_map.get(step.get("status", "pending"), "等待中"),
                "detail": step.get("detail", ""),
            }
            # Remove any API keys, URLs, internal params
            for key in list(safe_step.keys()):
                if key in ["api_key", "api_url", "token", "password", "internal_params"]:
                    del safe_step[key]
            safe_steps.append(safe_step)

        return safe_steps

    def _sanitize_description(self, description: str) -> str:
        """Remove any potentially sensitive information from descriptions."""
        import re
        # Remove URLs
        description = re.sub(r'https?://\S+', '[链接]', description)
        # Remove API keys (alphanumeric strings > 30 chars)
        description = re.sub(r'[A-Za-z0-9_-]{32,}', '[密钥]', description)
        # Remove IP addresses
        description = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP]', description)
        return description