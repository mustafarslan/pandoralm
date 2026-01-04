
import os
import sys
import logging
import shlex
import asyncio
from typing import Optional

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
from starlette.requests import Request
from mcp.server.sse import SseServerTransport
from mcp.client.stdio import StdioServerParameters, stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-bridge")

# Configuration from Environment
MCP_COMMAND = os.getenv("MCP_COMMAND")
MCP_ARGS = os.getenv("MCP_ARGS", "")

if not MCP_COMMAND:
    logger.error("MCP_COMMAND environment variable is required")
    # For testing purposes, we might default or exit. 
    # sys.exit(1) 

subprocess_env = os.environ.copy()

sse_transport = SseServerTransport("/messages")

async def handle_sse(scope, receive, send):
    """
    Raw ASGI endpoint to handle the SSE connection lifecycle via mcp SDK.
    """
    async with sse_transport.connect_sse(scope, receive, send) as streams:
        read_stream, write_stream = streams
        
        args = shlex.split(MCP_ARGS)
        server_params = StdioServerParameters(command=MCP_COMMAND, args=args, env=subprocess_env)
        
        logger.info(f"New SSE connection. Spawning: {MCP_COMMAND} {args}")

        try:
            async with stdio_client(server_params) as (proc_read, proc_write):
                
                # Task: Forward SSE -> Subprocess
                async def forward_to_proc():
                    try:
                        async for msg in read_stream:
                            await proc_write.send(msg)
                    except Exception as e:
                        logger.error(f"Error forwarding to subprocess: {e}")

                # Task: Forward Subprocess -> SSE
                async def forward_to_sse():
                    try:
                        async for msg in proc_read:
                            await write_stream.send(msg)
                    except Exception as e:
                        logger.error(f"Error forwarding to SSE: {e}")

                # Run both
                t1 = asyncio.create_task(forward_to_proc())
                t2 = asyncio.create_task(forward_to_sse())
                
                # Wait until one finishes (usually connection closed)
                done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
        except Exception as e:
            logger.error(f"Subprocess failed to start or crashed: {e}")
            # If subprocess fails, the SSE connection closes

async def handle_messages(request: Request):
    """
    Handle incoming POST messages for the SSE session.
    """
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return Response("OK", status_code=200)

routes = [
    Route("/sse", endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"])
]

app = Starlette(debug=True, routes=routes)
