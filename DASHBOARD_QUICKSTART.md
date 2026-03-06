# 🚀 Quick Start: Jarvis-OS Dashboard

## Installation (5 minutes)

### Step 1: Install Required Packages
```bash
pip install fastapi uvicorn
```

### Step 2: Generate Dashboard UI
```bash
python dashboard_ui_setup.py
```

Expected output:
```
✅ Created D:\Coding\Projects\Self_Impeove\static\index.html
```

### Step 3: Start the Dashboard
```bash
python dashboard_api.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Step 4: Access Dashboard
Open your browser and go to:
```
http://localhost:8000
```

## First Time Use

### What You Should See

1. **Dashboard Loads** with:
   - Header with Jarvis-OS logo
   - Status badges (Offline, Disconnected)
   - Start/Stop/Refresh buttons
   - 4 metric cards (all showing 0)

2. **Before Starting Agent**:
   - All metrics show 0
   - Charts are empty
   - Agent status: "Stopped"
   - Connection status: "Disconnected"

### Getting Started with Agent

1. **Click "Start Agent"** button
   - Agent status changes to: "Online"
   - Connection status changes to: "Connected"
   - WebSocket connection established

2. **Submit Test Task**:
   - Fill task type: "test"
   - Select priority: "NORMAL"
   - Click "Submit Task"
   - Task appears in Recent Tasks table

3. **Monitor Metrics**:
   - Total Tasks increases
   - Success Rate updates
   - Avg Execution time shows
   - Charts begin showing data

## API Testing

### Test Agent Status
```bash
curl http://localhost:8000/api/health
```

### Test Agent Control
```bash
curl -X POST http://localhost:8000/api/agent/start
curl http://localhost:8000/api/agent/status
```

### Test Task Submission
```bash
curl -X POST "http://localhost:8000/api/tasks/submit?task_type=compute&priority=NORMAL"
```

### Test Metrics
```bash
curl http://localhost:8000/api/agent/metrics
```

## Dashboard Features

### Real-Time Monitoring
- ✅ Live metric updates every 1-2 seconds
- ✅ WebSocket streaming of performance data
- ✅ Automatic chart updates

### Agent Control
- ✅ Start/Stop agent from UI
- ✅ Task submission form
- ✅ Refresh metrics manually

### Performance Visualization
- ✅ Success rate trend chart
- ✅ Memory utilization gauge
- ✅ Error pattern display
- ✅ System resource table

### Analysis Display
- ✅ Error patterns (top errors)
- ✅ Performance hotspots (slowest tasks)
- ✅ Optimization suggestions
- ✅ Recent tasks table

## API Endpoints Quick Reference

### Agent Operations
```
GET    /api/agent/status          - Agent status
GET    /api/agent/metrics         - Performance metrics
POST   /api/agent/start           - Start agent
POST   /api/agent/stop            - Stop agent
GET    /api/agent/config          - Get config
PUT    /api/agent/config          - Update config
```

### Task Management
```
POST   /api/tasks/submit          - Submit new task
GET    /api/tasks/status/{id}     - Get task status
GET    /api/tasks/all             - List all tasks
```

### Analysis
```
GET    /api/analysis/performance  - Performance analysis
GET    /api/analysis/errors       - Error patterns
GET    /api/analysis/hotspots     - Performance hotspots
GET    /api/analysis/suggestions  - Improvement suggestions
```

### Memory
```
GET    /api/memory/stats          - Memory statistics
POST   /api/memory/store          - Store value
GET    /api/memory/retrieve/{key} - Retrieve value
DELETE /api/memory/delete/{key}   - Delete value
```

### WebSocket
```
WS     /ws/metrics                - Real-time metrics stream
```

## Common Tasks

### Start Agent and Monitor
```bash
# Terminal 1: Start dashboard
python dashboard_api.py

# Terminal 2: Access browser
# Open http://localhost:8000
# Click "Start Agent" button
# Watch metrics update in real-time
```

### Submit Tasks via CLI
```bash
# Submit task
curl -X POST "http://localhost:8000/api/tasks/submit?task_type=compute&priority=HIGH"

# Check status
curl http://localhost:8000/api/tasks/all
```

### View Performance Analysis
```bash
# Get performance metrics
curl http://localhost:8000/api/analysis/performance

# Get error patterns
curl http://localhost:8000/api/analysis/errors

# Get suggestions
curl http://localhost:8000/api/analysis/suggestions
```

## Troubleshooting

### Dashboard doesn't load
```bash
# Check if API is running
curl http://localhost:8000/api/health

# Check if static files exist
ls D:\Coding\Projects\Self_Impeove\static\

# If missing, run:
python dashboard_ui_setup.py
```

### Metrics not updating
- Check agent is running: Click "Start Agent"
- Check WebSocket connection status in header
- Verify browser console for errors (F12)
- Reload page (Ctrl+R)

### Agent not starting
```bash
# Check Jarvis-OS core is working
python validate.py

# Check dependencies installed
pip list | grep -E "fastapi|uvicorn"
```

### Port already in use
```bash
# Use different port:
python -c "from dashboard_api import app; import uvicorn; uvicorn.run(app, port=8001)"

# Then access: http://localhost:8001
```

## Next Steps

### Explore More Features
1. Submit multiple tasks
2. Monitor error patterns
3. Check performance trends
4. View optimization suggestions
5. Manage memory entries

### Customize Dashboard
1. Modify dashboard_api.py to add endpoints
2. Customize dashboard_ui_setup.py for UI changes
3. Add authentication layer
4. Integrate database backend

### Move to Phase 2
1. Create REST API client library
2. Build advanced routing
3. Add database persistence
4. Implement authentication

## Production Deployment

### Using Docker
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn
RUN python dashboard_ui_setup.py
CMD ["python", "dashboard_api.py"]
```

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker dashboard_api:app
```

### Using systemd
```ini
[Unit]
Description=Jarvis-OS Dashboard
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/jarvis-os
ExecStart=/usr/bin/python3 /opt/jarvis-os/dashboard_api.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Support

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (ReDoc UI)
- **Health Check**: http://localhost:8000/api/health
- **Status**: http://localhost:8000/api/agent/status

## Performance Tips

- Use WebSocket for real-time monitoring
- Limit task query results with `limit` parameter
- Enable browser caching for static files
- Use gzip compression in production
- Deploy with multiple workers (4-8)

---

**Jarvis-OS Dashboard is ready to use!** 🎉

Start monitoring your AI agent in real-time.
