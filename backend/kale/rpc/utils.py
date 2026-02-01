# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2019–2025 The Kale Contributors.

import base64
import json


def serialize(value):
    """Base64 encode an JSON-serializable object."""
    return base64.b64encode(json.dumps(value).encode("utf-8")).decode("utf-8")


def deserialize(value):
    """Decode a Bse64 string into a JSON object."""
    return json.loads(base64.b64decode(value).decode("utf-8"))
