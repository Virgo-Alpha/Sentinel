import React, { useState, useEffect } from 'react';
import { 
  XMarkIcon, 
  LinkIcon, 
  CalendarIcon, 
  TagIcon,
  ExclamationTriangleIcon,
  ChatBubbleLeftIcon,
  CheckIcon,
  XMarkIcon as RejectIcon
} from '@heroicons/react/24/outline';
import { Article, Comment } from '../types';
import { apiService } from '../services/api';
import CommentThread from './CommentThread';

interface ArticleDetailModalProps {
  article: Article;
  onClose: () => void;
  showReviewControls?: boolean;
  onReview?: () => void;
}

const ArticleDetailModal: React.FC<ArticleDetailModalProps> = ({
  article,
  onClose,
  showReviewControls = false,
  onReview
}) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loadingComments, setLoadingComments] = useState(false);
  const [showComments, setShowComments] = useState(false);

  useEffect(() => {
    if (showComments) {
      loadComments();
    }
  }, [showComments, article.article_id]);

  const loadComments = async () => {
    setLoadingComments(true);
    try {
      const response = await apiService.getComments(article.article_id);
      if (response.data) {
        setComments(response.data);
      }
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setLoadingComments(false);
    }
  };

  const handleAddComment = async (content: string, parentId?: string) => {
    try {
      const response = await apiService.createComment(article.article_id, content, parentId);
      if (response.data) {
        await loadComments(); // Reload comments to get the new one
      }
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getRelevancyColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const keywordHits = article.keyword_matches.reduce((sum, match) => sum + match.hit_count, 0);

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {article.title}
            </h2>
            
            <div className="flex items-center space-x-4 text-sm text-gray-500 mb-4">
              <div className="flex items-center">
                <CalendarIcon className="h-4 w-4 mr-1" />
                {formatDate(article.published_at)}
              </div>
              
              <div className="flex items-center">
                <span className="font-medium">{article.source}</span>
              </div>

              <div className="flex items-center">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRelevancyColor(article.relevancy_score)}`}>
                  {Math.round(article.relevancy_score * 100)}% relevant
                </span>
              </div>

              {keywordHits > 0 && (
                <div className="flex items-center">
                  <TagIcon className="h-4 w-4 mr-1" />
                  {keywordHits} keyword hits
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2 mb-4">
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <LinkIcon className="h-4 w-4 mr-1" />
                View Original
              </a>

              {showReviewControls && onReview && (
                <button
                  onClick={onReview}
                  className="inline-flex items-center px-3 py-1 border border-blue-300 rounded-md text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100"
                >
                  <CheckIcon className="h-4 w-4 mr-1" />
                  Review Article
                </button>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-6">
          {/* Summary */}
          {article.summary_short && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Summary</h3>
              <p className="text-gray-700 leading-relaxed">{article.summary_short}</p>
            </div>
          )}

          {/* Analyst Card */}
          {article.summary_card && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Analyst Card</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="text-gray-700 whitespace-pre-wrap font-sans">
                  {article.summary_card}
                </pre>
              </div>
            </div>
          )}

          {/* Entity Extraction */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Entity Extraction</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* CVEs */}
              {article.entities.cves.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">CVEs</h4>
                  <div className="flex flex-wrap gap-1">
                    {article.entities.cves.map((cve) => (
                      <span
                        key={cve}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-red-100 text-red-800"
                      >
                        {cve}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Threat Actors */}
              {article.entities.threat_actors.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Threat Actors</h4>
                  <div className="flex flex-wrap gap-1">
                    {article.entities.threat_actors.map((actor) => (
                      <span
                        key={actor}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800"
                      >
                        {actor}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Malware */}
              {article.entities.malware.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Malware</h4>
                  <div className="flex flex-wrap gap-1">
                    {article.entities.malware.map((malware) => (
                      <span
                        key={malware}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-orange-100 text-orange-800"
                      >
                        {malware}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Vendors */}
              {article.entities.vendors.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Vendors</h4>
                  <div className="flex flex-wrap gap-1">
                    {article.entities.vendors.map((vendor) => (
                      <span
                        key={vendor}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        {vendor}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Products */}
              {article.entities.products.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Products</h4>
                  <div className="flex flex-wrap gap-1">
                    {article.entities.products.map((product) => (
                      <span
                        key={product}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800"
                      >
                        {product}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Sectors */}
              {article.entities.sectors.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Sectors</h4>
                  <div className="flex flex-wrap gap-1">
                    {article.entities.sectors.map((sector) => (
                      <span
                        key={sector}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-indigo-100 text-indigo-800"
                      >
                        {sector}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Countries */}
              {article.entities.countries.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Countries</h4>
                  <div className="flex flex-wrap gap-1">
                    {article.entities.countries.map((country) => (
                      <span
                        key={country}
                        className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800"
                      >
                        {country}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Keyword Matches */}
          {article.keyword_matches.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Keyword Matches</h3>
              <div className="space-y-3">
                {article.keyword_matches.map((match) => (
                  <div key={match.keyword} className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900">{match.keyword}</span>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {match.hit_count} hit{match.hit_count > 1 ? 's' : ''}
                      </span>
                    </div>
                    {match.contexts.length > 0 && (
                      <div className="space-y-1">
                        {match.contexts.slice(0, 3).map((context, index) => (
                          <p key={index} className="text-sm text-gray-600 italic">
                            "...{context}..."
                          </p>
                        ))}
                        {match.contexts.length > 3 && (
                          <p className="text-xs text-gray-500">
                            +{match.contexts.length - 3} more contexts
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tags */}
          {article.tags.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {article.tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Guardrail Flags */}
          {article.guardrail_flags.length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2 flex items-center">
                <ExclamationTriangleIcon className="h-5 w-5 text-orange-500 mr-2" />
                Guardrail Flags
              </h3>
              <div className="flex flex-wrap gap-2">
                {article.guardrail_flags.map((flag) => (
                  <span
                    key={flag}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-orange-100 text-orange-800"
                  >
                    {flag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Comments Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Comments</h3>
              <button
                onClick={() => setShowComments(!showComments)}
                className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <ChatBubbleLeftIcon className="h-4 w-4 mr-1" />
                {showComments ? 'Hide' : 'Show'} Comments
              </button>
            </div>

            {showComments && (
              <CommentThread
                comments={comments}
                loading={loadingComments}
                onAddComment={handleAddComment}
              />
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArticleDetailModal;