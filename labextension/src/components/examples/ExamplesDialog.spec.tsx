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
  render,
  screen,
  fireEvent,
  waitFor,
  act,
  within,
} from '@testing-library/react';
import { ExamplesDialog } from './ExamplesDialog';
import { IExampleEntry } from './types';
import { executeRpc } from '../../lib/RPCUtils';

// Mock executeRpc
jest.mock('../../lib/RPCUtils', () => ({
  executeRpc: jest.fn(),
}));

// Mock PageConfig
jest.mock('@jupyterlab/coreutils', () => ({
  PageConfig: {
    getOption: jest.fn().mockReturnValue('/home/jovyan'),
  },
}));

const mockedExecuteRpc = executeRpc as jest.Mock;

const mockKernel = {} as any;
const mockDocManager = {
  openOrReveal: jest.fn(),
} as any;

const sampleEntries: IExampleEntry[] = [
  {
    id: 'intro-ml',
    title: 'Intro to ML',
    description: 'Introduction to machine learning.',
    tags: ['ml', 'tutorial'],
    difficulty: 'beginner',
  },
  {
    id: 'advanced-nlp',
    title: 'Advanced NLP',
    description: 'Advanced natural language processing techniques.',
    tags: ['nlp', 'advanced-topic'],
    difficulty: 'advanced',
  },
  {
    id: 'data-viz',
    title: 'Data Visualization',
    description: 'Learn data visualization basics.',
    tags: ['tutorial', 'visualization'],
    difficulty: 'intermediate',
  },
];

describe('ExamplesDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading spinner while fetching catalog', async () => {
    let resolveRpc: (value: IExampleEntry[]) => void;
    mockedExecuteRpc.mockReturnValue(
      new Promise<IExampleEntry[]>(resolve => {
        resolveRpc = resolve;
      }),
    );

    render(
      <ExamplesDialog
        open={true}
        onClose={jest.fn()}
        kernel={mockKernel}
        docManager={mockDocManager}
      />,
    );

    expect(screen.getByRole('progressbar')).toBeTruthy();

    await act(async () => {
      resolveRpc!(sampleEntries);
    });
  });

  it('renders cards after catalog loads', async () => {
    mockedExecuteRpc.mockResolvedValue(sampleEntries);

    render(
      <ExamplesDialog
        open={true}
        onClose={jest.fn()}
        kernel={mockKernel}
        docManager={mockDocManager}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Intro to ML')).toBeTruthy();
    });

    expect(screen.getByText('Advanced NLP')).toBeTruthy();
    expect(screen.getByText('Data Visualization')).toBeTruthy();
  });

  it('shows empty state when catalog is empty', async () => {
    mockedExecuteRpc.mockResolvedValue([]);

    render(
      <ExamplesDialog
        open={true}
        onClose={jest.fn()}
        kernel={mockKernel}
        docManager={mockDocManager}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('No sample notebooks found.')).toBeTruthy();
    });
  });

  it('shows error message on RPC failure', async () => {
    mockedExecuteRpc.mockRejectedValue(new Error('Network error'));

    render(
      <ExamplesDialog
        open={true}
        onClose={jest.fn()}
        kernel={mockKernel}
        docManager={mockDocManager}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeTruthy();
    });
  });

  it('filters entries by tag when a tag chip is clicked', async () => {
    mockedExecuteRpc.mockResolvedValue(sampleEntries);

    render(
      <ExamplesDialog
        open={true}
        onClose={jest.fn()}
        kernel={mockKernel}
        docManager={mockDocManager}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Intro to ML')).toBeTruthy();
    });

    // Click the "nlp" tag filter chip (scoped to filter row to avoid card tag chips)
    const filterRow = document.querySelector('.kale-examples-filter-row')!;
    fireEvent.click(within(filterRow as HTMLElement).getByText('nlp'));

    // Only the NLP entry should remain visible
    expect(screen.getByText('Advanced NLP')).toBeTruthy();
    expect(screen.queryByText('Intro to ML')).toBeNull();
    expect(screen.queryByText('Data Visualization')).toBeNull();
  });

  it('shows all entries when "All" chip is clicked after filtering', async () => {
    mockedExecuteRpc.mockResolvedValue(sampleEntries);

    render(
      <ExamplesDialog
        open={true}
        onClose={jest.fn()}
        kernel={mockKernel}
        docManager={mockDocManager}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Intro to ML')).toBeTruthy();
    });

    // Filter by nlp (scoped to filter row)
    const filterRow = document.querySelector('.kale-examples-filter-row')!;
    fireEvent.click(within(filterRow as HTMLElement).getByText('nlp'));
    expect(screen.queryByText('Intro to ML')).toBeNull();

    // Click All to reset
    fireEvent.click(within(filterRow as HTMLElement).getByText('All'));
    expect(screen.getByText('Intro to ML')).toBeTruthy();
    expect(screen.getByText('Advanced NLP')).toBeTruthy();
  });

  it('calls onClose when close button is clicked', async () => {
    mockedExecuteRpc.mockResolvedValue(sampleEntries);
    const onClose = jest.fn();

    render(
      <ExamplesDialog
        open={true}
        onClose={onClose}
        kernel={mockKernel}
        docManager={mockDocManager}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Kale Examples')).toBeTruthy();
    });

    fireEvent.click(screen.getByLabelText('close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
