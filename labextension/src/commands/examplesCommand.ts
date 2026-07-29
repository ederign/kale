// Copyright 2026 The Kubeflow Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import * as React from 'react';
import { JupyterFrontEnd } from '@jupyterlab/application';
import { ReactWidget } from '@jupyterlab/apputils';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { ILauncher } from '@jupyterlab/launcher';
import { Kernel } from '@jupyterlab/services';
import { LabIcon } from '@jupyterlab/ui-components';
import { Widget } from '@lumino/widgets';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '../Theme';
import { ExamplesDialogContainer } from '../components/examples/ExamplesDialogContainer';

export function registerExamplesCommand(
  app: JupyterFrontEnd,
  kernel: Kernel.IKernelConnection,
  docManager: IDocumentManager,
  kaleIcon: LabIcon,
  launcher: ILauncher | null,
): void {
  let openExamplesDialog: (() => void) | null = null;

  app.commands.addCommand('kale:open-examples', {
    label: 'Kale Examples',
    icon: kaleIcon,
    execute: () => {
      if (openExamplesDialog) {
        openExamplesDialog();
      }
    },
  });

  if (launcher) {
    launcher.add({
      command: 'kale:open-examples',
      category: 'Other',
      rank: 100,
    });
  }

  const dialogWidget = ReactWidget.create(
    React.createElement(
      ThemeProvider,
      { theme },
      React.createElement(ExamplesDialogContainer, {
        kernel,
        docManager,
        onRegisterOpen: (openFn: () => void) => {
          openExamplesDialog = openFn;
        },
      }),
    ),
  );
  dialogWidget.id = 'kale-examples-dialog';
  Widget.attach(dialogWidget, document.body);
}
