import re
import json
from app.agents.base_agent import BaseAgent
from app.tools.gemini_client import ask_llm
from app.config import settings
from app.utils.logger import get_agent_logger, log_thinking, log_acting


class PlannerAgent(BaseAgent):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.logger = get_agent_logger("PlannerAgent")

    async def think(self, message):
        log_thinking(self.logger, "PlannerAgent")

        feature = message["feature"]
        context = message["context"]
        history = message["history"]

        recent_history = history[-settings.MAX_HISTORY:]
        formatted_history = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in recent_history
        ])

        prompt = f"""
            You are an expert AI system planner responsible for orchestrating a multi-agent software engineering system.

            The current system has the following agents:

            - planner : decides execution plan
            - assistant : answers questions, explains code, provides guidance
            - codegen : generates or modifies code
            - reviewer : reviews code quality and correctness
            - tester : runs tests using pytest
            - deployer : pushes code and creates a pull request

            ---

            Your job is to:
            1. Understand the USER REQUEST
            2. Decide which agents should run
            3. If codegen is needed, break work into FILE-LEVEL tasks
            4. Return a MINIMAL and CORRECT execution plan

            ---

            USER REQUEST:
            {feature}

            RECENT CONVERSATION HISTORY:
            {formatted_history}

            CONTEXT (optional):
            {context}

            ---

            ### Rules for Planning

            - Only include agents that are NECESSARY
            - Do NOT include unnecessary steps
            - Prefer shorter pipelines when possible

            ---

            ### Tool Usage Rules (VERY IMPORTANT)

            - If the user request requires REAL-TIME data from filesystem or project structure,
            you MUST use tools instead of answering from context.

            - NEVER answer from context if a tool can provide a more accurate answer.

            #### Use tools when user asks to:
            - "list files", "show files", "what files exist"
            - "read file", "open file", "show content"
            - "project structure", "directory contents"

            -> action_type = "tool_call"
            -> steps = ["file_manager"]
            -> include tool_operations

            CRITICAL RULE:
            If a tool can answer the request -> DO NOT use assistant

            ### Agent Selection Guidelines

            #### If user asks to:
            - "build", "create", "implement", "add feature"
            -> ["codegen", "reviewer", "tester", "deployer"]

            - "fix bug", "debug", "correct code"
            -> ["codegen", "tester"]

            - "review code", "is this correct", "check quality"
            -> ["reviewer"]

            - "test", "run tests", "validate"
            -> ["tester"]

            - "deploy", "create PR", "push to github"
            -> ["tester", "deployer"]

            - Question, explain, how does, what is, help understanding
            -> ["assistant"]

            ---

            ### Constraints

            - Always include "tester" before "deployer"
            - Never deploy untested code
            - Do NOT include "codegen" if user did not ask for code changes
            - Do NOT include "reviewer" unless explicitly needed or after codegen

            ---

            ### Task Generation (Only if codegen is needed)

            If codegen is selected, generate file-level tasks:
            - Each task = ONE output file
            - DO NOT split a file into multiple tasks
            - Minimum 4 sentences per description
            - Include key functions, logic, libraries

            ---

            ### Output Format (STRICT)

            Return ONLY valid JSON:

            {{
                "type": "workflow",
                "action_type": "codegen",  # options: "tool_call", "codegen", "codegen+tools", "question", "hybrid"
                "steps": ["agent1", "agent2", "..."],
                "tasks": [
                    {{"name": "task_name", "description": "...", "output_file": "file.ext"}}
                ],
                "tool_operations": [
                    {{"operation": "create_file|read_file|write_file|create_folder|delete_file|delete_folder|list_files", "path": "...", "content": "..."}}
                ]
            }}

            ---

            ### Examples

            User: "Build a login system"
            Output:
            {{
                "type": "workflow",
                "action_type": "codegen",
                "steps": ["codegen", "reviewer", "tester", "deployer"],
                "tasks": [{{"name": "login_handler", "description": "...", "output_file": "auth.py"}}],
                "tool_operations": []
            }}

            User: "Create a file named config.json with settings"
            Output:
            {{
                "type": "workflow",
                "action_type": "tool_call",
                "steps": ["file_manager"],
                "tasks": [],
                "tool_operations": [{{"operation": "write_file", "path": "config.json", "content": "..."}}]
            }}

            User: "Build login and also create a data directory"
            Output:
            {{
                "type": "workflow",
                "action_type": "codegen+tools",
                "steps": ["codegen", "file_manager", "reviewer", "tester", "deployer"],
                "tasks": [{{"name": "login_handler", "description": "...", "output_file": "auth.py"}}],
                "tool_operations": [{{"operation": "create_folder", "path": "data/"}}]
            }}

            User: "Test my code"
            Output:
            {{
                "type": "workflow",
                "action_type": "tool_call",
                "steps": ["tester"],
                "tasks": [],
                "tool_operations": []
            }}

            User: "Is this code correct?"
            Output:
            {{
                "type": "workflow",
                "action_type": "question",
                "steps": ["reviewer"],
                "tasks": []
            }}

            User: "list all files in the project"
            Output:
            {{
                "type": "workflow",
                "action_type": "tool_call",
                "steps": ["file_manager"],
                "tasks": [],
                "tool_operations": [{{"operation": "list_files", "path": "."}}]
            }}

            ---

            Return ONLY JSON. No explanation.
            """
        
        return {
            "type": "plan",
            "feature": feature,
            "prompt": prompt
        }


    async def act(self, plan):
        log_acting(self.logger, "PlannerAgent")

        response = ask_llm(plan["prompt"], settings.PLANNER_MODEL)

        try:
            cleaned = re.sub(r"```json|```", "", response).strip()
            plan_data = json.loads(cleaned)
            agents = plan_data.get("steps", [])
            tasks = plan_data.get("tasks", [])
            action_type = plan_data.get("action_type", "question")
            tool_operations = plan_data.get("tool_operations", [])
        except Exception as e:
            self.logger.warning(f"JSON parse failed: {e}")
            agents = []
            tasks = []
            action_type = "question"
            tool_operations = []
        
        self.logger.info(f"Action Type: {action_type}")
        self.logger.info(f"Selected agents: {agents}")
        self.logger.debug(f"Tasks: {tasks}")
        self.logger.debug(f"Tool Operations: {tool_operations}")

        return { "type": plan["type"], "feature": plan["feature"], "agents": agents, "tasks": tasks, "action_type": action_type, "tool_operations": tool_operations}
