import re
from app.agents.base_agent import BaseAgent
from app.tools.gemini_client import ask_llm
from app.config import settings
from app.utils.logger import get_agent_logger, log_thinking, log_acting


class ReviewAgent(BaseAgent):
    def __init__(self, name, bus):
        super().__init__(name, bus)
        self.logger = get_agent_logger("ReviewAgent")

    def load_file_content(self, file_path):
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            return f"# ERROR READING FILE: {e}"

    async def review_file(self, file_path, task, description):
        code = self.load_file_content(file_path)

        prompt = f"""You are a strict senior Python code reviewer.

            USER TASK: {task}

            TASK DESCRIPTION: {description}

            FILE: {file_path}

            CODE:
            ```python
            {code}
            ```

            Evaluate this file based on:
            1. Task completion
            2. Correctness
            3. Code quality
            4. Security issues
            5. Best practices

            Scoring:
            - 1.0 : fully correct
            - 0.8 : correct but minor issues
            - 0.6 : partially correct
            - 0.3 : major issues
            - 0.1 : incorrect

            Return ONLY a number between 0 and 1.
            """

        response = ask_llm(prompt, settings.REVIEWER_MODEL)

        try:
            score_match = re.findall(r"\d*\.?\d+", response)
            score = float(score_match[0]) if score_match else 0.5
        except:
            score = 0.5

        return {"file": file_path, "score": score}

    async def think(self, message):
        log_thinking(self.logger, "ReviewAgent")

        task = message.get("task", "")
        description = message.get("description", "")
        file_paths = message.get("files", [])
        code_context = message.get("code_context", "")

        # Skip case
        if not file_paths and not code_context:
            return {
                "type": "review",
                "skip": True
            }
        
        # Build plan
        return {
            "type": "review",
            "input": {
                "task": task,
                "description": description,
                "files": file_paths,
                "code_context": code_context
            }
        }


    async def act(self, plan):
        log_acting(self.logger, "ReviewAgent")

        if plan.get("skip"):
            self.logger.info("No files or code context, skipping review")
            return {
                "score": 1.0,
                "passed": True,
                "file_results": [],
                "files": [],
            }
        
        data = plan["input"]

        task = data["task"]
        description = data["description"]
        file_paths = data["files"]
        code_context = data["code_context"]

        if file_paths:
            file_results = []
            for path in file_paths:
                result = await self.review_file(path, task, description)
                file_results.append(result)

            scores = [r["score"] for r in file_results]
            overall_score = sum(scores) / len(scores) if scores else 0
        else:
            code = code_context

            prompt = f"""You are a strict senior Python code reviewer.

                USER TASK: {task}

                TASK DESCRIPTION: {description}

                CODE:
                ```python
                {code}
                ```

                Evaluate this file based on:
                1. Task completion
                2. Correctness
                3. Code quality
                4. Security issues
                5. Best practices

                Scoring:
                - 1.0 : fully correct
                - 0.8 : correct but minor issues
                - 0.6 : partially correct
                - 0.3 : major issues
                - 0.1 : incorrect

                Return ONLY a number between 0 and 1.
                """

            response = ask_llm(prompt, settings.REVIEWER_MODEL)
            try:
                score_match = re.findall(r"\d*\.?\d+", response)
                overall_score = float(score_match[0]) if score_match else 0.5
            except:
                overall_score = 0.5
            file_results = []

        passed = overall_score >= settings.CODE_REVIEW_THRESHOLD

        return {
            "score": overall_score,
            "passed": passed,
            "file_results": file_results,
            "files": file_paths,
        }
