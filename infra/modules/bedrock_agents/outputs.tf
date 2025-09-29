# Outputs for Bedrock Agents Module

output "ingestor_agent_id" {
  description = "ID of the Ingestor Agent"
  value       = aws_bedrockagent_agent.ingestor.agent_id
}

output "ingestor_agent_arn" {
  description = "ARN of the Ingestor Agent"
  value       = aws_bedrockagent_agent.ingestor.agent_arn
}

output "ingestor_agent_alias_id" {
  description = "ID of the Ingestor Agent live alias"
  value       = aws_bedrockagent_agent_alias.ingestor_live.agent_alias_id
}

output "analyst_assistant_agent_id" {
  description = "ID of the Analyst Assistant Agent"
  value       = aws_bedrockagent_agent.analyst_assistant.agent_id
}

output "analyst_assistant_agent_arn" {
  description = "ARN of the Analyst Assistant Agent"
  value       = aws_bedrockagent_agent.analyst_assistant.agent_arn
}

output "analyst_assistant_alias_id" {
  description = "ID of the Analyst Assistant Agent live alias"
  value       = aws_bedrockagent_agent_alias.analyst_assistant_live.agent_alias_id
}

output "agent_endpoints" {
  description = "Map of agent endpoints for invocation"
  value = {
    ingestor_agent = {
      agent_id  = aws_bedrockagent_agent.ingestor.agent_id
      agent_arn = aws_bedrockagent_agent.ingestor.agent_arn
      alias_id  = aws_bedrockagent_agent_alias.ingestor_live.agent_alias_id
      alias_arn = aws_bedrockagent_agent_alias.ingestor_live.agent_alias_arn
    }
    analyst_assistant = {
      agent_id  = aws_bedrockagent_agent.analyst_assistant.agent_id
      agent_arn = aws_bedrockagent_agent.analyst_assistant.agent_arn
      alias_id  = aws_bedrockagent_agent_alias.analyst_assistant_live.agent_alias_id
      alias_arn = aws_bedrockagent_agent_alias.analyst_assistant_live.agent_alias_arn
    }
  }
}