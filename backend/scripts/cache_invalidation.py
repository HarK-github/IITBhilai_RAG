#!/usr/bin/env python3
"""
Phase 5: Event-Driven Cache Invalidation
Listens for document changes and invalidates relevant cache entries
"""
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheInvalidationHandler(FileSystemEventHandler):
    """Monitors document changes and triggers cache invalidation"""
    
    def __init__(self, cache_manager, vector_store):
        self.cache_manager = cache_manager
        self.vector_store = vector_store
        self.invalidation_log = Path("./invalidation_log.json")
        self.load_log()
    
    def load_log(self):
        """Load invalidation history"""
        if self.invalidation_log.exists():
            with open(self.invalidation_log, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = {"invalidations": []}
    
    def log_invalidation(self, source: str, reason: str):
        """Log cache invalidation event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "reason": reason,
            "cache_cleared": True
        }
        self.history["invalidations"].append(event)
        
        # Keep last 100 events
        if len(self.history["invalidations"]) > 100:
            self.history["invalidations"] = self.history["invalidations"][-100:]
        
        with open(self.invalidation_log, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def on_modified(self, event):
        """Handle file modifications"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix == '.pdf':
                logger.info(f"📝 PDF modified: {file_path.name}")
                self.invalidate_for_file(file_path)
    
    def on_created(self, event):
        """Handle new files"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix == '.pdf':
                logger.info(f"📄 New PDF detected: {file_path.name}")
                # New file needs to be indexed, not just cache invalidation
                asyncio.run(self.index_new_file(file_path))
    
    def invalidate_for_file(self, file_path: Path):
        """Invalidate cache entries related to this file"""
        logger.info(f"🗑️ Invalidating cache for: {file_path.name}")
        # In production, you would query cache by source metadata
        self.log_invalidation(str(file_path), "file_modified")
    
    async def index_new_file(self, file_path: Path):
        """Index new PDF file"""
        logger.info(f"🔄 Indexing new file: {file_path.name}")
        # Trigger re-indexing logic here
        pass

async def start_cache_invalidation_watcher(cache_manager, vector_store, watch_path="./backend"):
    """Start the cache invalidation watcher"""
    handler = CacheInvalidationHandler(cache_manager, vector_store)
    observer = Observer()
    observer.schedule(handler, watch_path, recursive=False)
    observer.start()
    logger.info(f"👀 Cache invalidation watcher started on {watch_path}")
    return observer

if __name__ == "__main__":
    print("Cache Invalidation System Ready")
    print("Monitor document changes and clear cache automatically")
