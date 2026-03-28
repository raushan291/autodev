class BaseAgent:
    def __init__(self, name, bus):
        self.name = name
        self.bus = bus

    async def think(self, message):
        raise NotImplementedError

    async def act(self, plan):
        raise NotImplementedError

    async def run(self, message):
        plan = await self.think(message)
        result = await self.act(plan)
        return result
