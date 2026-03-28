import subprocess
from app.config import settings
from app.utils.logger import setup_logger


class TerminalTool:
    def __init__(self):
        self.logger = setup_logger("tool.terminal")

    def run_tests(self):
        try:
            result = subprocess.run(
                ["pytest"],
                capture_output=True,
                text=True,
                cwd=settings.REPO_PATH
            )

            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Test error: {e}")
            return False
