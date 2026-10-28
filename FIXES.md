# Fixes: export-pointclouds-project-in-supervisely-format (branch `ecosystem-fixes-2026-10`)

Lifecycle `legacy` (7,627 runs), small (~60 lines) and headless: entry point rewritten as a plain
`main()` and moved to the hardened image. Base: `origin/HEAD` f69b2af (v1.1.12). Nothing pushed or released.

## Behaviour contract (unchanged)

Headless, "Download as" on `point_cloud_project`.

| input | default | meaning |
|---|---|---|
| project context (`modal.state.slyProjectId`) | | every dataset, nested ones included |
| `modal.state.items` | `"True"` (missing → True with a warning) | `True` point clouds + annotations; `False` annotations, photo context images and empty placeholder `.pcd` files (SDK behaviour) |

Output: SDK point cloud project layout under a top folder named after the project
(`meta.json`, `key_id_map.json`, `<ds>/pointcloud|ann|related_images/<cloud>_pcd/…`, nested
`<ds>/datasets/<child>/…`), archived as `<task>_<project id>_<project name>.tar`, uploaded to
`/tmp/supervisely/export/Export pointclouds project in Supervisely format/`, set as the task
output archive. Workflow: project in, file out. Download batch size stays 1 (the SDK checks the
order of bulk annotations against names).

## Fixed

| # | commit | change | tests |
|---|---|---|---|
| 1 | 9bd6539 | **Image and runtime.** Off the shared legacy image `supervisely/base-py-sdk:6.74.32` onto `supervisely/base-py-sdk-hardened:6.74.34`; v1 `AppService` (agent event loop + callback + `my_app.stop`) replaced by `main()` under `sly.main_wrapper`; `distutils.util.strtobool` (gone in Python 3.12+) replaced by `settings.py`; ids read through `sly.env`; `globals.py` and `debug.env` removed, `local.env` added. | `tests/test_export.py`: 8 passed — real `sly.download_pointcloud_project` against a fake API (nested dataset, empty dataset, unlabeled cloud, non-ASCII and >80-char names, photo context), archive read back as `PointcloudProject` with every annotation deserialized; both `items` modes; flag parsing |

Run: 8/8 with SDK 6.74.34 (venv Python 3.14.3 and inside the image, Python 3.14.7), 8/8 with the
old SDK 6.74.32 (same layout). The old AppService entry point cannot run offline, so there is no
old-code count; no data-loss, wrong-success or security bug was found in the old code.

## Intentional changes

- An invalid `items` value fails before the download (before: `strtobool` raised inside the callback).
- Upload progress is reported with `sly.tqdm_sly` instead of a hand-rolled `sly.Progress` callback.

## Found, not fixed

- **Round trip through main-import is lossy for multi-dataset projects** (SDK, not this app):
  `supervisely/convert/pointcloud/sly/sly_pointcloud_converter.py` `validate_format` keys
  annotation files by bare file name across the whole archive and ignores the dataset tree, so
  `frame_000.pcd` in two datasets gets one of the two annotations, and datasets are flattened.
  Still on SDK `origin/master`.
- `items=False` exports empty placeholder `.pcd` files (SDK `touch`); such an archive is not
  meant for re-import.
- `config.json` has no `"version": "2.0.0"` (CI does not require it; left as is).

## Image

`supervisely/base-py-sdk:6.74.32` (sdk_legacy) → `supervisely/base-py-sdk-hardened:6.74.34`,
SDK 6.74.32 → 6.74.34: newest SDK `versions.json` allows for `instance_version` 6.17.22
([6.74.29, 6.74.35)); tag exists. The app imports only the SDK and python-dotenv (an SDK
dependency), so no per-app image; `release.yml` has no build job. `instance_version` unchanged.

## Dev-check plan

Compare branch vs published (v1.1.12) archives: member list + SHA-256 (clouds, images) and
canonical JSON (annotations, ignoring `key` UUIDs in `key_id_map.json`).

| case | command | expected (branch) | published |
|---|---|---|---|
| full, with photo context | `uv run ecosystem-fleet/fleet.py run export-pointclouds-project-in-supervisely-format --workspace 733 --project 1751 --version ecosystem-fixes-2026-10 --branch` | 30 clouds + ann + related images in `ds0`; task output archive `<task>_1751_Demo pointcloud project with labels.tar`; identical to published | same without `--version/--branch` |
| annotations only | `… --project 1751 --state items=False --version ecosystem-fixes-2026-10 --branch` | 30 annotations, empty `.pcd` placeholders; identical to published | same without `--version/--branch` |
| two datasets | `… --project 9779 --version ecosystem-fixes-2026-10 --branch` | `ds0`, `ds1` with 3 clouds each; identical to published | same without `--version/--branch` |
| nested (setup needed) | copy project 9779 into ws 733 as "agents export-pcd nested" with `ds1` moved under `ds0`; `… --project <id> --version ecosystem-fixes-2026-10 --branch` | `ds0/datasets/ds1/…` | same layout |

Also check in the task log that the app starts on the hardened image (no AppService lines) and
exits 0, and the workflow shows project → archive.
