from app.agents.base_agent import BaseAgent
from app.tools.terminal_tool import TerminalTool
from app.utils.logger import get_agent_logger, log_thinking, log_acting


class TestingAgent(BaseAgent):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.terminal = TerminalTool()
        self.logger = get_agent_logger("TestingAgent")

    async def think(self, message):
        log_thinking(self.logger, "TestingAgent")

        return {
            "context":message
        }

    async def act(self, plan):
        log_acting(self.logger, "TestingAgent")
        passed = self.terminal.run_tests()
        return {"tests_passed": passed}
