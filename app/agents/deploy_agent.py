from app.agents.base_agent import BaseAgent
from app.tools.github_manager import GitHubManager
from app.utils.logger import get_agent_logger, log_thinking, log_acting


class DeployAgent(BaseAgent):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.github_manager = GitHubManager()
        self.logger = get_agent_logger("DeployAgent")

    async def think(self, message):
        log_thinking(self.logger, "DeployAgent")
        
        context = {
            "workflow_context": message,
        }

        return {
            "context":context
        }
        

    async def act(self, plan):
        log_acting(self.logger, "DeployAgent")
        
        result = self.github_manager.deploy(plan["context"])
        return result
