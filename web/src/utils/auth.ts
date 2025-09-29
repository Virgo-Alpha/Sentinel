import React from 'react';
import { AuthUser, fetchAuthSession } from 'aws-amplify/auth';

export interface UserGroups {
  groups: string[];
  isAdmin: boolean;
  isAnalyst: boolean;
}

/**
 * Extract user groups from Cognito JWT token
 * Groups are stored in the 'cognito:groups' claim of the ID token
 */
export const getUserGroups = async (user?: AuthUser): Promise<string[]> => {
  if (!user) return [];
  
  try {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken;
    
    if (idToken) {
      // Decode JWT payload to get groups
      const payload = JSON.parse(atob(idToken.toString().split('.')[1]));
      const groups = payload['cognito:groups'] || [];
      return Array.isArray(groups) ? groups : [];
    }
    
    // Fallback: extract from user attributes if available
    const email = user.signInDetails?.loginId || '';
    if (email.includes('admin')) {
      return ['Admins'];
    }
    
    return ['Analysts']; // Default to analyst role
  } catch (error) {
    console.error('Error extracting user groups:', error);
    return ['Analysts']; // Default to analyst role
  }
};

/**
 * Get user groups synchronously (for components that can't use async)
 * This is a simplified version that doesn't decode JWT
 */
export const getUserGroupsSync = (user?: AuthUser): string[] => {
  if (!user?.signInDetails?.loginId) return [];
  
  try {
    // Simple heuristic based on email for immediate UI updates
    const email = user.signInDetails.loginId;
    if (email.includes('admin')) {
      return ['Admins'];
    }
    return ['Analysts'];
  } catch (error) {
    console.error('Error extracting user groups:', error);
    return ['Analysts'];
  }
};

export const isAdmin = (groups: string[]): boolean => {
  return groups.includes('Admins');
};

export const isAnalyst = (groups: string[]): boolean => {
  return groups.includes('Analysts') || groups.includes('Admins');
};

export const getUserDisplayName = (user?: AuthUser): string => {
  if (!user) return 'Unknown User';
  
  // Try to get name from user attributes
  const email = user.signInDetails?.loginId || '';
  const username = user.username || '';
  
  // Return email or username as display name
  return email || username || 'User';
};

export const formatUserRole = (groups: string[]): string => {
  if (groups.length === 0) return 'User';
  
  // Return the highest privilege role
  if (groups.includes('Admins')) return 'Administrator';
  if (groups.includes('Analysts')) return 'Security Analyst';
  
  return groups[0] || 'User';
};

/**
 * Hook for getting user groups with proper async handling
 */
export const useUserGroups = (user?: AuthUser): UserGroups => {
  const [groups, setGroups] = React.useState<string[]>([]);
  
  React.useEffect(() => {
    if (user) {
      getUserGroups(user).then(setGroups);
    }
  }, [user]);
  
  return {
    groups,
    isAdmin: isAdmin(groups),
    isAnalyst: isAnalyst(groups),
  };
};

