"""Workflow lineage: the input project and the output archive of this app."""

import supervisely as sly


def workflow_input(api: sly.Api, project_id: int | str) -> None:
    api.app.workflow.add_input_project(int(project_id))
    sly.logger.debug(f"Workflow: Input project - {project_id}")


def workflow_output(api: sly.Api, file: int | sly.api.file_api.FileInfo) -> None:
    try:
        if isinstance(file, int):
            file = api.file.get_info_by_id(file)
        relation_settings = sly.WorkflowSettings(
            title=file.name,
            icon="archive",
            icon_color="#33c94c",
            icon_bg_color="#d9f7e4",
            url=f"/files/{file.id}/true/?teamId={file.team_id}",
            url_title="Download",
        )
        meta = sly.WorkflowMeta(relation_settings=relation_settings)
        api.app.workflow.add_output_file(file, meta=meta)
        sly.logger.debug(f"Workflow: Output file - {file}")
    except Exception as e:
        sly.logger.debug(f"Failed to add output to the workflow: {repr(e)}")
