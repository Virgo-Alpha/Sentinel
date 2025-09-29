import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Authenticator } from '@aws-amplify/ui-react';
import '@testing-library/jest-dom';

// Mock CSS imports
jest.mock('@aws-amplify/ui-react/styles.css', () => '', { virtual: true });
jest.mock('../App.css', () => '', { virtual: true });

// Mock AWS Amplify
jest.mock('aws-amplify', () => ({
  Amplify: {
    configure: jest.fn(),
  },
}));

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

jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn(() => 
    Promise.resolve({
      tokens: {
        idToken: {
          toString: () => createMockJWT(['Analysts']),
        },
      },
    })
  ),
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

// Mock Authenticator to simulate authenticated state
jest.mock('@aws-amplify/ui-react', () => ({
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

describe('Authentication Flow', () => {
  beforeEach(() => {
    // Clear any previous mocks
    jest.clearAllMocks();
  });

  test('renders app with authenticated user', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Should redirect to dashboard when authenticated
    await waitFor(() => {
      expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    });
  });

  test('displays user information in layout', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
      expect(screen.getByText('Security Analyst')).toBeInTheDocument();
    });
  });

  test('navigation works correctly', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    // Check that navigation links are present
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Review Queue')).toBeInTheDocument();
      expect(screen.getByText('Analyst Assistant')).toBeInTheDocument();
    });
  });

  test('sign out button is present', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Sign out')).toBeInTheDocument();
    });
  });
});

describe('Unauthenticated State', () => {
  beforeEach(() => {
    // Mock unauthenticated state
    jest.mocked(require('@aws-amplify/ui-react').useAuthenticator).mockReturnValue({
      authStatus: 'unauthenticated',
    });
  });

  test('shows login page when unauthenticated', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    expect(screen.getByText('Sentinel')).toBeInTheDocument();
    expect(screen.getByText('Cybersecurity Intelligence Triage Platform')).toBeInTheDocument();
  });
});