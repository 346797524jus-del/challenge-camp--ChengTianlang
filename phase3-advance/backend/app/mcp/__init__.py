"""
MCP Protocol Integration - Multi-Server MCP Client
Uses langchain-mcp-adapters to connect weather, write, and amap-maps MCP servers.
"""
from app.mcp.mcp_manager import MCPManager, get_mcp_manager

__all__ = ["MCPManager", "get_mcp_manager"]