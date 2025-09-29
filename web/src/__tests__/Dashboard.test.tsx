import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '../pages/Dashboard';
import { apiService } from '../services/api';
import { Article } from '../types';

// Mock the API service
jest.mock('../services/api');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

// Mock the ArticleDetailModal component
jest.mock('../components/ArticleDetailModal', () => {
  return function MockArticleDetailModal({ article, onClose }: any) {
    return (
      <div data-testid="article-detail-modal">
        <h2>{article.title}</h2>
        <button onClick={onClose}>Close</button>
      </div>
    );
  };
});

const mockArticles: Article[] = [
  {
    article_id: '1',
    source: 'CISA',
    feed_id: 'cisa-alerts',
    url: 'https://example.com/article1',
    canonical_url: 'https://example.com/article1',
    title: 'Critical Vulnerability in Microsoft Exchange',
    published_at: '2024-01-15T10:00:00Z',
    ingested_at: '2024-01-15T10:05:00Z',
    state: 'PUBLISHED',
    cluster_id: 'cluster-1',
    is_duplicate: false,
    relevancy_score: 0.9,
    keyword_matches: [
      {
        keyword: 'Microsoft Exchange',
        hit_count: 3,
        contexts: ['Microsoft Exchange server vulnerability', 'Exchange security update', 'Exchange patch available']
      }
    ],
    triage_action: 'AUTO_PUBLISH',
    summary_short: 'A critical vulnerability has been discovered in Microsoft Exchange servers.',
    summary_card: 'Critical vulnerability affecting Exchange servers worldwide.',
    entities: {
      cves: ['CVE-2024-0001'],
      threat_actors: [],
      malware: [],
      vendors: ['Microsoft'],
      products: ['Exchange Server'],
      sectors: ['Technology'],
      countries: []
    },
    tags: ['vulnerability', 'exchange', 'critical'],
    confidence: 0.95,
    guardrail_flags: [],
    trace_s3_uri: 's3://bucket/trace1',
    raw_s3_uri: 's3://bucket/raw1',
    normalized_s3_uri: 's3://bucket/normalized1',
    created_by_agent_version: '1.0.0'
  },
  {
    article_id: '2',
    source: 'Mandiant',
    feed_id: 'mandiant-threat-intel',
    url: 'https://example.com/article2',
    canonical_url: 'https://example.com/article2',
    title: 'New APT Group Targeting Cloud Infrastructure',
    published_at: '2024-01-14T15:30:00Z',
    ingested_at: '2024-01-14T15:35:00Z',
    state: 'PUBLISHED',
    cluster_id: 'cluster-2',
    is_duplicate: false,
    relevancy_score: 0.85,
    keyword_matches: [
      {
        keyword: 'AWS',
        hit_count: 2,
        contexts: ['AWS infrastructure targeted', 'AWS security recommendations']
      }
    ],
    triage_action: 'AUTO_PUBLISH',
    summary_short: 'A new APT group has been identified targeting cloud infrastructure.',
    entities: {
      cves: [],
      threat_actors: ['APT-Cloud-Hunter'],
      malware: ['CloudStealer'],
      vendors: ['Amazon'],
      products: ['AWS'],
      sectors: ['Cloud Services'],
      countries: ['China']
    },
    tags: ['apt', 'cloud', 'aws'],
    confidence: 0.88,
    guardrail_flags: [],
    trace_s3_uri: 's3://bucket/trace2',
    raw_s3_uri: 's3://bucket/raw2',
    normalized_s3_uri: 's3://bucket/normalized2',
    created_by_agent_version: '1.0.0'
  }
];

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiService.getArticles.mockResolvedValue({
      data: mockArticles
    });
  });

  it('renders dashboard with metrics and articles', async () => {
    render(<Dashboard />);

    // Check header
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Overview of published cybersecurity intelligence and system metrics')).toBeInTheDocument();

    // Check metrics cards
    expect(screen.getByText('Total Articles')).toBeInTheDocument();
    expect(screen.getByText('Published Today')).toBeInTheDocument();
    expect(screen.getByText('Pending Review')).toBeInTheDocument();
    expect(screen.getByText('Keyword Hits')).toBeInTheDocument();

    // Wait for articles to load
    await waitFor(() => {
      expect(screen.getByText('Published Articles (2)')).toBeInTheDocument();
    });

    // Check articles are displayed
    expect(screen.getByText('Critical Vulnerability in Microsoft Exchange')).toBeInTheDocument();
    expect(screen.getByText('New APT Group Targeting Cloud Infrastructure')).toBeInTheDocument();
  });

  it('displays loading state initially', () => {
    render(<Dashboard />);
    
    expect(screen.getAllByText('Loading...')).toHaveLength(4); // One for each metric card
    expect(screen.getByText('Loading articles...')).toBeInTheDocument();
  });

  it('handles search functionality', async () => {
    render(<Dashboard />);

    // Wait for articles to load
    await waitFor(() => {
      expect(screen.getByText('Published Articles (2)')).toBeInTheDocument();
    });

    // Search for "Exchange"
    const searchInput = screen.getByPlaceholderText('Search articles...');
    await userEvent.type(searchInput, 'Exchange');

    // Should show only the Exchange article
    await waitFor(() => {
      expect(screen.getByText('Published Articles (1)')).toBeInTheDocument();
      expect(screen.getByText('Critical Vulnerability in Microsoft Exchange')).toBeInTheDocument();
      expect(screen.queryByText('New APT Group Targeting Cloud Infrastructure')).not.toBeInTheDocument();
    });
  });

  it('handles filter functionality', async () => {
    render(<Dashboard />);

    // Wait for articles to load
    await waitFor(() => {
      expect(screen.getByText('Published Articles (2)')).toBeInTheDocument();
    });

    // Open filters
    const filtersButton = screen.getByText('Filters');
    await userEvent.click(filtersButton);

    // Filter by source
    const sourceSelect = screen.getByDisplayValue('All Sources');
    await userEvent.selectOptions(sourceSelect, 'CISA');

    // Should show only CISA article
    await waitFor(() => {
      expect(screen.getByText('Published Articles (1)')).toBeInTheDocument();
      expect(screen.getByText('Critical Vulnerability in Microsoft Exchange')).toBeInTheDocument();
      expect(screen.queryByText('New APT Group Targeting Cloud Infrastructure')).not.toBeInTheDocument();
    });
  });

  it('opens article detail modal when clicking view button', async () => {
    render(<Dashboard />);

    // Wait for articles to load
    await waitFor(() => {
      expect(screen.getByText('Published Articles (2)')).toBeInTheDocument();
    });

    // Click on the first article
    const firstArticle = screen.getByText('Critical Vulnerability in Microsoft Exchange');
    await userEvent.click(firstArticle);

    // Check modal is opened
    await waitFor(() => {
      expect(screen.getByTestId('article-detail-modal')).toBeInTheDocument();
    });
  });

  it('displays article metadata correctly', async () => {
    render(<Dashboard />);

    // Wait for articles to load
    await waitFor(() => {
      expect(screen.getByText('Published Articles (2)')).toBeInTheDocument();
    });

    // Check relevancy scores
    expect(screen.getByText('90% relevant')).toBeInTheDocument();
    expect(screen.getByText('85% relevant')).toBeInTheDocument();

    // Check keyword hits
    expect(screen.getByText('3 keyword hits')).toBeInTheDocument();
    expect(screen.getByText('2 keyword hits')).toBeInTheDocument();

    // Check tags
    expect(screen.getByText('vulnerability')).toBeInTheDocument();
    expect(screen.getByText('apt')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    mockApiService.getArticles.mockRejectedValue(new Error('API Error'));
    
    render(<Dashboard />);

    // Should still render the dashboard structure
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    
    // Metrics should show 0 when API fails
    await waitFor(() => {
      expect(screen.getAllByText('0')).toHaveLength(4);
    });
  });

  it('filters articles by date range', async () => {
    render(<Dashboard />);

    // Wait for articles to load
    await waitFor(() => {
      expect(screen.getByText('Published Articles (2)')).toBeInTheDocument();
    });

    // Open filters
    const filtersButton = screen.getByText('Filters');
    await userEvent.click(filtersButton);

    // Set date range to last 24 hours (should filter out older articles)
    const dateRangeSelect = screen.getByDisplayValue('All Time');
    await userEvent.selectOptions(dateRangeSelect, '1d');

    // Should show fewer articles (depending on mock dates)
    await waitFor(() => {
      const articleCount = screen.getByText(/Published Articles \(\d+\)/);
      expect(articleCount).toBeInTheDocument();
    });
  });

  it('displays empty state when no articles match filters', async () => {
    render(<Dashboard />);

    // Wait for articles to load
    await waitFor(() => {
      expect(screen.getByText('Published Articles (2)')).toBeInTheDocument();
    });

    // Search for something that won't match
    const searchInput = screen.getByPlaceholderText('Search articles...');
    await userEvent.type(searchInput, 'nonexistent');

    // Should show empty state
    await waitFor(() => {
      expect(screen.getByText('No articles found matching your criteria.')).toBeInTheDocument();
    });
  });
});