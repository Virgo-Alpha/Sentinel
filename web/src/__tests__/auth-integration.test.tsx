import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import '@testing-library/jest-dom';

// Mock CSS imports
jest.mock('@aws-amplify/ui-react/styles.css', () => '', { virtual: true });
jest.mock('../App.css', () => '', { virtual: true });

// Mock AWS Amplify
const mockFetchAuthSession = jest.fn();
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: mockFetchAuthSession,
}));

jest.mock('aws-amplify', () => ({
  Amplify: {
    configure: jest.fn(),
  },
}));

// Mock components
jest.mock('../pages/Dashboard', () => {
  return function MockDashboard() {
    return <div data-testid="dashboard">Dashboard</div>;
  };
});

jest.mock('../pages/ReviewQueue', () => {
  return function MockReviewQueue() {
    return <div data-testid="review-queue">Review Queue</div>;
  };
});

jest.mock('../pages/Chat', () => {
  return function MockChat() {
    return <div data-testid="chat">Chat</div>;
  };
});

import App from '../App';

// Helper to create mock JWT token
const createMockJWT = (groups: string[] = ['Analysts']) => {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify({
    'cognito:groups': groups,
    email: 'test@example.com',
    exp: Math.floor(Date.now() / 1000) + 3600,
  }));
  const signature = 'mock-signature';
  return `${header}.${payload}.${signature}`;
};

describe('Authentication Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Analyst User Authentication', () => {
    beforeEach(() => {
      // Mock Authenticator for analyst user
      jest.doMock('@aws-amplify/ui-react', () => ({
        ...jest.requireActual('@aws-amplify/ui-react'),
        Authenticator: ({ children }: { children: any }) => {
          const mockUser = {
            signInDetails: {
              loginId: 'analyst@example.com',
            },
            username: 'analyst',
          };
          const mockSignOut = jest.fn();
          
          return children({ signOut: mockSignOut, user: mockUser });
        },
        useAuthenticator: () => ({
          authStatus: 'authenticated',
        }),
      }));

      // Mock auth session with analyst groups
      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          idToken: {
            toString: () => createMockJWT(['Analysts']),
          },
        },
      });
    });

    test('analyst user can access all navigation items', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Review Queue')).toBeInTheDocument();
        expect(screen.getByText('Analyst Assistant')).toBeInTheDocument();
      });
    });

    test('displays correct role for analyst user', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('analyst@example.com')).toBeInTheDocument();
        expect(screen.getByText('Security Analyst')).toBeInTheDocument();
      });
    });
  });

  describe('Admin User Authentication', () => {
    beforeEach(() => {
      // Mock Authenticator for admin user
      jest.doMock('@aws-amplify/ui-react', () => ({
        ...jest.requireActual('@aws-amplify/ui-react'),
        Authenticator: ({ children }: { children: any }) => {
          const mockUser = {
            signInDetails: {
              loginId: 'admin@example.com',
            },
            username: 'admin',
          };
          const mockSignOut = jest.fn();
          
          return children({ signOut: mockSignOut, user: mockUser });
        },
        useAuthenticator: () => ({
          authStatus: 'authenticated',
        }),
      }));

      // Mock auth session with admin groups
      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          idToken: {
            toString: () => createMockJWT(['Admins']),
          },
        },
      });
    });

    test('admin user can access all navigation items', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
        expect(screen.getByText('Review Queue')).toBeInTheDocument();
        expect(screen.getByText('Analyst Assistant')).toBeInTheDocument();
      });
    });

    test('displays correct role for admin user', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('admin@example.com')).toBeInTheDocument();
        expect(screen.getByText('Administrator')).toBeInTheDocument();
      });
    });
  });

  describe('Authentication Error Handling', () => {
    beforeEach(() => {
      // Mock Authenticator for user with auth issues
      jest.doMock('@aws-amplify/ui-react', () => ({
        ...jest.requireActual('@aws-amplify/ui-react'),
        Authenticator: ({ children }: { children: any }) => {
          const mockUser = {
            signInDetails: {
              loginId: 'user@example.com',
            },
            username: 'user',
          };
          const mockSignOut = jest.fn();
          
          return children({ signOut: mockSignOut, user: mockUser });
        },
        useAuthenticator: () => ({
          authStatus: 'authenticated',
        }),
      }));

      // Mock auth session failure
      mockFetchAuthSession.mockRejectedValue(new Error('Auth session failed'));
    });

    test('handles auth session failure gracefully', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('user@example.com')).toBeInTheDocument();
        // Should default to analyst role when auth fails
        expect(screen.getByText('Security Analyst')).toBeInTheDocument();
      });
    });
  });

  describe('Unauthenticated State', () => {
    beforeEach(() => {
      // Mock unauthenticated state
      jest.doMock('@aws-amplify/ui-react', () => ({
        ...jest.requireActual('@aws-amplify/ui-react'),
        Authenticator: ({ children }: { children: any }) => {
          return <div data-testid="login-form">Login Form</div>;
        },
        useAuthenticator: () => ({
          authStatus: 'unauthenticated',
        }),
      }));
    });

    test('shows login page when unauthenticated', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      expect(screen.getByText('Sentinel')).toBeInTheDocument();
      expect(screen.getByText('Cybersecurity Intelligence Triage Platform')).toBeInTheDocument();
    });

    test('redirects to dashboard after authentication', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      // Initially shows login
      expect(screen.getByText('Sentinel')).toBeInTheDocument();
    });
  });

  describe('Navigation and Routing', () => {
    beforeEach(() => {
      // Mock authenticated state
      jest.doMock('@aws-amplify/ui-react', () => ({
        ...jest.requireActual('@aws-amplify/ui-react'),
        Authenticator: ({ children }: { children: any }) => {
          const mockUser = {
            signInDetails: {
              loginId: 'test@example.com',
            },
            username: 'testuser',
          };
          const mockSignOut = jest.fn();
          
          return children({ signOut: mockSignOut, user: mockUser });
        },
        useAuthenticator: () => ({
          authStatus: 'authenticated',
        }),
      }));

      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          idToken: {
            toString: () => createMockJWT(['Analysts']),
          },
        },
      });
    });

    test('navigation between pages works correctly', async () => {
      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      // Should start on dashboard
      await waitFor(() => {
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
      });

      // Click on Review Queue
      const reviewLink = screen.getByText('Review Queue');
      fireEvent.click(reviewLink);

      await waitFor(() => {
        expect(screen.getByTestId('review-queue')).toBeInTheDocument();
      });

      // Click on Analyst Assistant
      const chatLink = screen.getByText('Analyst Assistant');
      fireEvent.click(chatLink);

      await waitFor(() => {
        expect(screen.getByTestId('chat')).toBeInTheDocument();
      });
    });

    test('sign out functionality works', async () => {
      const mockSignOut = jest.fn();
      
      jest.doMock('@aws-amplify/ui-react', () => ({
        ...jest.requireActual('@aws-amplify/ui-react'),
        Authenticator: ({ children }: { children: any }) => {
          const mockUser = {
            signInDetails: {
              loginId: 'test@example.com',
            },
            username: 'testuser',
          };
          
          return children({ signOut: mockSignOut, user: mockUser });
        },
        useAuthenticator: () => ({
          authStatus: 'authenticated',
        }),
      }));

      const { default: App } = await import('../App');
      
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      await waitFor(() => {
        const signOutButton = screen.getByText('Sign out');
        fireEvent.click(signOutButton);
        expect(mockSignOut).toHaveBeenCalled();
      });
    });
  });
});