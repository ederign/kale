#!/usr/bin/env bash
# ABOUTME: Serve locally-built wheels for KFP cluster testing.
# ABOUTME: Alternative to Makefile kfp-serve target for users who prefer shell scripts.

set -euo pipefail

WHEEL_DIR="${1:-.kfp-wheels}"
PORT="${2:-8765}"
KFP_DEV_VERSION="${3:-2.0.0a1}"
# Host address for KFP to reach the wheel server (Linux users: override with your host IP)
KFP_HOST_ADDR="${KFP_HOST_ADDR:-host.docker.internal}"

echo "Building backend wheel with version $KFP_DEV_VERSION..."
(cd backend && SETUPTOOLS_SCM_PRETEND_VERSION="$KFP_DEV_VERSION" uv build)

# Create PEP 503 compliant simple index structure
rm -rf "$WHEEL_DIR"
mkdir -p "$WHEEL_DIR/kubeflow-kale"
cp dist/kubeflow_kale-*.whl "$WHEEL_DIR/kubeflow-kale/"

# Generate index files for pip simple API
echo '<!DOCTYPE html><html><body><a href="kubeflow-kale/">kubeflow-kale</a></body></html>' > "$WHEEL_DIR/index.html"
(cd "$WHEEL_DIR/kubeflow-kale" && for f in *.whl; do echo "<a href=\"$f\">$f</a><br>"; done > index.html)

echo ""
echo "Serving wheels on http://0.0.0.0:$PORT"
echo ""
echo "For Kind clusters, set:"
echo "  export KALE_PIP_INDEX_URLS=\"http://$KFP_HOST_ADDR:$PORT\""
echo "  export KALE_PIP_TRUSTED_HOSTS=\"$KFP_HOST_ADDR\""
echo ""
echo "Linux users: set KFP_HOST_ADDR to your host IP before running this script."
echo ""

cd "$WHEEL_DIR" && python3 -m http.server "$PORT"
