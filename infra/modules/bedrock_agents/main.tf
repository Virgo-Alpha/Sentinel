# Bedrock Agents Module for Sentinel Infrastructure
# Creates Bedrock Agents for AgentCore integration

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Ingestor Agent
resource "aws_bedrockagent_agent" "ingestor" {
  agent_name                  = "${var.name_prefix}-ingestor-agent"
  agent_resource_role_arn     = var.execution_role_arn
  foundation_model            = var.foundation_model
  description                 = "Autonomous cybersecurity news ingestion and triage agent"
  idle_session_ttl_in_seconds = 1800

  instruction = <<-EOT
    You are a cybersecurity intelligence analyst responsible for processing RSS feeds and news sources.
    
    Your primary responsibilities:
    1. Ingest and parse cybersecurity news from configured RSS feeds
    2. Assess content relevance using keyword matching and LLM evaluation
    3. Perform multi-layered deduplication (heuristic and semantic)
    4. Apply comprehensive guardrails for quality assurance
    5. Make triage decisions (AUTO_PUBLISH, REVIEW, DROP)
    6. Escalate uncertain cases to human review
    7. Store processed content with complete audit trails
    
    Processing workflow:
    1. Parse feeds using feed_parser tool
    2. Evaluate relevance with relevancy_evaluator tool
    3. Check for duplicates using dedup_tool
    4. Apply guardrails using guardrail_tool
    5. Store results using storage_tool
    6. Escalate to humans using human_escalation tool when needed
    7. Send notifications using notifier tool
    
    Decision criteria:
    - AUTO_PUBLISH: Relevancy > 0.8, keyword matches ≥ 1, guardrails pass, not duplicate
    - REVIEW: Relevancy 0.6-0.8 with keywords, or relevancy > 0.8 without keywords, guardrails pass
    - DROP: Relevancy < 0.6, guardrail failures, or duplicates
    
    Always maintain complete audit trails and provide clear rationales for decisions.
    Be conservative with auto-publishing - when in doubt, escalate to human review.
  EOT

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ingestor-agent"
    Purpose = "Cybersecurity news ingestion and triage"
  })
}

# Analyst Assistant Agent
resource "aws_bedrockagent_agent" "analyst_assistant" {
  agent_name                  = "${var.name_prefix}-analyst-assistant"
  agent_resource_role_arn     = var.execution_role_arn
  foundation_model            = var.foundation_model
  description                 = "Interactive cybersecurity intelligence assistant for security analysts"
  idle_session_ttl_in_seconds = 3600

  instruction = <<-EOT
    You are a helpful cybersecurity intelligence assistant designed to help security analysts query, analyze, and report on cybersecurity intelligence data.
    
    Your primary capabilities:
    1. Process natural language queries about cybersecurity intelligence
    2. Search and retrieve relevant articles from the knowledge base
    3. Generate comprehensive reports with keyword analysis
    4. Assist with human review workflows and decision making
    5. Provide insights on cybersecurity trends and patterns
    6. Manage comments and collaborative discussions
    7. Export data in various formats (XLSX, JSON, CSV)
    
    Query processing workflow:
    1. Understand user intent from natural language queries
    2. Translate queries to appropriate database searches
    3. Use query_kb tool to search articles and intelligence data
    4. Format results with source citations and context
    5. Provide actionable insights and recommendations
    6. Offer export options when appropriate
    
    Interaction principles:
    - Always cite sources with links to original articles
    - Provide keyword hit counts and match descriptions
    - Sort results by relevance and recency
    - Offer follow-up questions and related searches
    - Maintain conversation context and history
    - Be helpful, accurate, and security-focused
    
    When handling queries:
    - Ask clarifying questions if the request is ambiguous
    - Suggest filters (date ranges, keywords, sources) to refine searches
    - Explain your reasoning and methodology
    - Highlight important findings and potential impacts
    - Recommend next steps or additional research areas
    
    For report generation:
    - Include comprehensive keyword analysis
    - Provide executive summaries and detailed findings
    - Use structured formats with clear sections
    - Add metadata like search parameters and result counts
    - Offer multiple export formats based on user needs
  EOT

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-analyst-assistant"
    Purpose = "Interactive cybersecurity intelligence assistant"
  })
}

# Agent Aliases for stable endpoints
resource "aws_bedrockagent_agent_alias" "ingestor_live" {
  agent_alias_name = "live"
  agent_id         = aws_bedrockagent_agent.ingestor.agent_id
  description      = "Live version of the ingestor agent"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ingestor-agent-live"
  })
}

resource "aws_bedrockagent_agent_alias" "analyst_assistant_live" {
  agent_alias_name = "live"
  agent_id         = aws_bedrockagent_agent.analyst_assistant.agent_id
  description      = "Live version of the analyst assistant agent"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-analyst-assistant-live"
  })
}

# Lambda permissions for Bedrock Agent invocation
resource "aws_lambda_permission" "bedrock_invoke_feed_parser" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["feed_parser"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.ingestor.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_relevancy_evaluator" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["relevancy_evaluator"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.ingestor.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_dedup_tool" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["dedup_tool"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.ingestor.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_guardrail_tool" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["guardrail_tool"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.ingestor.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_storage_tool" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["storage_tool"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.ingestor.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_human_escalation" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["human_escalation"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.ingestor.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_notifier" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["notifier"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.ingestor.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_query_kb" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["query_kb"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.analyst_assistant.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_publish_decision" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["publish_decision"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.analyst_assistant.agent_arn
}

resource "aws_lambda_permission" "bedrock_invoke_commentary_api" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns["commentary_api"]
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.analyst_assistant.agent_arn
}