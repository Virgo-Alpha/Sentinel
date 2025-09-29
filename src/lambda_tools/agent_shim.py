"""
Agent Shim Lambda for Sentinel cybersecurity triage system.

This Lambda function provides a deferral mechanism between direct Lambda tool orchestration
and Bedrock AgentCore agent execution. It maintains stable tool contracts while allowing
seamless transition between orchestration modes.

Environment Variables:
- ORCHESTRATOR: "direct" or "agentcore" (default: "direct")
- ENABLE_AGENTS: "true" or "false" (default: "false")
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
lambda_client = boto3.client('lambda')


class AgentShimError(Exception):
    """Custom exception for agent shim errors."""
    pass


class DirectLambdaOrchestrator:
    """Direct Lambda function orchestration for tool execution."""
    
    def __init__(self):
        self.lambda_client = lambda_client
        
        # Tool to Lambda function mapping
        self.tool_mappings = {
            'feed_parser': os.environ.get('FEED_PARSER_FUNCTION', 'sentinel-feed-parser'),
            'relevancy_evaluator': os.environ.get('RELEVANCY_EVALUATOR_FUNCTION', 'sentinel-relevancy-evaluator'),
            'dedup_tool': os.environ.get('DEDUP_TOOL_FUNCTION', 'sentinel-dedup-tool'),
            'guardrail_tool': os.environ.get('GUARDRAIL_TOOL_FUNCTION', 'sentinel-guardrail-tool'),
            'storage_tool': os.environ.get('STORAGE_TOOL_FUNCTION', 'sentinel-storage-tool'),
            'human_escalation': os.environ.get('HUMAN_ESCALATION_FUNCTION', 'sentinel-human-escalation'),
            'notifier': os.environ.get('NOTIFIER_FUNCTION', 'sentinel-notifier'),
            'query_kb': os.environ.get('QUERY_KB_FUNCTION', 'sentinel-query-kb'),
            'publish_decision': os.environ.get('PUBLISH_DECISION_FUNCTION', 'sentinel-publish-decision'),
            'commentary_api': os.environ.get('COMMENTARY_API_FUNCTION', 'sentinel-commentary-api')
        }
    
    def execute_ingestor_workflow(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ingestor agent workflow using direct Lambda calls."""
        try:
            logger.info("Executing ingestor workflow via direct Lambda orchestration")
            
            # Extract feed configuration from event
            feed_config = event.get('feed_config', {})
            feed_id = feed_config.get('feed_id')
            feed_url = feed_config.get('feed_url')
            since = event.get('since')
            
            if not feed_id or not feed_url:
                raise AgentShimError("feed_id and feed_url are required in feed_config")
            
            workflow_results = {
                'workflow_id': event.get('workflow_id', f"workflow-{datetime.utcnow().isoformat()}"),
                'feed_id': feed_id,
                'started_at': datetime.utcnow().isoformat(),
                'steps': []
            }
            
            # Step 1: Parse feed
            logger.info(f"Step 1: Parsing feed {feed_id}")
            parse_result = self._invoke_tool('feed_parser', {
                'feed_id': feed_id,
                'feed_url': feed_url,
                'since': since
            })
            workflow_results['steps'].append({
                'step': 'feed_parser',
                'status': 'completed' if parse_result.get('success') else 'failed',
                'result': parse_result
            })
            
            if not parse_result.get('success'):
                raise AgentShimError(f"Feed parsing failed: {parse_result.get('error')}")
            
            articles = parse_result.get('articles', [])
            processed_articles = []
            
            # Process each article through the workflow
            for article in articles:
                try:
                    article_result = self._process_article_workflow(article, feed_config)
                    processed_articles.append(article_result)
                except Exception as e:
                    logger.error(f"Error processing article {article.get('title', 'unknown')}: {e}")
                    processed_articles.append({
                        'article_id': article.get('article_id'),
                        'status': 'failed',
                        'error': str(e)
                    })
            
            workflow_results.update({
                'completed_at': datetime.utcnow().isoformat(),
                'articles_processed': len(processed_articles),
                'articles_published': len([a for a in processed_articles if a.get('action') == 'AUTO_PUBLISH']),
                'articles_escalated': len([a for a in processed_articles if a.get('action') == 'REVIEW']),
                'articles_dropped': len([a for a in processed_articles if a.get('action') == 'DROP']),
                'processed_articles': processed_articles
            })
            
            return {
                'statusCode': 200,
                'body': {
                    'success': True,
                    'orchestrator': 'direct',
                    'workflow_results': workflow_results
                }
            }
            
        except Exception as e:
            logger.error(f"Ingestor workflow failed: {e}")
            return {
                'statusCode': 500,
                'body': {
                    'success': False,
                    'orchestrator': 'direct',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            }
    
    def _process_article_workflow(self, article: Dict[str, Any], feed_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single article through the complete workflow."""
        article_id = article.get('article_id', f"article-{datetime.utcnow().isoformat()}")
        
        try:
            # Step 2: Evaluate relevance
            logger.info(f"Step 2: Evaluating relevance for article {article_id}")
            relevance_result = self._invoke_tool('relevancy_evaluator', {
                'article_id': article_id,
                'content': article.get('normalized_content', ''),
                'target_keywords': feed_config.get('target_keywords', [])
            })
            
            if not relevance_result.get('success'):
                return {'article_id': article_id, 'status': 'failed', 'step': 'relevancy_evaluator'}
            
            relevance_data = relevance_result.get('body', {})
            
            # Step 3: Check for duplicates
            logger.info(f"Step 3: Checking duplicates for article {article_id}")
            dedup_result = self._invoke_tool('dedup_tool', {
                'article_id': article_id,
                'content': article.get('normalized_content', ''),
                'metadata': {
                    'title': article.get('title'),
                    'url': article.get('url'),
                    'published_at': article.get('published_at'),
                    'source': article.get('source')
                }
            })
            
            if not dedup_result.get('success'):
                return {'article_id': article_id, 'status': 'failed', 'step': 'dedup_tool'}
            
            dedup_data = dedup_result.get('body', {})
            
            # Skip processing if duplicate
            if dedup_data.get('is_duplicate'):
                logger.info(f"Article {article_id} is duplicate, skipping further processing")
                return {
                    'article_id': article_id,
                    'status': 'completed',
                    'action': 'DROP',
                    'reason': 'duplicate',
                    'duplicate_of': dedup_data.get('duplicate_of')
                }
            
            # Step 4: Apply guardrails
            logger.info(f"Step 4: Applying guardrails for article {article_id}")
            guardrail_result = self._invoke_tool('guardrail_tool', {
                'article_id': article_id,
                'content': article.get('normalized_content', ''),
                'extracted_entities': relevance_data.get('entities', {}),
                'summary': relevance_data.get('summary', '')
            })
            
            if not guardrail_result.get('success'):
                return {'article_id': article_id, 'status': 'failed', 'step': 'guardrail_tool'}
            
            guardrail_data = guardrail_result.get('body', {})
            
            # Step 5: Make triage decision
            triage_action = self._make_triage_decision(relevance_data, guardrail_data)
            
            # Step 6: Store article with processing results
            logger.info(f"Step 6: Storing article {article_id} with action {triage_action}")
            
            article_data = {
                **article,
                'article_id': article_id,
                'relevancy_score': relevance_data.get('relevancy_score'),
                'keyword_matches': relevance_data.get('keyword_matches', []),
                'entities': relevance_data.get('entities', {}),
                'triage_action': triage_action,
                'guardrail_flags': guardrail_data.get('flags', []),
                'cluster_id': dedup_data.get('cluster_id'),
                'is_duplicate': False,
                'confidence': min(relevance_data.get('confidence', 0.5), guardrail_data.get('confidence', 0.5))
            }
            
            storage_result = self._invoke_tool('storage_tool', {
                'article_id': article_id,
                'operation': 'create',
                'data': article_data,
                'state': 'PROCESSED' if triage_action != 'DROP' else 'ARCHIVED'
            })
            
            if not storage_result.get('success'):
                return {'article_id': article_id, 'status': 'failed', 'step': 'storage_tool'}
            
            # Step 7: Handle triage action
            if triage_action == 'AUTO_PUBLISH':
                # Publish directly
                publish_result = self._invoke_tool('storage_tool', {
                    'article_id': article_id,
                    'operation': 'publish',
                    'data': article_data,
                    'state': 'PUBLISHED'
                })
                
                # Send publication notification
                self._invoke_tool('notifier', {
                    'notification_type': 'publication',
                    'recipients': feed_config.get('notification_recipients', []),
                    'subject': f"New cybersecurity intelligence published: {article.get('title', 'Unknown')}",
                    'content': {
                        'article': article_data,
                        'action': 'published'
                    }
                })
                
            elif triage_action == 'REVIEW':
                # Escalate to human review
                escalation_result = self._invoke_tool('human_escalation', {
                    'article_id': article_id,
                    'escalation_reason': self._get_escalation_reason(relevance_data, guardrail_data),
                    'priority': self._get_escalation_priority(relevance_data),
                    'context': {
                        'relevance_data': relevance_data,
                        'guardrail_data': guardrail_data,
                        'article_data': article_data
                    }
                })
            
            return {
                'article_id': article_id,
                'status': 'completed',
                'action': triage_action,
                'relevancy_score': relevance_data.get('relevancy_score'),
                'keyword_matches': len(relevance_data.get('keyword_matches', [])),
                'guardrail_passed': guardrail_data.get('passed', False)
            }
            
        except Exception as e:
            logger.error(f"Error processing article {article_id}: {e}")
            return {
                'article_id': article_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _make_triage_decision(self, relevance_data: Dict[str, Any], guardrail_data: Dict[str, Any]) -> str:
        """Make triage decision based on relevance and guardrail results."""
        relevancy_score = relevance_data.get('relevancy_score', 0.0)
        keyword_matches = len(relevance_data.get('keyword_matches', []))
        guardrail_passed = guardrail_data.get('passed', False)
        
        # Decision matrix from design document
        if not guardrail_passed:
            return 'REVIEW'
        
        if relevancy_score > 0.8 and keyword_matches >= 1:
            return 'AUTO_PUBLISH'
        elif (0.6 <= relevancy_score <= 0.8 and keyword_matches >= 1) or (relevancy_score > 0.8 and keyword_matches == 0):
            return 'REVIEW'
        else:
            return 'DROP'
    
    def _get_escalation_reason(self, relevance_data: Dict[str, Any], guardrail_data: Dict[str, Any]) -> str:
        """Determine escalation reason based on processing results."""
        if not guardrail_data.get('passed', False):
            return f"Guardrail violations: {', '.join(guardrail_data.get('violations', []))}"
        
        relevancy_score = relevance_data.get('relevancy_score', 0.0)
        keyword_matches = len(relevance_data.get('keyword_matches', []))
        
        if 0.6 <= relevancy_score <= 0.8:
            return "Medium relevancy score requires human review"
        elif relevancy_score > 0.8 and keyword_matches == 0:
            return "High relevancy but no keyword matches"
        else:
            return "Manual review requested"
    
    def _get_escalation_priority(self, relevance_data: Dict[str, Any]) -> str:
        """Determine escalation priority based on relevance data."""
        relevancy_score = relevance_data.get('relevancy_score', 0.0)
        entities = relevance_data.get('entities', {})
        
        # High priority if CVEs are mentioned
        if entities.get('cves'):
            return 'high'
        
        # Medium priority for high relevancy
        if relevancy_score > 0.8:
            return 'medium'
        
        return 'low'
    
    def _invoke_tool(self, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a Lambda tool function."""
        function_name = self.tool_mappings.get(tool_name)
        if not function_name:
            raise AgentShimError(f"Unknown tool: {tool_name}")
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            return result
            
        except ClientError as e:
            logger.error(f"Error invoking {function_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'ClientError'
            }
        except Exception as e:
            logger.error(f"Unexpected error invoking {function_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }


class BedrockAgentCoreOrchestrator:
    """Bedrock AgentCore orchestration for agent execution."""
    
    def __init__(self):
        self.bedrock_client = bedrock_agent_runtime
        self.ingestor_agent_id = os.environ.get('INGESTOR_AGENT_ID')
        self.analyst_assistant_agent_id = os.environ.get('ANALYST_ASSISTANT_AGENT_ID')
        self.ingestor_agent_alias_id = os.environ.get('INGESTOR_AGENT_ALIAS_ID', 'TSTALIASID')
        self.analyst_assistant_alias_id = os.environ.get('ANALYST_ASSISTANT_ALIAS_ID', 'TSTALIASID')
    
    def execute_ingestor_workflow(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ingestor agent workflow using Bedrock AgentCore."""
        try:
            logger.info("Executing ingestor workflow via Bedrock AgentCore")
            
            if not self.ingestor_agent_id:
                raise AgentShimError("INGESTOR_AGENT_ID environment variable is required for AgentCore orchestration")
            
            # Prepare agent input
            agent_input = {
                'inputText': json.dumps({
                    'task': 'ingest_and_process_feed',
                    'feed_config': event.get('feed_config', {}),
                    'since': event.get('since'),
                    'workflow_id': event.get('workflow_id')
                })
            }
            
            # Invoke Bedrock agent
            response = self.bedrock_client.invoke_agent(
                agentId=self.ingestor_agent_id,
                agentAliasId=self.ingestor_agent_alias_id,
                sessionId=event.get('session_id', f"session-{datetime.utcnow().isoformat()}"),
                inputText=agent_input['inputText']
            )
            
            # Process agent response
            agent_response = self._process_agent_response(response)
            
            return {
                'statusCode': 200,
                'body': {
                    'success': True,
                    'orchestrator': 'agentcore',
                    'agent_response': agent_response
                }
            }
            
        except Exception as e:
            logger.error(f"AgentCore ingestor workflow failed: {e}")
            return {
                'statusCode': 500,
                'body': {
                    'success': False,
                    'orchestrator': 'agentcore',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            }
    
    def execute_analyst_query(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analyst assistant query using Bedrock AgentCore."""
        try:
            logger.info("Executing analyst query via Bedrock AgentCore")
            
            if not self.analyst_assistant_agent_id:
                raise AgentShimError("ANALYST_ASSISTANT_AGENT_ID environment variable is required for AgentCore orchestration")
            
            # Prepare agent input
            query = event.get('query', '')
            if not query:
                raise AgentShimError("Query is required for analyst assistant")
            
            # Invoke Bedrock agent
            response = self.bedrock_client.invoke_agent(
                agentId=self.analyst_assistant_agent_id,
                agentAliasId=self.analyst_assistant_alias_id,
                sessionId=event.get('session_id', f"session-{datetime.utcnow().isoformat()}"),
                inputText=query
            )
            
            # Process agent response
            agent_response = self._process_agent_response(response)
            
            return {
                'statusCode': 200,
                'body': {
                    'success': True,
                    'orchestrator': 'agentcore',
                    'agent_response': agent_response
                }
            }
            
        except Exception as e:
            logger.error(f"AgentCore analyst query failed: {e}")
            return {
                'statusCode': 500,
                'body': {
                    'success': False,
                    'orchestrator': 'agentcore',
                    'error': str(e),
                    'error_type': type(e).__name__
                }
            }
    
    def _process_agent_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process Bedrock agent response."""
        try:
            # Extract response from event stream
            completion = ""
            trace = []
            
            for event in response.get('completion', []):
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        completion += chunk['bytes'].decode('utf-8')
                elif 'trace' in event:
                    trace.append(event['trace'])
            
            return {
                'completion': completion,
                'trace': trace,
                'session_id': response.get('sessionId'),
                'response_metadata': response.get('ResponseMetadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            return {
                'error': str(e),
                'raw_response': response
            }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for agent shim.
    
    Expected event format:
    {
        "agent_type": "ingestor" | "analyst_assistant",
        "operation": "workflow" | "query",
        "feed_config": {...},  // For ingestor workflows
        "query": "...",        // For analyst queries
        "session_id": "...",   // Optional session ID
        "workflow_id": "...",  // Optional workflow ID
        "since": "..."         // Optional datetime filter
    }
    """
    try:
        # Determine orchestration mode
        orchestrator_mode = os.environ.get('ORCHESTRATOR', 'direct').lower()
        enable_agents = os.environ.get('ENABLE_AGENTS', 'false').lower() == 'true'
        
        # Override orchestrator mode if agents are disabled
        if not enable_agents:
            orchestrator_mode = 'direct'
        
        logger.info(f"Agent shim executing with orchestrator: {orchestrator_mode}")
        
        # Extract operation details
        agent_type = event.get('agent_type', 'ingestor')
        operation = event.get('operation', 'workflow')
        
        # Route to appropriate orchestrator
        if orchestrator_mode == 'agentcore':
            orchestrator = BedrockAgentCoreOrchestrator()
            
            if agent_type == 'ingestor' and operation == 'workflow':
                return orchestrator.execute_ingestor_workflow(event)
            elif agent_type == 'analyst_assistant' and operation == 'query':
                return orchestrator.execute_analyst_query(event)
            else:
                raise AgentShimError(f"Unsupported operation: {agent_type}/{operation} for AgentCore")
        
        else:  # direct mode
            orchestrator = DirectLambdaOrchestrator()
            
            if agent_type == 'ingestor' and operation == 'workflow':
                return orchestrator.execute_ingestor_workflow(event)
            else:
                raise AgentShimError(f"Unsupported operation: {agent_type}/{operation} for direct orchestration")
        
    except Exception as e:
        logger.error(f"Agent shim execution failed: {e}")
        return {
            'statusCode': 500,
            'body': {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'orchestrator': os.environ.get('ORCHESTRATOR', 'direct')
            }
        }


# For testing
if __name__ == "__main__":
    # Test event for ingestor workflow
    test_event = {
        "agent_type": "ingestor",
        "operation": "workflow",
        "feed_config": {
            "feed_id": "test-feed",
            "feed_url": "https://example.com/feed.xml",
            "target_keywords": ["AWS", "Azure", "security"],
            "notification_recipients": ["test@example.com"]
        },
        "since": "2024-01-01T00:00:00Z",
        "workflow_id": "test-workflow-123"
    }
    
    # Set test environment
    os.environ['ORCHESTRATOR'] = 'direct'
    os.environ['ENABLE_AGENTS'] = 'false'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))