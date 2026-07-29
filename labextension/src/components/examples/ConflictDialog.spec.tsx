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
import { render, screen, fireEvent } from '@testing-library/react';
import { ConflictDialog } from './ConflictDialog';

describe('ConflictDialog', () => {
  const defaultProps = {
    open: true,
    sampleTitle: 'My Notebook',
    onCancel: jest.fn(),
    onOpenExisting: jest.fn(),
    onRecreate: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the dialog title', () => {
    render(<ConflictDialog {...defaultProps} />);
    expect(screen.getByText('Sample Already Exists')).toBeTruthy();
  });

  it('renders the sample title in the message', () => {
    render(<ConflictDialog {...defaultProps} />);
    expect(screen.getByText(/My Notebook/)).toBeTruthy();
  });

  it('renders three action buttons', () => {
    render(<ConflictDialog {...defaultProps} />);
    expect(screen.getByText('Cancel')).toBeTruthy();
    expect(screen.getByText('Open Existing')).toBeTruthy();
    expect(screen.getByText('Recreate')).toBeTruthy();
  });

  it('calls onCancel when Cancel is clicked', () => {
    render(<ConflictDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('Cancel'));
    expect(defaultProps.onCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onOpenExisting when Open Existing is clicked', () => {
    render(<ConflictDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('Open Existing'));
    expect(defaultProps.onOpenExisting).toHaveBeenCalledTimes(1);
  });

  it('calls onRecreate when Recreate is clicked', () => {
    render(<ConflictDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('Recreate'));
    expect(defaultProps.onRecreate).toHaveBeenCalledTimes(1);
  });

  it('does not render when open is false', () => {
    render(<ConflictDialog {...defaultProps} open={false} />);
    expect(screen.queryByText('Sample Already Exists')).toBeNull();
  });
});
