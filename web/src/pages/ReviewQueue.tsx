import React from 'react';

const ReviewQueue: React.FC = () => {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
        <p className="mt-2 text-gray-600">
          Articles requiring human review and approval
        </p>
      </div>

      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="text-center py-8">
            <p className="text-gray-500">
              Review queue functionality will be implemented in task 9.2
            </p>
            <p className="text-sm text-gray-400 mt-2">
              This will include approval/rejection controls, article details, and comment system
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewQueue;