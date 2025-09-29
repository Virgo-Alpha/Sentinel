import { fetchAuthSession } from 'aws-amplify/auth';

const API_BASE_URL = process.env.REACT_APP_API_GATEWAY_URL || '';

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

class ApiService {
  private async getAuthHeaders(): Promise<HeadersInit> {
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
      };
    } catch (error) {
      console.error('Failed to get auth headers:', error);
      return {
        'Content-Type': 'application/json',
      };
    }
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const headers = await this.getAuthHeaders();
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          ...headers,
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      return { 
        error: error instanceof Error ? error.message : 'Unknown error occurred' 
      };
    }
  }

  // Articles API
  async getArticles(params?: {
    state?: string;
    limit?: number;
    offset?: number;
    search?: string;
  }): Promise<ApiResponse<any[]>> {
    const queryParams = new URLSearchParams();
    if (params?.state) queryParams.append('state', params.state);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.search) queryParams.append('search', params.search);

    const endpoint = `/articles${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
    return this.makeRequest(endpoint);
  }

  async getArticle(id: string): Promise<ApiResponse<any>> {
    return this.makeRequest(`/articles/${id}`);
  }

  // Chat API
  async sendChatMessage(message: string, sessionId?: string): Promise<ApiResponse<any>> {
    return this.makeRequest('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        sessionId,
      }),
    });
  }

  // Query API
  async queryKnowledgeBase(query: string, filters?: any): Promise<ApiResponse<any>> {
    return this.makeRequest('/query', {
      method: 'POST',
      body: JSON.stringify({
        query,
        filters,
      }),
    });
  }

  // Comments API
  async getComments(articleId: string): Promise<ApiResponse<any[]>> {
    return this.makeRequest(`/comments?articleId=${articleId}`);
  }

  async createComment(articleId: string, content: string, parentId?: string): Promise<ApiResponse<any>> {
    return this.makeRequest('/comments', {
      method: 'POST',
      body: JSON.stringify({
        articleId,
        content,
        parentId,
      }),
    });
  }

  // Review API
  async submitReviewDecision(
    articleId: string,
    decision: 'approve' | 'reject',
    reason?: string
  ): Promise<ApiResponse<any>> {
    return this.makeRequest('/review', {
      method: 'POST',
      body: JSON.stringify({
        articleId,
        decision,
        reason,
      }),
    });
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<any>> {
    return this.makeRequest('/health');
  }
}

export const apiService = new ApiService();
export default apiService;