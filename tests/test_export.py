"""End to end: the archive the app uploads must be a point cloud project main-import reads back."""

import os
import tarfile

import pytest
import supervisely as sly

import main
from conftest import CLOUDS, FakeApi, tar_members
from settings import Settings


@pytest.fixture
def env(monkeypatch, tmp_path):
    for key in list(os.environ):
        if key.startswith("modal.state.") or key.startswith("context."):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("TASK_ID", "77")
    monkeypatch.setenv("context.teamId", "1")
    monkeypatch.setenv("context.workspaceId", "2")
    monkeypatch.setenv("modal.state.slyProjectId", "10")
    monkeypatch.setenv("SLY_APP_DATA_DIR", str(tmp_path / "data"))
    return monkeypatch


def _run(env, **state):
    for key, value in state.items():
        env.setenv(f"modal.state.{key}", value)
    api = FakeApi()
    env.setattr(sly.Api, "from_env", classmethod(lambda cls, *a, **k: api))
    main.main()
    return api


def _read_back(archive, tmp_path):
    out = tmp_path / "unpacked"
    with tarfile.open(archive) as tar:
        tar.extractall(out, filter="data")
    (project_dir,) = [p for p in out.iterdir()]
    project = sly.PointcloudProject(str(project_dir), sly.OpenMode.READ)
    sly.KeyIdMap.load_json(os.path.join(project_dir, "key_id_map.json"))  # must be valid
    items = {}
    for dataset in project.datasets:
        for name in dataset.get_items_names():
            ann = sly.PointcloudAnnotation.load_json_file(dataset.get_ann_path(name), project.meta, sly.KeyIdMap())
            items[(dataset.name, name)] = (len(ann.figures), dataset)
    return project_dir, items


def test_full_export_round_trips_with_nested_and_empty_datasets(env, tmp_path):
    api = _run(env, items="True")
    ((team_id, local, remote),) = api.uploaded
    assert team_id == 1
    assert remote == "/tmp/supervisely/export/Export pointclouds project in Supervisely format/77_10_Lidar Ünï.tar"
    ((args, kwargs),) = api.outputs
    assert args[0] == 77 and args[2] == "77_10_Lidar Ünï.tar"
    assert api.workflow == [("project", 10), ("file",)]

    members = tar_members(local)
    assert "Lidar Ünï/meta.json" in members and "Lidar Ünï/key_id_map.json" in members
    assert "Lidar Ünï/lidar/datasets/night/pointcloud/" + CLOUDS[2][0][1] in members
    assert "Lidar Ünï/lidar/related_images/frame_000_pcd/cam0.png" in members

    project_dir, items = _read_back(local, tmp_path)
    assert {k: v[0] for k, v in items.items()} == {
        ("lidar", "frame_000.pcd"): 1,
        ("lidar", "frame_001.pcd"): 0,  # no labels: annotation still exported
        ("lidar/night", CLOUDS[2][0][1]): 1,
    }
    assert os.path.isdir(project_dir / "empty")
    assert sorted(api.downloaded) == [101, 102, 201]


def test_annotations_only_skips_point_cloud_files(env, tmp_path):
    api = _run(env, items="False")
    assert api.downloaded == []
    ((_, local, _),) = api.uploaded
    _, items = _read_back(local, tmp_path)
    assert len(items) == 3


@pytest.mark.parametrize(
    "raw, expected", [("True", True), ("true", True), ("False", False), ("false", False), (None, True)]
)
def test_items_flag(raw, expected):
    env = {} if raw is None else {"modal.state.items": raw}
    assert Settings.from_env(env).download_items is expected


def test_bad_items_flag_fails_early():
    with pytest.raises(ValueError):
        Settings.from_env({"modal.state.items": "maybe"})
