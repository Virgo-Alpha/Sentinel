import React, { useState } from 'react';
import { ChatBubbleLeftIcon, UserCircleIcon, PlusIcon } from '@heroicons/react/24/outline';
import { Comment } from '../types';

interface CommentThreadProps {
  comments: Comment[];
  loading: boolean;
  onAddComment: (content: string, parentId?: string) => Promise<void>;
}

interface CommentItemProps {
  comment: Comment;
  onReply: (content: string, parentId: string) => Promise<void>;
  depth?: number;
}

const CommentItem: React.FC<CommentItemProps> = ({ comment, onReply, depth = 0 }) => {
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleReplySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyContent.trim()) return;

    setSubmitting(true);
    try {
      await onReply(replyContent.trim(), comment.comment_id);
      setReplyContent('');
      setShowReplyForm(false);
    } catch (error) {
      console.error('Failed to submit reply:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const maxDepth = 3; // Limit nesting depth
  const indentClass = depth > 0 ? `ml-${Math.min(depth * 4, 12)}` : '';

  return (
    <div className={`${indentClass} ${depth > 0 ? 'border-l-2 border-gray-200 pl-4' : ''}`}>
      <div className="bg-gray-50 rounded-lg p-4 mb-3">
        {/* Comment Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <UserCircleIcon className="h-6 w-6 text-gray-400" />
            <span className="text-sm font-medium text-gray-900">{comment.author}</span>
            <span className="text-xs text-gray-500">•</span>
            <span className="text-xs text-gray-500">{formatDate(comment.created_at)}</span>
            {comment.updated_at && comment.updated_at !== comment.created_at && (
              <>
                <span className="text-xs text-gray-500">•</span>
                <span className="text-xs text-gray-500">edited</span>
              </>
            )}
          </div>
        </div>

        {/* Comment Content */}
        <div className="text-gray-700 mb-3 whitespace-pre-wrap">
          {comment.content}
        </div>

        {/* Comment Actions */}
        {depth < maxDepth && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowReplyForm(!showReplyForm)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {showReplyForm ? 'Cancel' : 'Reply'}
            </button>
          </div>
        )}

        {/* Reply Form */}
        {showReplyForm && (
          <form onSubmit={handleReplySubmit} className="mt-3 pt-3 border-t border-gray-200">
            <textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply..."
              rows={3}
              className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
              required
            />
            <div className="flex justify-end space-x-2 mt-2">
              <button
                type="button"
                onClick={() => {
                  setShowReplyForm(false);
                  setReplyContent('');
                }}
                className="px-3 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!replyContent.trim() || submitting}
                className="px-3 py-1 text-xs font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Posting...' : 'Post Reply'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Nested Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="space-y-2">
          {comment.replies.map((reply) => (
            <CommentItem
              key={reply.comment_id}
              comment={reply}
              onReply={onReply}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const CommentThread: React.FC<CommentThreadProps> = ({ comments, loading, onAddComment }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    setSubmitting(true);
    try {
      await onAddComment(newComment.trim());
      setNewComment('');
      setShowAddForm(false);
    } catch (error) {
      console.error('Failed to add comment:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReply = async (content: string, parentId: string) => {
    await onAddComment(content, parentId);
  };

  // Organize comments into a tree structure
  const organizeComments = (comments: Comment[]): Comment[] => {
    const commentMap = new Map<string, Comment>();
    const rootComments: Comment[] = [];

    // First pass: create map of all comments
    comments.forEach(comment => {
      commentMap.set(comment.comment_id, { ...comment, replies: [] });
    });

    // Second pass: organize into tree structure
    comments.forEach(comment => {
      const commentWithReplies = commentMap.get(comment.comment_id)!;
      
      if (comment.parent_id) {
        const parent = commentMap.get(comment.parent_id);
        if (parent) {
          parent.replies = parent.replies || [];
          parent.replies.push(commentWithReplies);
        } else {
          // Parent not found, treat as root comment
          rootComments.push(commentWithReplies);
        }
      } else {
        rootComments.push(commentWithReplies);
      }
    });

    return rootComments;
  };

  const organizedComments = organizeComments(comments);

  if (loading) {
    return (
      <div className="text-center py-4">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
        <p className="text-gray-500 text-sm mt-2">Loading comments...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Add Comment Button */}
      {!showAddForm && (
        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Add Comment
        </button>
      )}

      {/* Add Comment Form */}
      {showAddForm && (
        <form onSubmit={handleAddComment} className="bg-white border border-gray-200 rounded-lg p-4">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Write a comment..."
            rows={4}
            className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            required
          />
          <div className="flex justify-end space-x-2 mt-3">
            <button
              type="button"
              onClick={() => {
                setShowAddForm(false);
                setNewComment('');
              }}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!newComment.trim() || submitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Posting...' : 'Post Comment'}
            </button>
          </div>
        </form>
      )}

      {/* Comments List */}
      {organizedComments.length === 0 ? (
        <div className="text-center py-8">
          <ChatBubbleLeftIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No comments yet.</p>
          <p className="text-sm text-gray-400 mt-1">
            Be the first to add a comment about this article.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {organizedComments.map((comment) => (
            <CommentItem
              key={comment.comment_id}
              comment={comment}
              onReply={handleReply}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default CommentThread;