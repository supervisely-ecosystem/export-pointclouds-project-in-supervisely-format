import os
import sys
from pathlib import Path
import supervisely as sly
from supervisely.app.v1.app_service import AppService
from distutils import util

root_source_dir = str(Path(sys.argv[0]).parents[1])
print(f"App source directory: {root_source_dir}")
sys.path.append(root_source_dir)

# only for convenient debug
from dotenv import load_dotenv
debug_env_path = os.path.join(root_source_dir, "debug.env")
secret_debug_env_path = os.path.join(root_source_dir, "secret_debug.env")
load_dotenv(debug_env_path)
load_dotenv(secret_debug_env_path, override=True)

api: sly.Api = sly.Api.from_env()
my_app = AppService()

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
TASK_ID = int(os.environ["TASK_ID"])
RESULT_DIR_NAME = 'Export pointclouds project in Supervisely format'
logger = sly.logger

try:
    os.environ['modal.state.items']
except KeyError:
    logger.warn('The option to download project is not selected, project will be download with items')
    DOWNLOAD_ITEMS = True
else:
    DOWNLOAD_ITEMS = bool(util.strtobool(os.environ['modal.state.items']))
