"""
Observability Dashboard for Jarvis-OS
Provides a real-time web interface using FastAPI and React for monitoring
agent performance, memory status, and task execution rates.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
from typing import Dict, Any
import logging

from jarvis_os import JarvisOS

logger = logging.getLogger(__name__)


class JarvisDashboard:
    """
    Real-time observability dashboard for a Jarvis-OS agent instance.
    """
    
    def __init__(self, agent: JarvisOS, host: str = "0.0.0.0", port: int = 8000):
        self.agent = agent
        self.host = host
        self.port = port
        self.app = FastAPI(title=f"Jarvis-OS Dashboard: {agent.config.name}")
        self._setup_routes()
        
    def _setup_routes(self):
        @self.app.get("/")
        async def root():
            return HTMLResponse(content=self._get_html_template())
            
        @self.app.get("/api/status")
        async def get_status():
            try:
                return self.agent.get_status()
            except Exception as e:
                return {"error": str(e)}
            
        @self.app.get("/api/metrics")
        async def get_metrics():
            try:
                return self.agent.get_metrics()
            except Exception as e:
                return {"error": str(e)}

    def run_sync(self):
        """Run the dashboard synchronously (blocking)"""
        logger.info(f"Starting Jarvis-OS dashboard on http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")
            
    async def serve_async(self):
        """Start the dashboard asynchronously using Uvicorn's serve()"""
        config = uvicorn.Config(app=self.app, host=self.host, port=self.port, log_level="warning")
        server = uvicorn.Server(config)
        logger.info(f"Starting Jarvis-OS dashboard centrally on http://{self.host}:{self.port}")
        await server.serve()

    def _get_html_template(self) -> str:
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Jarvis-OS Dashboard</title>
    <!-- Use Tailwind CSS for rapid styling -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Use React and ReactDOM -->
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/babel-standalone@6/babel.min.js"></script>
</head>
<body class="bg-gray-900 text-white p-8 font-sans">
    <div id="root"></div>

    <script type="text/babel">
        function Dashboard() {
            const [status, setStatus] = React.useState(null);
            
            React.useEffect(() => {
                const fetchStatus = async () => {
                    try {
                        const res = await fetch('/api/status');
                        const data = await res.json();
                        setStatus(data);
                    } catch (e) {
                        console.error('Failed to fetch status', e);
                    }
                };
                
                fetchStatus();
                const interval = setInterval(fetchStatus, 2000); // 2s refresh
                return () => clearInterval(interval);
            }, []);

            if (!status) return <div className="text-center mt-20 text-2xl font-bold animate-pulse">Initializing Jarvis-OS Link...</div>;

            return (
                <div className="max-w-6xl mx-auto">
                    <div className="flex items-center justify-between mb-8 pb-4 border-b border-gray-700">
                        <div>
                            <h1 className="text-4xl font-bold text-blue-400">Jarvis-OS <span className="text-gray-500 text-2xl">v{status.version || '1.0'}</span></h1>
                            <p className="text-gray-400 mt-2">Agent ID: {status.name}</p>
                        </div>
                        <div className="text-right">
                            <span className={`px-4 py-2 rounded-full font-bold uppercase tracking-wide text-sm ${status.running ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
                                {status.running ? 'Online & Running' : 'Offline'}
                            </span>
                        </div>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl hover:border-blue-500 transition-colors">
                            <h2 className="text-sm uppercase tracking-wider font-semibold mb-2 text-gray-500">Executor Engine</h2>
                            <p className="text-4xl font-bold text-green-400 mb-4">{(status.executor_stats?.success_rate * 100 || 0).toFixed(1)}% <span className="text-sm font-normal text-gray-500">Success</span></p>
                            <div className="space-y-2 text-sm text-gray-300">
                                <div className="flex justify-between"><span>Completed Tasks</span> <span className="font-mono">{status.executor_stats?.completed || 0}</span></div>
                                <div className="flex justify-between"><span>Failed Tasks</span> <span className="font-mono text-red-400">{status.executor_stats?.failed || 0}</span></div>
                                <div className="flex justify-between"><span>Avg Duration</span> <span className="font-mono">{(status.executor_stats?.avg_execution_time || 0).toFixed(3)}s</span></div>
                            </div>
                        </div>
                        
                        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl hover:border-purple-500 transition-colors">
                            <h2 className="text-sm uppercase tracking-wider font-semibold mb-2 text-gray-500">Memory Cluster</h2>
                            <p className="text-4xl font-bold text-purple-400 mb-4">{(status.memory_stats?.hit_rate * 100 || 0).toFixed(1)}% <span className="text-sm font-normal text-gray-500">Hit Rate</span></p>
                            <div className="space-y-2 text-sm text-gray-300">
                                <div className="flex justify-between"><span>Short-term L1</span> <span className="font-mono group-hover:text-purple-300">{status.memory_stats?.short_term_size || 0} items</span></div>
                                <div className="flex justify-between"><span>Long-term L2</span> <span className="font-mono">{status.memory_stats?.long_term_size || 0} items</span></div>
                            </div>
                        </div>

                        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl hover:border-red-500 transition-colors">
                            <h2 className="text-sm uppercase tracking-wider font-semibold mb-2 text-gray-500">Autopsy Analyzer</h2>
                            <p className="text-4xl font-bold text-red-400 mb-4">{status.autopsy_analysis?.error_rate > 0 ? (status.autopsy_analysis.error_rate * 100).toFixed(1) + '%' : '0%'} <span className="text-sm font-normal text-gray-500">Errors</span></p>
                            <div className="space-y-2 text-sm text-gray-300">
                                <div className="flex justify-between"><span>Pattern Detections</span> <span className="font-mono">Active</span></div>
                                <div className="flex justify-between"><span>Mutation Engine</span> <span className="font-mono text-blue-400 whitespace-nowrap overflow-hidden">Standing By</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<Dashboard />);
    </script>
</body>
</html>
        """
