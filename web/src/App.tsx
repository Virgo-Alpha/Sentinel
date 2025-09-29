import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Amplify } from 'aws-amplify';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import './App.css';

// Components
import AppRoutes from './routes/AppRoutes';
import Login from './pages/Login';

// Configure Amplify
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_USER_POOL_ID || '',
      userPoolClientId: process.env.REACT_APP_USER_POOL_WEB_CLIENT_ID || '',
      identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID || '',
      loginWith: {
        email: true,
        username: false,
      },
      signUpVerificationMethod: 'code' as const,
      userAttributes: {
        email: {
          required: true,
        },
        given_name: {
          required: false,
        },
        family_name: {
          required: false,
        },
      },
      allowGuestAccess: false,
      passwordFormat: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireNumbers: true,
        requireSpecialCharacters: true,
      },
    },
  },
  API: {
    REST: {
      SentinelAPI: {
        endpoint: process.env.REACT_APP_API_GATEWAY_URL || '',
        region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
      },
    },
  },
};

Amplify.configure(amplifyConfig);

const App: React.FC = () => {
  return (
    <Authenticator.Provider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={
              <Authenticator hideSignUp={true}>
                {({ signOut, user }) => (
                  <AppRoutes user={user} signOut={signOut} />
                )}
              </Authenticator>
            } />
          </Routes>
        </div>
      </Router>
    </Authenticator.Provider>
  );
};

export default App;