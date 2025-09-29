import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Chat from '../pages/Chat';
import { apiService } from '../services/api';

// Mock the API service
jest.mock('../services/api', () => ({
  apiService: {
    sendChatMessage: jest.fn(),
    queryKnowledgeBase: jest.fn(),
  },
}));

const mockApiService = apiService as jest.Mocked<typeof apiService>;

const renderChat = () => {
  return render(
    <BrowserRouter>
      <Chat />
    </BrowserRouter>
  );
};

describe('Chat Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders chat interface with welcome message', () => {
    renderChat();
    
    expect(screen.getByText('Analyst Assistant')).toBeInTheDocument();
    expect(screen.getByText('Natural language queries and intelligence analysis')).toBeInTheDocument();
    expect(screen.getByText('Welcome to the Analyst Assistant')).toBeInTheDocument();
  });

  test('displays suggested queries', () => {
    renderChat();
    
    expect(screen.getByText(/Show me recent articles about AWS vulnerabilities/)).toBeInTheDocument();
    expect(screen.getByText(/Find articles mentioning Microsoft 365/)).toBeInTheDocument();
    expect(screen.getByText(/What are the latest CVEs/)).toBeInTheDocument();
  });

  test('allows user to type and send messages', async () => {
    mockApiService.sendChatMessage.mockResolvedValue({
      data: {
        message: 'I found 5 articles about AWS vulnerabilities.',
        sources: [],
      },
    });

    renderChat();
    
    const input = screen.getByPlaceholderText(/Ask me about cybersecurity intelligence/);
    const sendButton = screen.getByRole('button', { name: /send message/i });
    
    fireEvent.change(input, { target: { value: 'Show me AWS vulnerabilities' } });
    fireEvent.click(sendButton);
    
    expect(mockApiService.sendChatMessage).toHaveBeenCalledWith(
      'Show me AWS vulnerabilities',
      expect.any(String)
    );
    
    await waitFor(() => {
      expect(screen.getByText('Show me AWS vulnerabilities')).toBeInTheDocument();
    });
  });

  test('handles suggested query clicks', () => {
    renderChat();
    
    const suggestedQuery = screen.getByText(/Show me recent articles about AWS vulnerabilities/);
    fireEvent.click(suggestedQuery);
    
    const input = screen.getByPlaceholderText(/Ask me about cybersecurity intelligence/) as HTMLTextAreaElement;
    expect(input.value).toBe('Show me recent articles about AWS vulnerabilities');
  });

  test('displays loading state when sending message', async () => {
    mockApiService.sendChatMessage.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    renderChat();
    
    const input = screen.getByPlaceholderText(/Ask me about cybersecurity intelligence/);
    const sendButton = screen.getByRole('button', { name: /send message/i });
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText('Thinking...')).toBeInTheDocument();
    });
  });

  test('handles API errors gracefully', async () => {
    mockApiService.sendChatMessage.mockRejectedValue(new Error('API Error'));
    
    renderChat();
    
    const input = screen.getByPlaceholderText(/Ask me about cybersecurity intelligence/);
    const sendButton = screen.getByRole('button', { name: /send message/i });
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);
    
    await waitFor(() => {
      expect(screen.getByText(/Sorry, I encountered an error/)).toBeInTheDocument();
    });
  });

  test('clears chat when clear button is clicked', async () => {
    mockApiService.sendChatMessage.mockResolvedValue({
      data: {
        message: 'Test response',
        sources: [],
      },
    });

    renderChat();
    
    // Send a message first
    const input = screen.getByPlaceholderText(/Ask me about cybersecurity intelligence/);
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.submit(input.closest('form')!);
    
    await waitFor(() => {
      expect(screen.getByText('Test message')).toBeInTheDocument();
    });
    
    // Clear the chat
    const clearButton = screen.getByText('Clear Chat');
    fireEvent.click(clearButton);
    
    expect(screen.queryByText('Test message')).not.toBeInTheDocument();
    expect(screen.getByText('Welcome to the Analyst Assistant')).toBeInTheDocument();
  });

  test('handles keyboard shortcuts correctly', () => {
    renderChat();
    
    const input = screen.getByPlaceholderText(/Ask me about cybersecurity intelligence/);
    
    // Test Enter key submission
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });
    
    expect(mockApiService.sendChatMessage).toHaveBeenCalled();
  });

  test('displays session information', () => {
    renderChat();
    
    expect(screen.getByText(/Session:/)).toBeInTheDocument();
    expect(screen.getByText(/0 messages/)).toBeInTheDocument();
    expect(screen.getByText('Real-time intelligence analysis')).toBeInTheDocument();
  });
});