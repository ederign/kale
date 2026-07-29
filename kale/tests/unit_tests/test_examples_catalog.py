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

import json
import logging
import os
from unittest.mock import patch

import pytest
import yaml

from kale.examples_catalog import loader, materializer
from kale.rpc import nb
from kale.rpc.errors import RPCNotFoundError


def _make_catalog_structure(
    base_dir, catalog_items, kind="ExamplesCatalog", filename="catalog.yaml"
):
    """Helper to create a catalog YAML and sample directories in a data dir."""
    catalog_dir = os.path.join(base_dir, "kale", "catalog")
    samples_dir = os.path.join(base_dir, "kale", "samples")
    os.makedirs(catalog_dir, exist_ok=True)

    doc = {
        "apiVersion": "kale.kubeflow.org/v2alpha1",
        "kind": kind,
        "items": catalog_items,
    }
    with open(os.path.join(catalog_dir, filename), "w") as f:
        yaml.dump(doc, f)

    for item in catalog_items:
        if isinstance(item, dict) and "assets" in item:
            source = item["assets"].get("source", "")
            if source and ".." not in source and not source.startswith("/"):
                sample_dir = os.path.join(samples_dir, source)
                os.makedirs(sample_dir, exist_ok=True)
                notebook = item.get("entrypoint", {}).get("notebook", "main.ipynb")
                with open(os.path.join(sample_dir, notebook), "w") as f:
                    f.write("{}")

    return base_dir


def _valid_item(sample_id="test-sample", **overrides):
    item = {
        "id": sample_id,
        "title": "Test Sample",
        "description": "A test sample",
        "tags": ["test"],
        "difficulty": "beginner",
        "assets": {"source": sample_id},
        "entrypoint": {"notebook": "main.ipynb"},
    }
    item.update(overrides)
    return item


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------


class TestDiscoverExamples:
    def test_single_catalog(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item()])
        result = loader.discover_examples(data_dirs=[data_dir])
        assert len(result) == 1
        assert result[0]["id"] == "test-sample"
        assert result[0]["title"] == "Test Sample"
        assert result[0]["tags"] == ["test"]
        assert result[0]["difficulty"] == "beginner"

    def test_empty_dir(self, tmp_path):
        data_dir = str(tmp_path / "empty")
        os.makedirs(data_dir)
        result = loader.discover_examples(data_dirs=[data_dir])
        assert result == []

    def test_invalid_yaml(self, tmp_path):
        data_dir = str(tmp_path / "data")
        catalog_dir = os.path.join(data_dir, "kale", "catalog")
        os.makedirs(catalog_dir)
        with open(os.path.join(catalog_dir, "bad.yaml"), "w") as f:
            f.write(": invalid: yaml: {{{}}")
        result = loader.discover_examples(data_dirs=[data_dir])
        assert result == []

    def test_missing_required_fields(self, tmp_path):
        data_dir = str(tmp_path / "data")
        items = [{"id": "incomplete"}]
        _make_catalog_structure(data_dir, items)
        result = loader.discover_examples(data_dirs=[data_dir])
        assert result == []

    def test_missing_sample_dir(self, tmp_path):
        data_dir = str(tmp_path / "data")
        catalog_dir = os.path.join(data_dir, "kale", "catalog")
        os.makedirs(catalog_dir)
        item = _valid_item(sample_id="missing-dir")
        doc = {
            "apiVersion": "kale.kubeflow.org/v2alpha1",
            "kind": "ExamplesCatalog",
            "items": [item],
        }
        with open(os.path.join(catalog_dir, "catalog.yaml"), "w") as f:
            yaml.dump(doc, f)
        result = loader.discover_examples(data_dirs=[data_dir])
        assert result == []

    def test_merge_across_files(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("sample-a")], filename="a.yaml")
        _make_catalog_structure(data_dir, [_valid_item("sample-b")], filename="b.yaml")
        result = loader.discover_examples(data_dirs=[data_dir])
        ids = {e["id"] for e in result}
        assert ids == {"sample-a", "sample-b"}

    def test_merge_across_data_dirs(self, tmp_path):
        dir1 = str(tmp_path / "high")
        dir2 = str(tmp_path / "low")
        _make_catalog_structure(dir1, [_valid_item("from-high")])
        _make_catalog_structure(dir2, [_valid_item("from-low")])
        result = loader.discover_examples(data_dirs=[dir1, dir2])
        ids = {e["id"] for e in result}
        assert ids == {"from-high", "from-low"}

    def test_priority_first_wins(self, tmp_path):
        dir1 = str(tmp_path / "high")
        dir2 = str(tmp_path / "low")
        _make_catalog_structure(dir1, [_valid_item("shared", title="High Priority")])
        _make_catalog_structure(dir2, [_valid_item("shared", title="Low Priority")])
        result = loader.discover_examples(data_dirs=[dir1, dir2])
        assert len(result) == 1
        assert result[0]["title"] == "High Priority"

    def test_wrong_kind_skipped(self, tmp_path, caplog):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item()], kind="OtherKind")
        with caplog.at_level("WARNING", logger="kale.examples_catalog.loader"):
            result = loader.discover_examples(data_dirs=[data_dir])
        assert result == []
        # Wrong kind is silently skipped -- no warning should be logged
        assert not any("OtherKind" in r.message for r in caplog.records)

    def test_unknown_api_version_skipped(self, tmp_path, caplog):
        data_dir = str(tmp_path / "data")
        catalog_dir = os.path.join(data_dir, "kale", "catalog")
        samples_dir = os.path.join(data_dir, "kale", "samples", "test-sample")
        os.makedirs(catalog_dir)
        os.makedirs(samples_dir)
        doc = {
            "apiVersion": "unknown/v1",
            "kind": "ExamplesCatalog",
            "items": [_valid_item()],
        }
        with open(os.path.join(catalog_dir, "catalog.yaml"), "w") as f:
            yaml.dump(doc, f)
        # The kale logger has propagate=False (set by logutils.get_or_create_logger),
        # so caplog's root-level handler never sees records. Temporarily enable
        # propagation so caplog can capture the warning.
        kale_logger = logging.getLogger("kale")
        orig_propagate = kale_logger.propagate
        kale_logger.propagate = True
        try:
            with caplog.at_level(logging.WARNING, logger="kale.examples_catalog.loader"):
                result = loader.discover_examples(data_dirs=[data_dir])
        finally:
            kale_logger.propagate = orig_propagate
        assert result == []
        assert any("unknown apiVersion" in r.message for r in caplog.records)

    def test_yml_extension_discovered(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("yml-sample")], filename="catalog.yml")
        result = loader.discover_examples(data_dirs=[data_dir])
        assert len(result) == 1
        assert result[0]["id"] == "yml-sample"

    def test_invalid_difficulty(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item(difficulty="expert")])
        result = loader.discover_examples(data_dirs=[data_dir])
        assert result == []

    def test_defaults_tags_empty_difficulty_none(self, tmp_path):
        data_dir = str(tmp_path / "data")
        item = {
            "id": "minimal-sample",
            "title": "Minimal",
            "description": "No tags or difficulty",
            "assets": {"source": "minimal-sample"},
            "entrypoint": {"notebook": "main.ipynb"},
        }
        _make_catalog_structure(data_dir, [item])
        result = loader.discover_examples(data_dirs=[data_dir])
        assert len(result) == 1
        assert result[0]["tags"] == []
        assert result[0]["difficulty"] is None

    def test_same_dir_duplicate_last_wins(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("dup", title="From A")], filename="a.yaml")
        _make_catalog_structure(data_dir, [_valid_item("dup", title="From B")], filename="b.yaml")
        result = loader.discover_examples(data_dirs=[data_dir])
        assert len(result) == 1
        # b.yaml comes after a.yaml alphabetically, so "From B" should win
        assert result[0]["title"] == "From B"

    def test_valid_with_invalid(self, tmp_path):
        data_dir = str(tmp_path / "data")
        items = [
            _valid_item("good-sample"),
            {"id": "bad-sample"},  # missing fields
        ]
        _make_catalog_structure(data_dir, items)
        result = loader.discover_examples(data_dirs=[data_dir])
        assert len(result) == 1
        assert result[0]["id"] == "good-sample"

    def test_non_dict_item_in_catalog_skipped(self, tmp_path):
        """Non-dict items in the catalog items list are skipped."""
        data_dir = str(tmp_path / "data")
        catalog_dir = os.path.join(data_dir, "kale", "catalog")
        samples_dir = os.path.join(data_dir, "kale", "samples", "valid-sample")
        os.makedirs(catalog_dir)
        os.makedirs(samples_dir)
        with open(os.path.join(samples_dir, "main.ipynb"), "w") as f:
            f.write("{}")

        doc = {
            "apiVersion": "kale.kubeflow.org/v2alpha1",
            "kind": "ExamplesCatalog",
            "items": [
                "just-a-bare-string",
                _valid_item("valid-sample"),
            ],
        }
        with open(os.path.join(catalog_dir, "catalog.yaml"), "w") as f:
            yaml.dump(doc, f)

        result = loader.discover_examples(data_dirs=[data_dir])
        assert len(result) == 1
        assert result[0]["id"] == "valid-sample"


class TestValidateEntry:
    def test_path_traversal_id(self, tmp_path):
        data_dir = str(tmp_path)
        valid, reason = loader.validate_entry(_valid_item(sample_id="../escape"), data_dir)
        assert not valid
        assert "path separators" in reason or ".." in reason

    def test_path_traversal_id_slash(self, tmp_path):
        data_dir = str(tmp_path)
        valid, reason = loader.validate_entry(_valid_item(sample_id="a/b"), data_dir)
        assert not valid

    def test_missing_assets_source(self, tmp_path):
        data_dir = str(tmp_path)
        item = {
            "id": "no-assets",
            "title": "No Assets",
            "description": "Missing assets dict",
        }
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "assets.source" in reason

    def test_missing_entrypoint_notebook(self, tmp_path):
        data_dir = str(tmp_path)
        samples_dir = os.path.join(data_dir, "kale", "samples", "src")
        os.makedirs(samples_dir, exist_ok=True)
        item = {
            "id": "no-entrypoint",
            "title": "No Entrypoint",
            "description": "Missing entrypoint dict",
            "assets": {"source": "src"},
        }
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "entrypoint.notebook" in reason

    def test_non_string_required_field_rejected(self, tmp_path):
        data_dir = str(tmp_path)
        item = _valid_item()
        item["id"] = 123  # non-string truthy value
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "missing required field" in reason

    def test_path_traversal_source(self, tmp_path):
        data_dir = str(tmp_path)
        item = _valid_item()
        item["assets"]["source"] = "../etc"
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "path traversal" in reason

    def test_path_traversal_id_backslash(self, tmp_path):
        data_dir = str(tmp_path)
        valid, reason = loader.validate_entry(_valid_item(sample_id="foo\\bar"), data_dir)
        assert not valid
        assert "path separators" in reason or "\\" in reason

    def test_absolute_path_source(self, tmp_path):
        data_dir = str(tmp_path)
        item = _valid_item()
        item["assets"]["source"] = "/etc/passwd"
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "path traversal" in reason

    def test_absolute_path_notebook(self, tmp_path):
        data_dir = str(tmp_path)
        item = _valid_item()
        item["entrypoint"]["notebook"] = "/etc/passwd"
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "path traversal" in reason

    def test_path_traversal_notebook(self, tmp_path):
        data_dir = str(tmp_path)
        item = _valid_item()
        item["entrypoint"]["notebook"] = "../../etc/passwd"
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "path traversal" in reason

    def test_non_list_tags_rejected(self, tmp_path):
        """A non-list tags value is rejected with an appropriate message."""
        data_dir = str(tmp_path)
        samples_dir = os.path.join(data_dir, "kale", "samples", "test-sample")
        os.makedirs(samples_dir, exist_ok=True)
        with open(os.path.join(samples_dir, "main.ipynb"), "w") as f:
            f.write("{}")

        item = _valid_item()
        item["tags"] = "single-tag"  # string instead of list
        valid, reason = loader.validate_entry(item, data_dir)
        assert not valid
        assert "tags must be a list" in reason


class TestResolveSampleDir:
    def test_resolve_found(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        result = loader.resolve_sample_dir("my-sample", data_dirs=[data_dir])
        assert result is not None
        source_dir, entry = result
        assert entry["id"] == "my-sample"
        assert os.path.isdir(source_dir)

    def test_resolve_not_found(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("other")])
        result = loader.resolve_sample_dir("nonexistent", data_dirs=[data_dir])
        assert result is None


# ---------------------------------------------------------------------------
# Materializer tests
# ---------------------------------------------------------------------------


class TestCheckExisting:
    def test_exists_true(self, tmp_path):
        dest = tmp_path / "kale-samples" / "my-sample"
        dest.mkdir(parents=True)
        assert materializer.check_existing("my-sample", server_root=str(tmp_path))

    def test_exists_false(self, tmp_path):
        assert not materializer.check_existing("my-sample", server_root=str(tmp_path))


class TestMaterialize:
    def test_copies_files(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        result = materializer.materialize(
            "my-sample", server_root=server_root, data_dirs=[data_dir]
        )
        assert "my-sample" in result
        assert "main.ipynb" in result

        dest = os.path.join(server_root, "kale-samples", "my-sample")
        assert os.path.isdir(dest)
        assert os.path.isfile(os.path.join(dest, "main.ipynb"))

    def test_provenance(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        materializer.materialize("my-sample", server_root=server_root, data_dirs=[data_dir])

        provenance_path = os.path.join(
            server_root, "kale-samples", "my-sample", ".kale-sample.json"
        )
        assert os.path.isfile(provenance_path)
        with open(provenance_path) as f:
            prov = json.load(f)
        assert prov["sample_id"] == "my-sample"
        # source_path should point to the actual sample directory
        expected_source = os.path.join(data_dir, "kale", "samples", "my-sample")
        assert prov["source_path"] == expected_source
        # timestamp should be a valid ISO 8601 string
        from datetime import datetime

        datetime.fromisoformat(prov["timestamp"])

    def test_relative_path(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        result = materializer.materialize(
            "my-sample", server_root=server_root, data_dirs=[data_dir]
        )
        assert result == os.path.join("kale-samples", "my-sample", "main.ipynb")

    def test_not_found(self, tmp_path):
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)
        with pytest.raises(ValueError, match="not found"):
            materializer.materialize("nonexistent", data_dirs=[data_dir])

    def test_idempotent(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        materializer.materialize("my-sample", server_root=server_root, data_dirs=[data_dir])

        provenance_path = os.path.join(
            server_root, "kale-samples", "my-sample", ".kale-sample.json"
        )
        with open(provenance_path) as f:
            first_prov = json.load(f)
        first_ts = first_prov["timestamp"]

        marker = os.path.join(server_root, "kale-samples", "my-sample", "marker.txt")
        with open(marker, "w") as f:
            f.write("user data")

        import time

        time.sleep(0.01)
        materializer.materialize("my-sample", server_root=server_root, data_dirs=[data_dir])
        assert os.path.isfile(marker), "existing files should not be overwritten"

        with open(provenance_path) as f:
            second_prov = json.load(f)
        second_ts = second_prov["timestamp"]
        assert second_ts > first_ts, "provenance timestamp should be updated"

    def test_with_server_root(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "srv")
        os.makedirs(server_root)

        materializer.materialize("my-sample", server_root=server_root, data_dirs=[data_dir])
        assert os.path.isdir(os.path.join(server_root, "kale-samples", "my-sample"))

    def test_custom_dir_env(self, tmp_path, monkeypatch):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)
        monkeypatch.setenv("KALE_MATERIALIZATION_DIR", "custom-samples")

        result = materializer.materialize(
            "my-sample", server_root=server_root, data_dirs=[data_dir]
        )
        assert "custom-samples" in result
        assert os.path.isdir(os.path.join(server_root, "custom-samples", "my-sample"))

    def test_default_dir(self, tmp_path, monkeypatch):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)
        monkeypatch.delenv("KALE_MATERIALIZATION_DIR", raising=False)

        result = materializer.materialize(
            "my-sample", server_root=server_root, data_dirs=[data_dir]
        )
        assert "kale-samples" in result

    def test_materialize_preserves_subdirectories(self, tmp_path):
        """Nested subdirectories in sample source are preserved after materialization."""
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("nested-sample")])

        # Create nested subdirectory structure in the sample source
        sample_src = os.path.join(data_dir, "kale", "samples", "nested-sample")
        nested_dir = os.path.join(sample_src, "data", "train")
        os.makedirs(nested_dir)
        with open(os.path.join(nested_dir, "input.csv"), "w") as f:
            f.write("col1,col2\n1,2\n")

        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        materializer.materialize("nested-sample", server_root=server_root, data_dirs=[data_dir])

        dest = os.path.join(server_root, "kale-samples", "nested-sample")
        assert os.path.isdir(os.path.join(dest, "data", "train"))
        assert os.path.isfile(os.path.join(dest, "data", "train", "input.csv"))
        with open(os.path.join(dest, "data", "train", "input.csv")) as f:
            assert f.read() == "col1,col2\n1,2\n"


class TestRecreate:
    def test_replaces_existing(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        materializer.materialize("my-sample", server_root=server_root, data_dirs=[data_dir])
        marker = os.path.join(server_root, "kale-samples", "my-sample", "marker.txt")
        with open(marker, "w") as f:
            f.write("old data")

        materializer.recreate("my-sample", server_root=server_root, data_dirs=[data_dir])
        assert not os.path.isfile(marker), "marker should be gone after recreate"
        assert os.path.isdir(os.path.join(server_root, "kale-samples", "my-sample"))

    def test_recreate_from_scratch(self, tmp_path):
        """Recreate works when no prior materialization exists."""
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("fresh-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        # Ensure no prior materialization exists
        dest = os.path.join(server_root, "kale-samples", "fresh-sample")
        assert not os.path.exists(dest)

        result = materializer.recreate(
            "fresh-sample", server_root=server_root, data_dirs=[data_dir]
        )

        # Verify materialization happened correctly
        assert os.path.isdir(dest)
        assert os.path.isfile(os.path.join(dest, "main.ipynb"))
        assert "fresh-sample" in result
        assert "main.ipynb" in result

        # Verify provenance written
        provenance_path = os.path.join(dest, ".kale-sample.json")
        assert os.path.isfile(provenance_path)
        with open(provenance_path) as f:
            prov = json.load(f)
        assert prov["sample_id"] == "fresh-sample"


class TestPathTraversalProtection:
    """Test that materializer functions reject path traversal sample IDs."""

    def test_materialize_rejects_traversal(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            materializer.materialize("../escape", server_root=str(tmp_path))

    def test_recreate_rejects_traversal(self, tmp_path):
        with pytest.raises(ValueError, match="path separators"):
            materializer.recreate("../escape", server_root=str(tmp_path))

    def test_check_existing_rejects_traversal(self, tmp_path):
        with pytest.raises(ValueError, match="path separators"):
            materializer.check_existing("../escape", server_root=str(tmp_path))

    def test_materialize_rejects_slash(self, tmp_path):
        with pytest.raises(ValueError):
            materializer.materialize("a/b", server_root=str(tmp_path))

    def test_check_existing_rejects_slash(self, tmp_path):
        with pytest.raises(ValueError, match="path separators"):
            materializer.check_existing("a/b", server_root=str(tmp_path))


# ---------------------------------------------------------------------------
# RPC endpoint tests
# ---------------------------------------------------------------------------


class TestRPCEndpoints:
    def test_list_examples(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("sample-a"), _valid_item("sample-b")])
        with patch("jupyter_core.paths.jupyter_path", return_value=[data_dir]):
            result = nb.list_examples(None)
        assert len(result) == 2
        expected_keys = {"id", "title", "description", "tags", "difficulty", "assets", "entrypoint"}
        for entry in result:
            assert set(entry.keys()) == expected_keys, (
                f"entry keys {set(entry.keys())} != {expected_keys}"
            )
            # No internal underscore-prefixed keys should be present
            assert not any(k.startswith("_") for k in entry)

    def test_check_sample_exists_true(self, tmp_path):
        dest = tmp_path / "kale-samples" / "my-sample"
        dest.mkdir(parents=True)
        result = nb.check_sample_exists(None, "my-sample", server_root=str(tmp_path))
        assert result == {"exists": True}

    def test_check_sample_exists_false(self, tmp_path):
        result = nb.check_sample_exists(None, "nonexistent", server_root=str(tmp_path))
        assert result == {"exists": False}

    def test_load_example_success(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        with patch("jupyter_core.paths.jupyter_path", return_value=[data_dir]):
            result = nb.load_example(None, "my-sample", server_root=server_root)
        assert "notebook_path" in result
        assert "my-sample" in result["notebook_path"]

    def test_load_example_recreate(self, tmp_path):
        data_dir = str(tmp_path / "data")
        _make_catalog_structure(data_dir, [_valid_item("my-sample")])
        server_root = str(tmp_path / "workspace")
        os.makedirs(server_root)

        # First materialize
        with patch("jupyter_core.paths.jupyter_path", return_value=[data_dir]):
            nb.load_example(None, "my-sample", server_root=server_root)

        # Add a marker file
        marker = os.path.join(server_root, "kale-samples", "my-sample", "marker.txt")
        with open(marker, "w") as f:
            f.write("old data")

        # Recreate should remove marker
        with patch("jupyter_core.paths.jupyter_path", return_value=[data_dir]):
            result = nb.load_example(None, "my-sample", server_root=server_root, recreate=True)
        assert "notebook_path" in result
        assert not os.path.isfile(marker), "marker should be gone after recreate"

    def test_load_example_not_found(self, tmp_path):
        class FakeRequest:
            trans_id = "test-123"

            class log:
                @staticmethod
                def exception(*args, **kwargs):
                    pass

        with (
            patch("jupyter_core.paths.jupyter_path", return_value=[str(tmp_path)]),
            pytest.raises(RPCNotFoundError),
        ):
            nb.load_example(FakeRequest(), "nonexistent", server_root=str(tmp_path))
