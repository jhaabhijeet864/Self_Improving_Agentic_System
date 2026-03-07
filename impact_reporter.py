import os
import json
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ImpactReporter:
    """
    Phase 6: Mutation Impact Report
    Generates structured markdown reports after a mutation has been running.
    """
    def __init__(self, db, output_dir="mutations/impact_reports"):
        self.db = db
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
    async def generate_report(self, mutation_id: str, pre_stats: dict, post_stats: dict) -> str:
        """
        Generates a Markdown report comparing pre and post mutation stats.
        """
        report_path = os.path.join(self.output_dir, f"impact_{mutation_id}.md")
        
        pre_sr = pre_stats.get('success_rate', 0)
        post_sr = post_stats.get('success_rate', 0)
        sr_delta = post_sr - pre_sr
        
        pre_latency = pre_stats.get('avg_latency', 0)
        post_latency = post_stats.get('avg_latency', 0)
        latency_delta = post_latency - pre_latency
        
        report_content = f"""# Mutation Impact Report
**Mutation ID:** {mutation_id}
**Generated At:** {datetime.now().isoformat()}

## Executive Summary
* **Success Rate:** {post_sr*100:.2f}% (Delta: {sr_delta*100:+.2f}%)
* **Avg Latency:** {post_latency:.2f}s (Delta: {latency_delta:+.2f}s)

## Conclusion
"""
        if sr_delta > 0:
            report_content += "The mutation had a **positive** impact on success rates.\n"
        elif sr_delta < -0.05:
            report_content += "The mutation caused a **significant degradation**.\n"
        else:
            report_content += "The mutation had a **neutral or minor** impact.\n"
            
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(report_content)
            
        logger.info(f"Generated Impact Report at {report_path}")
        return report_path
