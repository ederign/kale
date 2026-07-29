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
  Card,
  CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  Typography,
} from '@mui/material';
import { IExampleEntry } from './types';

export interface IExampleCardProps {
  example: IExampleEntry;
  onImport: (example: IExampleEntry) => void;
  loading: boolean;
}

export const getDifficultyColor = (difficulty: string | null): string => {
  switch (difficulty) {
    case 'beginner':
      return 'var(--jp-success-color1)';
    case 'intermediate':
      return 'var(--jp-warn-color1)';
    case 'advanced':
      return 'var(--jp-error-color1)';
    default:
      return 'var(--jp-border-color2)';
  }
};

export const ExampleCard: React.FC<IExampleCardProps> = ({
  example,
  onImport,
  loading,
}) => {
  return (
    <Card sx={{ position: 'relative' }}>
      <CardActionArea disabled={loading} onClick={() => onImport(example)}>
        <CardContent>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {example.title}
          </Typography>
          <Typography variant="body2" className="kale-example-card-description">
            {example.description}
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
            {example.difficulty && (
              <Chip
                label={example.difficulty}
                size="small"
                sx={{
                  backgroundColor: getDifficultyColor(example.difficulty),
                  color: '#fff',
                }}
              />
            )}
            {example.tags.map(tag => (
              <Chip
                key={tag}
                label={tag}
                variant="outlined"
                size="small"
                sx={{ borderColor: 'var(--jp-border-color2)' }}
              />
            ))}
          </Box>
        </CardContent>
      </CardActionArea>
      {loading && (
        <Box className="kale-example-card-loading-overlay">
          <CircularProgress size={32} />
        </Box>
      )}
    </Card>
  );
};
