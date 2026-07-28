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

import glob
import logging
import os

import yaml

log = logging.getLogger(__name__)

CATALOG_API_VERSION = "kale.kubeflow.org/v2alpha1"
CATALOG_KIND = "ExamplesCatalog"
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
REQUIRED_FIELDS = {"id", "title", "description"}
CATALOG_SUBDIR = os.path.join("kale", "catalog")
SAMPLES_SUBDIR = os.path.join("kale", "samples")


def _has_path_traversal(value):
    """Check if a string contains path traversal components."""
    return ".." in value or value.startswith("/") or "\\" in value


def _has_id_traversal(value):
    """Check if an id contains path separators or traversal."""
    return "/" in value or "\\" in value or ".." in value


def validate_entry(entry, data_dir):
    """Validate a single catalog entry against schema and filesystem.

    Returns (True, "") if valid, or (False, reason) if invalid.
    """
    if not isinstance(entry, dict):
        return False, "entry is not a dict"

    for field in REQUIRED_FIELDS:
        if field not in entry or not isinstance(entry[field], str) or not entry[field]:
            return False, f"missing required field '{field}'"

    assets = entry.get("assets")
    if not isinstance(assets, dict) or "source" not in assets:
        return False, "missing required field 'assets.source'"
    if not isinstance(assets["source"], str):
        return False, "assets.source must be a string"

    entrypoint = entry.get("entrypoint")
    if not isinstance(entrypoint, dict) or "notebook" not in entrypoint:
        return False, "missing required field 'entrypoint.notebook'"
    if not isinstance(entrypoint["notebook"], str):
        return False, "entrypoint.notebook must be a string"

    sample_id = entry["id"]
    if _has_id_traversal(sample_id):
        return False, f"id '{sample_id}' contains path separators or '..'"

    source = assets["source"]
    if _has_path_traversal(source):
        return False, f"assets.source '{source}' contains path traversal"

    notebook = entrypoint["notebook"]
    if _has_path_traversal(notebook):
        return False, f"entrypoint.notebook '{notebook}' contains path traversal"

    difficulty = entry.get("difficulty")
    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        return False, f"invalid difficulty '{difficulty}'"

    if "tags" in entry and not isinstance(entry["tags"], list):
        return False, "tags must be a list"

    sample_dir = os.path.join(data_dir, SAMPLES_SUBDIR, source)
    if not os.path.isdir(sample_dir):
        return False, f"sample directory '{sample_dir}' does not exist"

    return True, ""


def discover_examples(data_dirs=None, _keep_source_dir=False):
    """Discover catalog entries from Jupyter data directories.

    Args:
        data_dirs: List of data directories to scan. If None, uses
            jupyter_core.paths.jupyter_path().
        _keep_source_dir: Internal flag. When True, includes '_source_dir'
            in returned entries for use by resolve_sample_dir.

    Returns:
        List of catalog entry dicts, merged with priority ordering
        (first directory wins for duplicate ids).
    """
    if data_dirs is None:
        from jupyter_core.paths import jupyter_path

        data_dirs = jupyter_path()

    seen_ids = {}  # id -> (data_dir, index in entries list)
    entries = []

    for data_dir in data_dirs:
        catalog_dir = os.path.join(data_dir, CATALOG_SUBDIR)
        if not os.path.isdir(catalog_dir):
            continue

        yaml_files = sorted(
            glob.glob(os.path.join(catalog_dir, "*.yaml"))
            + glob.glob(os.path.join(catalog_dir, "*.yml"))
        )
        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    doc = yaml.safe_load(f)
            except Exception:
                log.warning(
                    "Skipping %s: invalid YAML", yaml_file, exc_info=True
                )
                continue

            if not isinstance(doc, dict):
                log.warning("Skipping %s: not a YAML mapping", yaml_file)
                continue

            kind = doc.get("kind")
            if kind != CATALOG_KIND:
                continue

            api_version = doc.get("apiVersion")
            if api_version != CATALOG_API_VERSION:
                log.warning(
                    "Skipping %s: unknown apiVersion %s", yaml_file, api_version
                )
                continue

            items = doc.get("items", [])
            if not isinstance(items, list):
                log.warning("'items' in '%s' is not a list, skipping file", yaml_file)
                continue

            for item in items:
                valid, reason = validate_entry(item, data_dir)
                if not valid:
                    log.warning(
                        "Skipping invalid entry in '%s': %s",
                        yaml_file,
                        reason,
                    )
                    continue

                sample_id = item["id"]
                entry = {
                    "id": sample_id,
                    "title": item["title"],
                    "description": item["description"],
                    "tags": item.get("tags", []),
                    "difficulty": item.get("difficulty"),
                    "assets": item["assets"],
                    "entrypoint": item["entrypoint"],
                }
                if _keep_source_dir:
                    source = item["assets"]["source"]
                    entry["_source_dir"] = os.path.join(
                        data_dir, SAMPLES_SUBDIR, source
                    )

                if sample_id in seen_ids:
                    prev_dir, prev_idx = seen_ids[sample_id]
                    if prev_dir == data_dir:
                        # Same data_dir: later file wins (overwrite)
                        entries[prev_idx] = entry
                    # Different data_dir: higher-priority (earlier) dir wins, skip
                else:
                    seen_ids[sample_id] = (data_dir, len(entries))
                    entries.append(entry)

    return entries


def resolve_sample_dir(sample_id, data_dirs=None):
    """Find the sample directory and entry for a given sample id.

    Returns:
        Tuple of (source_dir_path, entry_dict) or None if not found.
    """
    entries = discover_examples(data_dirs=data_dirs, _keep_source_dir=True)
    for entry in entries:
        if entry["id"] == sample_id:
            source_dir = entry.pop("_source_dir")
            return source_dir, entry
    return None
