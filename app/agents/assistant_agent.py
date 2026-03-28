from app.agents.base_agent import BaseAgent
from app.tools.gemini_client import ask_llm
from app.config import settings
from app.utils.logger import get_agent_logger, log_thinking, log_acting


class AssistantAgent(BaseAgent):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.logger = get_agent_logger("AssistantAgent")

    async def think(self, message):
        log_thinking(self.logger, "AssistantAgent")

        feature = message.get("feature", "")
        context = message.get("context", "")
        history = message.get("history", [])

        recent_history = history[-settings.MAX_HISTORY:]
        formatted_history = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in recent_history
        ])

        prompt = f"""
            You are an expert software engineer and assistant.

            Answer the user's question clearly and accurately using the provided context.

            USER QUESTION:
            {feature}

            RECENT CONVERSATION HISTORY:
            {formatted_history}

            RELEVANT CODEBASE CONTEXT:
            {context}

            INSTRUCTIONS:
            - If the context contains relevant information, use it in your answer
            - If the context is not relevant, answer using your own knowledge
            - Keep the answer concise but helpful
            - Include code examples if useful
            - Do NOT mention "context" explicitly in your answer
            - Do NOT hallucinate project-specific details if not present in context

            Return a clear, direct answer.
            """
        
        return {
            "type": "question",
            "prompt": prompt
        }


    async def act(self, plan):
        log_acting(self.logger, "AssistantAgent")
        answer = ask_llm(plan["prompt"], settings.ASSISTANT_MODEL)

        return {
            "type": "question",
            "answer": answer.strip()
        }
