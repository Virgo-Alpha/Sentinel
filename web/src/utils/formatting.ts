import { Article } from '../types';

export const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch (error) {
    return 'Invalid Date';
  }
};

export const formatRelativeTime = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) {
      return 'Just now';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 604800) {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days} day${days > 1 ? 's' : ''} ago`;
    } else {
      return formatDate(dateString);
    }
  } catch (error) {
    return 'Unknown';
  }
};

export const getStatusColor = (state: Article['state']): string => {
  switch (state) {
    case 'PUBLISHED':
      return 'status-published';
    case 'REVIEW':
      return 'status-review';
    case 'ARCHIVED':
      return 'status-archived';
    case 'INGESTED':
    case 'PROCESSED':
      return 'status-ingested';
    default:
      return 'status-archived';
  }
};

export const getStatusText = (state: Article['state']): string => {
  switch (state) {
    case 'PUBLISHED':
      return 'Published';
    case 'REVIEW':
      return 'Under Review';
    case 'ARCHIVED':
      return 'Archived';
    case 'INGESTED':
      return 'Ingested';
    case 'PROCESSED':
      return 'Processed';
    default:
      return 'Unknown';
  }
};

export const getPriorityClass = (relevancyScore: number): string => {
  if (relevancyScore >= 0.8) return 'priority-high';
  if (relevancyScore >= 0.6) return 'priority-medium';
  return 'priority-low';
};

export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

export const formatKeywordMatches = (matches: Article['keyword_matches']): string => {
  if (!matches || matches.length === 0) return 'No keywords';
  
  const totalHits = matches.reduce((sum, match) => sum + match.hit_count, 0);
  const keywordNames = matches.map(match => match.keyword).join(', ');
  
  return `${totalHits} hits: ${keywordNames}`;
};

export const formatEntityList = (entities: string[]): string => {
  if (!entities || entities.length === 0) return 'None';
  if (entities.length <= 3) return entities.join(', ');
  return `${entities.slice(0, 3).join(', ')} +${entities.length - 3} more`;
};

export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.8) return 'text-green-600';
  if (confidence >= 0.6) return 'text-yellow-600';
  return 'text-red-600';
};

export const formatConfidence = (confidence: number): string => {
  return `${Math.round(confidence * 100)}%`;
};