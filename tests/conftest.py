"""Offline test harness: a small in-memory fake of the sly.Api calls the SDK point cloud
download makes, so the real `sly.download_pointcloud_project` runs without a server.

Run from the repo root with the SDK from dev_requirements.txt installed (plus pytest):
    python -m pytest
"""

import os
import sys
import tarfile
from types import SimpleNamespace

import numpy as np
import supervisely as sly
from supervisely.api.pointcloud.pointcloud_api import PointcloudInfo
from supervisely.geometry.cuboid_3d import Cuboid3d, Vector3d
from supervisely.video_annotation.key_id_map import KeyIdMap

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

PROJECT_ID = 10
CAR = sly.ObjClass("car", Cuboid3d)
META = sly.ProjectMeta(obj_classes=[CAR])

# tree: 1 "lidar" -> 2 "night" (nested); 3 "empty" (no point clouds)
DATASETS = {1: ("lidar", None), 2: ("night", 1), 3: ("empty", None)}
# dataset id -> [(cloud id, name, labeled, related image names)]
CLOUDS = {
    1: [(101, "frame_000.pcd", True, ["cam0.png"]), (102, "frame_001.pcd", False, [])],
    2: [(201, "Ночь_ünïcode_" + "x" * 80 + ".pcd", True, ["front.jpg", "back.jpg"])],
    3: [],
}


def _dataset_info(ds_id):
    name, parent = DATASETS[ds_id]
    fields = {f: None for f in sly.DatasetInfo._fields}
    fields.update(id=ds_id, name=name, parent_id=parent, project_id=PROJECT_ID)
    return sly.DatasetInfo(**fields)


def _parents(ds_id):
    out, parent = [], DATASETS[ds_id][1]
    while parent is not None:
        out.insert(0, DATASETS[parent][0])
        parent = DATASETS[parent][1]
    return out


def _cloud_info(cloud_id, name, ds_id):
    fields = {f: None for f in PointcloudInfo._fields}
    fields.update(id=cloud_id, name=name, dataset_id=ds_id, meta={"frame": cloud_id})
    return PointcloudInfo(**fields)


def _ann_json(cloud_id, name, labeled):
    if not labeled:
        ann = sly.PointcloudAnnotation()
    else:
        obj = sly.PointcloudObject(CAR)
        cuboid = Cuboid3d(Vector3d(1, 2, 3), Vector3d(0, 0, 0.5), Vector3d(4, 2, 1.5))
        ann = sly.PointcloudAnnotation(
            objects=sly.VideoObjectCollection([obj]), figures=[sly.PointcloudFigure(obj, cuboid)]
        )
    data = ann.to_json(KeyIdMap())
    data["name"] = name
    data["pointCloudId"] = cloud_id
    # the server returns ids on objects and figures
    for i, item in enumerate(data["objects"] + data["figures"]):
        item["id"] = cloud_id * 100 + i
    return data


class FakeApi:
    def __init__(self):
        self.downloaded = []
        clouds = {c[0]: (ds, c) for ds, items in CLOUDS.items() for c in items}
        rimages = {}
        for items in CLOUDS.values():
            for cloud_id, _, _, names in items:
                rimages[cloud_id] = [
                    {"id": cloud_id * 10 + i, "name": n, "entityId": cloud_id, "meta": {"deviceId": n}}
                    for i, n in enumerate(names)
                ]
        self.project = SimpleNamespace(
            get_meta=lambda id, with_settings=False: META.to_json(),
            get_info_by_id=lambda id: SimpleNamespace(id=id, name="Lidar Ünï", type="point_clouds"),
        )
        self.dataset = SimpleNamespace(
            tree=lambda project_id: iter([(_parents(i), _dataset_info(i)) for i in DATASETS])
        )

        def write(path, data):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)

        def download_path(cloud_id, path):
            self.downloaded.append(cloud_id)
            write(path, b"# .PCD v0.7\n")

        def download_related_image(rimage_id, path):
            sly.image.write(path, np.zeros((4, 4, 3), dtype=np.uint8))

        self.pointcloud = SimpleNamespace(
            get_list=lambda ds_id: [_cloud_info(c, n, ds_id) for c, n, _, _ in CLOUDS[ds_id]],
            annotation=SimpleNamespace(
                download_bulk=lambda ds_id, ids: [
                    _ann_json(i, clouds[i][1][1], clouds[i][1][2]) for i in ids
                ]
            ),
            get_list_related_images_batch=lambda ds_id, ids: [r for i in ids for r in rimages[i]],
            get_list_related_images=lambda cloud_id: [dict(r) for r in rimages[cloud_id]],
            download_path=download_path,
            download_related_image=download_related_image,
        )
        self.image = SimpleNamespace(figure=SimpleNamespace(download=lambda dataset_id, image_ids: {}))
        self.uploaded = []
        self.outputs = []
        self.workflow = []
        self.file = SimpleNamespace(upload=self._upload)
        self.task = SimpleNamespace(set_output_archive=lambda *a, **k: self.outputs.append((a, k)))
        self.app = SimpleNamespace(
            workflow=SimpleNamespace(
                add_input_project=lambda i: self.workflow.append(("project", i)),
                add_output_file=lambda *a, **k: self.workflow.append(("file",)),
            )
        )

    def _upload(self, team_id, src, dst, progress_cb=None):
        self.uploaded.append((team_id, src, dst))
        return SimpleNamespace(id=1, name=os.path.basename(dst), storage_path=dst, team_id=team_id)


def tar_members(path):
    with tarfile.open(path) as tar:
        return sorted(m.name for m in tar.getmembers() if m.isfile())
