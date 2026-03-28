from app.config import Settings
from app.utils.logger import setup_logger, log_workflow_step


class FeatureDeliveryWorkflow:

    def __init__(self, bus, session_store=None, code_indexer=None, context_indexer=None, session_id="default"):
        self.bus = bus
        self.session_store = session_store
        self.code_indexer = code_indexer
        self.context_indexer = context_indexer
        self.session_id = session_id
        self.logger = setup_logger("workflow.feature_delivery")

    async def run(self, feature):
        if self.session_store:
            self.session_store.create_session(self.session_id)
            self.session_store.add_message(self.session_id, "user", feature)
            if self.context_indexer:
                self.context_indexer.index_user_query(self.session_id, feature)

        rag_context = await self.bus.send(
            "rag",
            {"query": feature}
        )

        history = self.session_store.get_messages(self.session_id) if self.session_store else []
        plan = await self.bus.send("planner", {"feature": feature, "context": rag_context["context"], "history":history})

        agents = plan.get("agents", [])
        action_type = plan.get("action_type", "question")
        tool_operations = plan.get("tool_operations", [])

        self.logger.info(f"Agentic Flow: {agents}")
        self.logger.info(f"Action Type: {action_type}")

        workflow_state = {
            "feature": feature,
            "context": rag_context["context"],
            "tasks": plan.get("tasks", []),
            "results": {},
            "action_type": action_type,
            "tool_operations": tool_operations,
        }

        for agent_name in agents:
            log_workflow_step(self.logger, f"Running agent: {agent_name}")
            
            if agent_name == "assistant":
                workflow_state = await self._execute_assistant(workflow_state)
            elif agent_name == "codegen":
                workflow_state = await self._execute_codegen_pipeline(workflow_state)
            elif agent_name == "file_manager":
                workflow_state = await self._execute_file_manager(workflow_state)
            elif agent_name == "reviewer":
                if workflow_state.get("results", {}).get("codegen"):
                    self.logger.info("Skipping standalone reviewer - codegen already includes review")
                else:
                    workflow_state = await self._execute_reviewer(workflow_state)
            elif agent_name == "tester":
                workflow_state = await self._execute_tester(workflow_state)
            elif agent_name == "deployer":
                test_result = workflow_state.get("results", {}).get("tester", {})
                if not test_result.get("tests_passed", False):
                    self.logger.info("Skipping deployer - tests failed")
                    workflow_state["results"]["deployer"] = {"status": "skipped", "reason": "tests_failed"}
                else:
                    workflow_state = await self._execute_deployer(workflow_state)
            else:
                self.logger.warning(f"Unknown agent: {agent_name}")

        if self.session_store:
            for agent_name, result in workflow_state.get("results", {}).items():
                self.session_store.add_user_context(
                    self.session_id,
                    agent_name,
                    str(result)
                )

        result = workflow_state.get("results", {})
        log_workflow_step(self.logger, "Final Result", str(result)[:100])
        return result

    async def _execute_codegen_pipeline(self, workflow_state):
        tasks = workflow_state.get("tasks", [])
        
        if not tasks:
            self.logger.info("No tasks provided for codegen, skipping...")
            workflow_state["results"]["codegen"] = []
            return workflow_state
            
        results = []
        all_generated_files = []

        for task in tasks:
            self.logger.info(f"Generating: {task['output_file']}")

            context = await self.bus.send(
                "rag",
                {"query": task["description"]}
            )

            retries = 0

            code = await self.bus.send(
                "codegen",
                {
                    "task": task,
                    "context": context["context"],
                },
            )

            review = await self.bus.send("reviewer", code)
            
            self.logger.info(f"Review score: {review['score']}")
            
            while review["score"] < Settings.CODE_REVIEW_THRESHOLD and retries < Settings.MAX_RETRIES:
                retries += 1
                self.logger.info(f"Retrying generation ({retries})...")

                code = await self.bus.send("codegen", {"task": task, "context": context["context"]})
                review = await self.bus.send("reviewer", code)

            results.append(code)
            
            if code.get("files"):
                all_generated_files.extend(code["files"])

        if self.code_indexer and all_generated_files:
            self.logger.info(f"Indexing {len(all_generated_files)} generated files")
            self.code_indexer.index_files(all_generated_files)

        workflow_state["results"]["codegen"] = results
        return workflow_state

    async def _execute_reviewer(self, workflow_state):
        tasks = workflow_state.get("tasks", [])
        feature = workflow_state.get("feature", "")
        
        if tasks:
            results = []
            for task in tasks:
                file_paths = [task.get("output_file", "")]
                result = await self.bus.send("reviewer", {
                    "task": task.get("name", ""),
                    "description": task.get("description", ""),
                    "files": file_paths,
                })
                results.append(result)
            result = results
        else:
            rag_result = await self.bus.send("rag", {"query": feature})
            code_context = rag_result.get("context", "")
            
            result = await self.bus.send("reviewer", {
                "task": "Review requested code",
                "description": feature,
                "files": [],
                "code_context": code_context,
            })
        
        workflow_state["results"]["reviewer"] = result
        return workflow_state

    async def _execute_tester(self, workflow_state):
        self.logger.info("Running tests...")
        test = await self.bus.send("tester", {})
        self.logger.info(f"Test result: {test}")
        workflow_state["results"]["tester"] = test
        workflow_state["results"]["tester"]["status"] = "completed" if test.get("tests_passed") else "tests_failed"
        if not test["tests_passed"]:
            workflow_state["status"] = "tests_failed"
        return workflow_state

    async def _execute_deployer(self, workflow_state):
        deploy = await self.bus.send("deployer", {})
        workflow_state["results"]["deployer"] = deploy
        return workflow_state

    async def _execute_assistant(self, workflow_state):
        history = self.session_store.get_messages(self.session_id) if self.session_store else []
        result = await self.bus.send("assistant", {
            "feature": workflow_state["feature"],
            "context": workflow_state["context"],
            "history": history
        })
        workflow_state["results"]["assistant"] = result
        
        if self.session_store:
            self.session_store.add_message(self.session_id, "assistant", result.get("answer", ""))
        
        return workflow_state

    async def _execute_file_manager(self, workflow_state):
        tool_operations = workflow_state.get("tool_operations", [])
        
        if not tool_operations:
            self.logger.info("No tool operations provided for file_manager, skipping...")
            workflow_state["results"]["file_manager"] = {"status": "skipped", "reason": "no_operations"}
            return workflow_state

        result = await self.bus.send("file_manager", {
            "operations": tool_operations
        })
        
        workflow_state["results"]["file_manager"] = result
        return workflow_state
