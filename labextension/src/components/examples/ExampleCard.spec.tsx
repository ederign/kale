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
import { ExampleCard, getDifficultyColor } from './ExampleCard';
import { IExampleEntry } from './types';

const sampleEntry: IExampleEntry = {
  id: 'sample-1',
  title: 'Test Notebook',
  description: 'A test notebook for unit testing purposes.',
  tags: ['ml', 'tutorial'],
  difficulty: 'beginner',
};

describe('getDifficultyColor', () => {
  it('returns success color for beginner', () => {
    expect(getDifficultyColor('beginner')).toBe('var(--jp-success-color1)');
  });

  it('returns warn color for intermediate', () => {
    expect(getDifficultyColor('intermediate')).toBe('var(--jp-warn-color1)');
  });

  it('returns error color for advanced', () => {
    expect(getDifficultyColor('advanced')).toBe('var(--jp-error-color1)');
  });

  it('returns border color for null difficulty', () => {
    expect(getDifficultyColor(null)).toBe('var(--jp-border-color2)');
  });

  it('returns border color for unknown difficulty', () => {
    expect(getDifficultyColor('unknown')).toBe('var(--jp-border-color2)');
  });
});

describe('ExampleCard', () => {
  it('renders title and description', () => {
    const onImport = jest.fn();
    render(
      <ExampleCard example={sampleEntry} onImport={onImport} loading={false} />,
    );
    expect(screen.getByText('Test Notebook')).toBeTruthy();
    expect(
      screen.getByText('A test notebook for unit testing purposes.'),
    ).toBeTruthy();
  });

  it('renders difficulty chip when difficulty is present', () => {
    const onImport = jest.fn();
    render(
      <ExampleCard example={sampleEntry} onImport={onImport} loading={false} />,
    );
    expect(screen.getByText('beginner')).toBeTruthy();
  });

  it('does not render difficulty chip when difficulty is null', () => {
    const onImport = jest.fn();
    const entryNoDifficulty: IExampleEntry = {
      ...sampleEntry,
      difficulty: null,
    };
    render(
      <ExampleCard
        example={entryNoDifficulty}
        onImport={onImport}
        loading={false}
      />,
    );
    expect(screen.queryByText('beginner')).toBeNull();
  });

  it('renders tag chips', () => {
    const onImport = jest.fn();
    render(
      <ExampleCard example={sampleEntry} onImport={onImport} loading={false} />,
    );
    expect(screen.getByText('ml')).toBeTruthy();
    expect(screen.getByText('tutorial')).toBeTruthy();
  });

  it('calls onImport when clicked', () => {
    const onImport = jest.fn();
    render(
      <ExampleCard example={sampleEntry} onImport={onImport} loading={false} />,
    );
    fireEvent.click(screen.getByText('Test Notebook'));
    expect(onImport).toHaveBeenCalledWith(sampleEntry);
  });

  it('shows loading overlay when loading is true', () => {
    const onImport = jest.fn();
    const { container } = render(
      <ExampleCard example={sampleEntry} onImport={onImport} loading={true} />,
    );
    expect(
      container.querySelector('.kale-example-card-loading-overlay'),
    ).toBeTruthy();
  });

  it('hides loading overlay when loading is false', () => {
    const onImport = jest.fn();
    const { container } = render(
      <ExampleCard example={sampleEntry} onImport={onImport} loading={false} />,
    );
    expect(
      container.querySelector('.kale-example-card-loading-overlay'),
    ).toBeNull();
  });
});
