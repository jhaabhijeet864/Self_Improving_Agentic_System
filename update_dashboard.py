import re

with open('dashboard_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
imports = '''
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Depends, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import jwt
import database
'''
content = content.replace('import os', 'import os\n' + imports)

# Add Rate limiter & Auth config
auth_setup = '''
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
'''
content = content.replace('active_connections: List[WebSocket] = []', 'active_connections: List[WebSocket] = []\n' + auth_setup)

# Protect endpoints & Add rate limits
# Replace @app.post('/api/agent/start')
content = re.sub(r'@app\.post\(\"/api/agent/start\"\)\s+async def start_agent\(config: Optional\[AgentConfig\] = None\):', 
'''@app.post("/api/agent/start")
@limiter.limit("10/minute")
async def start_agent(request: Request, config: Optional[AgentConfig] = None, token: dict = Depends(verify_token)):''', content)

content = re.sub(r'@app\.post\(\"/api/agent/stop\"\)\s+async def stop_agent\(\):',
'''@app.post("/api/agent/stop")
@limiter.limit("10/minute")
async def stop_agent(request: Request, token: dict = Depends(verify_token)):''', content)

content = re.sub(r'@app\.get\(\"/api/agent/status\"\)\s+async def get_agent_status\(\):',
'''@app.get("/api/agent/status")
@limiter.limit("60/minute")
async def get_agent_status(request: Request, token: dict = Depends(verify_token)):''', content)

content = re.sub(r'@app\.get\(\"/api/agent/metrics\"\)\s+async def get_agent_metrics\(\):',
'''@app.get("/api/agent/metrics")
@limiter.limit("60/minute")
async def get_agent_metrics(request: Request, token: dict = Depends(verify_token)):''', content)

content = re.sub(r'@app\.get\(\"/api/agent/config\"\)\s+async def get_agent_config\(\):',
'''@app.get("/api/agent/config")
@limiter.limit("60/minute")
async def get_agent_config(request: Request, token: dict = Depends(verify_token)):''', content)

content = re.sub(r'@app\.put\(\"/api/agent/config\"\)\s+async def update_agent_config\(config_update: Dict\[str, Any\]\):',
'''@app.put("/api/agent/config")
@limiter.limit("10/minute")
async def update_agent_config(request: Request, config_update: Dict[str, Any], token: dict = Depends(verify_token)):''', content)

content = re.sub(r'@app\.post\(\"/api/tasks/submit\"\)\s+async def submit_task\(',
'''@app.post("/api/tasks/submit")
@limiter.limit("100/minute")
async def submit_task(
    request: Request,
    token: dict = Depends(verify_token),''', content)

content = re.sub(r'@app\.get\(\"/api/tasks/status/\{task_id\}\"\)\s+async def get_task_status\(task_id: str\):',
'''@app.get("/api/tasks/status/{task_id}")
@limiter.limit("120/minute")
async def get_task_status(request: Request, task_id: str, token: dict = Depends(verify_token)):''', content)

content = re.sub(r'@app\.get\(\"/api/tasks/all\"\)\s+async def get_all_tasks\(',
'''@app.get("/api/tasks/all")
@limiter.limit("30/minute")
async def get_all_tasks_endpoint(
    request: Request,
    token: dict = Depends(verify_token),''', content)

# Database replacement for get_all_tasks
old_tasks_logic = '''all_results = await agent.executor.get_all_results()
    tasks = list(all_results.items())[offset:offset + limit]
    
    return {
        "total": len(all_results),
        "limit": limit,
        "offset": offset,
        "tasks": [
            {
                "task_id": task_id,
                "status": result.status.value,
                "execution_time": result.execution_time,
                "timestamp": result.timestamp,
            }
            for task_id, result in tasks
        ]
    }'''
new_tasks_logic = '''all_tasks_db = await database.get_all_tasks(limit=limit, offset=offset)
    return {
        "limit": limit,
        "offset": offset,
        "tasks": all_tasks_db
    }'''

content = content.replace(old_tasks_logic, new_tasks_logic)

# Startup event DB init
content = content.replace('global agent\n    print("Dashboard API started")', 'global agent\n    await database.init_db()\n    print("Dashboard API started with DB")')

with open('dashboard_api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done updating dashboard_api.py.')
