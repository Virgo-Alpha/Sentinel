import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReviewQueue from '../pages/ReviewQueue';
import { apiService } from '../services/api';
import { Article } from '../types';

// Mock the API service
jest.mock('../services/api');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

// Mock the modal components
jest.mock('../components/ArticleDetailModal', () => {
  return function MockArticleDetailModal({ article, onClose, onReview }: any) {
    return (
      <div data-testid="article-detail-modal">
        <h2>{article.title}</h2>
        <button onClick={onClose}>Close</button>
        {onReview && <button onClick={onReview}>Review</button>}
      </div>
    );
  };
});

jest.mock('../components/ReviewDecisionModal', () => {
  return function MockReviewDecisionModal({ article, onClose, onSubmit }: any) {
    return (
      <div data-testid="review-decision-modal">
        <h2>Review: {article.title}</h2>
        <button onClick={() => onSubmit({ article_id: article.article_id, decision: 'approve', reviewer: 'test', timestamp: new Date().toISOString() })}>
          Approve
        </button>
        <button onClick={() => onSubmit({ article_id: article.article_id, decision: 'reject', reason: 'Test rejection', reviewer: 'test', timestamp: new Date().toISOString() })}>
          Reject
        </button>
        <button onClick={onClose}>Cancel</button>
      </div>
    )
  }
}
)