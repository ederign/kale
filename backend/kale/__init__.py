# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2019–2025 The Kale Contributors.

# --- Detect package version at runtime ---
# Use:
# from kale import __version__ as KALE_VERSION
# use KALE_VERSION wherever a display/log/version check is needed
import os

# Allow overriding version via environment variable for local KFP testing.
# SETUPTOOLS_SCM_PRETEND_VERSION is the standard setuptools_scm override.
# This only affects local development (e.g., make jupyter-kfp). In production,
# the env var is not set, so we fall through to importlib.metadata.version().
_version_override = os.environ.get("SETUPTOOLS_SCM_PRETEND_VERSION")
if _version_override:
    __version__ = _version_override
else:
    try:
        from importlib.metadata import PackageNotFoundError, version as _pkg_version
    except Exception:  # Py<3.8 fallback if needed
        from importlib_metadata import (  # type: ignore
            PackageNotFoundError,
            version as _pkg_version,
        )

    try:
        __version__ = _pkg_version("kubeflow-kale")
    except PackageNotFoundError:
        # this might happen when a developer tried to test Kale locally from source
        # without installing it first.
        __version__ = "0+unknown"

# -----------------------------------------

from typing import Any, NamedTuple


class PipelineParam(NamedTuple):
    """A pipeline parameter."""

    param_type: str
    param_value: Any


class Artifact(NamedTuple):
    """A Step artifact."""

    name: str
    type: str
    is_input: bool = False


from kale.common import logutils

from .compiler import Compiler
from .pipeline import Pipeline, PipelineConfig, VolumeConfig
from .processors import NotebookConfig, NotebookProcessor, PythonProcessor
from .step import Step, StepConfig

__all__ = [
    "PipelineParam",
    "Artifact",
    "NotebookConfig",
    "NotebookProcessor",
    "PythonProcessor",
    "Step",
    "StepConfig",
    "Pipeline",
    "PipelineConfig",
    "VolumeConfig",
    "Compiler",
    "marshal",
]

logutils.get_or_create_logger(module=__name__, name="kale")
del logutils
