"""Minimal stdio MCP facade for Autoresearch Agent."""

from .server import StdioMcpServer, serve_stdio

__all__ = ["StdioMcpServer", "serve_stdio"]
