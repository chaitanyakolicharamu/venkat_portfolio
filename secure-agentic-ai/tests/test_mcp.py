import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_real_mcp_handshake_discovery_and_policy():
    params = StdioServerParameters(command=sys.executable, args=["-m", "agent_platform.mcp_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert len(listed.tools) == 14
            health = await session.call_tool("service_health", {"arguments": {"service": "claims-api"}})
            assert not health.isError
            assert "degraded" in str(health)
            denied = await session.call_tool("revoke_access", {"arguments": {"user_id": "demo-analyst"}})
            assert denied.isError
