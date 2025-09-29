import { getUserGroupsSync, isAdmin, isAnalyst, getUserDisplayName, formatUserRole } from '../utils/auth';
import { formatDate, formatRelativeTime, getStatusColor, getStatusText } from '../utils/formatting';
import { AuthUser } from 'aws-amplify/auth';

describe('Auth Utils', () => {
  const mockUser: Partial<AuthUser> = {
    signInDetails: {
      loginId: 'test@example.com',
    },
    username: 'testuser',
  };

  const mockAdminUser: Partial<AuthUser> = {
    signInDetails: {
      loginId: 'admin@example.com',
    },
    username: 'admin',
  };

  describe('getUserGroupsSync', () => {
    test('returns Analysts for regular user', () => {
      const groups = getUserGroupsSync(mockUser as AuthUser);
      expect(groups).toEqual(['Analysts']);
    });

    test('returns Admins for admin user', () => {
      const groups = getUserGroupsSync(mockAdminUser as AuthUser);
      expect(groups).toEqual(['Admins']);
    });

    test('returns empty array for undefined user', () => {
      const groups = getUserGroupsSync(undefined);
      expect(groups).toEqual([]);
    });
  });

  describe('isAdmin', () => {
    test('returns false for regular user', () => {
      const groups = getUserGroupsSync(mockUser as AuthUser);
      expect(isAdmin(groups)).toBe(false);
    });

    test('returns true for admin user', () => {
      const groups = getUserGroupsSync(mockAdminUser as AuthUser);
      expect(isAdmin(groups)).toBe(true);
    });

    test('returns false for undefined user', () => {
      expect(isAdmin([])).toBe(false);
    });
  });

  describe('isAnalyst', () => {
    test('returns true for regular user', () => {
      const groups = getUserGroupsSync(mockUser as AuthUser);
      expect(isAnalyst(groups)).toBe(true);
    });

    test('returns true for admin user (admins are also analysts)', () => {
      const groups = getUserGroupsSync(mockAdminUser as AuthUser);
      expect(isAnalyst(groups)).toBe(true);
    });

    test('returns false for undefined user', () => {
      expect(isAnalyst([])).toBe(false);
    });
  });

  describe('getUserDisplayName', () => {
    test('returns email for user with email', () => {
      expect(getUserDisplayName(mockUser as AuthUser)).toBe('test@example.com');
    });

    test('returns Unknown User for undefined user', () => {
      expect(getUserDisplayName(undefined)).toBe('Unknown User');
    });
  });

  describe('formatUserRole', () => {
    test('returns Security Analyst for regular user', () => {
      const groups = getUserGroupsSync(mockUser as AuthUser);
      expect(formatUserRole(groups)).toBe('Security Analyst');
    });

    test('returns Administrator for admin user', () => {
      const groups = getUserGroupsSync(mockAdminUser as AuthUser);
      expect(formatUserRole(groups)).toBe('Administrator');
    });

    test('returns User for undefined user', () => {
      expect(formatUserRole([])).toBe('User');
    });
  });
});

describe('Formatting Utils', () => {
  describe('formatDate', () => {
    test('formats valid date string', () => {
      const dateString = '2024-01-15T10:30:00Z';
      const formatted = formatDate(dateString);
      expect(formatted).toMatch(/Jan 15, 2024/);
    });

    test('handles invalid date string', () => {
      const formatted = formatDate('invalid-date');
      expect(formatted).toBe('Invalid Date');
    });
  });

  describe('formatRelativeTime', () => {
    test('returns "Just now" for recent time', () => {
      const now = new Date();
      const recent = new Date(now.getTime() - 30000); // 30 seconds ago
      expect(formatRelativeTime(recent.toISOString())).toBe('Just now');
    });

    test('returns minutes for time within an hour', () => {
      const now = new Date();
      const minutes = new Date(now.getTime() - 300000); // 5 minutes ago
      expect(formatRelativeTime(minutes.toISOString())).toBe('5 minutes ago');
    });

    test('returns hours for time within a day', () => {
      const now = new Date();
      const hours = new Date(now.getTime() - 7200000); // 2 hours ago
      expect(formatRelativeTime(hours.toISOString())).toBe('2 hours ago');
    });

    test('handles invalid date string', () => {
      expect(formatRelativeTime('invalid-date')).toBe('Invalid Date');
    });
  });

  describe('getStatusColor', () => {
    test('returns correct color for PUBLISHED', () => {
      expect(getStatusColor('PUBLISHED')).toBe('status-published');
    });

    test('returns correct color for REVIEW', () => {
      expect(getStatusColor('REVIEW')).toBe('status-review');
    });

    test('returns correct color for ARCHIVED', () => {
      expect(getStatusColor('ARCHIVED')).toBe('status-archived');
    });

    test('returns correct color for INGESTED', () => {
      expect(getStatusColor('INGESTED')).toBe('status-ingested');
    });
  });

  describe('getStatusText', () => {
    test('returns correct text for each status', () => {
      expect(getStatusText('PUBLISHED')).toBe('Published');
      expect(getStatusText('REVIEW')).toBe('Under Review');
      expect(getStatusText('ARCHIVED')).toBe('Archived');
      expect(getStatusText('INGESTED')).toBe('Ingested');
      expect(getStatusText('PROCESSED')).toBe('Processed');
    });
  });
});