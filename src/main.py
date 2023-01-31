import os
import supervisely as sly
from dotenv import load_dotenv
from distutils import util


if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))


try:
    os.environ['modal.state.items']
except KeyError:
    sly.logger.warn('The option to download project is not selected, project will be download with items')
    DOWNLOAD_ITEMS = True
else:
    DOWNLOAD_ITEMS = bool(util.strtobool(os.environ['modal.state.items']))

STORAGE_DIR = sly.app.get_data_dir()


class MyExport(sly.app.Export):
    def process(self, context: sly.app.Export.Context):

        api = sly.Api.from_env()
        project = api.project.get_info_by_id(context.project_id)
        project_name = project.name

        result_dir = os.path.join(STORAGE_DIR, f"{project.id}_{project_name}")
        dataset_ids = [context.dataset_id] if context.dataset_id is not None else None

        sly.download_pointcloud_project(api=api, project_id=context.project_id, dest_dir=result_dir, dataset_ids=dataset_ids,
                                download_items=DOWNLOAD_ITEMS, batch_size=1, log_progress=True)

        archive_name = f"{project.id}_{project_name}.tar.gz"
        result_archive = os.path.join(STORAGE_DIR, archive_name)
        sly.fs.archive_directory(result_dir, result_archive)
        sly.logger.info("Result directory is archived")


app = MyExport()
app.run()
