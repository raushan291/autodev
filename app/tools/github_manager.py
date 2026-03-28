import json
from app.tools.github_tool import GitHubTool
from app.tools.gemini_client import ask_llm
from app.utils.logger import setup_logger
from app.config import Settings


logger = setup_logger("tool.github_manager")


class GitHubManager:
    def __init__(self):
        self.github = GitHubTool()

    def get_state(self):
        state = {}

        remotes = self.github.git_remote.execute(action="check")
        state["remotes"] = remotes

        branches = self.github.git_branch.execute(action="list")
        state["branches"] = branches

        status = self.github.git_commit.execute(action="status")
        state["git_status"] = status

        repo_exists = self.github.github_repo.execute(action="check")
        state["repo_exists"] = repo_exists.get("exists", False) if "exists" in repo_exists else False

        current_branch = branches.get("current_branch", "")
        if current_branch:
            pr_check = self.github.github_pr.check_pr_exists(current_branch)
            if pr_check["exists"] and pr_check.get("state") == "OPEN":
                state["pr_exists"] = True
                state["pr_url"] = pr_check.get("url", "")
            else:
                state["pr_exists"] = False
                state["pr_url"] = ""
        else:
            state["pr_exists"] = False
            state["pr_url"] = ""

        return state

    def build_tools_description(self):
        tools = [
            {
                "name": "git_init",
                "description": "Initialize a new git repository if none exists",
                "params": {}
            },
            {
                "name": "git_remote_add",
                "description": "Add a remote origin URL",
                "params": {"url": "Git remote URL"}
            },
            {
                "name": "git_ensure_main",
                "description": "Ensure main branch exists and is up-to-date with origin",
                "params": {}
            },
            {
                "name": "git_branch_create",
                "description": "Create and switch to a new branch",
                "params": {"branch_name": "Name of branch to create", "start_point": "Optional starting point"}
            },
            {
                "name": "git_commit",
                "description": "Stage all changes and commit with a message",
                "params": {"message": "Commit message"}
            },
            {
                "name": "github_repo_create",
                "description": "Create a new GitHub repository (only if it doesn't exist)",
                "params": {}
            },
            {
                "name": "git_push",
                "description": "Push branch to remote (force if needed)",
                "params": {"branch_name": "Branch to push", "force": "Force push"}
            },
            {
                "name": "github_pr_create",
                "description": "Create a pull request (only if one doesn't already exist for this branch)",
                "params": {"branch_name": "Branch for PR", "title": "PR title", "base_branch": "Base branch (default: main)"}
            },
            {
                "name": "done",
                "description": "Deployment is complete (use when PR already exists or successfully created)",
                "params": {}
            }
        ]
        return json.dumps(tools, indent=2)

    def build_state_description(self, state):
        has_origin = state.get("remotes", {}).get("origin", False)
        branches = state.get("branches", {}).get("branches", "")
        has_changes = state.get("git_status", {}).get("has_changes", False)
        repo_exists = state.get("repo_exists", False)
        pr_exists = state.get("pr_exists", False)
        pr_url = state.get("pr_url", "")

        desc = f"""Current Git State:
            - Has remote origin: {has_origin}
            - Branches: {branches if branches else 'none'}
            - Has uncommitted changes: {has_changes}
            - GitHub repo exists: {repo_exists}
            - PR already exists: {pr_exists}
            - PR URL: {pr_url if pr_url else 'N/A'}
            """
        return desc

    def decide_next_action(self, state, context):
        tools_desc = self.build_tools_description()
        state_desc = self.build_state_description(state)

        prompt = f"""You are a deploy agent. Your task is to create a GitHub PR for a feature.

            Context from workflow:
            {json.dumps(context, indent=2)}

            {state_desc}

            Available tools:
            {tools_desc}

            Based on the current state and context, decide what to do next. Return a JSON object with:
            - "tool": tool name to call
            - "params": parameters for the tool (empty object if none needed)
            - "reasoning": why you chose this action

            IMPORTANT: If a PR already exists (pr_exists: true), use "done" tool immediately. Do NOT try to create another PR.
            If PR is successfully created, use "done" tool.

            Return ONLY valid JSON, no other text
            """

        try:
            response = ask_llm(prompt, Settings.DEPLOYER_MODEL)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"tool": "done", "params": {}, "reasoning": "Failed to parse LLM response"}
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {"tool": "done", "params": {}, "reasoning": f"LLM error: {e}"}

    def execute_tool(self, tool_name, params):
        if tool_name == "git_init":
            return self.github.git_init.execute(**params)
        elif tool_name == "git_remote_add":
            return self.github.git_remote.execute(action="add", **params)
        elif tool_name == "git_ensure_main":
            return self.github.git_branch.execute(action="ensure_main", **params)
        elif tool_name == "git_branch_create":
            return self.github.git_branch.execute(action="create", **params)
        elif tool_name == "git_commit":
            return self.github.git_commit.execute(action="stage") and self.github.git_commit.execute(action="commit", **params)
        elif tool_name == "github_repo_create":
            return self.github.github_repo.execute(action="create")
        elif tool_name == "git_push":
            return self.github.git_push.execute(**params)
        elif tool_name == "github_pr_create":
            return self.github.github_pr.execute(**params)
        elif tool_name == "done":
            return {"success": True, "message": "Deployment complete", "action": "done"}
        else:
            return {"success": False, "message": f"Unknown tool: {tool_name}"}

    def deploy(self, context):
        state = self.get_state()
        iteration = 0
        max_iterations = 10
        results = []

        if state.get("pr_exists"):
            logger.info("PR already exists, skipping deployment")
            return {
                "status": "deployed",
                "message": f"PR already exists: {state.get('pr_url', 'N/A')}",
                "iterations": 0,
                "steps": []
            }

        while iteration < max_iterations:
            if state.get("pr_exists"):
                logger.info(f"PR created in iteration {iteration + 1}, stopping.")
                break

            decision = self.decide_next_action(state, context)
            tool_name = decision.get("tool", "done")
            params = decision.get("params", {})
            reasoning = decision.get("reasoning", "")

            logger.info(f"Iteration {iteration + 1}: Tool: {tool_name} | Reason: {reasoning}")

            if tool_name == "done":
                logger.info("Deployment complete!")
                break

            result = self.execute_tool(tool_name, params)
            results.append({
                "tool": tool_name,
                "params": params,
                "result": result
            })

            state = self.get_state()
            iteration += 1

        return {
            "status": "deployed" if any(r["tool"] == "github_pr_create" and r["result"].get("success") for r in results) else "incomplete",
            "iterations": iteration,
            "steps": results
        }


class LegacyGitHubTool:
    def __init__(self):
        self.github = GitHubTool()

    def create_pr(self, branch, title):
        return self.github.create_pr(branch, title)
