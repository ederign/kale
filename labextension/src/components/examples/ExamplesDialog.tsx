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
  Box,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { Kernel } from '@jupyterlab/services';
import { IDocumentManager } from '@jupyterlab/docmanager';
import { PageConfig } from '@jupyterlab/coreutils';
import { executeRpc } from '../../lib/RPCUtils';
import { IExampleEntry } from './types';
import { ExampleCard } from './ExampleCard';
import { ConflictDialog } from './ConflictDialog';

export interface IExamplesDialogProps {
  open: boolean;
  onClose: () => void;
  kernel: Kernel.IKernelConnection;
  docManager: IDocumentManager;
}

export const ExamplesDialog: React.FC<IExamplesDialogProps> = ({
  open,
  onClose,
  kernel,
  docManager,
}) => {
  const [entries, setEntries] = React.useState<IExampleEntry[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedTag, setSelectedTag] = React.useState<string | null>(null);
  const [loadingId, setLoadingId] = React.useState<string | null>(null);

  // Conflict dialog state
  const [conflictOpen, setConflictOpen] = React.useState(false);
  const [conflictExample, setConflictExample] =
    React.useState<IExampleEntry | null>(null);

  // Reset state and fetch catalog on dialog open
  React.useEffect(() => {
    if (!open) {
      return;
    }
    setSelectedTag(null);
    setError(null);
    setLoadingId(null);
    setConflictOpen(false);
    setConflictExample(null);
    setLoading(true);

    executeRpc(kernel, 'nb.list_examples')
      .then((result: IExampleEntry[]) => {
        setEntries(result);
        setLoading(false);
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : 'Failed to load examples catalog.';
        setError(message);
        setLoading(false);
      });
  }, [open, kernel]);

  const allTags = React.useMemo(() => {
    const tagSet = new Set<string>();
    entries.forEach(e => e.tags.forEach(t => tagSet.add(t)));
    return Array.from(tagSet);
  }, [entries]);

  const filteredEntries = selectedTag
    ? entries.filter(e => e.tags.includes(selectedTag))
    : entries;

  const serverRoot = PageConfig.getOption('serverRoot');

  const openNotebook = (notebookPath: string) => {
    docManager.openOrReveal(notebookPath);
    onClose();
    setLoadingId(null);
  };

  const handleImport = async (example: IExampleEntry) => {
    if (loadingId) {
      return;
    }
    setLoadingId(example.id);
    setError(null);

    try {
      const existsResult = await executeRpc(kernel, 'nb.check_sample_exists', {
        sample_id: example.id,
        server_root: serverRoot,
      });

      if (existsResult.exists) {
        setConflictExample(example);
        setConflictOpen(true);
        return;
      }

      const loadResult = await executeRpc(kernel, 'nb.load_example', {
        sample_id: example.id,
        server_root: serverRoot,
      });
      openNotebook(loadResult.notebook_path);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to import example.';
      setError(message);
      setLoadingId(null);
    }
  };

  const handleConflictCancel = () => {
    setConflictOpen(false);
    setConflictExample(null);
    setLoadingId(null);
  };

  const handleConflictOpenExisting = async () => {
    if (!conflictExample) {
      return;
    }
    setConflictOpen(false);
    try {
      const result = await executeRpc(kernel, 'nb.load_example', {
        sample_id: conflictExample.id,
        server_root: serverRoot,
      });
      openNotebook(result.notebook_path);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to open existing example.';
      setError(message);
      setLoadingId(null);
    }
  };

  const handleConflictRecreate = async () => {
    if (!conflictExample) {
      return;
    }
    setConflictOpen(false);
    try {
      const result = await executeRpc(kernel, 'nb.load_example', {
        sample_id: conflictExample.id,
        server_root: serverRoot,
        recreate: true,
      });
      openNotebook(result.notebook_path);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to recreate example.';
      setError(message);
      setLoadingId(null);
    }
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        sx={{ '& .MuiDialog-paper': { height: '40vh' } }}
      >
        <DialogTitle
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          Kale Examples
          <IconButton aria-label="close" onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {loading && (
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
              }}
            >
              <CircularProgress />
            </Box>
          )}

          {error && !loading && (
            <Typography color="error" sx={{ mb: 2 }}>
              {error}
            </Typography>
          )}

          {!loading && !error && entries.length === 0 && (
            <Typography
              sx={{ textAlign: 'center', mt: 4 }}
              color="textSecondary"
            >
              No sample notebooks found.
            </Typography>
          )}

          {!loading && !error && entries.length > 0 && (
            <>
              <Box className="kale-examples-filter-row">
                <Chip
                  label="All"
                  onClick={() => setSelectedTag(null)}
                  color={selectedTag === null ? 'primary' : 'default'}
                  variant={selectedTag === null ? 'filled' : 'outlined'}
                  size="small"
                />
                {allTags.map(tag => (
                  <Chip
                    key={tag}
                    label={tag}
                    onClick={() => setSelectedTag(tag)}
                    color={selectedTag === tag ? 'primary' : 'default'}
                    variant={selectedTag === tag ? 'filled' : 'outlined'}
                    size="small"
                  />
                ))}
              </Box>
              <Grid container spacing={2}>
                {filteredEntries.map(entry => (
                  <Grid key={entry.id} size={{ xs: 12, sm: 6 }}>
                    <ExampleCard
                      example={entry}
                      onImport={handleImport}
                      loading={loadingId === entry.id}
                    />
                  </Grid>
                ))}
              </Grid>
            </>
          )}
        </DialogContent>
      </Dialog>

      <ConflictDialog
        open={conflictOpen}
        sampleTitle={conflictExample?.title ?? ''}
        onCancel={handleConflictCancel}
        onOpenExisting={handleConflictOpenExisting}
        onRecreate={handleConflictRecreate}
      />
    </>
  );
};
