import React, { useState, useEffect } from 'react';
import { 
  CheckIcon, 
  XMarkIcon, 
  EyeIcon, 
  ClockIcon, 
  ExclamationTriangleIcon,
  ChatBubbleLeftIcon,
  TagIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';
import { Article, ReviewDecision } from '../types';
import { apiService } from '../services/api';
import ArticleDetailModal from '../components/ArticleDetailModal';
import ReviewDecisionModal from '../components/ReviewDecisionModal';

const ReviewQueue: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [reviewingArticle, setReviewingArticle] = useState<Article | null>(null);
  const [sortBy, setSortBy] = useState<'published_at' | 'relevancy_score' | 'keyword_hits'>('published_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filterPriority, setFilterPriority] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    loadReviewQueue();
  }, []);

  const loadReviewQueue = async () => {
    setLoading(true);
    try {
      const response = await apiService.getArticles({ 
        state: 'REVIEW',
        limit: 100 
      });
      
      if (response.data) {
        setArticles(response.data);
      }
    } catch (error) {
      console.error('Failed to load review queue:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReviewDecision = async (decision: ReviewDecision) => {
    try {
      const response = await apiService.submitReviewDecision(
        decision.article_id,
        decision.decision,
        decision.reason
      );

      if (response.data) {
        // Remove the reviewed article from the queue
        setArticles(prev => prev.filter(a => a.article_id !== decision.article_id));
        setReviewingArticle(null);
      }
    } catch (error) {
      console.error('Failed to submit review decision:', error);
    }
  };

  const getPriorityLevel = (article: Article): 'high' | 'medium' | 'low' => {
    const keywordHits = article.keyword_matches.reduce((sum, match) => sum + match.hit_count, 0);
    const hasHighPriorityEntities = article.entities.cves.length > 0 || 
                                   article.entities.threat_actors.length > 0;
    
    if (article.relevancy_score >= 0.8 || keywordHits >= 5 || hasHighPriorityEntities) {
      return 'high';
    } else if (article.relevancy_score >= 0.6 || keywordHits >= 2) {
      return 'medium';
    }
    return 'low';
  };

  const getPriorityColor = (priority: 'high' | 'medium' | 'low') => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
    }
  };

  const sortedAndFilteredArticles = articles
    .filter(article => {
      if (filterPriority === 'all') return true;
      return getPriorityLevel(article) === filterPriority;
    })
    .sort((a, b) => {
      let aValue: number, bValue: number;
      
      switch (sortBy) {
        case 'published_at':
          aValue = new Date(a.published_at).getTime();
          bValue = new Date(b.published_at).getTime();
          break;
        case 'relevancy_score':
          aValue = a.relevancy_score;
          bValue = b.relevancy_score;
          break;
        case 'keyword_hits':
          aValue = a.keyword_matches.reduce((sum, match) => sum + match.hit_count, 0);
          bValue = b.keyword_matches.reduce((sum, match) => sum + match.hit_count, 0);
          break;
        default:
          return 0;
      }
      
      return sortOrder === 'desc' ? bValue - aValue : aValue - bValue;
    });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getGuardrailIcon = (flags: string[]) => {
    if (flags.length === 0) return null;
    return (
      <div className="flex items-center text-orange-600">
        <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
        <span className="text-xs">{flags.length} flag{flags.length > 1 ? 's' : ''}</span>
      </div>
    );
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
        <p className="mt-2 text-gray-600">
          Articles requiring human review and approval ({articles.length} pending)
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Priority Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>
                <select
                  value={filterPriority}
                  onChange={(e) => setFilterPriority(e.target.value as any)}
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Priorities</option>
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="low">Low Priority</option>
                </select>
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="published_at">Date Published</option>
                  <option value="relevancy_score">Relevancy Score</option>
                  <option value="keyword_hits">Keyword Hits</option>
                </select>
              </div>

              {/* Sort Order */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Order
                </label>
                <select
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value as any)}
                  className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>
            </div>

            <button
              onClick={loadReviewQueue}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <ClockIcon className="h-4 w-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Review Queue */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-gray-500 mt-2">Loading review queue...</p>
            </div>
          ) : sortedAndFilteredArticles.length === 0 ? (
            <div className="text-center py-8">
              <CheckIcon className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <p className="text-gray-500">No articles pending review!</p>
              <p className="text-sm text-gray-400 mt-1">
                All articles have been processed or there are no items matching your filters.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {sortedAndFilteredArticles.map((article) => {
                const priority = getPriorityLevel(article);
                const keywordHits = article.keyword_matches.reduce((sum, match) => sum + match.hit_count, 0);
                
                return (
                  <div
                    key={article.article_id}
                    className={`border-2 rounded-lg p-4 ${getPriorityColor(priority)}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(priority)}`}>
                            {priority.toUpperCase()} PRIORITY
                          </span>
                          
                          {getGuardrailIcon(article.guardrail_flags)}
                          
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {Math.round(article.relevancy_score * 100)}% relevant
                          </span>
                        </div>

                        <h4 className="text-lg font-medium text-gray-900 mb-2">
                          {article.title}
                        </h4>
                        
                        {article.summary_short && (
                          <p className="text-gray-600 mb-3 line-clamp-3">
                            {article.summary_short}
                          </p>
                        )}

                        <div className="flex items-center mb-3 space-x-4 text-sm text-gray-500">
                          <div className="flex items-center">
                            <CalendarIcon className="h-4 w-4 mr-1" />
                            {formatDate(article.published_at)}
                          </div>
                          
                          <div className="flex items-center">
                            <span className="font-medium">{article.source}</span>
                          </div>

                          {keywordHits > 0 && (
                            <div className="flex items-center">
                              <TagIcon className="h-4 w-4 mr-1" />
                              {keywordHits} keyword hit{keywordHits > 1 ? 's' : ''}
                            </div>
                          )}
                        </div>

                        {/* Entities Preview */}
                        {(article.entities.cves.length > 0 || article.entities.threat_actors.length > 0) && (
                          <div className="mb-3">
                            <div className="flex flex-wrap gap-1">
                              {article.entities.cves.slice(0, 3).map((cve) => (
                                <span
                                  key={cve}
                                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-red-100 text-red-800"
                                >
                                  {cve}
                                </span>
                              ))}
                              {article.entities.threat_actors.slice(0, 2).map((actor) => (
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

                        {/* Keyword Matches Preview */}
                        {article.keyword_matches.length > 0 && (
                          <div className="mb-3">
                            <div className="flex flex-wrap gap-1">
                              {article.keyword_matches.slice(0, 5).map((match) => (
                                <span
                                  key={match.keyword}
                                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800"
                                >
                                  {match.keyword} ({match.hit_count})
                                </span>
                              ))}
                              {article.keyword_matches.length > 5 && (
                                <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                                  +{article.keyword_matches.length - 5} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Guardrail Flags */}
                        {article.guardrail_flags.length > 0 && (
                          <div className="mb-3">
                            <p className="text-sm font-medium text-orange-800 mb-1">Guardrail Flags:</p>
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
                          </div>
                        )}
                      </div>

                      <div className="ml-4 flex-shrink-0 space-y-2">
                        <div className="flex flex-col space-y-2">
                          <button
                            onClick={() => setSelectedArticle(article)}
                            className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                          >
                            <EyeIcon className="h-4 w-4 mr-1" />
                            View Details
                          </button>
                          
                          <button
                            onClick={() => setReviewingArticle(article)}
                            className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                          >
                            <ChatBubbleLeftIcon className="h-4 w-4 mr-1" />
                            Review
                          </button>
                        </div>

                        <div className="flex flex-col space-y-1">
                          <button
                            onClick={() => setReviewingArticle(article)}
                            className="inline-flex items-center px-3 py-1 border border-transparent rounded-md text-sm font-medium text-white bg-green-600 hover:bg-green-700"
                          >
                            <CheckIcon className="h-4 w-4 mr-1" />
                            Approve
                          </button>
                          
                          <button
                            onClick={() => setReviewingArticle(article)}
                            className="inline-flex items-center px-3 py-1 border border-transparent rounded-md text-sm font-medium text-white bg-red-600 hover:bg-red-700"
                          >
                            <XMarkIcon className="h-4 w-4 mr-1" />
                            Reject
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Article Detail Modal */}
      {selectedArticle && (
        <ArticleDetailModal
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
          showReviewControls={true}
          onReview={() => {
            setReviewingArticle(selectedArticle);
            setSelectedArticle(null);
          }}
        />
      )}

      {/* Review Decision Modal */}
      {reviewingArticle && (
        <ReviewDecisionModal
          article={reviewingArticle}
          onClose={() => setReviewingArticle(null)}
          onSubmit={handleReviewDecision}
        />
      )}
    </div>
  );
};

export default ReviewQueue;