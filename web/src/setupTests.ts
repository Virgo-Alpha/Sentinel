// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock environment variables
process.env.REACT_APP_AWS_REGION = 'us-east-1';
process.env.REACT_APP_USER_POOL_ID = 'us-east-1_test123';
process.env.REACT_APP_USER_POOL_WEB_CLIENT_ID = 'test-client-id';
process.env.REACT_APP_IDENTITY_POOL_ID = 'us-east-1:test-identity-pool';
process.env.REACT_APP_API_GATEWAY_URL = 'https://api.example.com';
process.env.REACT_APP_PROJECT_NAME = 'sentinel';

// Mock console.error to reduce noise in tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is no longer supported')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});