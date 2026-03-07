import json
import logging
from typing import List, Dict, Any, Optional
import uuid
try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    embedding_functions = None

logger = logging.getLogger(__name__)

class ProjectContextGraph:
    """
    Phase 5: Project Context Graph
    A ChromaDB collection where each 'document' is a project snapshot.
    """
    def __init__(self, db_path: str = "./chroma_db", collection_name: str = "project_contexts"):
        self.client = None
        self.collection = None
        if chromadb and embedding_functions:
            try:
                self.client = chromadb.PersistentClient(path=db_path)
                self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_fn
                )
                logger.info(f"Initialized Project Context Graph at {db_path}")
            except Exception as e:
                logger.error(f"Failed to initialize Project Context Graph: {e}")
        else:
            logger.warning("chromadb or sentence_transformers not installed. Project Context Graph disabled.")

    def store_snapshot(self, project_id: str, goal: str, commands: List[str], metadata: Dict[str, Any] = None):
        if not self.collection:
            return
            
        doc_text = f"Goal: {goal}\nCommands: {', '.join(commands)}"
        
        if metadata is None:
            metadata = {}
            
        # Store inferred goal in metadata for easy filtering
        metadata["goal"] = goal
        metadata["project_id"] = project_id
        
        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        
        try:
            self.collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[snapshot_id]
            )
            logger.info(f"Stored project snapshot {snapshot_id} for goal: {goal}")
        except Exception as e:
            logger.error(f"Failed to store snapshot: {e}")

    def query_context(self, initial_commands: List[str], n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Query the context graph using the first few commands of a session.
        """
        if not self.collection or self.collection.count() == 0:
            return []
            
        query_text = ", ".join(initial_commands)
        num = min(n_results, self.collection.count())
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=num
            )
            
            contexts = []
            if results and 'documents' in results and results['documents']:
                docs = results['documents'][0]
                metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else [{}] * len(docs)
                
                for i in range(len(docs)):
                    contexts.append({
                        "context_text": docs[i],
                        "metadata": metadatas[i]
                    })
                    
            return contexts
        except Exception as e:
            logger.error(f"Failed to query Project Context Graph: {e}")
            return []
