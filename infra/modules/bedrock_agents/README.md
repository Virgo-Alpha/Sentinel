# Bedrock Agents Module

This module creates AWS Bedrock Agents for the Sentinel cybersecurity triage system. It implements the AgentCore integration that allows the system to use Bedrock Agents instead of direct Lambda orchestration.

## Architecture

The module creates two main agents:

### 1. Ingestor Agent
- **Purpose**: Autonomous cybersecurity news ingestion and triage
- **Model**: Claude 3.5 Sonnet
- **Tools**: 
  - `feed_parser` - Parse RSS/Atom feeds
  - `relevancy_evaluator` - Assess content relevance
  - `dedup_tool` - Identify duplicates
  - `guardrail_tool` - Apply content validation
  - `storage_tool` - Store processed articles
  - `human_escalation` - Queue items for review
  - `notifier` - Send notifications

### 2. Analyst Assistant Agent
- **Purpose**: Interactive cybersecurity intelligence assistant
- **Model**: Claude 3.5 Sonnet
- **Tools**:
  - `query_kb` - Search knowledge base
  - `publish_decision` - Process review decisions
  - `commentary_api` - Manage comments and discussions

## Usage

This module is conditionally deployed based on the `enable_agents` feature flag:

```hcl
module "bedrock_agents" {
  count  = var.enable_agents ? 1 : 0
  source = "./modules/bedrock_agents"

  name_prefix          = local.name_prefix
  lambda_function_arns = module.lambda.function_arns
  execution_role_arn   = module.iam.bedrock_agent_role_arn
  tags                 = local.common_tags
}
```

## Deployment Strategy

The system supports a phased deployment approach:

1. **Phase 1**: Direct Lambda orchestration (`enable_agents = false`)
2. **Phase 2**: Bedrock AgentCore integration (`enable_agents = true`)

This allows for gradual migration from Step Functions orchestration to Bedrock Agents without disrupting the system.

## Agent Configuration

Each agent is configured with:
- **Foundation Model**: Anthropic Claude 3.5 Sonnet
- **Session TTL**: 30 minutes (Ingestor) / 60 minutes (Assistant)
- **Action Groups**: Lambda tool integrations with OpenAPI schemas
- **Aliases**: Live aliases for stable endpoint access

## Permissions

The module automatically creates Lambda permissions for Bedrock Agent invocation and uses the IAM execution role created by the IAM module.

## Outputs

- Agent IDs and ARNs for both agents
- Agent alias IDs and ARNs
- Complete endpoint map for invocation

## Integration

The agents integrate with:
- **Step Functions**: Ingestor Agent triggered by workflows
- **API Gateway**: Analyst Assistant accessible via REST API
- **Lambda Functions**: All processing tools as agent actions
- **IAM**: Execution roles with appropriate permissions