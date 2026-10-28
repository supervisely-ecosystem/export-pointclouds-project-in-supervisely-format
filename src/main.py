"""Export a point cloud project in Supervisely format: headless task from "Download as"."""

import os

import supervisely as sly
from dotenv import load_dotenv

import workflow as w
from settings import Settings

RESULT_DIR_NAME = "Export pointclouds project in Supervisely format"


def export_project(api: sly.Api, project, settings: Settings, work_dir: str) -> str:
    """Download the project to `<work_dir>/<RESULT_DIR_NAME>/<project name>/`; return the parent folder.

    The parent folder is what gets archived, so the archive's top folder is the project name.
    """
    root = os.path.join(work_dir, RESULT_DIR_NAME)
    sly.fs.mkdir(root, remove_content_if_exists=True)
    sly.download_pointcloud_project(
        api=api,
        project_id=project.id,
        dest_dir=os.path.join(root, project.name),
        dataset_ids=None,  # every dataset, nested ones included
        download_items=settings.download_items,
        batch_size=1,
        log_progress=True,
    )
    return root


def upload_archive(api: sly.Api, team_id: int, task_id: int, project, root: str, work_dir: str):
    """Archive `root` as `<task>_<project id>_<project name>.tar` into Team Files and set it as task output."""
    archive_name = f"{task_id}_{project.id}_{project.name}.tar"
    local_archive = os.path.join(work_dir, archive_name)
    sly.fs.archive_directory(root, local_archive)
    sly.logger.info("Result directory is archived")

    remote_archive = os.path.join(sly.team_files.RECOMMENDED_EXPORT_PATH, RESULT_DIR_NAME, archive_name)
    progress = sly.tqdm_sly(
        desc=f"Upload {archive_name!r}", total=os.path.getsize(local_archive), unit="B", unit_scale=True
    )
    file_info = api.file.upload(team_id, local_archive, remote_archive, progress_cb=progress)
    sly.logger.info(f"Uploaded to Team-Files: {file_info.storage_path!r}")
    api.task.set_output_archive(task_id, file_info.id, archive_name, file_url=file_info.storage_path)
    return file_info


def main() -> None:
    if not sly.is_production():
        load_dotenv("local.env")
        load_dotenv(os.path.expanduser("~/supervisely.env"))

    settings = Settings.from_env()
    team_id = sly.env.team_id()
    task_id = sly.env.task_id()
    project_id = sly.env.project_id()
    sly.logger.info(f"Team: {team_id}, project: {project_id}, settings: {settings}")
    api = sly.Api.from_env()

    project = api.project.get_info_by_id(project_id)
    w.workflow_input(api, project.id)
    work_dir = sly.app.get_data_dir()
    root = export_project(api, project, settings, work_dir)
    file_info = upload_archive(api, team_id, task_id, project, root, work_dir)
    w.workflow_output(api, file_info)


if __name__ == "__main__":
    sly.main_wrapper("main", main)
