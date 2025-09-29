// Mock AWS Amplify auth
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn(),
}));

import { 
  getUserGroups, 
  getUserGroupsSync, 
  isAdmin, 
  isAnalyst, 
  getUserDisplayName, 
  formatUserRole 
} from '../utils/auth';

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

describe('Auth Utils', () => {
  const mockFetchAuthSession = require('aws-amplify/auth').fetchAuthSession;
  
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getUserGroups (async)', () => {
    test('extracts groups from JWT token', async () => {
      const mockUser = {
        signInDetails: { loginId: 'test@example.com' },
        username: 'testuser',
      };

      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          idToken: {
            toString: () => createMockJWT(['Analysts', 'CustomGroup']),
          },
        },
      });

      const groups = await getUserGroups(mockUser as any);
      expect(groups).toEqual(['Analysts', 'CustomGroup']);
    });

    test('returns empty array for no user', async () => {
      const groups = await getUserGroups();
      expect(groups).toEqual([]);
    });

    test('falls back to email-based detection when JWT fails', async () => {
      const mockUser = {
        signInDetails: { loginId: 'admin@example.com' },
        username: 'admin',
      };

      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          idToken: null,
        },
      });

      const groups = await getUserGroups(mockUser as any);
      expect(groups).toEqual(['Admins']);
    });

    test('defaults to Analysts when auth session fails', async () => {
      const mockUser = {
        signInDetails: { loginId: 'test@example.com' },
        username: 'testuser',
      };

      mockFetchAuthSession.mockRejectedValue(new Error('Auth failed'));

      const groups = await getUserGroups(mockUser as any);
      expect(groups).toEqual(['Analysts']);
    });

    test('handles malformed JWT gracefully', async () => {
      const mockUser = {
        signInDetails: { loginId: 'test@example.com' },
        username: 'testuser',
      };

      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          idToken: {
            toString: () => 'invalid.jwt.token',
          },
        },
      });

      const groups = await getUserGroups(mockUser as any);
      expect(groups).toEqual(['Analysts']);
    });
  });

  describe('getUserGroupsSync', () => {
    test('returns admin group for admin email', () => {
      const mockUser = {
        signInDetails: { loginId: 'admin@example.com' },
        username: 'admin',
      };

      const groups = getUserGroupsSync(mockUser as any);
      expect(groups).toEqual(['Admins']);
    });

    test('returns analyst group for regular email', () => {
      const mockUser = {
        signInDetails: { loginId: 'user@example.com' },
        username: 'user',
      };

      const groups = getUserGroupsSync(mockUser as any);
      expect(groups).toEqual(['Analysts']);
    });

    test('returns empty array for no user', () => {
      const groups = getUserGroupsSync();
      expect(groups).toEqual([]);
    });

    test('handles missing login ID gracefully', () => {
      const mockUser = {
        signInDetails: {},
        username: 'user',
      };

      const groups = getUserGroupsSync(mockUser as any);
      expect(groups).toEqual([]);
    });
  });

  describe('isAdmin', () => {
    test('returns true for admin groups', () => {
      expect(isAdmin(['Admins'])).toBe(true);
      expect(isAdmin(['Analysts', 'Admins'])).toBe(true);
    });

    test('returns false for non-admin groups', () => {
      expect(isAdmin(['Analysts'])).toBe(false);
      expect(isAdmin(['CustomGroup'])).toBe(false);
      expect(isAdmin([])).toBe(false);
    });
  });

  describe('isAnalyst', () => {
    test('returns true for analyst groups', () => {
      expect(isAnalyst(['Analysts'])).toBe(true);
      expect(isAnalyst(['Analysts', 'CustomGroup'])).toBe(true);
    });

    test('returns true for admin groups (admins are also analysts)', () => {
      expect(isAnalyst(['Admins'])).toBe(true);
      expect(isAnalyst(['Admins', 'Analysts'])).toBe(true);
    });

    test('returns false for non-analyst/admin groups', () => {
      expect(isAnalyst(['CustomGroup'])).toBe(false);
      expect(isAnalyst([])).toBe(false);
    });
  });

  describe('getUserDisplayName', () => {
    test('returns email from signInDetails', () => {
      const mockUser = {
        signInDetails: { loginId: 'test@example.com' },
        username: 'testuser',
      };

      const displayName = getUserDisplayName(mockUser as any);
      expect(displayName).toBe('test@example.com');
    });

    test('falls back to username when no email', () => {
      const mockUser = {
        signInDetails: {},
        username: 'testuser',
      };

      const displayName = getUserDisplayName(mockUser as any);
      expect(displayName).toBe('testuser');
    });

    test('returns default for no user', () => {
      const displayName = getUserDisplayName();
      expect(displayName).toBe('Unknown User');
    });

    test('returns default for empty user data', () => {
      const mockUser = {
        signInDetails: {},
        username: '',
      };

      const displayName = getUserDisplayName(mockUser as any);
      expect(displayName).toBe('User');
    });
  });

  describe('formatUserRole', () => {
    test('returns Administrator for admin groups', () => {
      expect(formatUserRole(['Admins'])).toBe('Administrator');
      expect(formatUserRole(['Analysts', 'Admins'])).toBe('Administrator');
    });

    test('returns Security Analyst for analyst groups', () => {
      expect(formatUserRole(['Analysts'])).toBe('Security Analyst');
    });

    test('returns first group for custom groups', () => {
      expect(formatUserRole(['CustomGroup'])).toBe('CustomGroup');
      expect(formatUserRole(['Group1', 'Group2'])).toBe('Group1');
    });

    test('returns default for empty groups', () => {
      expect(formatUserRole([])).toBe('User');
    });
  });
});