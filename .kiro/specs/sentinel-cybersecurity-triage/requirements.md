# Requirements Document

## Introduction

Sentinel is an AWS-native, multi-agent cybersecurity news triage and publishing system that autonomously ingests, processes, and publishes cybersecurity intelligence from RSS feeds and news sources. The system reduces analyst workload by automatically deduplicating content, extracting relevant entities, and intelligently routing items for human review or auto-publication. It features natural language querying capabilities and demonstrates advanced agentic patterns including planning, tool use, agent-to-agent collaboration, and human-in-the-loop workflows.

## Requirements

### Requirement 1: Automated Content Ingestion

**User Story:** As a security analyst, I want the system to automatically fetch and normalize cybersecurity news from configured RSS feeds and sources, so that I don't have to manually monitor multiple information sources.

#### Acceptance Criteria

1. WHEN a scheduled ingestion event triggers THEN the system SHALL fetch content from all configured RSS feeds including ANSSI, CISA, NCSC, Microsoft Security, Google TAG, Mandiant, CrowdStrike, NCC Group, SANS ISC, DarkReading, BleepingComputer, The Hacker News, SecurityWeek, Krebs on Security, Leak-Lookup, Cybernews, ENISA, and Cybersecurity Hub
2. WHEN content is fetched THEN the system SHALL normalize HTML to clean text and extract metadata including title, author, publication time, and canonical URL
3. WHEN content is processed THEN the system SHALL store raw and normalized payloads in S3 with content hash and create a DynamoDB item with state=INGESTED
4. WHEN feeds are categorized THEN the system SHALL classify them by type: Advisories, Alerts, Vulnerabilities, Vendor, Threat Intel, Research, News, Data Breach, and Policy
5. IF a feed is temporarily unavailable THEN the system SHALL implement backoff retry logic and continue processing other feeds
6. WHEN ingestion completes THEN the system SHALL maintain audit logs with correlation IDs for observability

### Requirement 2: Intelligent Relevance Assessment and Keyword Targeting

**User Story:** As a content lead, I want the system to automatically determine if ingested content is relevant to cybersecurity topics and specifically identify mentions of our target technologies and vendors, so that analysts only review pertinent information that affects our technology stack.

#### Acceptance Criteria

1. WHEN an article is ingested THEN the system SHALL use LLM-based evaluation to determine relevance to defined cybersecurity topics (breaches, CVEs, malware, threat actors)
2. WHEN content is evaluated THEN the system SHALL scan for specific target keywords including: Azure/Entra/Microsoft 365, Amazon Web Services (AWS), Google Workspace, Mimecast, Fortinet Products, CloudFlare, DarkTrace, SentinelOne, ThreatLocker, Digital Guardian, Varonis, Symantec, Moodle, Blockmark Registry, Pervade Software, Rizikon, Jamf Pro, Brevo, TextLocal, Strata Insight, Tenable, N-able Mail Assure, Cylance, CyberArk, Checkpoint Firewall, BlackBerry UEM, Oracle HCM, Oracle FlexCUBE, Olympic Banking System, Cisco Devices (Nexus9000, C3850, 9300), Citrix Products (StoreFront, Xen Desktop, ADC, License Server), LexisNexis Risk Solutions, and Nutanix HCI
3. WHEN keyword matches are found THEN the system SHALL record keyword hit counts and assign higher relevancy scores to articles mentioning target technologies
4. WHEN content is evaluated THEN the system SHALL extract structured entities including CVEs, threat actors, malware families, vendors, products, sectors, and countries with confidence scores
5. IF content is deemed irrelevant AND contains no target keywords THEN the system SHALL mark state=ARCHIVED while maintaining searchability
6. WHEN relevance assessment completes THEN the system SHALL assign relevancy scores between 0 and 1 with keyword matches contributing to higher scores
7. WHEN entities are extracted THEN the system SHALL validate entity formats and flag potential hallucinations

### Requirement 3: Advanced Deduplication

**User Story:** As a security analyst, I want the system to identify and cluster duplicate or near-duplicate articles, so that I don't waste time reviewing the same information multiple times.

#### Acceptance Criteria

1. WHEN an article is processed THEN the system SHALL perform heuristic deduplication using canonical URL, normalized title, and source domain
2. WHEN heuristic deduplication is insufficient THEN the system SHALL use semantic analysis with Bedrock embeddings and OpenSearch k-NN search
3. WHEN duplicates are identified THEN the system SHALL assign cluster_id and mark items as is_duplicate=true with reference to canonical item
4. WHEN deduplication completes THEN the system SHALL maintain one canonical item per cluster with duplicates referenced via duplicate_of field
5. IF similarity threshold is met and older item exists THEN the system SHALL mark newer item as duplicate

### Requirement 4: Automated Triage and Classification

**User Story:** As a security analyst, I want the system to automatically categorize and prioritize articles based on their content and potential impact, so that I can focus on the most critical information first.

#### Acceptance Criteria

1. WHEN an article passes relevance checks THEN the system SHALL assign one of three actions: AUTO_PUBLISH, REVIEW, or DROP
2. WHEN assigning actions THEN the system SHALL consider relevancy score, quality assessment, guardrail compliance, and duplication status
3. WHEN articles are triaged THEN the system SHALL assign appropriate tags from the defined topic taxonomy
4. WHEN severity assessment is needed THEN the system SHALL use CVSS scores when available or LLM-estimated impact scores
5. IF an article meets auto-publish criteria THEN the system SHALL route directly to publication without human intervention

### Requirement 5: Multi-Style Content Summarization

**User Story:** As a security analyst, I want the system to generate both detailed analyst cards and executive summaries, so that different stakeholders can quickly understand the key information.

#### Acceptance Criteria

1. WHEN an article is processed THEN the system SHALL generate an analyst card with bullets covering what happened, who/what was affected, indicators, and source links
2. WHEN executive summary is needed THEN the system SHALL create a concise 2-line summary suitable for leadership consumption
3. WHEN summarization completes THEN the system SHALL implement reflection steps to validate completeness using checklists
4. WHEN reflection validation occurs THEN the system SHALL verify CVE extraction, source citation, and absence of PII
5. IF summarization quality is insufficient THEN the system SHALL route item to human review queue

### Requirement 6: Comprehensive Guardrails and Quality Assurance

**User Story:** As a platform admin, I want the system to implement robust guardrails to prevent publication of inaccurate, sensitive, or inappropriate content, so that our intelligence feed maintains high quality and security standards.

#### Acceptance Criteria

1. WHEN content is processed THEN the system SHALL validate all outputs against defined JSON schemas
2. WHEN CVE references are detected THEN the system SHALL validate CVE format patterns and flag potential hallucinations
3. WHEN content contains sensitive information THEN the system SHALL detect and redact PII, credentials, and other sensitive data
4. WHEN content analysis occurs THEN the system SHALL check for banned terms, bias, and sensationalism using conservative thresholds
5. IF any guardrail violation is detected THEN the system SHALL route item to state=REVIEW with specific reason codes

### Requirement 7: Intelligent Alert and Publishing System

**User Story:** As a security analyst, I want to receive timely notifications about published intelligence and items requiring review, so that I can stay informed and take action when needed.

#### Acceptance Criteria

1. WHEN an item receives AUTO_PUBLISH action THEN the system SHALL write to DynamoDB PublishedItems and push to Amplify dashboard
2. WHEN items require human review THEN the system SHALL queue for reviewers and send SES notifications
3. WHEN publishing occurs THEN the system SHALL maintain complete decision traces including tool calls and LLM rationales
4. WHEN digest schedules trigger THEN the system SHALL send configurable email summaries via SES
5. WHEN alerts are sent THEN the system SHALL track delivery status and provide escalation paths

### Requirement 8: Human-in-the-Loop Review Workflow

**User Story:** As a security analyst, I want to review flagged items, approve or reject publications, and add commentary, so that I maintain control over what intelligence gets published.

#### Acceptance Criteria

1. WHEN accessing the review queue THEN the system SHALL display items requiring human review with full context and decision rationale
2. WHEN reviewing items THEN the system SHALL allow analysts to approve, reject, edit tags/summaries, and add commentary
3. WHEN decisions are made THEN the system SHALL update item status and trigger appropriate downstream actions
4. WHEN commentary is added THEN the system SHALL store comments in DynamoDB with author attribution and timestamps
5. WHEN feedback is provided THEN the system SHALL capture thumbs-up/down ratings for continuous improvement

### Requirement 9: Natural Language Query Interface with Keyword Analysis

**User Story:** As a security analyst, I want to query the intelligence database using natural language and generate reports with keyword analysis, so that I can quickly find relevant information and export findings in structured formats.

#### Acceptance Criteria

1. WHEN a natural language query is submitted THEN the Analyst Assistant Agent SHALL translate it to appropriate database queries
2. WHEN queries are processed THEN the system SHALL search across DynamoDB and OpenSearch indexes with proper filtering including keyword-based searches
3. WHEN results are returned THEN the system SHALL provide source citations, links to original articles, keyword hit counts, and match descriptions
4. WHEN complex queries are made THEN the system SHALL support time ranges, entity filters, topic-based searches, and specific keyword filtering
5. WHEN report generation is requested THEN the system SHALL export results in XLSX format with columns for article title, link, date, keyword, keyword hit count, and description
6. WHEN query results are displayed THEN the system SHALL sort articles by date in descending order and allow users to add commentary and provide feedback
7. WHEN deep research is requested THEN the system SHALL perform comprehensive analysis across all configured feeds for specified keywords and time periods

### Requirement 10: Comprehensive Memory and State Management

**User Story:** As a system administrator, I want the system to maintain appropriate short-term and long-term memory for agent interactions and decision history, so that the system can learn and improve over time.

#### Acceptance Criteria

1. WHEN chat sessions occur THEN the system SHALL maintain short-term memory for up to 60 days with automatic TTL cleanup
2. WHEN decisions are made THEN the system SHALL store long-term memory including published cards, entities, decisions, and feedback
3. WHEN agents collaborate THEN the system SHALL maintain A2A memory for duplicate rationale and cross-agent context
4. WHEN memory is accessed THEN the system SHALL provide correlation IDs for tracing decision chains
5. WHEN memory limits are reached THEN the system SHALL implement appropriate cleanup and archival strategies

### Requirement 11: Security and Compliance

**User Story:** As a platform admin, I want the system to implement comprehensive security controls and maintain audit trails, so that we meet enterprise security requirements and can demonstrate compliance.

#### Acceptance Criteria

1. WHEN users access the system THEN authentication SHALL be handled via Cognito with appropriate user groups and permissions
2. WHEN data is stored THEN the system SHALL use KMS encryption for S3, DynamoDB, and OpenSearch data at rest
3. WHEN network communication occurs THEN the system SHALL use VPC endpoints for Bedrock and OpenSearch access
4. WHEN decisions are made THEN the system SHALL maintain complete audit trails with tool calls, prompts, model IDs, and rationales
5. WHEN sensitive data is processed THEN the system SHALL implement least-privilege IAM policies and WAF protection

### Requirement 12: Performance and Reliability

**User Story:** As a platform admin, I want the system to meet performance targets and handle failures gracefully, so that analysts can rely on timely and consistent intelligence delivery.

#### Acceptance Criteria

1. WHEN processing articles THEN the system SHALL achieve median end-to-end latency of ≤5 minutes from RSS ingestion to dashboard publication
2. WHEN chat queries are made THEN the system SHALL respond within 2 seconds for cached embeddings
3. WHEN failures occur THEN the system SHALL implement idempotent operations with SQS buffering and retry logic
4. WHEN errors are encountered THEN the system SHALL route failed items to dead letter queues with appropriate alerting
5. WHEN system load varies THEN the system SHALL implement autoscaling with configurable cost caps

### Requirement 13: Feed Configuration and Keyword Management

**User Story:** As a platform admin, I want to configure RSS feeds and manage target keywords through a centralized system, so that I can easily update monitoring sources and target technologies without code changes.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL load feed configurations from a structured data source containing feed names, URLs, and categories
2. WHEN feeds are configured THEN the system SHALL support the following categories: Advisories, Alerts, Vulnerabilities, Vendor, Threat Intel, Research, News, Data Breach, and Policy
3. WHEN keyword lists are updated THEN the system SHALL reload target keywords without requiring system restart
4. WHEN new feeds are added THEN the system SHALL automatically begin monitoring them on the next scheduled ingestion cycle
5. WHEN feed health is monitored THEN the system SHALL track successful/failed fetch attempts per feed and alert on persistent failures
6. WHEN keyword analysis is performed THEN the system SHALL maintain statistics on keyword hit rates and trending topics
7. WHEN configuration changes occur THEN the system SHALL maintain audit logs of feed and keyword modifications

### Requirement 14: Observability and Monitoring

**User Story:** As a platform admin, I want comprehensive monitoring and observability into system performance and agent behavior, so that I can troubleshoot issues and optimize operations.

#### Acceptance Criteria

1. WHEN system operates THEN CloudWatch dashboards SHALL display ingest rates, relevancy rates, deduplication rates, publish/review ratios, and keyword hit statistics
2. WHEN requests are processed THEN X-Ray SHALL provide end-to-end traces with agent tool spans and correlation IDs
3. WHEN failures occur THEN the system SHALL trigger DLQ alarms with email/Slack notifications to operations teams
4. WHEN experiments run THEN the system SHALL support A/B testing of prompts with precision and latency comparisons
5. WHEN costs accumulate THEN the system SHALL provide cost tracking and alerting with per-component breakdown
6. WHEN keyword analysis occurs THEN the system SHALL track trending keywords, hit rates per feed, and generate periodic keyword effectiveness reports