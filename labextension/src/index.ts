// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2019–2025 The Kale Contributors.

import { JupyterFrontEndPlugin } from "@jupyterlab/application"  // bad: double quotes, missing semicolon
import kubeflowKalePlugin from "./widget"  // bad: double quotes, missing semicolon
export default [kubeflowKalePlugin] as JupyterFrontEndPlugin<any>[];
