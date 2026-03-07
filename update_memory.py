with open('memory_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

store_old = '''    async def store(
        self,
        key: str,
        value: Any,
        persistent: bool = False,
        ttl: Optional[float] = None,
        priority: int = 0,
    ):
        """
        Store a value in memory
        """
        self.short_term.set(key, value, ttl, priority)
        
        if persistent:
            if self.redis_long_term:
                self.redis_long_term.set(key, value, ttl, priority)
            elif self.db:
                import time
                await self.db.set_memory(key, value, timestamp=time.time(), ttl=ttl, priority=priority)'''

store_new = '''    async def store(
        self,
        key: str,
        value: Any,
        persistent: bool = False,
        ttl: Optional[float] = None,
        priority: int = 0,
        semantic: bool = False,
    ):
        """
        Store a value in memory
        """
        self.short_term.set(key, value, ttl, priority)
        
        if persistent:
            if self.redis_long_term:
                self.redis_long_term.set(key, value, ttl, priority)
            elif self.db:
                import time
                await self.db.set_memory(key, value, timestamp=time.time(), ttl=ttl, priority=priority)
                
        if semantic and self.semantic:
            if isinstance(value, str):
                self.semantic.store_document(doc_id=key, text=value)
            elif isinstance(value, dict):
                import json
                self.semantic.store_document(doc_id=key, text=json.dumps(value), metadata=value)
            else:
                self.semantic.store_document(doc_id=key, text=str(value))'''

search_new = '''    async def search_semantic(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search memory semantically using ChromaDB"""
        if not self.semantic:
            return []
        
        results = self.semantic.search(query, n_results)
        
        formatted_results = []
        if results and 'documents' in results and results['documents']:
            docs = results['documents'][0]
            metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else [{}] * len(docs)
            ids = results['ids'][0] if 'ids' in results and results['ids'] else []
            distances = results['distances'][0] if 'distances' in results and results['distances'] else [0] * len(docs)
            
            for i in range(len(docs)):
                formatted_results.append({
                    'id': ids[i] if i < len(ids) else '',
                    'text': docs[i],
                    'metadata': metadatas[i],
                    'distance': distances[i]
                })
                
        return formatted_results
'''

if store_old in content:
    content = content.replace(store_old, store_new)
    content = content.replace('    async def delete(self, key: str) -> bool:', search_new + '\n    async def delete(self, key: str) -> bool:')
    with open('memory_manager.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done modifying memory_manager.py')
else:
    print('store_old not found in memory_manager.py')
