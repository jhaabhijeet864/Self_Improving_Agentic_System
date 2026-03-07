"""
Jarvis-OS Dashboard API - Complete FastAPI Implementation
Provides real-time metrics, WebSocket support, and agent control
"""

from fastapi import FastAPI, WebSocket, HTTPException, Query, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import asdict
import os

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import jwt
import database

import jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import Jarvis components
from jarvis_os import JarvisOS, AgentConfig
from fast_router import TaskPriority
from autopsy import Autopsy, LogEntry

app = FastAPI(
    title="Jarvis-OS Dashboard API",
    description="Real-time dashboard and API for Jarvis-OS agents",
    version="1.0.0"
)

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Auth Configuration
JARVIS_ADMIN_SECRET = os.getenv("JARVIS_ADMIN_SECRET", "super-secret-default-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JARVIS_ADMIN_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JARVIS_ADMIN_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/auth/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # In a real app we'd verify against a DB. Here we use the admin secret as password.
    if form_data.password != JARVIS_ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Incorrect password or secret")
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Global agent instance
agent: Optional[JarvisOS] = None
active_connections: List[WebSocket] = []

# --- Auth & Rate Limiting (Gaps 8, 18) ---
JARVIS_ADMIN_SECRET = os.environ.get('JARVIS_ADMIN_SECRET', 'secret')
ALGORITHM = 'HS256'

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/token')

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JARVIS_ADMIN_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail='Invalid token')

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.post('/api/token')
@limiter.limit('5/minute')
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.password != JARVIS_ADMIN_SECRET:
        raise HTTPException(status_code=400, detail='Incorrect password')
    token = jwt.encode({'sub': form_data.username}, JARVIS_ADMIN_SECRET, algorithm=ALGORITHM)
    return {'access_token': token, 'token_type': 'bearer'}

# -----------------------------------------



# ============================================================================
# WebSocket Support for Real-time Updates
# ============================================================================

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics streaming"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            if agent and agent.running:
                metrics = agent.get_metrics()
                await websocket.send_json({
                    "type": "metrics",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "performance": metrics['performance'],
                        "memory": metrics['memory'],
                        "router": metrics['router'],
                    }
                })
            await asyncio.sleep(1)  # Update every second
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)


async def broadcast_message(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)
    
    for connection in disconnected:
        active_connections.remove(connection)


# ============================================================================
# Agent Management Endpoints
# ============================================================================

@app.post("/api/agent/start")
@limiter.limit("10/minute")
async def start_agent(request: Request, config: Optional[AgentConfig] = None, token: dict = Depends(verify_token)):
    """Start the Jarvis-OS agent"""
    global agent
    
    if agent and agent.running:
        return {"status": "already_running", "message": "Agent is already running"}
    
    config = config or AgentConfig(name="dashboard-agent")
    agent = JarvisOS(config)
    await agent.start()
    
    return {
        "status": "started",
        "agent": config.name,
        "version": config.version,
    }


@app.post("/api/agent/stop")
@limiter.limit("10/minute")
async def stop_agent(request: Request, token: dict = Depends(verify_token)):
    """Stop the Jarvis-OS agent"""
    global agent
    
    if not agent:
        raise HTTPException(status_code=400, detail="No agent running")
    
    await agent.stop()
    return {"status": "stopped"}


@app.get("/api/agent/status")
@limiter.limit("60/minute")
async def get_agent_status(request: Request, token: dict = Depends(verify_token)):
    """Get current agent status"""
    if not agent:
        return {"status": "not_running"}
    
    return agent.get_status()


@app.get("/api/agent/metrics")
@limiter.limit("60/minute")
async def get_agent_metrics(request: Request, token: dict = Depends(verify_token)):
    """Get detailed agent metrics"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    metrics = agent.get_metrics()
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
    }


@app.get("/api/agent/config")
@limiter.limit("60/minute")
async def get_agent_config(request: Request, token: dict = Depends(verify_token)):
    """Get agent configuration"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    config = agent.config
    return asdict(config)


@app.put("/api/agent/config")
@limiter.limit("10/minute")
async def update_agent_config(request: Request, config_update: Dict[str, Any], token: dict = Depends(verify_token)):
    """Update agent configuration"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    for key, value in config_update.items():
        if hasattr(agent.config, key):
            setattr(agent.config, key, value)
    
    return {"status": "updated", "config": asdict(agent.config)}


# ============================================================================
# Task Management Endpoints
# ============================================================================

@app.post("/api/tasks/submit")
@limiter.limit("30/minute")
async def submit_task(
    request: Request,
    task_type: str,
    params: Dict[str, Any] = None,
    priority: str = "NORMAL",
    current_user: str = Depends(verify_token)
):
    """Submit a new task to the agent - Rate limited to 30 per minute"""
    if not agent or not agent.running:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    try:
        priority_enum = TaskPriority[priority.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
    
    # Execute task
    async def dummy_task(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"task": task_type, "result": "completed"}
    
    result = await agent.execute_task(
        task_type=task_type,
        task_func=dummy_task,
        task_params=params or {},
        priority=priority_enum,
    )
    
    return {
        "task_id": result.task_id,
        "status": result.status.value,
        "result": result.result,
        "execution_time": result.execution_time,
    }


@app.get("/api/tasks/status/{task_id}")
@limiter.limit("120/minute")
async def get_task_status(request: Request, task_id: str, token: dict = Depends(verify_token)):
    """Get status of a specific task"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    result = await agent.executor.get_task_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {
        "task_id": task_id,
        "status": result.status.value,
        "result": result.result,
        "error": result.error,
        "execution_time": result.execution_time,
    }


@app.get("/api/tasks/all")
@limiter.limit("30/minute")
async def get_all_tasks_endpoint(
    request: Request,
    token: dict = Depends(verify_token),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get all executed tasks"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    all_tasks_db = await database.get_all_tasks(limit=limit, offset=offset)
    return {
        "limit": limit,
        "offset": offset,
        "tasks": all_tasks_db
    }


# ============================================================================
# Analysis Endpoints
# ============================================================================

@app.get("/api/analysis/performance")
async def get_performance_analysis():
    """Get performance analysis"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    analysis = agent.autopsy.analyze()
    return {
        "error_rate": analysis.error_rate,
        "avg_execution_time": analysis.avg_execution_time,
        "total_entries": analysis.total_entries,
        "performance_trends": analysis.performance_trends,
    }


@app.get("/api/analysis/errors")
async def get_error_analysis():
    """Get error pattern analysis"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    patterns = agent.autopsy.identify_error_patterns(top_n=10)
    return {"patterns": patterns}


@app.get("/api/analysis/hotspots")
async def get_performance_hotspots(percentile: float = Query(0.95, ge=0.5, le=1.0)):
    """Get performance hotspots"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    hotspots = agent.autopsy.identify_performance_hotspots(percentile=percentile)
    return {"hotspots": hotspots}


@app.get("/api/analysis/suggestions")
async def get_optimization_suggestions():
    """Get optimization suggestions"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    suggestions = agent.autopsy.generate_suggestions()
    return {"suggestions": suggestions}


# ============================================================================
# Memory Management Endpoints
# ============================================================================

@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get memory statistics"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    return await agent.memory.get_stats()


@app.post("/api/memory/store")
async def store_in_memory(key: str, value: Any, persistent: bool = False):
    """Store data in memory"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    await agent.memory.store(key, value, persistent=persistent)
    return {"status": "stored", "key": key}


@app.get("/api/memory/retrieve/{key}")
async def retrieve_from_memory(key: str):
    """Retrieve data from memory"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    value = await agent.memory.retrieve(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Key {key} not found")
    
    return {"key": key, "value": value}


@app.delete("/api/memory/delete/{key}")
async def delete_from_memory(key: str):
    """Delete data from memory"""
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not running")
    
    await agent.memory.delete(key)
    return {"status": "deleted", "key": key}


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_running": agent is not None and agent.running if agent else False,
    }


@app.get("/api/info")
async def get_info():
    """Get system information"""
    return {
        "name": "Jarvis-OS Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ============================================================================
# Static Files & UI
# ============================================================================

# Try to mount static files if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def get_root():
    """Serve dashboard UI"""
    dashboard_file = os.path.join(static_dir, "index.html") if os.path.exists(static_dir) else None
    if dashboard_file and os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    return {
        "message": "Jarvis-OS Dashboard API",
        "docs": "/docs",
        "status_endpoint": "/api/health",
    }


# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    global agent
    await database.init_db()
    print("Dashboard API started with DB")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global agent
    if agent and agent.running:
        await agent.stop()
    print("Dashboard API stopped")


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
