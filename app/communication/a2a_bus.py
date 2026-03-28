class A2ABus:

    def __init__(self):
        self.agents = {}

    def register(self, agent):
        self.agents[agent.name] = agent

    async def send(self, target, message):
        agent = self.agents[target]
        return await agent.run(message)
