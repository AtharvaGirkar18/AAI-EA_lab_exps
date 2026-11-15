import asyncio, json, os, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

root = Path(__file__).resolve().parents[1]
async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(root / 'mcp_server.py')], env=os.environ.copy())
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool('run_tests', {'test_path':'test_calculator.py','timeout_seconds':30})
            print(json.dumps({'discovered_tools':[x.name for x in tools.tools], 'isError':result.isError, 'result':[getattr(x,'text','') for x in result.content]}, ensure_ascii=False))
asyncio.run(main())
