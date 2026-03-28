from app.agents.base_agent import BaseAgent
from app.utils.logger import get_agent_logger, log_thinking, log_acting


class RAGAgent(BaseAgent):
    def __init__(self, name, bus, store, context_indexer=None):
        super().__init__(name, bus)
        self.store = store
        self.context_indexer = context_indexer
        self.logger = get_agent_logger("RAGAgent")

    async def think(self, message):
        log_thinking(self.logger, "RAGAgent")

        query = message.get("query")
        include_context = message.get("include_context", True)
        return {
            "query": query,
            "include_context": include_context
        }

    async def act(self, plan):
        log_acting(self.logger, "RAGAgent")

        code_results = self.store.search(plan["query"], k=5)
        
        context_results = []
        if self.context_indexer and plan.get("include_context", True):
            context_results = self.context_indexer.search_user_contexts(plan["query"], k=3)

        return {
            "context": code_results,
            "user_context": context_results
        }
