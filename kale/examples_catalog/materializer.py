# Copyright 2026 The Kubeflow Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import logging
import os
import shutil

from kale.examples_catalog import loader

log = logging.getLogger(__name__)

KALE_MATERIALIZATION_DIR_ENV = "KALE_MATERIALIZATION_DIR"
DEFAULT_MATERIALIZATION_DIR = "kale-samples"
PROVENANCE_FILENAME = ".kale-sample.json"


def _get_materialization_dir():
    return os.environ.get(KALE_MATERIALIZATION_DIR_ENV, DEFAULT_MATERIALIZATION_DIR)


def _validate_sample_id(sample_id):
    if "/" in sample_id or "\\" in sample_id or ".." in sample_id:
        raise ValueError(
            f"Invalid sample_id '{sample_id}': must not contain path separators or '..'"
        )


def _get_sample_dest(sample_id, server_root=None):
    base = server_root if server_root else os.path.expanduser("~")
    mat_dir = _get_materialization_dir()
    return os.path.join(base, mat_dir, sample_id)


def _write_provenance(dest, sample_id, source_path):
    provenance = {
        "sample_id": sample_id,
        "source_path": source_path,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    provenance_path = os.path.join(dest, PROVENANCE_FILENAME)
    with open(provenance_path, "w") as f:
        json.dump(provenance, f, indent=2)


def check_existing(sample_id, server_root=None):
    """Check if a materialized copy of the sample exists."""
    dest = _get_sample_dest(sample_id, server_root)
    return os.path.isdir(dest)


def materialize(sample_id, server_root=None, data_dirs=None):
    """Materialize a sample and return the notebook path relative to server_root.

    If the sample is already materialized, updates the provenance timestamp
    without copying files (Open Existing flow).
    """
    _validate_sample_id(sample_id)

    result = loader.resolve_sample_dir(sample_id, data_dirs)
    if result is None:
        raise ValueError(f"Sample '{sample_id}' not found in any catalog")

    source_dir, entry = result
    dest = _get_sample_dest(sample_id, server_root)

    if not os.path.isdir(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copytree(source_dir, dest)
        log.info("Materialized sample '%s' to '%s'", sample_id, dest)

    _write_provenance(dest, sample_id, source_dir)

    mat_dir = _get_materialization_dir()
    notebook = entry["entrypoint"]["notebook"]
    return os.path.join(mat_dir, sample_id, notebook)


def recreate(sample_id, server_root=None, data_dirs=None):
    """Delete existing materialization and create a fresh copy."""
    dest = _get_sample_dest(sample_id, server_root)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
        log.info("Removed existing materialization at '%s'", dest)

    return materialize(sample_id, server_root, data_dirs)
