import React, { useState } from 'react';
import { XMarkIcon, CheckIcon, XMarkIcon as RejectIcon } from '@heroicons/react/24/outline';
import { Article, ReviewDecision } from '../types';

interface ReviewDecisionModalProps {
  article: Article;
  onClose: () => void;
  onSubmit: (decision: ReviewDecision) => void;
}

const ReviewDecisionModal: React.FC<ReviewDecisionModalProps> = ({
  article,
  onClose,
  onSubmit
}) => {
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!decision) return;

    setSubmitting(true);
    try {
      await onSubmit({
        article_id: article.article_id,
        decision,
        reason: reason.trim() || undefined,
        reviewer: 'current-user', // This would come from auth context in real app
        timestamp: new Date().toISOString()
      });
    } finally {
      setSubmitting(false);
    }
  };

  const getDecisionColor = (type: 'approve' | 'reject') => {
    if (decision === type) {
      return type === 'approve' 
        ? 'bg-green-600 text-white border-green-600' 
        : 'bg-red-600 text-white border-red-600';
    }
    return 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50';
  };

  const reasonPlaceholders = {
    approve: 'Optional: Add notes about why this article should be published...',
    reject: 'Please explain why this article should be rejected...'
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-2xl shadow-lg rounded-md bg-white">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Review Article
            </h2>
            <p className="text-gray-600">
              Make a decision on whether to publish or reject this article
            </p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Article Summary */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-medium text-gray-900 mb-2 line-clamp-2">
            {article.title}
          </h3>
          <div className="flex items-center space-x-4 text-sm text-gray-500 mb-2">
            <span>{article.source}</span>
            <span>•</span>
            <span>{Math.round(article.relevancy_score * 100)}% relevant</span>
            <span>•</span>
            <span>
              {article.keyword_matches.reduce((sum, match) => sum + match.hit_count, 0)} keyword hits
            </span>
          </div>
          {article.summary_short && (
            <p className="text-gray-700 text-sm line-clamp-3">
              {article.summary_short}
            </p>
          )}
        </div>

        {/* Decision Form */}
        <form onSubmit={handleSubmit}>
          {/* Decision Buttons */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Decision
            </label>
            <div className="flex space-x-4">
              <button
                type="button"
                onClick={() => setDecision('approve')}
                className={`flex-1 inline-flex items-center justify-center px-4 py-3 border rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 ${getDecisionColor('approve')}`}
              >
                <CheckIcon className="h-5 w-5 mr-2" />
                Approve & Publish
              </button>
              
              <button
                type="button"
                onClick={() => setDecision('reject')}
                className={`flex-1 inline-flex items-center justify-center px-4 py-3 border rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 ${getDecisionColor('reject')}`}
              >
                <RejectIcon className="h-5 w-5 mr-2" />
                Reject
              </button>
            </div>
          </div>

          {/* Reason */}
          {decision && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {decision === 'reject' ? 'Reason for Rejection *' : 'Notes (Optional)'}
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                placeholder={reasonPlaceholders[decision]}
                required={decision === 'reject'}
              />
              {decision === 'reject' && (
                <p className="mt-1 text-sm text-gray-500">
                  Please provide a clear reason for rejection to help improve the system.
                </p>
              )}
            </div>
          )}

          {/* Guardrail Warnings */}
          {article.guardrail_flags.length > 0 && (
            <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <h4 className="text-sm font-medium text-orange-800 mb-2">
                ⚠️ Guardrail Flags Detected
              </h4>
              <div className="flex flex-wrap gap-1">
                {article.guardrail_flags.map((flag) => (
                  <span
                    key={flag}
                    className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-orange-100 text-orange-800"
                  >
                    {flag}
                  </span>
                ))}
              </div>
              <p className="text-sm text-orange-700 mt-2">
                Please review these flags carefully before making your decision.
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            
            <button
              type="submit"
              disabled={!decision || submitting || (decision === 'reject' && !reason.trim())}
              className={`px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                decision === 'approve'
                  ? 'bg-green-600 hover:bg-green-700 focus:ring-green-500'
                  : decision === 'reject'
                  ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                  : 'bg-gray-400 cursor-not-allowed'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {submitting ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Submitting...
                </div>
              ) : (
                `${decision === 'approve' ? 'Approve' : decision === 'reject' ? 'Reject' : 'Submit'} Decision`
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReviewDecisionModal;