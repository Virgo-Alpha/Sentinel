import React, { useState, useEffect, useRef } from 'react';
import { 
  PaperAirplaneIcon, 
  DocumentArrowDownIcon,
  ClockIcon,
  LinkIcon,
  TagIcon,
  HandThumbUpIcon,
  HandThumbDownIcon,
  TrashIcon,
  ChatBubbleLeftRightIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';
import { ChatMessage, ChatSession, QueryResult } from '../types';
import { apiService } from '../services/api';

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [queryResults, setQueryResults] = useState<QueryResult | null>(null);
  const [showExportOptions, setShowExportOptions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Generate session ID on component mount
  useEffect(() => {
    setSessionId(`session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const scrollToBottom = () => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      content: inputMessage.trim(),
      role: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await apiService.sendChatMessage(userMessage.content, sessionId);
      
      if (response.data) {
        const assistantMessage: ChatMessage = {
          id: `msg-${Date.now()}-assistant`,
          content: response.data.message || 'I received your query and am processing it.',
          role: 'assistant',
          timestamp: new Date().toISOString(),
          sources: response.data.sources || []
        };

        setMessages(prev => [...prev, assistantMessage]);

        // If the response includes query results, store them
        if (response.data.queryResults) {
          setQueryResults(response.data.queryResults);
        }
      } else {
        throw new Error(response.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: ChatMessage = {
        id: `msg-${Date.now()}-error`,
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        role: 'assistant',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  const handleFeedback = async (messageId: string, feedback: 'up' | 'down') => {
    try {
      // In a real implementation, this would send feedback to the API
      console.log(`Feedback for message ${messageId}: ${feedback}`);
      
      // Update the message to show feedback was given
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, feedback } 
          : msg
      ));
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const handleExportResults = async (format: 'xlsx' | 'json') => {
    if (!queryResults) return;

    try {
      setIsLoading(true);
      
      // In a real implementation, this would call the API to generate the export
      const exportResponse = await apiService.queryKnowledgeBase(
        'export-last-results', 
        { export_format: format }
      );

      if (exportResponse.data?.export_url) {
        // Trigger download
        const link = document.createElement('a');
        link.href = exportResponse.data.export_url;
        link.download = `sentinel-query-results-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch (error) {
      console.error('Failed to export results:', error);
    } finally {
      setIsLoading(false);
      setShowExportOptions(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setQueryResults(null);
    setSessionId(`session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const suggestedQueries = [
    "Show me recent articles about AWS vulnerabilities",
    "Find articles mentioning Microsoft 365 security issues from the last 30 days",
    "What are the latest CVEs affecting our technology stack?",
    "Search for articles about ransomware targeting healthcare",
    "Show me high-priority articles from this week",
    "Find articles mentioning Fortinet or SentinelOne"
  ];

  return (
    <div className="flex flex-col chat-container">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analyst Assistant</h1>
          <p className="mt-2 text-gray-600">
            Natural language queries and intelligence analysis
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          {queryResults && (
            <div className="relative">
              <button
                onClick={() => setShowExportOptions(!showExportOptions)}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                Export Results
              </button>
              
              {showExportOptions && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border border-gray-200 export-dropdown">
                  <div className="py-1">
                    <button
                      onClick={() => handleExportResults('xlsx')}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Export as Excel (.xlsx)
                    </button>
                    <button
                      onClick={() => handleExportResults('json')}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      Export as JSON
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
          
          <button
            onClick={clearChat}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <TrashIcon className="h-4 w-4 mr-2" />
            Clear Chat
          </button>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 bg-white shadow rounded-lg flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 chat-messages">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <ChatBubbleLeftRightIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Welcome to the Analyst Assistant
              </h3>
              <p className="text-gray-500 mb-6">
                Ask me anything about the cybersecurity intelligence database. I can help you find articles, 
                analyze trends, and generate reports.
              </p>
              
              <div className="max-w-2xl mx-auto">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Try these example queries:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {suggestedQueries.map((query, index) => (
                    <button
                      key={index}
                      onClick={() => setInputMessage(query)}
                      className="text-left p-3 text-sm text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      "{query}"
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-3xl px-4 py-3 rounded-lg ${
                      message.role === 'user'
                        ? 'chat-message-user text-white'
                        : 'chat-message-assistant text-gray-900'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    
                    {/* Sources */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Sources:</h4>
                        <div className="space-y-2">
                          {message.sources.map((source, index) => (
                            <div key={index} className="text-sm">
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 font-medium flex items-center"
                              >
                                <LinkIcon className="h-3 w-3 mr-1" />
                                {source.title}
                              </a>
                              <p className="text-gray-600 mt-1">{source.snippet}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs opacity-75">
                        {formatTimestamp(message.timestamp)}
                      </span>
                      
                      {message.role === 'assistant' && (
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => handleFeedback(message.id, 'up')}
                            className={`p-1 rounded hover:bg-gray-200 ${
                              (message as any).feedback === 'up' ? 'text-green-600' : 'text-gray-400'
                            }`}
                          >
                            <HandThumbUpIcon className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => handleFeedback(message.id, 'down')}
                            className={`p-1 rounded hover:bg-gray-200 ${
                              (message as any).feedback === 'down' ? 'text-red-600' : 'text-gray-400'
                            }`}
                          >
                            <HandThumbDownIcon className="h-3 w-3" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="max-w-3xl px-4 py-3 rounded-lg bg-gray-100">
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                      <span className="text-gray-600">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Query Results Display */}
        {queryResults && (
          <div className="border-t border-gray-200 p-6 bg-gray-50">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Query Results ({queryResults.total} articles found)
              </h3>
            </div>
            
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {queryResults.articles.slice(0, 10).map((article) => (
                <div key={article.article_id} className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 mb-1">
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-blue-600"
                        >
                          {article.title}
                        </a>
                      </h4>
                      
                      <div className="flex items-center space-x-4 text-sm text-gray-500 mb-2">
                        <span>{article.source}</span>
                        <span>•</span>
                        <span>{formatDate(article.published_at)}</span>
                        {article.keyword_matches && article.keyword_matches.length > 0 && (
                          <>
                            <span>•</span>
                            <div className="flex items-center">
                              <TagIcon className="h-3 w-3 mr-1" />
                              {article.keyword_matches.reduce((sum, match) => sum + match.hit_count, 0)} keyword hits
                            </div>
                          </>
                        )}
                      </div>
                      
                      {article.summary_short && (
                        <p className="text-gray-700 text-sm line-clamp-2">
                          {article.summary_short}
                        </p>
                      )}
                      
                      {article.keyword_matches && article.keyword_matches.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
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
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {queryResults.articles.length > 10 && (
                <div className="text-center py-2">
                  <p className="text-sm text-gray-500">
                    Showing first 10 results. Export to see all {queryResults.total} articles.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSendMessage} className="flex space-x-3">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me about cybersecurity intelligence... (Press Enter to send, Shift+Enter for new line)"
                rows={1}
                className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 auto-resize-textarea"
                disabled={isLoading}
                style={{ minHeight: '40px', maxHeight: '120px' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                }}
              />
            </div>
            <button
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              {isLoading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <PaperAirplaneIcon className="h-4 w-4" />
              )}
            </button>
          </form>
          
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <div className="flex items-center space-x-4">
              <span>Session: {sessionId.split('-').pop()}</span>
              <span>•</span>
              <span>{messages.length} messages</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <ClockIcon className="h-3 w-3" />
              <span>Real-time intelligence analysis</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;