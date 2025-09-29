# Step Functions Module for Sentinel Infrastructure
# Creates state machine for direct Lambda orchestration

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

# Main ingestion state machine
resource "aws_sfn_state_machine" "ingestion" {
  name     = "${var.name_prefix}-ingestion-workflow"
  role_arn = var.execution_role_arn

  definition = jsonencode({
    Comment = "Sentinel cybersecurity news ingestion and triage workflow"
    StartAt = var.enable_agents ? "InvokeIngestorAgent" : "ParseFeeds"
    States = merge(
      # Agent-based workflow (when agents are enabled)
      var.enable_agents ? {
        InvokeIngestorAgent = {
          Type     = "Task"
          Resource = "arn:aws:states:::bedrock:invokeAgent"
          Parameters = {
            AgentId      = var.ingestor_agent_id
            AgentAliasId = "TSTALIASID"
            SessionId    = "$.sessionId"
            InputText    = "$.inputText"
          }
          Retry = [
            {
              ErrorEquals     = ["States.TaskFailed"]
              IntervalSeconds = 2
              MaxAttempts     = 3
              BackoffRate     = 2.0
            }
          ]
          Catch = [
            {
              ErrorEquals = ["States.ALL"]
              Next        = "HandleAgentError"
            }
          ]
          End = true
        }
        HandleAgentError = {
          Type = "Task"
          Resource = var.lambda_function_arns["human_escalation"]
          Parameters = {
            "error.$"   = "$.Error"
            "cause.$"   = "$.Cause"
            "input.$"   = "$"
            "errorType" = "AgentExecutionError"
          }
          End = true
        }
      } : {},
      # Direct Lambda workflow (when agents are disabled)
      !var.enable_agents ? {
        ParseFeeds = {
          Type     = "Task"
          Resource = var.lambda_function_arns["feed_parser"]
          Parameters = {
            "feedConfigs.$" = "$.feedConfigs"
            "batchSize.$"   = "$.batchSize"
          }
          Retry = [
            {
              ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
              IntervalSeconds = 2
              MaxAttempts     = 6
              BackoffRate     = 2.0
            }
          ]
          Catch = [
            {
              ErrorEquals = ["States.ALL"]
              Next        = "HandleParseError"
              ResultPath  = "$.error"
            }
          ]
          Next = "ProcessArticles"
        }
        ProcessArticles = {
          Type = "Map"
          ItemsPath = "$.articles"
          MaxConcurrency = var.max_concurrent_executions
          Iterator = {
            StartAt = "EvaluateRelevance"
            States = {
              EvaluateRelevance = {
                Type     = "Task"
                Resource = var.lambda_function_arns["relevancy_evaluator"]
                Parameters = {
                  "article.$" = "$"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                Next = "CheckRelevance"
              }
              CheckRelevance = {
                Type = "Choice"
                Choices = [
                  {
                    Variable      = "$.relevancy_score"
                    NumericGreaterThan = 0.7
                    Next          = "DeduplicateArticle"
                  }
                ]
                Default = "ArchiveArticle"
              }
              DeduplicateArticle = {
                Type     = "Task"
                Resource = var.lambda_function_arns["dedup_tool"]
                Parameters = {
                  "article.$" = "$"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                Next = "CheckDuplication"
              }
              CheckDuplication = {
                Type = "Choice"
                Choices = [
                  {
                    Variable = "$.is_duplicate"
                    BooleanEquals = true
                    Next     = "ArchiveArticle"
                  }
                ]
                Default = "ApplyGuardrails"
              }
              ApplyGuardrails = {
                Type     = "Task"
                Resource = var.lambda_function_arns["guardrail_tool"]
                Parameters = {
                  "article.$" = "$"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                Next = "CheckGuardrails"
              }
              CheckGuardrails = {
                Type = "Choice"
                Choices = [
                  {
                    Variable = "$.guardrail_passed"
                    BooleanEquals = false
                    Next     = "EscalateForReview"
                  },
                  {
                    Variable = "$.triage_action"
                    StringEquals = "AUTO_PUBLISH"
                    Next     = "StoreAndPublish"
                  }
                ]
                Default = "EscalateForReview"
              }
              StoreAndPublish = {
                Type     = "Task"
                Resource = var.lambda_function_arns["storage_tool"]
                Parameters = {
                  "article.$" = "$"
                  "action"    = "publish"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                Next = "SendNotification"
              }
              EscalateForReview = {
                Type     = "Task"
                Resource = var.lambda_function_arns["human_escalation"]
                Parameters = {
                  "article.$" = "$"
                  "reason"    = "requires_review"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                Next = "StoreForReview"
              }
              StoreForReview = {
                Type     = "Task"
                Resource = var.lambda_function_arns["storage_tool"]
                Parameters = {
                  "article.$" = "$"
                  "action"    = "review"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                End = true
              }
              ArchiveArticle = {
                Type     = "Task"
                Resource = var.lambda_function_arns["storage_tool"]
                Parameters = {
                  "article.$" = "$"
                  "action"    = "archive"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                End = true
              }
              SendNotification = {
                Type     = "Task"
                Resource = var.lambda_function_arns["notifier"]
                Parameters = {
                  "article.$"        = "$"
                  "notification_type" = "published"
                }
                Retry = [
                  {
                    ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                    IntervalSeconds = 2
                    MaxAttempts     = 3
                    BackoffRate     = 2.0
                  }
                ]
                End = true
              }
            }
          }
          Next = "CompileResults"
        }
        CompileResults = {
          Type = "Task"
          Resource = "arn:aws:states:::lambda:invoke"
          Parameters = {
            FunctionName = var.lambda_function_arns["storage_tool"]
            Payload = {
              "results.$" = "$"
              "action"    = "compile_batch_results"
            }
          }
          End = true
        }
        HandleParseError = {
          Type = "Task"
          Resource = var.lambda_function_arns["human_escalation"]
          Parameters = {
            "error.$"   = "$.error"
            "input.$"   = "$"
            "errorType" = "FeedParsingError"
          }
          End = true
        }
      } : {}
    )
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = var.enable_xray_tracing
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-ingestion-state-machine"
    Purpose = "Article ingestion and triage workflow"
  })
}

# Review workflow state machine
resource "aws_sfn_state_machine" "review_workflow" {
  name     = "${var.name_prefix}-review-workflow"
  role_arn = var.execution_role_arn

  definition = jsonencode({
    Comment = "Human review workflow for flagged articles"
    StartAt = "ProcessReviewDecision"
    States = {
      ProcessReviewDecision = {
        Type     = "Task"
        Resource = var.lambda_function_arns["publish_decision"]
        Parameters = {
          "reviewDecision.$" = "$"
        }
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Next = "CheckDecision"
      }
      CheckDecision = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.decision"
            StringEquals = "approved"
            Next     = "PublishArticle"
          },
          {
            Variable = "$.decision"
            StringEquals = "rejected"
            Next     = "ArchiveRejected"
          }
        ]
        Default = "HandleUnknownDecision"
      }
      PublishArticle = {
        Type     = "Task"
        Resource = var.lambda_function_arns["storage_tool"]
        Parameters = {
          "article.$" = "$.article"
          "action"    = "publish"
        }
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        Next = "NotifyPublication"
      }
      ArchiveRejected = {
        Type     = "Task"
        Resource = var.lambda_function_arns["storage_tool"]
        Parameters = {
          "article.$" = "$.article"
          "action"    = "archive"
          "reason"    = "rejected_by_reviewer"
        }
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        End = true
      }
      NotifyPublication = {
        Type     = "Task"
        Resource = var.lambda_function_arns["notifier"]
        Parameters = {
          "article.$"        = "$.article"
          "notification_type" = "published_after_review"
        }
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
        End = true
      }
      HandleUnknownDecision = {
        Type = "Task"
        Resource = var.lambda_function_arns["human_escalation"]
        Parameters = {
          "decision.$" = "$"
          "errorType"  = "UnknownReviewDecision"
        }
        End = true
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = var.enable_xray_tracing
  }

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-review-workflow-state-machine"
    Purpose = "Human review decision processing"
  })
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-step-functions-logs"
    Purpose = "Step Functions execution logs"
  })
}

# CloudWatch Alarms for Step Functions
resource "aws_cloudwatch_metric_alarm" "step_functions_failed_executions" {
  alarm_name          = "${var.name_prefix}-step-functions-failed-executions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors failed Step Functions executions"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.ingestion.arn
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-step-functions-failed-executions-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "step_functions_execution_time" {
  alarm_name          = "${var.name_prefix}-step-functions-execution-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = "300"
  statistic           = "Average"
  threshold           = var.execution_time_alarm_threshold
  alarm_description   = "This metric monitors Step Functions execution time"
  alarm_actions       = var.alarm_topic_arn != null ? [var.alarm_topic_arn] : []

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.ingestion.arn
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-step-functions-execution-time-alarm"
  })
}