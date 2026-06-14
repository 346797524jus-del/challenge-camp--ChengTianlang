"""
MCP Manager - Multi-Server MCP Client using langchain-mcp-adapters.
Connects to weather, write, amap-maps MCP servers.
Tools are merged with custom tools and passed to the Agent.
"""
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from app.config import get_settings, MCP_DIR


class MCPTool:
    """Represents a tool from an MCP server."""

    def __init__(self, name: str, description: str, server_name: str,
                 input_schema: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.server_name = server_name
        self.input_schema = input_schema or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "server": self.server_name,
            "input_schema": self.input_schema,
        }


class MCPManager:
    """
    Manages multiple MCP server connections.
    Loads config from servers_config.json, initializes connections,
    and provides tools to the Agent pipeline.
    """

    def __init__(self, config_path: Optional[str] = None):
        settings = get_settings()
        self._config_path = config_path or str(MCP_DIR / "servers_config.json")
        self._servers_config: Dict[str, Any] = {}
        self._tools: List[MCPTool] = []
        self._connected = False
        self._load_config()

    def _load_config(self):
        """Load MCP servers configuration from JSON file."""
        try:
            config_file = Path(self._config_path)
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    self._servers_config = json.load(f)
                logger.info(
                    f"📡 Loaded MCP config: {len(self._servers_config.get('mcpServers', {}))} servers"
                )
            else:
                logger.warning(f"MCP config not found at {self._config_path}")
                self._servers_config = {"mcpServers": {}}
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            self._servers_config = {"mcpServers": {}}

    def get_tools(self) -> List[MCPTool]:
        """
        Get all loaded MCP tools.
        In production, this would connect to actual MCP servers via langchain-mcp-adapters.
        For now, we register mock tools based on the server config.
        """
        if self._tools:
            return self._tools

        servers = self._servers_config.get("mcpServers", {})

        # Weather server tools
        if "weather" in servers:
            self._tools.append(MCPTool(
                name="get_weather_forecast",
                description="获取指定城市的天气预报，包括温度、湿度、天气状况等信息",
                server_name="weather",
                input_schema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称，如'北京'、'上海'"},
                        "days": {"type": "integer", "description": "预报天数，默认3天"},
                    },
                    "required": ["city"],
                },
            ))
            self._tools.append(MCPTool(
                name="get_current_weather",
                description="获取指定城市的实时天气信息",
                server_name="weather",
                input_schema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"},
                    },
                    "required": ["city"],
                },
            ))

        # Write server tools
        if "write" in servers:
            self._tools.append(MCPTool(
                name="write_file",
                description="写入文件内容到指定路径",
                server_name="write",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "文件内容"},
                    },
                    "required": ["path", "content"],
                },
            ))

        # Amap Maps server tools (SSE)
        if "amap-maps" in servers:
            self._tools.append(MCPTool(
                name="search_places",
                description="在高德地图中搜索地点信息",
                server_name="amap-maps",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keywords": {"type": "string", "description": "搜索关键词"},
                        "city": {"type": "string", "description": "城市名称"},
                    },
                    "required": ["keywords"],
                },
            ))
            self._tools.append(MCPTool(
                name="get_directions",
                description="获取两点之间的路线规划",
                server_name="amap-maps",
                input_schema={
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string", "description": "起点"},
                        "destination": {"type": "string", "description": "终点"},
                    },
                    "required": ["origin", "destination"],
                },
            ))

        logger.info(f"🔧 Registered {len(self._tools)} MCP tools")
        return self._tools

    def get_tools_description(self) -> str:
        """Get a text description of all MCP tools for the system prompt."""
        tools = self.get_tools()
        if not tools:
            return ""

        lines = ["\n## MCP 工具说明\n"]
        for tool in tools:
            lines.append(f"- **{tool.name}** (来自 {tool.server_name}): {tool.description}")

        return "\n".join(lines)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an MCP tool with the given arguments.
        Returns the tool result.
        """
        logger.info(f"🔧 Executing MCP tool: {tool_name} with args: {arguments}")

        # Mock executions for MVP - in production this would call actual MCP servers
        if tool_name in ("get_weather_forecast", "get_current_weather"):
            return await self._mock_weather(tool_name, arguments)
        elif tool_name == "write_file":
            return await self._mock_write(arguments)
        elif tool_name in ("search_places", "get_directions"):
            return await self._mock_amap(tool_name, arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    async def _mock_weather(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Mock weather tool for MVP (will connect to real MCP in production)."""
        city = args.get("city", "北京")
        days = args.get("days", 3)

        # In production: call actual MCP weather server
        weather_data = {
            "city": city,
            "forecast": [
                {"date": "今天", "temp_high": 28, "temp_low": 18, "condition": "晴转多云", "humidity": 55},
                {"date": "明天", "temp_high": 26, "temp_low": 17, "condition": "多云", "humidity": 60},
                {"date": "后天", "temp_high": 24, "temp_low": 16, "condition": "小雨", "humidity": 75},
            ][:days],
        }
        return weather_data

    async def _mock_write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Mock write tool for MVP."""
        path = args.get("path", "")
        content = args.get("content", "")
        return {"path": path, "bytes_written": len(content), "success": True}

    async def _mock_amap(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Amap tool for MVP."""
        if tool_name == "search_places":
            return {
                "keywords": args.get("keywords", ""),
                "results": [
                    {"name": "搜索结果1", "address": "示例地址1", "location": "116.397,39.908"},
                ],
            }
        else:
            return {
                "origin": args.get("origin", ""),
                "destination": args.get("destination", ""),
                "distance": "5.2km",
                "duration": "15分钟",
            }

    def get_system_prompt_appendix(self) -> str:
        """
        Build system prompt appendix describing available MCP tools.
        This is injected into the LLM system prompt so the agent knows
        what tools are available and how to use them.
        """
        tools = self.get_tools()
        if not tools:
            return ""

        prompt = "\n\n## 可用工具（MCP协议集成）\n"
        prompt += "你可以调用以下工具来获取实时信息或执行操作：\n\n"
        for tool in tools:
            prompt += f"- **{tool.name}**: {tool.description}\n"
            if tool.input_schema.get("properties"):
                props = tool.input_schema["properties"]
                required = tool.input_schema.get("required", [])
                for prop_name, prop_info in props.items():
                    req_mark = " *[必填]*" if prop_name in required else ""
                    prompt += f"  - `{prop_name}`{req_mark}: {prop_info.get('description', '')}\n"

        return prompt

    async def cleanup(self):
        """Clean up all MCP server connections."""
        logger.info("🧹 Cleaning up MCP connections...")
        self._tools.clear()
        self._connected = False


# Singleton
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get or create the singleton MCP manager."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager