import { apiService } from '../services/api';

// Mock fetch
global.fetch = jest.fn();

// Mock AWS Amplify auth
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn(),
}));

describe('API Service', () => {
  const mockFetchAuthSession = require('aws-amplify/auth').fetchAuthSession;
  
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.REACT_APP_API_GATEWAY_URL = 'https://api.example.com';
    
    // Default mock for successful auth session
    mockFetchAuthSession.mockResolvedValue({
      tokens: {
        idToken: {
          toString: () => 'mock-token',
        },
      },
    });
  });

  describe('Authentication', () => {
    test('includes authorization header in requests', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ data: 'test' }),
      };
      (fetch as jest.Mock).mockResolvedValue(mockResponse);

      await apiService.getArticles();

      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/articles',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-token',
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    test('handles auth session failure gracefully', async () => {
      mockFetchAuthSession.mockRejectedValue(new Error('Auth failed'));

      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ data: 'test' }),
      };
      (fetch as jest.Mock).mockResolvedValue(mockResponse);

      await apiService.getArticles();

      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/articles',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });
  });

  describe('Articles API', () => {
    test('getArticles makes correct request', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ articles: [] }),
      };
      (fetch as jest.Mock).mockResolvedValue(mockResponse);

      const result = await apiService.getArticles({
        state: 'PUBLISHED',
        limit: 10,
        search: 'test',
      });

      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/articles?state=PUBLISHED&limit=10&search=test',
        expect.any(Object)
      );
      expect(result.data).toEqual({ articles: [] });
    });

    test('getArticle makes correct request', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ article: { id: '123' } }),
      };
      (fetch as jest.Mock).mockResolvedValue(mockResponse);

      await apiService.getArticle('123');

      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/articles/123',
        expect.any(Object)
      );
    });
  });

  describe('Chat API', () => {
    test('sendChatMessage makes correct request', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ response: 'Hello' }),
      };
      (fetch as jest.Mock).mockResolvedValue(mockResponse);

      await apiService.sendChatMessage('Hello', 'session-123');

      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/chat',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            message: 'Hello',
            sessionId: 'session-123',
          }),
        })
      );
    });
  });

  describe('Query API', () => {
    test('queryKnowledgeBase makes correct request', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ results: [] }),
      };
      (fetch as jest.Mock).mockResolvedValue(mockResponse);

      const filters = { date_range: { start: '2024-01-01', end: '2024-01-31' } };
      await apiService.queryKnowledgeBase('test query', filters);

      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/query',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            query: 'test query',
            filters,
          }),
        })
      );
    });
  });

  describe('Error Handling', () => {
    test('handles HTTP errors', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
      };
      (fetch as jest.Mock).mockResolvedValue(mockResponse);

      const result = await apiService.getArticles();

      expect(result.error).toBe('HTTP error! status: 404');
      expect(result.data).toBeUndefined();
    });

    test('handles network errors', async () => {
      (fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      const result = await apiService.getArticles();

      expect(result.error).toBe('Network error');
      expect(result.data).toBeUndefined();
    });
  });
});