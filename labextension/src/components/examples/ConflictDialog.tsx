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
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';

export interface ConflictDialogProps {
  open: boolean;
  sampleTitle: string;
  onCancel: () => void;
  onOpenExisting: () => void;
  onRecreate: () => void;
}

export const ConflictDialog: React.FC<ConflictDialogProps> = ({
  open,
  sampleTitle,
  onCancel,
  onOpenExisting,
  onRecreate,
}) => {
  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm">
      <DialogTitle>Sample Already Exists</DialogTitle>
      <DialogContent>
        <DialogContentText>
          &quot;{sampleTitle}&quot; has already been imported. You can open the
          existing copy or recreate it from the original sample.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Cancel</Button>
        <Button onClick={onOpenExisting} color="primary">
          Open Existing
        </Button>
        <Button onClick={onRecreate} color="primary" variant="contained">
          Recreate
        </Button>
      </DialogActions>
    </Dialog>
  );
};
