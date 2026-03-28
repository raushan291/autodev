import os
class Settings:

    # DB settings
    COLLECTION_NAME = "codebase"
    PERSIST_DIR = "./chroma_db"
    EMB_MODLEL_NAME = "all-mpnet-base-v2"

    # Model configurations per agent
    DEFAULT_MODEL = "gemini-2.5-flash"
    
    PLANNER_MODEL = "gemini-2.5-pro"
    ASSISTANT_MODEL = "gemini-2.5-flash"
    CODEGEN_MODEL = "gemini-2.5-flash"
    REVIEWER_MODEL = "gemini-2.5-pro"
    DEPLOYER_MODEL = "gemini-2.5-flash"

    # Conversation settings
    MAX_HISTORY = 5

    # Code generation settings
    REPO_PATH = "/home/raushan/Documents/dummy_projetcs/app"
    MAX_RETRIES = 3
    CODE_REVIEW_THRESHOLD = 0.7

    if not os.path.exists(REPO_PATH):
        os.makedirs(REPO_PATH)

    # Github settings
    DEFAULT_BRANCH = "main"
    GITHUB_REPO_NAME = "test-repo"
    GITHUB_REPO_URL = "https://github.com/raushan291/test-repo"
    GITHUB_VISIBILITY = "public"

settings = Settings()
