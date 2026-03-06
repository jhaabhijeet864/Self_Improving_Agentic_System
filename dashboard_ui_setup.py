"""
Jarvis-OS Dashboard - Embedded Static Files Generator
Creates static HTML, CSS, and JS files inline without requiring file system directories
"""

import os

def create_dashboard_ui():
    """Create dashboard UI files"""
    
    # Create static directory
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)
    
    # HTML
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jarvis-OS Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #e2e8f0; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: #1e293b; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .header-content h1 { color: #60a5fa; margin-bottom: 10px; }
        .header-status { display: flex; gap: 10px; }
        .status-badge { padding: 8px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-online { background: #10b981; color: white; }
        .status-offline { background: #ef4444; color: white; }
        .status-connected { background: #3b82f6; color: white; }
        .status-disconnected { background: #6b7280; color: white; }
        .nav { display: flex; gap: 10px; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; transition: all 0.3s; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-danger:hover { background: #dc2626; }
        .btn-secondary { background: #6b7280; color: white; }
        .btn-secondary:hover { background: #4b5563; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .card h3 { color: #60a5fa; margin-bottom: 15px; font-size: 18px; }
        .cards-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .metric-card { text-align: center; }
        .metric-value { font-size: 32px; font-weight: bold; color: #10b981; margin: 10px 0; }
        .metric-label { font-size: 12px; color: #94a3b8; }
        .charts-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .chart-card { }
        .chart-card canvas { max-height: 300px; }
        .status-table { width: 100%; border-collapse: collapse; }
        .status-table tr { border-bottom: 1px solid #334155; }
        .status-table td { padding: 12px; }
        .status-table td:first-child { font-weight: bold; color: #94a3b8; }
        .errors-list, .suggestions-list { max-height: 300px; overflow-y: auto; }
        .error-item, .suggestion-item { background: #0f172a; padding: 12px; margin: 8px 0; border-radius: 4px; border-left: 4px solid #ef4444; }
        .suggestion-item { border-left-color: #f59e0b; }
        .empty-message { color: #64748b; font-style: italic; padding: 20px; text-align: center; }
        .task-form { display: grid; grid-template-columns: 1fr 1fr auto; gap: 15px; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; }
        .form-group label { margin-bottom: 5px; font-weight: bold; color: #cbd5e1; }
        .form-group input, .form-group select { padding: 10px; background: #0f172a; border: 1px solid #334155; border-radius: 4px; color: #e2e8f0; }
        .tasks-table { width: 100%; border-collapse: collapse; }
        .tasks-table th { background: #0f172a; padding: 12px; text-align: left; font-weight: bold; border-bottom: 2px solid #334155; }
        .tasks-table td { padding: 12px; border-bottom: 1px solid #334155; }
        .tasks-table tr:hover { background: #0f172a; }
        .footer { text-align: center; padding: 20px; color: #64748b; font-size: 12px; }
        @media (max-width: 768px) { .task-form { grid-template-columns: 1fr; } .charts-section { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-content">
                <h1>🤖 Jarvis-OS Dashboard</h1>
                <div class="header-status">
                    <span id="agent-status" class="status-badge status-offline">Offline</span>
                    <span id="connection-status" class="status-badge status-disconnected">Disconnected</span>
                </div>
            </div>
            <nav class="nav">
                <button id="btn-start" class="btn btn-primary">Start Agent</button>
                <button id="btn-stop" class="btn btn-danger">Stop Agent</button>
                <button id="btn-refresh" class="btn btn-secondary">Refresh</button>
            </nav>
        </header>

        <main>
            <section class="cards-section">
                <div class="card metric-card">
                    <h3>Total Tasks</h3>
                    <div class="metric-value" id="metric-tasks">0</div>
                    <p class="metric-label">Completed</p>
                </div>
                <div class="card metric-card">
                    <h3>Success Rate</h3>
                    <div class="metric-value" id="metric-success">0%</div>
                    <p class="metric-label">Performance</p>
                </div>
                <div class="card metric-card">
                    <h3>Avg Execution</h3>
                    <div class="metric-value" id="metric-avgtime">0ms</div>
                    <p class="metric-label">Per Task</p>
                </div>
                <div class="card metric-card">
                    <h3>Memory Hit Rate</h3>
                    <div class="metric-value" id="metric-memory">0%</div>
                    <p class="metric-label">Cache</p>
                </div>
            </section>

            <section class="charts-section">
                <div class="card chart-card">
                    <h3>Performance Over Time</h3>
                    <canvas id="chart-performance"></canvas>
                </div>
                <div class="card chart-card">
                    <h3>Memory Utilization</h3>
                    <canvas id="chart-memory"></canvas>
                </div>
            </section>

            <section class="status-section" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div class="card">
                    <h3>Agent Status</h3>
                    <table class="status-table">
                        <tr><td>Status</td><td id="status-running">Stopped</td></tr>
                        <tr><td>Tasks Executed</td><td id="status-tasks">0</td></tr>
                        <tr><td>Failed Tasks</td><td id="status-failed">0</td></tr>
                        <tr><td>Error Rate</td><td id="status-error">0%</td></tr>
                    </table>
                </div>
                <div class="card">
                    <h3>System Resources</h3>
                    <table class="status-table">
                        <tr><td>Short-term Memory</td><td id="status-short-mem">0 / 1000</td></tr>
                        <tr><td>Long-term Memory</td><td id="status-long-mem">0</td></tr>
                        <tr><td>Memory Hit Rate</td><td id="status-hit-rate">0%</td></tr>
                        <tr><td>Last Update</td><td id="status-update">Never</td></tr>
                    </table>
                </div>
            </section>

            <section style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div class="card">
                    <h3>⚠️ Error Patterns</h3>
                    <div id="errors-list" class="errors-list">
                        <p class="empty-message">No errors detected</p>
                    </div>
                </div>
                <div class="card">
                    <h3>💡 Suggestions</h3>
                    <div id="suggestions-list" class="suggestions-list">
                        <p class="empty-message">No suggestions available</p>
                    </div>
                </div>
            </section>

            <div class="card">
                <h3>Submit Task</h3>
                <form id="task-form" class="task-form">
                    <div class="form-group">
                        <label>Task Type:</label>
                        <input type="text" id="task-type" placeholder="e.g., compute" required>
                    </div>
                    <div class="form-group">
                        <label>Priority:</label>
                        <select id="task-priority">
                            <option value="LOW">Low</option>
                            <option value="NORMAL">Normal</option>
                            <option value="HIGH">High</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary">Submit</button>
                </form>
            </div>

            <div class="card">
                <h3>Recent Tasks</h3>
                <table class="tasks-table">
                    <thead><tr><th>Task ID</th><th>Status</th><th>Duration</th><th>Time</th></tr></thead>
                    <tbody id="tasks-tbody"><tr><td colspan="4" class="empty-message">No tasks</td></tr></tbody>
                </table>
            </div>
        </main>

        <footer class="footer">
            <p>Jarvis-OS Dashboard v1.0.0 | Real-time Agent Monitoring</p>
        </footer>
    </div>

    <script>
        // Global state
        let wsConnected = false;
        let agentRunning = false;
        let performanceChart = null;
        let memoryChart = null;
        const perfData = { labels: [], data: [] };
        const memoryData = { labels: [], data: [] };

        // Connect to WebSocket
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${window.location.host}/ws/metrics`);
            
            ws.onopen = () => {
                wsConnected = true;
                document.getElementById('connection-status').textContent = 'Connected';
                document.getElementById('connection-status').className = 'status-badge status-connected';
            };
            
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === 'metrics') {
                    updateMetrics(msg.data);
                }
            };
            
            ws.onclose = () => {
                wsConnected = false;
                document.getElementById('connection-status').textContent = 'Disconnected';
                document.getElementById('connection-status').className = 'status-badge status-disconnected';
                setTimeout(connectWebSocket, 3000);
            };
        }

        // Update metrics
        function updateMetrics(data) {
            const perf = data.performance || {};
            const mem = data.memory || {};
            
            document.getElementById('metric-tasks').textContent = perf.total_tasks || 0;
            document.getElementById('metric-success').textContent = ((perf.success_rate || 0) * 100).toFixed(1) + '%';
            document.getElementById('metric-avgtime').textContent = (perf.avg_execution_time || 0).toFixed(2) + 's';
            document.getElementById('metric-memory').textContent = ((mem.hit_rate || 0) * 100).toFixed(1) + '%';
            
            document.getElementById('status-tasks').textContent = perf.total_tasks || 0;
            document.getElementById('status-failed').textContent = perf.failed || 0;
            document.getElementById('status-error').textContent = ((perf.success_rate || 1 - (perf.error_rate || 0)) * 100).toFixed(1) + '%';
            document.getElementById('status-short-mem').textContent = mem.short_term_size + ' / 1000';
            document.getElementById('status-long-mem').textContent = mem.long_term_size || 0;
            document.getElementById('status-hit-rate').textContent = ((mem.hit_rate || 0) * 100).toFixed(1) + '%';
            document.getElementById('status-update').textContent = new Date().toLocaleTimeString();
            
            // Update charts
            updateCharts(perf);
        }

        function updateCharts(data) {
            perfData.labels.push(new Date().toLocaleTimeString());
            perfData.data.push((data.success_rate || 0) * 100);
            if (perfData.labels.length > 20) {
                perfData.labels.shift();
                perfData.data.shift();
            }
            
            if (performanceChart) {
                performanceChart.data.labels = perfData.labels;
                performanceChart.data.datasets[0].data = perfData.data;
                performanceChart.update();
            }
        }

        // Initialize charts
        function initCharts() {
            const ctx1 = document.getElementById('chart-performance');
            performanceChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Success Rate %',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { max: 100, min: 0 }
                    }
                }
            });

            const ctx2 = document.getElementById('chart-memory');
            memoryChart = new Chart(ctx2, {
                type: 'doughnut',
                data: {
                    labels: ['Used', 'Available'],
                    datasets: [{
                        data: [30, 70],
                        backgroundColor: ['#3b82f6', '#334155'],
                    }]
                }
            });
        }

        // Event listeners
        document.getElementById('btn-start').onclick = async () => {
            const resp = await fetch('/api/agent/start', { method: 'POST' });
            if (resp.ok) {
                agentRunning = true;
                document.getElementById('agent-status').textContent = 'Online';
                document.getElementById('agent-status').className = 'status-badge status-online';
                document.getElementById('status-running').textContent = 'Running';
            }
        };

        document.getElementById('btn-stop').onclick = async () => {
            const resp = await fetch('/api/agent/stop', { method: 'POST' });
            if (resp.ok) {
                agentRunning = false;
                document.getElementById('agent-status').textContent = 'Offline';
                document.getElementById('agent-status').className = 'status-badge status-offline';
                document.getElementById('status-running').textContent = 'Stopped';
            }
        };

        document.getElementById('btn-refresh').onclick = async () => {
            const resp = await fetch('/api/agent/metrics');
            if (resp.ok) {
                const data = await resp.json();
                updateMetrics(data.metrics);
            }
        };

        document.getElementById('task-form').onsubmit = async (e) => {
            e.preventDefault();
            const type = document.getElementById('task-type').value;
            const priority = document.getElementById('task-priority').value;
            await fetch(`/api/tasks/submit?task_type=${type}&priority=${priority}`, { method: 'POST' });
            document.getElementById('task-type').value = '';
        };

        // Initialize
        window.onload = () => {
            initCharts();
            connectWebSocket();
            setInterval(() => fetch('/api/agent/metrics').then(r => r.ok && r.json()).then(d => updateMetrics(d?.metrics)), 2000);
        };
    </script>
</body>
</html>'''
    
    # Write HTML
    html_path = os.path.join(static_dir, "index.html")
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Created {html_path}")
    return static_dir

if __name__ == "__main__":
    create_dashboard_ui()
