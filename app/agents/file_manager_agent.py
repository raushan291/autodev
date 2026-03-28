import os
from app.agents.base_agent import BaseAgent
from app.config import settings
from app.utils.logger import get_agent_logger, log_thinking, log_acting
from external_agents import TOOLS


class FileManagerAgent(BaseAgent):
    def __init__(self, name, bus, base_path=None):
        super().__init__(name, bus)
        self.base_path = base_path or settings.REPO_PATH
        self.tools = TOOLS
        self.logger = get_agent_logger("FileManagerAgent")

    def _get_tool_function(self, operation):
        tool_map = {
            "create_file": "create_file",
            "delete_file": "delete_file",
            "read_file": "read_file",
            "write_file": "write_file",
            "modify_file": "modify_file",
            "create_folder": "create_folder",
            "delete_folder": "delete_folder",
            "list_files": "list_files",
            "search_file_by_name": "search_file_by_name",
            "search_by_extension": "search_by_extension",
            "get_file_info": "get_file_info",
            "get_permissions": "get_permissions",
            "file_exists": "file_exists",
            "zip_folder": "zip_folder",
            "unzip_file": "unzip_file",
            "run_python_file": "run_python_file",
            "run_shell_command": "run_shell_command",
            "stop_process": "stop_process",
        }
        tool_name = tool_map.get(operation)
        tool = self.tools.get(tool_name) if tool_name else None
        return tool["function"] if tool and "function" in tool else None

    async def think(self, message):
        log_thinking(self.logger, "FileManagerAgent")
        
        operations = message.get("operations", [])
        
        return {
            "type": "file_operations",
            "operations": operations
        }

    async def act(self, plan):
        log_acting(self.logger, "FileManagerAgent")
        
        operations = plan.get("operations", [])
        results = []

        for op in operations:
            operation = op.get("operation", "")
            path = op.get("path", "")
            content = op.get("content", "")
            
            result = self._execute_operation(operation, path, content)
            results.append({
                "operation": operation,
                "path": path,
                "result": result
            })
            
            self.logger.info(f"Operation '{operation}' on '{path}': {result}")

        return {
            "type": "file_operations",
            "results": results
        }

    def _execute_operation(self, operation, path, content=""):
        tool_func = self._get_tool_function(operation)
        
        if not tool_func:
            return {"status": "error", "message": f"Unknown operation: {operation}"}
        
        try:
            if operation in ["create_file", "write_file"]:
                return tool_func(os.path.join(self.base_path, path), content or "")
            
            elif operation == "read_file":
                return tool_func(os.path.join(self.base_path, path))
            
            elif operation == "delete_file":
                return tool_func(os.path.join(self.base_path, path))
            
            elif operation == "modify_file":
                return tool_func(os.path.join(self.base_path, path), content)
            
            elif operation == "create_folder":
                return tool_func(os.path.join(self.base_path, path))
            
            elif operation == "delete_folder":
                return tool_func(os.path.join(self.base_path, path))
            
            elif operation == "list_files":
                return tool_func(self.base_path)
            
            elif operation == "search_file_by_name":
                pattern = path
                return tool_func(pattern, self.base_path)
            
            elif operation == "search_by_extension":
                ext = path
                return tool_func(ext, self.base_path)
            
            elif operation == "get_file_info":
                return tool_func(os.path.join(self.base_path, path))
            
            elif operation == "get_permissions":
                return tool_func(os.path.join(self.base_path, path))
            
            elif operation == "file_exists":
                return tool_func(os.path.join(self.base_path, path))
            
            else:
                return {"status": "error", "message": f"Operation not supported: {operation}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
