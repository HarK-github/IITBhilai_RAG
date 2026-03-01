"""
Registry for managing pluggable tools
"""
import yaml
from typing import Dict, List, Optional
from pathlib import Path
import logging

from .base_tool import BaseTool, WebsiteTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages all available tools/plugins"""
    
    def __init__(self, config_path: str = "config/websites.yaml"):
        self.tools: Dict[str, BaseTool] = {}
        self.config_path = Path(config_path)
        self.vector_store = None
        self.load_config()
    
    def set_vector_store(self, vector_store):
        """Inject vector store dependency"""
        self.vector_store = vector_store
    
    def load_config(self):
        """Load website configurations"""
        if not self.config_path.exists():
            logger.warning(f"Config not found: {self.config_path}")
            return
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.website_configs = config.get('websites', [])
        logger.info(f"Loaded {len(self.website_configs)} website configs")
    
    def register_tool(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def register_website(self, website_config: dict):
        """Create and register a website tool"""
        if not self.vector_store:
            logger.error("Vector store not set. Call set_vector_store() first")
            return
        
        tool = WebsiteTool(
            name=website_config['name'],
            namespace=website_config['namespace'],
            vector_store=self.vector_store,
            description=website_config.get('description'),
            config=website_config
        )
        
        self.register_tool(tool)
    
    def register_all_websites(self):
        """Register all configured websites"""
        for config in self.website_configs:
            if config.get('enabled', True):
                self.register_website(config)
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def get_relevant_tools(self, question: str, top_k: int = 3) -> List[BaseTool]:
        """Get tools that can handle the question"""
        scored_tools = []
        
        for tool in self.tools.values():
            if tool.enabled:
                score = tool.can_handle(question)
                scored_tools.append((score, tool))
        
        # Sort by confidence and return top k
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        return [tool for score, tool in scored_tools[:top_k] if score > 0.3]
    
    def list_tools(self) -> List[dict]:
        """List all registered tools"""
        return [tool.get_metadata() for tool in self.tools.values()]
    
    def disable_tool(self, name: str):
        """Disable a tool"""
        if name in self.tools:
            self.tools[name].enabled = False
            logger.info(f"Disabled tool: {name}")
    
    def enable_tool(self, name: str):
        """Enable a tool"""
        if name in self.tools:
            self.tools[name].enabled = True
            logger.info(f"Enabled tool: {name}")
