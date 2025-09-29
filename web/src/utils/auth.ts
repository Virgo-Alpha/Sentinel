import { AuthUser } from 'aws-amplify/auth';

export const getUserGroups = (user?: AuthUser): string[] => {
  if (!user?.signInDetails?.loginId) return [];
  
  try {
    // In a real implementation, you would decode the JWT token to get groups
    // For now, we'll extract from user attributes or assume default
    const groups = user.signInDetails?.loginId?.includes('admin') ? ['Admins'] : ['Analysts'];
    return groups;
  } catch (error) {
    console.error('Error extracting user groups:', error);
    return ['Analysts']; // Default to analyst role
  }
};

export const isAdmin = (user?: AuthUser): boolean => {
  const groups = getUserGroups(user);
  return groups.includes('Admins');
};

export const isAnalyst = (user?: AuthUser): boolean => {
  const groups = getUserGroups(user);
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

export const formatUserRole = (user?: AuthUser): string => {
  const groups = getUserGroups(user);
  if (groups.length === 0) return 'User';
  
  // Return the highest privilege role
  if (groups.includes('Admins')) return 'Administrator';
  if (groups.includes('Analysts')) return 'Security Analyst';
  
  return groups[0] || 'User';
};