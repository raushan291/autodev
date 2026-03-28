import os
import subprocess
from app.config import settings
from app.utils.logger import setup_logger


logger = setup_logger("tool.github")


class BaseTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def run(self, cmd, cwd=None, check=False):
        result = subprocess.run(
            cmd,
            cwd=cwd or settings.REPO_PATH,
            capture_output=True,
            text=True,
            check=False
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    def execute(self, **kwargs):
        raise NotImplementedError


class GitInitTool(BaseTool):
    def __init__(self):
        super().__init__("git_init", "Initialize a new git repository")

    def execute(self, **kwargs):
        git_dir = os.path.join(settings.REPO_PATH, ".git")
        if os.path.exists(git_dir):
            return {"success": True, "message": "Git repo already exists", "action": "init_skipped"}

        result = self.run(["git", "init"])
        if result["success"]:
            self.run(["git", "branch", "-M", settings.DEFAULT_BRANCH])

        return {
            "success": result["success"],
            "message": "Initialized git repo" if result["success"] else result["stderr"],
            "action": "init" if result["success"] else "init_failed"
        }


class GitRemoteTool(BaseTool):
    def __init__(self):
        super().__init__("git_remote", "Manage git remotes (add, list, check existence)")

    def get_remotes(self):
        result = self.run(["git", "remote", "-v"])
        remotes = result["stdout"].strip()
        return {"origin": "origin" in remotes, "raw": remotes}

    def add_remote(self, url, name="origin"):
        result = self.run(["git", "remote", "add", name, url])
        return {
            "success": result["success"],
            "message": f"Added remote {name}" if result["success"] else result["stderr"],
            "action": "remote_added" if result["success"] else "remote_add_failed"
        }

    def execute(self, action="check", url=None, name="origin", **kwargs):
        if action == "check":
            return self.get_remotes()
        elif action == "add":
            return self.add_remote(url, name)
        return {"success": False, "message": "Unknown action", "action": "unknown"}


class GitBranchTool(BaseTool):
    def __init__(self):
        super().__init__("git_branch", "Manage git branches (create, switch, ensure main)")

    def list_branches(self):
        result = self.run(["git", "branch", "-a"])
        current = self.run(["git", "branch", "--show-current"])
        current_branch = current["stdout"].strip() if current["success"] else ""
        return {"branches": result["stdout"].strip(), "raw": result["stdout"], "current_branch": current_branch}

    def branch_exists(self, branch_name):
        result = self.run(["git", "branch", "--list", branch_name])
        return bool(result["stdout"].strip())

    def create_branch(self, branch_name, start_point=None):
        cmd = ["git", "checkout", "-B", branch_name]
        if start_point:
            cmd.append(start_point)
        result = self.run(cmd)
        return {
            "success": result["success"],
            "message": f"Created/switched to branch {branch_name}" if result["success"] else result["stderr"],
            "action": "branch_created" if result["success"] else "branch_create_failed"
        }

    def switch_branch(self, branch_name):
        result = self.run(["git", "checkout", branch_name])
        return {
            "success": result["success"],
            "message": f"Switched to {branch_name}" if result["success"] else result["stderr"],
            "action": "branch_switched" if result["success"] else "branch_switch_failed"
        }

    def ensure_main_branch(self):
        self.run(["git", "stash"])
        self.run(["git", "fetch", "origin"])

        main_exists = self.branch_exists(settings.DEFAULT_BRANCH)

        if main_exists:
            self.run(["git", "checkout", settings.DEFAULT_BRANCH])
            self.run(["git", "pull", "origin", settings.DEFAULT_BRANCH])
            return {
                "success": True,
                "message": f"Switched to existing {settings.DEFAULT_BRANCH} and pulled",
                "action": "main_synced"
            }
        else:
            self.run(["git", "clean", "-fd"])
            result = self.run(["git", "checkout", "-b", settings.DEFAULT_BRANCH, "origin/" + settings.DEFAULT_BRANCH])
            return {
                "success": result["success"],
                "message": f"Created {settings.DEFAULT_BRANCH} from origin" if result["success"] else result["stderr"],
                "action": "main_created" if result["success"] else "main_create_failed"
            }

    def execute(self, action="list", branch_name=None, start_point=None, **kwargs):
        if action == "list":
            return self.list_branches()
        elif action == "exists":
            return {"exists": self.branch_exists(branch_name)}
        elif action == "create":
            return self.create_branch(branch_name, start_point)
        elif action == "switch":
            return self.switch_branch(branch_name)
        elif action == "ensure_main":
            return self.ensure_main_branch()
        return {"success": False, "message": "Unknown action", "action": "unknown"}


class GitCommitTool(BaseTool):
    def __init__(self):
        super().__init__("git_commit", "Stage and commit changes")

    def get_status(self):
        result = self.run(["git", "status", "--porcelain"])
        return {"has_changes": bool(result["stdout"].strip()), "status": result["stdout"]}

    def stage_all(self):
        result = self.run(["git", "add", "."])
        return {
            "success": result["success"],
            "message": "Staged all changes" if result["success"] else result["stderr"],
            "action": "staged"
        }

    def commit(self, message):
        result = self.run(["git", "commit", "-m", message])
        stdout_lower = result["stdout"].lower()
        stderr_lower = result["stderr"].lower()

        if "nothing to commit" in stdout_lower or "nothing to commit" in stderr_lower:
            return {
                "success": True,
                "message": "Nothing to commit",
                "action": "nothing_to_commit",
                "committed": False
            }

        return {
            "success": result["success"],
            "message": "Commit created" if result["success"] else result["stderr"],
            "action": "committed" if result["success"] else "commit_failed"
        }

    def execute(self, action="status", message=None, **kwargs):
        if action == "status":
            return self.get_status()
        elif action == "stage":
            return self.stage_all()
        elif action == "commit":
            return self.commit(message)
        return {"success": False, "message": "Unknown action", "action": "unknown"}


class GitHubRepoTool(BaseTool):
    def __init__(self):
        super().__init__("github_repo_create", "Create GitHub repository using gh CLI")

    def check_repo_exists(self):
        result = self.run(["gh", "repo", "view", settings.GITHUB_REPO_NAME])
        return result["success"]

    def create_repo(self):
        visibility_flag = "--public" if settings.GITHUB_VISIBILITY == "public" else "--private"
        result = self.run([
            "gh", "repo", "create",
            settings.GITHUB_REPO_NAME,
            visibility_flag,
            "--source=.",
            "--remote=origin",
            "--push"
        ])

        return {
            "success": result["success"],
            "message": "Created GitHub repo" if result["success"] else result["stderr"],
            "action": "repo_created" if result["success"] else "repo_create_failed"
        }

    def execute(self, action="check", **kwargs):
        if action == "check":
            return {"exists": self.check_repo_exists()}
        elif action == "create":
            return self.create_repo()
        return {"success": False, "message": "Unknown action", "action": "unknown"}


class GitPushTool(BaseTool):
    def __init__(self):
        super().__init__("git_push", "Push branch to remote")

    def push(self, branch_name, force=False):
        cmd = ["git", "push", "-u", "origin", branch_name]
        if force:
            cmd.insert(2, "-f")
        result = self.run(cmd)

        return {
            "success": result["success"],
            "message": f"Pushed {branch_name} to origin" if result["success"] else result["stderr"],
            "action": "pushed" if result["success"] else "push_failed"
        }

    def execute(self, branch_name=None, force=False, **kwargs):
        if branch_name:
            return self.push(branch_name, force)
        return {"success": False, "message": "Branch name required", "action": "unknown"}


class GitHubPRTool(BaseTool):
    def __init__(self):
        super().__init__("github_pr_create", "Create GitHub pull request")

    def check_pr_exists(self, branch_name):
        result = self.run(["gh", "pr", "view", branch_name, "--json", "url,state"])
        if result["success"] and result["stdout"]:
            try:
                import json
                data = json.loads(result["stdout"])
                return {"exists": True, "url": data.get("url"), "state":data.get("state")}
            except:
                return {"exists": True}
        return {"exists": False}

    def create_pr(self, branch_name, title, base_branch=None):
        base = base_branch or settings.DEFAULT_BRANCH
        result = self.run([
            "gh", "pr", "create",
            "--base", base,
            "--head", branch_name,
            "--title", title,
            "--body", f"Auto-generated PR for: {title}"
        ])

        if result["success"]:
            return {
                "success": True,
                "message": "PR created successfully",
                "action": "pr_created",
                "url": result["stdout"].strip() if result["stdout"] else None
            }

        return {
            "success": False,
            "message": result["stderr"],
            "action": "pr_create_failed"
        }

    def execute(self, branch_name=None, title=None, base_branch=None, **kwargs):
        if branch_name and title:
            return self.create_pr(branch_name, title, base_branch)
        return {"success": False, "message": "Branch name and title required", "action": "unknown"}


class GitHubTool:
    def __init__(self):
        self.git_init = GitInitTool()
        self.git_remote = GitRemoteTool()
        self.git_branch = GitBranchTool()
        self.git_commit = GitCommitTool()
        self.github_repo = GitHubRepoTool()
        self.git_push = GitPushTool()
        self.github_pr = GitHubPRTool()

    def get_all_tools(self):
        return [
            self.git_init,
            self.git_remote,
            self.git_branch,
            self.git_commit,
            self.github_repo,
            self.git_push,
            self.github_pr
        ]

    def create_pr(self, branch, title):
        try:
            self.git_init.execute()
            remotes = self.git_remote.execute(action="check")
            if not remotes.get("origin"):
                self.git_remote.execute(action="add", url=settings.GITHUB_REPO_URL)

            self.git_branch.execute(action="ensure_main")
            self.git_branch.execute(action="create", branch_name=branch)

            status = self.git_commit.execute(action="status")
            if status.get("has_changes"):
                self.git_commit.execute(action="stage")
                self.git_commit.execute(action="commit", message=title)

            self.github_repo.execute(action="create")
            self.git_push.execute(branch_name=branch, force=True)
            pr_result = self.github_pr.execute(branch_name=branch, title=title)

            return {"status": "deployed", "message": "PR created successfully"}

        except Exception as e:
            logger.error(f"GitHubTool error: {e}")
            return {"status": "error", "message": str(e)}
