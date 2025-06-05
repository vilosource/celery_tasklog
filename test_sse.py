#!/usr/bin/env python3

import asyncio
import aiohttp
from aiohttp import web
import json

async def sse_handler(request):
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    await response.prepare(request)
    
    # Send initial message
    await response.write(f"data: {json.dumps({'type': 'connected'})}\n\n".encode())
    
    # Send periodic messages
    for i in range(10):
        await asyncio.sleep(1)
        message = {'type': 'message', 'count': i}
        await response.write(f"data: {json.dumps(message)}\n\n".encode())
    
    return response

app = web.Application()
app.router.add_get('/sse', sse_handler)

if __name__ == '__main__':
    web.run_app(app, host='localhost', port=9000)
