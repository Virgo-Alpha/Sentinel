import React from 'react';
import { Navigate } from 'react-router-dom';
import { Authenticator, useAuthenticator } from '@aws-amplify/ui-react';

const Login: React.FC = () => {
  const { authStatus } = useAuthenticator((context) => [context.authStatus]);

  if (authStatus === 'authenticated') {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sentinel
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Cybersecurity Intelligence Triage Platform
          </p>
        </div>
        <div className="bg-white py-8 px-6 shadow rounded-lg">
          <Authenticator hideSignUp={true}>
            {({ signOut, user }) => (
              <Navigate to="/dashboard" replace />
            )}
          </Authenticator>
        </div>
      </div>
    </div>
  );
};

export default Login;