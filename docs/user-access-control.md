# Sentinel User Access Control Guide

This guide covers user management, role-based access control, and security procedures for the Sentinel system.

## User Roles and Permissions

### Security Analyst
**Permissions:**
- View and review articles
- Add comments and make relevancy decisions
- Generate basic reports
- Access dashboard and search functionality

**Restrictions:**
- Cannot manage other users
- Cannot modify system configuration
- Limited to standard reporting features

### Security Manager  
**Permissions:**
- All Security Analyst permissions
- Manage team users (create, modify, deactivate)
- Generate advanced reports and analytics
- Configure notification settings
- Access user activity logs

**Restrictions:**
- Cannot modify system infrastructure
- Cannot change global system settings

### Administrator
**Permissions:**
- All Security Manager permissions
- Full system configuration access
- Infrastructure management
- Global settings modification
- Audit log access
- Integration management

## User Management Procedures

### Creating New Users
```bash
# Create user account
aws cognito-idp admin-create-user \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com \
    --user-attributes Name=email,Value=user@company.com \
    --temporary-password TempPass123! \
    --message-action SUPPRESS

# Assign to appropriate group
aws cognito-idp admin-add-user-to-group \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com \
    --group-name SecurityAnalysts
```

### Modifying User Access
```bash
# Change user group membership
aws cognito-idp admin-remove-user-from-group \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com \
    --group-name SecurityAnalysts

aws cognito-idp admin-add-user-to-group \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com \
    --group-name SecurityManagers
```

### Deactivating Users
```bash
# Disable user account
aws cognito-idp admin-disable-user \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com

# Delete user account (if required)
aws cognito-idp admin-delete-user \
    --user-pool-id us-east-1_XXXXXXXXX \
    --username user@company.com
```

## Security Best Practices

### Multi-Factor Authentication
- Enable MFA for all users
- Use TOTP authenticator apps
- Provide backup recovery codes
- Regular MFA device rotation

### Password Policies
- Minimum 12 characters
- Require uppercase, lowercase, numbers, symbols
- Password expiration every 90 days
- Prevent password reuse (last 12 passwords)

### Access Reviews
- Monthly user access reviews
- Quarterly permission audits
- Annual role-based access certification
- Immediate access revocation for terminated users