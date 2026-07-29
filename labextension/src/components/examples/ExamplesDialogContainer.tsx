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
import { Kernel } from '@jupyterlab/services';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { ExamplesDialog } from './ExamplesDialog';

export interface IExamplesDialogContainerProps {
  kernel: Kernel.IKernelConnection;
  docManager: IDocumentManager;
  onRegisterOpen: (openFn: () => void) => void;
}

export const ExamplesDialogContainer: React.FC<
  IExamplesDialogContainerProps
> = ({ kernel, docManager, onRegisterOpen }) => {
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    onRegisterOpen(() => setOpen(true));
  }, [onRegisterOpen]);

  return (
    <ExamplesDialog
      open={open}
      onClose={() => setOpen(false)}
      kernel={kernel}
      docManager={docManager}
    />
  );
};
