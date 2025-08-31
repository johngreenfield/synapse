# Synapse - Load Balancer
# This application acts as a reverse proxy and load balancer for the
# backend LLM server nodes. It distributes requests in a round-robin
# fashion and performs health checks to ensure requests are only sent
# to healthy nodes.

import aiohttp
import asyncio
from itertools import cycle
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response # Use the standard, non-streaming Response
from contextlib import asynccontextmanager

# --- Configuration ---
BACKEND_SERVERS = [
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost:8002",
]
HEALTH_CHECK_INTERVAL = 10  # in seconds

# --- Global Variables ---
healthy_servers = []
server_iterator = cycle(healthy_servers)

# --- Health Check Logic (using aiohttp) ---
async def health_check_task():
    """
    Periodically checks the health of the backend servers and updates
    the list of healthy servers.
    """
    global healthy_servers, server_iterator
    while True:
        currently_healthy = []
        async with aiohttp.ClientSession() as session:
            for server in BACKEND_SERVERS:
                try:
                    async with session.get(f"{server}/health", timeout=2) as response:
                        if response.status == 200:
                            currently_healthy.append(server)
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    print(f"Server {server} is down.")

        if set(currently_healthy) != set(healthy_servers):
            print(f"Healthy servers changed: {currently_healthy}")
            healthy_servers.clear()
            healthy_servers.extend(currently_healthy)
            server_iterator = cycle(healthy_servers)

        await asyncio.sleep(HEALTH_CHECK_INTERVAL)

# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup events for the application.
    Performs an initial health check and starts the background health check task.
    """
    print("--- Starting Synapse Load Balancer ---")
    global healthy_servers, server_iterator
    initially_healthy = []
    async with aiohttp.ClientSession() as session:
        for server in BACKEND_SERVERS:
            try:
                async with session.get(f"{server}/health", timeout=2) as response:
                    if response.status == 200:
                        initially_healthy.append(server)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass
    
    healthy_servers.extend(initially_healthy)
    server_iterator = cycle(healthy_servers)
    print(f"Initial healthy servers: {healthy_servers}")

    asyncio.create_task(health_check_task())
    
    yield
    
    print("--- Shutting down Synapse Load Balancer ---")

# --- FastAPI Application ---
app = FastAPI(title="Synapse - Load Balancer", lifespan=lifespan)

# --- Final Proxy Logic (Standard Non-Streaming Proxy) ---
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    """
    Catches all incoming requests, forwards them, waits for the full response,
    and then forwards that full response back to the client.
    """
    if not healthy_servers:
        raise HTTPException(status_code=503, detail="No healthy backend servers available.")

    target_server = next(server_iterator)
    print(f"Forwarding request to {target_server}")
    
    url = f"{target_server}/{path}"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Recreate headers, excluding the Host header
            backend_headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
            
            async with session.request(
                method=request.method,
                url=url,
                headers=backend_headers,
                params=request.query_params,
                data=await request.body(),
                timeout=aiohttp.ClientTimeout(total=120.0)
            ) as response:
                
                # Read the entire response body from the backend server.
                content = await response.read()

                # Filter hop-by-hop headers that shouldn't be forwarded.
                response_headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() not in ("transfer-encoding", "connection")
                }
                
                # Return a standard FastAPI Response with the full content.
                return Response(
                    content=content,
                    status_code=response.status,
                    headers=response_headers,
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        raise HTTPException(status_code=502, detail=f"Bad Gateway or connection error: {e}")
