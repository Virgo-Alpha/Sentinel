# Sentinel Web Application

The Sentinel web application is a React/TypeScript frontend for the cybersecurity intelligence triage platform. It provides authentication, dashboard, review queue, and chat interfaces for security analysts and administrators.

## Features

- **Authentication**: AWS Cognito integration with user groups (Analysts, Admins)
- **Dashboard**: View published cybersecurity intelligence articles
- **Review Queue**: Human-in-the-loop review interface for flagged content
- **Analyst Assistant**: Chat interface for natural language queries
- **Responsive Design**: Mobile-friendly interface using Tailwind CSS

## Prerequisites

- Node.js 18+ and npm
- AWS Cognito User Pool configured with user groups
- API Gateway endpoint for backend communication

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env.local
   ```
   
   Update `.env.local` with your AWS configuration:
   ```
   REACT_APP_AWS_REGION=us-east-1
   REACT_APP_USER_POOL_ID=us-east-1_XXXXXXXXX
   REACT_APP_USER_POOL_WEB_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
   REACT_APP_IDENTITY_POOL_ID=us-east-1:XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
   REACT_APP_API_GATEWAY_URL=https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod
   ```

3. **Start development server**:
   ```bash
   npm start
   ```

4. **Run tests**:
   ```bash
   npm test
   ```

5. **Build for production**:
   ```bash
   npm run build
   ```

## Authentication

The application uses AWS Amplify with Cognito for authentication. Users must be assigned to one of two groups:

- **Analysts**: Can access dashboard, review queue, and chat interface
- **Admins**: Full access to all features (inherits analyst permissions)

### User Group Configuration

User groups are extracted from the JWT token's `cognito:groups` claim. The application handles group-based permissions automatically.

## Architecture

```
src/
├── components/          # Reusable UI components
│   └── Layout.tsx      # Main application layout
├── pages/              # Page components
│   ├── Dashboard.tsx   # Published articles dashboard
│   ├── ReviewQueue.tsx # Review interface
│   ├── Chat.tsx        # Analyst assistant chat
│   └── Login.tsx       # Authentication page
├── routes/             # Routing configuration
│   └── AppRoutes.tsx   # Protected route definitions
├── services/           # API and external services
│   └── api.ts          # API service layer
├── utils/              # Utility functions
│   ├── auth.ts         # Authentication utilities
│   └── formatting.ts   # Data formatting utilities
└── __tests__/          # Test files
```

## API Integration

The application communicates with the backend through API Gateway. All requests include JWT authentication headers automatically.

### Available Endpoints

- `GET /articles` - Fetch articles with filtering
- `POST /chat` - Send messages to Analyst Assistant
- `POST /query` - Query knowledge base
- `POST /review` - Submit review decisions
- `GET /comments` - Fetch article comments
- `POST /comments` - Create new comments

## Testing

The application includes comprehensive tests:

- **Unit Tests**: Component and utility function tests
- **Integration Tests**: Authentication flow and API integration
- **E2E Tests**: Full user workflow testing

Run tests with:
```bash
npm test                    # Interactive mode
npm test -- --coverage     # With coverage report
npm test -- --watchAll=false  # Single run
```

## Deployment

### AWS Amplify Deployment

1. **Connect repository** to AWS Amplify
2. **Configure build settings** using the included `amplify.yml`
3. **Set environment variables** in Amplify console
4. **Deploy** automatically on code changes

### Manual Deployment

1. **Build the application**:
   ```bash
   npm run build
   ```

2. **Deploy to S3** or other static hosting:
   ```bash
   aws s3 sync build/ s3://your-bucket-name --delete
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REACT_APP_AWS_REGION` | AWS region | Yes |
| `REACT_APP_USER_POOL_ID` | Cognito User Pool ID | Yes |
| `REACT_APP_USER_POOL_WEB_CLIENT_ID` | Cognito App Client ID | Yes |
| `REACT_APP_IDENTITY_POOL_ID` | Cognito Identity Pool ID | Yes |
| `REACT_APP_API_GATEWAY_URL` | Backend API endpoint | Yes |
| `REACT_APP_PROJECT_NAME` | Project identifier | No |
| `REACT_APP_ENVIRONMENT` | Environment name | No |
| `REACT_APP_ENABLE_CHAT` | Enable chat interface | No |
| `REACT_APP_ENABLE_REVIEW` | Enable review queue | No |
| `REACT_APP_ENABLE_EXPORT` | Enable data export | No |

## Troubleshooting

### Authentication Issues

1. **Verify Cognito configuration** in AWS console
2. **Check user group assignments** for test users
3. **Validate JWT token** using jwt.io
4. **Review browser console** for authentication errors

### API Connection Issues

1. **Verify API Gateway endpoint** is accessible
2. **Check CORS configuration** on backend
3. **Validate authentication headers** in network tab
4. **Review API Gateway logs** for errors

### Build Issues

1. **Clear node_modules** and reinstall:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Check TypeScript errors**:
   ```bash
   npx tsc --noEmit
   ```

3. **Verify environment variables** are set correctly

## Contributing

1. **Follow TypeScript best practices**
2. **Write tests for new features**
3. **Use Tailwind CSS for styling**
4. **Follow existing code patterns**
5. **Update documentation as needed**

## Security Considerations

- All API requests include authentication headers
- Sensitive data is not stored in localStorage
- User sessions expire automatically
- HTTPS is enforced in production
- Content Security Policy headers are configured