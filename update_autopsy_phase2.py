with open('autopsy.py', 'r', encoding='utf-8') as f:
    content = f.read()

imports = '''from jarvis_common.schemas import CausalTrace, CausalCluster, ErrorCategory
from typing import List, Dict, Any, Optional
import uuid
'''

if 'CausalTrace' not in content:
    content = content.replace('from typing import Any, Dict, List, Optional', imports)

causal_code = '''
    def find_causal_clusters(self, error_category: ErrorCategory, traces: List[CausalTrace] = None) -> List[CausalCluster]:
        """
        Phase 2: Group failed CausalTrace objects by shared upstream features.
        """
        if traces is None:
            traces = getattr(self, 'traces', [])
            
        failed_traces = [t for t in traces if t.error_category == error_category]
        clusters = []
        
        # Partition by executor, prompt length > 2000, and intent (if available in user_input/router_decision)
        cluster_map = {}
        for trace in failed_traces:
            executor = trace.router_decision.chosen_executor
            is_long_prompt = trace.prompt_length_tokens > 2000
            
            # Simple heuristic intent extraction for demonstration
            intent = "unknown"
            if "code_gen" in trace.user_input.lower():
                intent = "code_gen"
            
            key = (executor, is_long_prompt, intent)
            if key not in cluster_map:
                cluster_map[key] = []
            cluster_map[key].append(trace.trace_id)
            
        for (executor, is_long, intent), t_ids in cluster_map.items():
            if len(t_ids) > 0:
                desc = f"{error_category.value} when prompt > 2000 tokens={is_long} on {intent} routed to {executor}"
                clusters.append(CausalCluster(
                    cluster_id=str(uuid.uuid4()),
                    error_category=error_category,
                    description=desc,
                    common_features={
                        "executor": executor,
                        "prompt_length_gt_2000": is_long,
                        "intent": intent
                    },
                    trace_ids=t_ids
                ))
                
        return clusters
'''

if 'find_causal_clusters' not in content:
    content = content.replace('class Autopsy:', 'class Autopsy:\n' + causal_code)

with open('autopsy.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Phase 2 added to autopsy.py')
