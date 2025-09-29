# Implementation Plan

- [x] 1. Set up project structure and core configuration

  - Create comprehensive directory structure following recommended Terraform layout (infra/modules/, infra/envs/, src/, config/, docs/)
  - Set up Terraform remote state backend with S3 + DynamoDB locking
  - Define configuration schemas for RSS feeds and target keywords in YAML format
  - Set up Python project with dependencies (boto3, requests, beautifulsoup4, feedparser, etc.) in a virtual env
  - Create shared data models and type definitions for articles, entities, and processing results
  - Configure feature flags for gradual rollout (enable_agents, enable_amplify, enable_opensearch)
  - _Requirements: 1.1, 1.2, 13.1, 13.2_

- [x] 2. Implement feed configuration and keyword management system

  - [x] 2.1 Create feed configuration loader

    - Implement FeedConfig class to load RSS feeds from CSV/JSON configuration
    - Add validation for feed URLs, categories, and fetch intervals
    - Create unit tests for configuration loading and validation
    - _Requirements: 13.1, 13.2, 13.3_

  - [x] 2.2 Implement keyword management system
    - [x] Create KeywordManager class to load and manage target keywords from configuration
    - [x] Implement keyword categorization (cloud platforms, security vendors, enterprise tools)
    - [x] Add fuzzy matching capabilities for keyword variations with Levenshtein distance
    - [x] Implement exact matching with context extraction and confidence scoring
    - [x] Add comprehensive validation for keyword configurations and weights
    - [x] Write unit tests for keyword loading and matching logic
    - [x] Add performance optimization with indexed lookups and caching
    - _Requirements: 2.2, 2.6, 13.3_

- [-] 3. Build core Lambda tools for agent integration

  - [x] 3.1 Implement FeedParser Lambda tool

    - Create Lambda function to parse RSS/Atom feeds using feedparser library
    - Add HTML content normalization and metadata extraction
    - Implement error handling for malformed feeds and network issues
    - Store raw content in S3 with content hashing
    - Write unit tests for feed parsing and content normalization
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 3.2 Implement RelevancyEvaluator Lambda tool

    - Create Lambda function that uses Bedrock to assess content relevance
    - Implement keyword matching with hit counting and context extraction
    - Add entity extraction for CVEs, threat actors, malware, vendors, products
    - Include confidence scoring and rationale generation
    - Write unit tests for relevancy assessment and entity extraction
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.7_

  - [x] 3.3 Implement DedupTool Lambda tool

    - Create Lambda function for multi-layered deduplication
    - Implement heuristic deduplication (URL, title, domain comparison)
    - Add semantic deduplication using Bedrock embeddings and OpenSearch k-NN
    - Include cluster assignment and duplicate relationship management
    - Write unit tests for both heuristic and semantic deduplication
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.4 Implement GuardrailTool Lambda tool

    - Create Lambda function for comprehensive content validation
    - Add JSON schema validation for structured outputs
    - Implement PII detection and sensitive data redaction
    - Include CVE format validation and hallucination detection
    - Add bias and sensationalism filtering
    - Write unit tests for all guardrail validation layers
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 3.5 Implement StorageTool Lambda tool
    - Create Lambda function for DynamoDB and S3 operations
    - Add article creation, updates, and state management
    - Implement batch operations for performance optimization
    - Include data consistency checks and error handling
    - Write unit tests for storage operations and data integrity
    - _Requirements: 1.3, 4.1, 4.2, 4.3, 4.4_

- [x] 4. Create comprehensive Terraform infrastructure for complete deployment

  - [x] 4.1 Build foundational Terraform modules

    - Create network module with VPC, subnets, and VPC endpoints for Bedrock/OpenSearch
    - Build KMS module for encryption keys with proper key policies
    - Implement S3 module with buckets for artifacts, raw content, normalized content, and traces
    - Create DynamoDB module with Articles, Comments, Memory tables and GSIs
    - Build OpenSearch Serverless module with collections, security policies, and access policies
    - Add IAM module with scoped roles for each Lambda function and service
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 12.3_

  - [x] 4.2 Implement Lambda packaging and deployment modules

    - Create Lambda module with archive_file packaging and S3 upload triggers
    - Add hash-based rebuilds for Lambda code changes (pip-compile/poetry.lock triggers)
    - Configure Lambda functions with X-Ray tracing and AWS Powertools
    - Set up parameterized memory/timeout configurations
    - Include VPC configuration for private subnet deployment
    - _Requirements: 1.1, 1.2, 1.3, 14.2_

  - [x] 4.3 Build orchestration and messaging modules

    - Create Step Functions module with state machine for direct Lambda orchestration
    - Implement EventBridge module with scheduled rules per feed category
    - Build SQS module with queues and dead letter queues for error handling
    - Add SES module with verified identities and email templates
    - Configure retry logic, backoff strategies, and compensation paths
    - _Requirements: 1.1, 1.4, 1.5, 7.2, 12.3, 12.4_

  - [x] 4.4 Implement web application and authentication modules

    - Create Cognito module with user pools, groups (Analyst, Admin), and identity providers
    - Build API Gateway module for Analyst Assistant integration
    - Implement Amplify module with app/branch configuration and build settings
    - Add WAF module for web application firewall protection
    - Configure authentication flows and authorization policies
    - _Requirements: 11.1, 11.5, 8.1_

  - [x] 4.5 Set up observability and monitoring modules

    - Create CloudWatch module with dashboards for all key metrics
    - Implement X-Ray module with sampling rules and trace analysis
    - Build alerting module with SNS topics and alarm configurations
    - Add cost tracking and budget alerting capabilities
    - Configure log aggregation and retention policies
    - _Requirements: 14.1, 14.2, 14.5_

  - [x] 4.6 Create environment-specific configurations
    - Build dev environment configuration with reduced resources
    - Create prod environment configuration with full scaling
    - Implement variable files (terraform.tfvars) for each environment
    - Add validation rules and constraint checking
    - Configure environment-specific feature flags and thresholds
    - _Requirements: All infrastructure requirements_

- [x] 5. Develop Strands agent definitions

  - [x] 5.1 Create Ingestor Agent Strands configuration

    - Write Strands YAML configuration for the Ingestor Agent
    - Define agent instructions, model selection, and tool bindings
    - Configure deployment settings for Bedrock AgentCore
    - Add execution role and permission specifications
    - Test agent creation and tool integration locally
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

  - [x] 5.2 Create Analyst Assistant Agent Strands configuration
    - Write Strands YAML configuration for the Analyst Assistant Agent
    - Define conversational instructions and query processing capabilities
    - Configure API integration settings and session management
    - Add tool bindings for knowledge base operations
    - Test agent creation and query processing locally
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [x] 6. Implement query and reporting Lambda tools

  - [x] 6.1 Implement QueryKB Lambda tool

    - Create Lambda function for natural language query processing
    - Add DynamoDB and OpenSearch query translation
    - Implement filtering by date range, keywords, categories, and sources
    - Include result ranking and relevance scoring
    - Write unit tests for query translation and result processing
    - _Requirements: 9.1, 9.2, 9.4_

  - [x] 6.2 Implement report generation functionality
    - Add XLSX export capability with keyword hit analysis
    - Implement result sorting by date in descending order
    - Include columns for title, link, date, keyword, hit count, and description
    - Add batch processing for large result sets
    - Write unit tests for report generation and export
    - _Requirements: 9.5, 9.6, 9.7_

- [x] 7. Build human-in-the-loop Lambda tools

  - [x] 7.1 Implement HumanEscalation Lambda tool

    - Create Lambda function to queue items for human review
    - Add SES notification system for reviewer alerts
    - Implement priority scoring and queue management
    - Include escalation reason tracking and context preservation
    - Write unit tests for escalation logic and notifications
    - _Requirements: 7.2, 8.1, 8.2_

  - [x] 7.2 Implement PublishDecision Lambda tool

    - Create Lambda function for human approval/rejection processing
    - Add state transitions and downstream action triggering
    - Implement audit trail creation for all decisions
    - Include batch decision processing capabilities
    - Write unit tests for decision processing and state management
    - _Requirements: 8.2, 8.3, 8.4_

  - [x] 7.3 Implement CommentaryAPI Lambda tool
    - Create Lambda function for comment creation and management
    - Add threaded discussion support with author attribution
    - Implement comment moderation and visibility controls
    - Include search and filtering capabilities for comments
    - Write unit tests for comment operations and threading
    - _Requirements: 8.3, 8.4_

- [x] 8. Implement agent orchestration with deferral capability

  - [x] 8.1 Create agent shim Lambda for future AgentCore integration

    - Build thin Lambda "agent shim" with same interface as Step Functions expects
    - Implement environment variable toggle (ORCHESTRATOR=direct|agentcore)
    - Add direct Lambda forwarding for initial deployment (enable_agents=false)
    - Include AgentCore InvokeAgent capability for future use (enable_agents=true)
    - Maintain stable tool contracts for seamless agent integration
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

  - [x] 8.2 Prepare Bedrock AgentCore deployment scripts
    - Create deployment scripts for Strands CLI agent deployment
    - Configure CI/CD pipeline integration for agent updates
    - Add agent health checking and rollback capabilities
    - Implement monitoring for agent execution performance
    - Document agent deployment and management procedures
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [-] 9. Create Amplify web application

  - [-] 9.1 Set up Amplify project with authentication

    - Initialize Amplify project with React/TypeScript
    - Configure Cognito authentication with user groups (Analyst, Admin)
    - Set up API Gateway integration for agent communication
    - Create base application structure and routing
    - Write integration tests for authentication flow
    - _Requirements: 11.1, 8.1_

  - [ ] 9.2 Implement dashboard and review interfaces

    - Create published articles dashboard with filtering and search
    - Build review queue interface with approval/rejection controls
    - Add article detail views with entity extraction display
    - Implement comment system with threading support
    - Write UI tests for dashboard and review functionality
    - _Requirements: 7.1, 8.1, 8.2, 8.3, 8.4_

  - [ ] 9.3 Build chat interface for Analyst Assistant
    - Create conversational UI for natural language queries
    - Add result display with source citations and export options
    - Implement session management and query history
    - Include feedback collection (thumbs up/down) interface
    - Write UI tests for chat functionality and result display
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 8.5_

- [ ] 10. Implement monitoring and observability

  - [ ] 10.1 Set up CloudWatch dashboards

    - Create dashboards for ingestion rates, relevancy rates, and deduplication metrics
    - Add publish/review ratio tracking and keyword hit statistics
    - Include system performance metrics and cost tracking
    - Configure alerting for anomalies and threshold breaches
    - Test dashboard functionality and alert delivery
    - _Requirements: 14.1, 14.5, 14.6_

  - [ ] 10.2 Configure distributed tracing
    - Enable X-Ray tracing for all Lambda functions and agent executions
    - Add correlation IDs for end-to-end request tracking
    - Implement trace analysis for performance optimization
    - Create trace-based alerting for error patterns
    - Test tracing functionality across the entire pipeline
    - _Requirements: 14.2, 11.4_

- [ ] 11. Implement comprehensive testing suite

  - [ ] 11.1 Create integration tests

    - Build end-to-end tests for feed ingestion pipeline
    - Add agent interaction tests with mock tools
    - Implement database consistency validation tests
    - Create API endpoint integration tests
    - Test error handling and recovery scenarios
    - _Requirements: All requirements validation_

  - [ ] 11.2 Add performance and load testing
    - Create load tests for high-volume feed ingestion scenarios
    - Add concurrent user query testing for the web application
    - Implement bulk report generation performance tests
    - Test system resource utilization under load
    - Validate autoscaling and cost optimization features
    - _Requirements: 12.1, 12.2, 12.5_

- [ ] 12. Deploy complete infrastructure and validate system

  - [ ] 12.1 Execute full Terraform deployment

    - Run terraform plan and apply for complete infrastructure stack
    - Validate all AWS resources are created correctly with proper configurations
    - Verify IAM permissions, VPC endpoints, and security policies
    - Test Lambda packaging, deployment, and function execution
    - Confirm OpenSearch Serverless collections and DynamoDB tables are accessible
    - _Requirements: All infrastructure requirements_

  - [ ] 12.2 Configure RSS feeds and keywords

    - Load all 21 RSS feed configurations into the system
    - Configure target keyword lists for cloud platforms, security vendors, and enterprise tools
    - Set up feed categorization (Advisories, Alerts, Vulnerabilities, etc.)
    - Test feed parsing and keyword matching functionality
    - Validate configuration reload capabilities without system restart
    - _Requirements: 1.1, 2.2, 13.1, 13.2, 13.3_

  - [ ] 12.3 Execute end-to-end system validation
    - Run complete ingestion cycle with real RSS feeds
    - Validate deduplication clustering and keyword detection accuracy
    - Test human review workflow with sample escalations
    - Verify report generation and XLSX export functionality
    - Confirm all performance metrics are achievable (≤5 min latency, ≥85% dup detection)
    - _Requirements: All requirements comprehensive validation_

- [ ] 13. Create comprehensive documentation and deployment guides

  - [ ] 13.1 Write project documentation

    - Update the README.md with infrastructure architecture diagram
    - Document RSS feed configuration process and supported feed formats
    - Write keyword management guide with examples and best practices
    - Create user guide for web interface and natural language querying
    - Document troubleshooting procedures and common issues
    - _Requirements: All requirements for operational documentation_

  - [ ] 13.2 Create deployment and operations guides

    - Write step-by-step deployment guide with prerequisites and setup instructions
    - Document Terraform module usage and customization options
    - Create operations runbook for monitoring, alerting, and maintenance
    - Write disaster recovery and backup procedures
    - Document scaling and cost optimization strategies
    - _Requirements: 11.4, 12.5, 14.1, 14.5_

  - [ ] 13.3 Document configuration management
    - Create guide for adding/updating RSS feed sources with examples
    - Document keyword list management and update procedures
    - Write email recipient configuration guide for SES notifications
    - Document user management and access control procedures
    - Create configuration change audit and rollback procedures
    - _Requirements: 7.2, 8.1, 13.6, 13.7_

- [ ] 14. Create alternative AWS CloudFormation template as Terraform backup

  - Create comprehensive CloudFormation template equivalent to Terraform infrastructure
  - Convert all Terraform modules to CloudFormation nested stacks or resources in a single yaml file
  - Include VPC, Lambda functions, DynamoDB tables, OpenSearch Serverless, S3 buckets
  - Add Step Functions, EventBridge, SQS, SES, Cognito, API Gateway, and Amplify resources
  - Configure IAM roles, policies, and KMS encryption keys with proper permissions
  - Include CloudWatch dashboards, alarms, and X-Ray tracing configuration
  - Add parameter files for dev and prod environment configurations
  - Document deployment procedures and parameter customization options
  - Test CloudFormation stack deployment and validate resource creation
  - _Requirements: All infrastructure requirements as backup deployment method_
