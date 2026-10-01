"""Official MCP SDK, stdio transport. Raw MCP writes are intentionally denied.

Use the graph's human-review flow to authorize a write. A caller cannot assert
its own approval by adding an argument to an MCP tool request.
"""
from mcp.server.fastmcp import FastMCP

from .tools import SPECS, Sandbox

server = FastMCP("secure-agentic-ai-sandbox")
sandbox = Sandbox()


def handler(name):
    def call(arguments: dict) -> dict:
        return sandbox.execute(name, arguments, role="viewer")
    call.__name__ = name
    return call


for spec in SPECS:
    server.add_tool(handler(spec.name), name=spec.name, description=spec.description)


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
