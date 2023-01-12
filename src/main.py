import os
import supervisely as sly
import globals as g


@g.my_app.callback("export-pointclouds-project-in-supervisely-format")
@sly.timeit
def export_pointclouds_project_in_supervisely_format(api: sly.Api, task_id, context, state, app_logger):
    project = api.project.get_info_by_id(g.PROJECT_ID)
    project_name = project.name

    result_dir = os.path.join(g.my_app.data_dir, g.RESULT_DIR_NAME, project_name)
    result_archive_path = os.path.join(g.my_app.data_dir, g.RESULT_DIR_NAME)
    archive_name = f"{g.TASK_ID}_{g.PROJECT_ID}_{project_name}.tar.gz"
    result_archive = os.path.join(g.my_app.data_dir, archive_name)
    remote_archive_path = os.path.join(
        sly.team_files.RECOMMENDED_EXPORT_PATH, f"{g.RESULT_DIR_NAME}/{archive_name}")

    sly.download_pointcloud_project(api=api, project_id=g.PROJECT_ID, dest_dir=result_dir, dataset_ids=None,
                               download_items=g.DOWNLOAD_ITEMS, batch_size=1, log_progress=True)

    sly.fs.archive_directory(result_archive_path, result_archive)
    app_logger.info("Result directory is archived")

    upload_progress = []

    def _print_progress(monitor, upload_progress):
        if len(upload_progress) == 0:
            upload_progress.append(sly.Progress(message="Upload {!r}".format(archive_name),
                                                total_cnt=monitor.len,
                                                ext_logger=app_logger,
                                                is_size=True))
        upload_progress[0].set_current_value(monitor.bytes_read)

    file_info = api.file.upload(g.TEAM_ID, result_archive, remote_archive_path,
                                lambda m: _print_progress(m, upload_progress))
    app_logger.info("Uploaded to Team-Files: {!r}".format(file_info.storage_path))
    api.task.set_output_archive(task_id, file_info.id, archive_name, file_url=file_info.storage_path)

    g.my_app.stop()


def main():
    sly.logger.info("Script arguments", extra={
        "TEAM_ID": g.TEAM_ID,
        "WORKSPACE_ID": g.WORKSPACE_ID,
        "modal.state.slyProjectId": g.PROJECT_ID
    })
    g.my_app.run(initial_events=[{"command": "export-pointclouds-project-in-supervisely-format"}])


if __name__ == '__main__':
    sly.main_wrapper("main", main)
