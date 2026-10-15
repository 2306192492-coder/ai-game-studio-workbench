import asyncio,json,shutil
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
async def main():
 command=shutil.which('unity')
 if not command:raise RuntimeError('Unity CLI is not available on PATH')
 (ROOT/'Evidence').mkdir(exist_ok=True)
 params=StdioServerParameters(command=command,args=['mcp','--project-path',str(ROOT/'Project')])
 async with stdio_client(params) as (read,write):
  async with ClientSession(read,write) as session:
   init=await session.initialize();catalog=await session.list_tools()
   candidates=[t for t in catalog.tools if t.name=='eval' or t.name.endswith('_eval')]
   if not candidates:raise RuntimeError([t.name for t in catalog.tools])
   code='return "AI_STUDIO_MCP_OK:" + UnityEngine.Application.dataPath;'
   result=await session.call_tool(candidates[0].name,{'code':code})
   texts=[c.text for c in result.content if c.type=='text']
   expected='AI_STUDIO_MCP_OK:' + (ROOT/'Project'/'Assets').as_posix()
   passed=not result.isError and any(expected in t.replace('\\','/') for t in texts)
   report=dict(passed=passed,server=init.serverInfo.model_dump(),toolCount=len(catalog.tools),calledTool=candidates[0].name,texts=texts)
   (ROOT/'Evidence'/'unity-mcp-verdict.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
   print(json.dumps(report,ensure_ascii=False),flush=True)
   assert passed
asyncio.run(asyncio.wait_for(main(),60))
