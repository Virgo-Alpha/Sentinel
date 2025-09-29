# Outputs for Step Functions Module

output "ingestion_state_machine_arn" {
  description = "ARN of the ingestion state machine"
  value       = aws_sfn_state_machine.ingestion.arn
}

output "ingestion_state_machine_name" {
  description = "Name of the ingestion state machine"
  value       = aws_sfn_state_machine.ingestion.name
}

output "review_workflow_state_machine_arn" {
  description = "ARN of the review workflow state machine"
  value       = aws_sfn_state_machine.review_workflow.arn
}

output "review_workflow_state_machine_name" {
  description = "Name of the review workflow state machine"
  value       = aws_sfn_state_machine.review_workflow.name
}

output "state_machine_arns" {
  description = "Map of all state machine ARNs"
  value = {
    ingestion      = aws_sfn_state_machine.ingestion.arn
    review_workflow = aws_sfn_state_machine.review_workflow.arn
  }
}

output "state_machine_names" {
  description = "Map of all state machine names"
  value = {
    ingestion      = aws_sfn_state_machine.ingestion.name
    review_workflow = aws_sfn_state_machine.review_workflow.name
  }
}

output "log_group_name" {
  description = "Name of CloudWatch log group"
  value       = aws_cloudwatch_log_group.step_functions.name
}

output "log_group_arn" {
  description = "ARN of CloudWatch log group"
  value       = aws_cloudwatch_log_group.step_functions.arn
}