from app.communication.a2a_bus import A2ABus
from app.agents.planner_agent import PlannerAgent
from app.agents.assistant_agent import AssistantAgent
from app.agents.codegen_agent import CodeGenAgent
from app.agents.review_agent import ReviewAgent
from app.agents.testing_agent import TestingAgent
from app.agents.deploy_agent import DeployAgent
from app.agents.rag_agent import RAGAgent
from app.agents.file_manager_agent import FileManagerAgent
from app.rag.vector_store import SimpleVectorStore
from app.rag.repo_indexer import RepoIndexer
from app.rag.code_indexer import CodeIndexer
from app.rag.context_indexer import ContextIndexer
from app.storage.session_store import SessionStore
from app.workflows.feature_delivery_workflow import FeatureDeliveryWorkflow
from app.config import Settings


async def create_system(session_id="default"):
    bus = A2ABus()
    store = SimpleVectorStore()
    indexer = RepoIndexer(store)
    indexer.index_repo(Settings.REPO_PATH)

    code_indexer = CodeIndexer(store)
    session_store = SessionStore()
    context_indexer = ContextIndexer(store)

    planner = PlannerAgent("planner", bus)
    assistant = AssistantAgent("assistant", bus)
    rag = RAGAgent("rag", bus, store, context_indexer=context_indexer)
    codegen = CodeGenAgent("codegen", bus)
    reviewer = ReviewAgent("reviewer", bus)
    tester = TestingAgent("tester", bus)
    deployer = DeployAgent("deployer", bus)
    file_manager = FileManagerAgent("file_manager", bus, base_path=Settings.REPO_PATH)

    bus.register(planner)
    bus.register(assistant)
    bus.register(rag)
    bus.register(codegen)
    bus.register(reviewer)
    bus.register(tester)
    bus.register(deployer)
    bus.register(file_manager)

    workflow = FeatureDeliveryWorkflow(
        bus, 
        session_store=session_store, 
        code_indexer=code_indexer, 
        context_indexer=context_indexer,
        session_id=session_id
    )

    return workflow


async def build_feature(feature, session_id="default"):
    workflow = await create_system(session_id)
    result = await workflow.run(feature)
    return result
