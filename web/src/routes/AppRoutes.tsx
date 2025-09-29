import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthUser } from 'aws-amplify/auth';

// Components
import Layout from '../components/Layout';
import Dashboard from '../pages/Dashboard';
import ReviewQueue from '../pages/ReviewQueue';
import Chat from '../pages/Chat';

interface AppRoutesProps {
  user?: AuthUser;
  signOut?: () => void;
}

const AppRoutes: React.FC<AppRoutesProps> = ({ user, signOut }) => {
  return (
    <Layout user={user} signOut={signOut}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/review" element={<ReviewQueue />} />
        <Route path="/chat" element={<Chat />} />
        {/* Catch all route - redirect to dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
};

export default AppRoutes;