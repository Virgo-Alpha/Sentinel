#!/usr/bin/env python3
"""
Infrastructure validation script for Sentinel Cybersecurity Triage System.
Validates all AWS resources are created correctly with proper configurations.
"""

import boto3
import json
import sys
import argparse
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import subprocess
import os

class InfrastructureValidator:
    """Validates deployed AWS infrastructure."""
    
    def __init__(self, environment: str, region: str = None, verbose: bool = False):
        self.environment = environment
        self.region = region or boto3.Session().region_name or 'us-east-1'
        self.verbose = verbose
        self.validation_results = {}
        
        # Initialize AWS clients
        self.session = boto3.Session(region_name=self.region)
        self.ec2 = self.session.client('ec2')
        self.dynamodb = self.session.client('dynamodb')
        self.s3 = self.session.client('s3')
        self.lambda_client = self.session.client('lambda')
        self.iam = self.session.client('iam')
        self.opensearch = self.session.client('opensearchserverless')
        self.sqs = self.session.client('sqs')
        self.sns = self.session.client('sns')
        self.events = self.session.client('events')
        self.stepfunctions = self.session.client('stepfunctions')
        self.cognito_idp = self.session.client('cognito-idp')
        self.apigateway = self.session.client('apigatewayv2')
        self.amplify = self.session.client('amplify')
        self.cloudwatch = self.session.client('cloudwatch')
        self.xray = self.session.client('xray')
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        prefix = f"[{timestamp}] [{level}]"
        print(f"{prefix} {message}")
        
        if self.verbose and level == "DEBUG":
            print(f"{prefix} {message}")
    
    def get_terraform_outputs(self) -> Dict[str, Any]:
        """Get Terraform outputs for the environment."""
        try:
            # Change to infrastructure directory
            infra_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'infra')
            os.chdir(infra_dir)
            
            # Get Terraform outputs
            result = subprocess.run(
                ['terraform', 'output', '-json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            outputs = json.loads(result.stdout)
            
            # Extract values from Terraform output format
            extracted_outputs = {}
            for key, value in outputs.items():
                if isinstance(value, dict) and 'value' in value:
                    extracted_outputs[key] = value['value']
                else:
                    extracted_outputs[key] = value
            
            return extracted_outputs
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to get Terraform outputs: {e}", "ERROR")
            return {}
        except json.JSONDecodeError as e:
            self.log(f"Failed to parse Terraform outputs: {e}", "ERROR")
            return {}
    
    def validate_vpc_infrastructure(self, outputs: Dict[str, Any]) -> bool:
        """Validate VPC and networking infrastructure."""
        self.log("Validating VPC infrastructure...")
        
        vpc_id = outputs.get('vpc_id')
        if not vpc_id:
            self.log("VPC ID not found in outputs", "ERROR")
            return False
        
        try:
            # Validate VPC
            vpc_response = self.ec2.describe_vpcs(VpcIds=[vpc_id])
            vpc = vpc_response['Vpcs'][0]
            
            if vpc['State'] != 'available':
                self.log(f"VPC {vpc_id} is not in available state: {vpc['State']}", "ERROR")
                return False
            
            self.log(f"✓ VPC validated: {vpc_id} ({vpc['CidrBlock']})")
            
            # Validate subnets
            subnet_ids = outputs.get('private_subnet_ids', [])
            if subnet_ids:
                subnets_response = self.ec2.describe_subnets(SubnetIds=subnet_ids)
                for subnet in subnets_response['Subnets']:
                    if subnet['State'] != 'available':
                        self.log(f"Subnet {subnet['SubnetId']} is not available", "ERROR")
                        return False
                    self.log(f"✓ Subnet validated: {subnet['SubnetId']} ({subnet['CidrBlock']})")
            
            # Validate VPC endpoints
            vpc_endpoints = self.ec2.describe_vpc_endpoints(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            expected_endpoints = ['s3', 'dynamodb', 'lambda', 'monitoring']
            found_endpoints = []
            
            for endpoint in vpc_endpoints['VpcEndpoints']:
                service_name = endpoint['ServiceName'].split('.')[-1]
                found_endpoints.append(service_name)
                if endpoint['State'] != 'available':
                    self.log(f"VPC endpoint {endpoint['VpcEndpointId']} is not available", "ERROR")
                    return False
                self.log(f"✓ VPC endpoint validated: {service_name}")
            
            # Check for missing critical endpoints
            missing_endpoints = set(expected_endpoints) - set(found_endpoints)
            if missing_endpoints:
                self.log(f"Missing VPC endpoints: {missing_endpoints}", "WARNING")
            
            self.validation_results['vpc'] = {
                'status': 'passed',
                'vpc_id': vpc_id,
                'subnets_count': len(subnet_ids),
                'endpoints_count': len(found_endpoints)
            }
            
            return True
            
        except Exception as e:
            self.log(f"VPC validation failed: {e}", "ERROR")
            self.validation_results['vpc'] = {'status': 'failed', 'error': str(e)}
            return False
    
    def validate_dynamodb_tables(self, outputs: Dict[str, Any]) -> bool:
        """Validate DynamoDB tables."""
        self.log("Validating DynamoDB tables...")
        
        expected_tables = {
            'articles_table_name': 'Articles',
            'feeds_table_name': 'Feeds',
            'comments_table_name': 'Comments',
            'memory_table_name': 'Memory'
        }
        
        validated_tables = {}
        
        for output_key, table_type in expected_tables.items():
            table_name = outputs.get(output_key)
            if not table_name:
                self.log(f"{table_type} table name not found in outputs", "WARNING")
                continue
            
            try:
                # Describe table
                response = self.dynamodb.describe_table(TableName=table_name)
                table = response['Table']
                
                # Check table status
                if table['TableStatus'] != 'ACTIVE':
                    self.log(f"Table {table_name} is not active: {table['TableStatus']}", "ERROR")
                    return False
                
                # Validate key schema
                key_schema = {item['AttributeName']: item['KeyType'] for item in table['KeySchema']}
                
                # Check for required attributes based on table type
                if table_type == 'Articles':
                    if 'article_id' not in key_schema or key_schema['article_id'] != 'HASH':
                        self.log(f"Articles table missing correct hash key", "ERROR")
                        return False
                
                # Check GSIs
                gsi_count = len(table.get('GlobalSecondaryIndexes', []))
                
                self.log(f"✓ DynamoDB table validated: {table_name} ({table_type})")
                self.log(f"  Status: {table['TableStatus']}, GSIs: {gsi_count}")
                
                validated_tables[table_type] = {
                    'name': table_name,
                    'status': table['TableStatus'],
                    'gsi_count': gsi_count,
                    'item_count': table.get('ItemCount', 0)
                }
                
            except Exception as e:
                self.log(f"Failed to validate {table_type} table {table_name}: {e}", "ERROR")
                return False
        
        self.validation_results['dynamodb'] = {
            'status': 'passed',
            'tables': validated_tables
        }
        
        return True
    
    def validate_s3_buckets(self, outputs: Dict[str, Any]) -> bool:
        """Validate S3 buckets."""
        self.log("Validating S3 buckets...")
        
        bucket_outputs = [
            'artifacts_bucket_name',
            'raw_content_bucket_name',
            'normalized_content_bucket_name',
            'traces_bucket_name'
        ]
        
        validated_buckets = {}
        
        for bucket_output in bucket_outputs:
            bucket_name = outputs.get(bucket_output)
            if not bucket_name:
                self.log(f"Bucket name not found for {bucket_output}", "WARNING")
                continue
            
            try:
                # Check if bucket exists and is accessible
                self.s3.head_bucket(Bucket=bucket_name)
                
                # Check bucket encryption
                try:
                    encryption = self.s3.get_bucket_encryption(Bucket=bucket_name)
                    encryption_status = "enabled"
                except self.s3.exceptions.ClientError:
                    encryption_status = "disabled"
                    self.log(f"Bucket {bucket_name} does not have encryption enabled", "WARNING")
                
                # Check bucket versioning
                versioning = self.s3.get_bucket_versioning(Bucket=bucket_name)
                versioning_status = versioning.get('Status', 'Disabled')
                
                # Check bucket policy
                try:
                    self.s3.get_bucket_policy(Bucket=bucket_name)
                    policy_status = "configured"
                except self.s3.exceptions.ClientError:
                    policy_status = "not_configured"
                
                self.log(f"✓ S3 bucket validated: {bucket_name}")
                self.log(f"  Encryption: {encryption_status}, Versioning: {versioning_status}")
                
                validated_buckets[bucket_output] = {
                    'name': bucket_name,
                    'encryption': encryption_status,
                    'versioning': versioning_status,
                    'policy': policy_status
                }
                
            except Exception as e:
                self.log(f"Failed to validate S3 bucket {bucket_name}: {e}", "ERROR")
                return False
        
        self.validation_results['s3'] = {
            'status': 'passed',
            'buckets': validated_buckets
        }
        
        return True
    
    def validate_lambda_functions(self, outputs: Dict[str, Any]) -> bool:
        """Validate Lambda functions."""
        self.log("Validating Lambda functions...")
        
        function_names = outputs.get('lambda_function_names', [])
        if not function_names:
            self.log("No Lambda function names found in outputs", "WARNING")
            return True
        
        validated_functions = {}
        
        for function_name in function_names:
            try:
                # Get function configuration
                response = self.lambda_client.get_function(FunctionName=function_name)
                config = response['Configuration']
                
                # Check function state
                if config['State'] != 'Active':
                    self.log(f"Lambda function {function_name} is not active: {config['State']}", "ERROR")
                    return False
                
                # Check runtime
                runtime = config['Runtime']
                if not runtime.startswith('python'):
                    self.log(f"Lambda function {function_name} has unexpected runtime: {runtime}", "WARNING")
                
                # Check memory and timeout
                memory_size = config['MemorySize']
                timeout = config['Timeout']
                
                # Check VPC configuration
                vpc_config = config.get('VpcConfig', {})
                vpc_configured = bool(vpc_config.get('VpcId'))
                
                # Check environment variables
                env_vars = config.get('Environment', {}).get('Variables', {})
                
                # Check X-Ray tracing
                tracing_config = config.get('TracingConfig', {})
                xray_enabled = tracing_config.get('Mode') == 'Active'
                
                self.log(f"✓ Lambda function validated: {function_name}")
                self.log(f"  Runtime: {runtime}, Memory: {memory_size}MB, Timeout: {timeout}s")
                self.log(f"  VPC: {vpc_configured}, X-Ray: {xray_enabled}")
                
                validated_functions[function_name] = {
                    'state': config['State'],
                    'runtime': runtime,
                    'memory_size': memory_size,
                    'timeout': timeout,
                    'vpc_configured': vpc_configured,
                    'xray_enabled': xray_enabled,
                    'env_vars_count': len(env_vars)
                }
                
            except Exception as e:
                self.log(f"Failed to validate Lambda function {function_name}: {e}", "ERROR")
                return False
        
        self.validation_results['lambda'] = {
            'status': 'passed',
            'functions': validated_functions
        }
        
        return True
    
    def validate_opensearch_serverless(self, outputs: Dict[str, Any]) -> bool:
        """Validate OpenSearch Serverless collection."""
        self.log("Validating OpenSearch Serverless...")
        
        collection_name = outputs.get('opensearch_collection_name')
        if not collection_name:
            self.log("OpenSearch collection name not found in outputs", "WARNING")
            return True
        
        try:
            # Get collection details
            response = self.opensearch.batch_get_collection(names=[collection_name])
            
            if not response['collectionDetails']:
                self.log(f"OpenSearch collection {collection_name} not found", "ERROR")
                return False
            
            collection = response['collectionDetails'][0]
            
            # Check collection status
            if collection['status'] != 'ACTIVE':
                self.log(f"OpenSearch collection {collection_name} is not active: {collection['status']}", "ERROR")
                return False
            
            # Get collection endpoint
            collection_endpoint = collection.get('collectionEndpoint', '')
            
            self.log(f"✓ OpenSearch Serverless collection validated: {collection_name}")
            self.log(f"  Status: {collection['status']}, Type: {collection['type']}")
            
            self.validation_results['opensearch'] = {
                'status': 'passed',
                'collection_name': collection_name,
                'collection_status': collection['status'],
                'collection_type': collection['type'],
                'endpoint': collection_endpoint
            }
            
            return True
            
        except Exception as e:
            self.log(f"Failed to validate OpenSearch Serverless collection: {e}", "ERROR")
            self.validation_results['opensearch'] = {'status': 'failed', 'error': str(e)}
            return False
    
    def validate_iam_roles(self, outputs: Dict[str, Any]) -> bool:
        """Validate IAM roles and policies."""
        self.log("Validating IAM roles...")
        
        lambda_execution_roles = outputs.get('lambda_execution_roles', [])
        if not lambda_execution_roles:
            self.log("No Lambda execution roles found in outputs", "WARNING")
            return True
        
        validated_roles = {}
        
        for role_arn in lambda_execution_roles:
            role_name = role_arn.split('/')[-1]
            
            try:
                # Get role details
                role_response = self.iam.get_role(RoleName=role_name)
                role = role_response['Role']
                
                # Get attached policies
                policies_response = self.iam.list_attached_role_policies(RoleName=role_name)
                attached_policies = policies_response['AttachedPolicies']
                
                # Get inline policies
                inline_policies_response = self.iam.list_role_policies(RoleName=role_name)
                inline_policies = inline_policies_response['PolicyNames']
                
                self.log(f"✓ IAM role validated: {role_name}")
                self.log(f"  Attached policies: {len(attached_policies)}, Inline policies: {len(inline_policies)}")
                
                validated_roles[role_name] = {
                    'arn': role['Arn'],
                    'attached_policies_count': len(attached_policies),
                    'inline_policies_count': len(inline_policies),
                    'created_date': role['CreateDate'].isoformat()
                }
                
            except Exception as e:
                self.log(f"Failed to validate IAM role {role_name}: {e}", "ERROR")
                return False
        
        self.validation_results['iam'] = {
            'status': 'passed',
            'roles': validated_roles
        }
        
        return True
    
    def validate_step_functions(self, outputs: Dict[str, Any]) -> bool:
        """Validate Step Functions state machines."""
        self.log("Validating Step Functions...")
        
        state_machine_arn = outputs.get('step_function_arn')
        if not state_machine_arn:
            self.log("Step Function ARN not found in outputs", "WARNING")
            return True
        
        try:
            # Describe state machine
            response = self.stepfunctions.describe_state_machine(stateMachineArn=state_machine_arn)
            
            # Check status
            status = response['status']
            if status != 'ACTIVE':
                self.log(f"Step Function is not active: {status}", "ERROR")
                return False
            
            self.log(f"✓ Step Function validated: {response['name']}")
            self.log(f"  Status: {status}, Type: {response['type']}")
            
            self.validation_results['step_functions'] = {
                'status': 'passed',
                'state_machine_arn': state_machine_arn,
                'state_machine_status': status,
                'state_machine_type': response['type']
            }
            
            return True
            
        except Exception as e:
            self.log(f"Failed to validate Step Functions: {e}", "ERROR")
            self.validation_results['step_functions'] = {'status': 'failed', 'error': str(e)}
            return False
    
    def validate_monitoring_setup(self, outputs: Dict[str, Any]) -> bool:
        """Validate CloudWatch and X-Ray setup."""
        self.log("Validating monitoring setup...")
        
        try:
            # Check CloudWatch dashboards
            dashboards = self.cloudwatch.list_dashboards()
            sentinel_dashboards = [d for d in dashboards['DashboardEntries'] 
                                 if 'sentinel' in d['DashboardName'].lower()]
            
            # Check X-Ray service map
            try:
                service_map = self.xray.get_service_graph(
                    StartTime=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
                    EndTime=datetime.now(timezone.utc)
                )
                xray_services = len(service_map.get('Services', []))
            except Exception:
                xray_services = 0
            
            self.log(f"✓ Monitoring setup validated")
            self.log(f"  CloudWatch dashboards: {len(sentinel_dashboards)}")
            self.log(f"  X-Ray services: {xray_services}")
            
            self.validation_results['monitoring'] = {
                'status': 'passed',
                'cloudwatch_dashboards': len(sentinel_dashboards),
                'xray_services': xray_services
            }
            
            return True
            
        except Exception as e:
            self.log(f"Failed to validate monitoring setup: {e}", "ERROR")
            self.validation_results['monitoring'] = {'status': 'failed', 'error': str(e)}
            return False
    
    def test_lambda_execution(self, outputs: Dict[str, Any]) -> bool:
        """Test Lambda function execution."""
        self.log("Testing Lambda function execution...")
        
        function_names = outputs.get('lambda_function_names', [])
        if not function_names:
            self.log("No Lambda functions to test", "WARNING")
            return True
        
        test_results = {}
        
        for function_name in function_names[:3]:  # Test first 3 functions
            try:
                # Create test payload
                test_payload = {
                    "test": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "environment": self.environment
                }
                
                # Invoke function
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(test_payload)
                )
                
                # Check response
                status_code = response['StatusCode']
                if status_code == 200:
                    self.log(f"✓ Lambda function test passed: {function_name}")
                    test_results[function_name] = {'status': 'passed', 'status_code': status_code}
                else:
                    self.log(f"Lambda function test failed: {function_name} (status: {status_code})", "ERROR")
                    test_results[function_name] = {'status': 'failed', 'status_code': status_code}
                
            except Exception as e:
                self.log(f"Failed to test Lambda function {function_name}: {e}", "ERROR")
                test_results[function_name] = {'status': 'error', 'error': str(e)}
        
        self.validation_results['lambda_tests'] = test_results
        return True
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        report = {
            'validation_summary': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'environment': self.environment,
                'region': self.region,
                'overall_status': 'passed' if all(
                    result.get('status') == 'passed' 
                    for result in self.validation_results.values()
                    if isinstance(result, dict) and 'status' in result
                ) else 'failed'
            },
            'validation_results': self.validation_results,
            'recommendations': []
        }
        
        # Add recommendations based on validation results
        if self.validation_results.get('vpc', {}).get('status') != 'passed':
            report['recommendations'].append("Review VPC configuration and ensure all required resources are created")
        
        if self.validation_results.get('opensearch', {}).get('status') != 'passed':
            report['recommendations'].append("Verify OpenSearch Serverless collection configuration and access policies")
        
        # Check for warnings
        warning_count = sum(1 for result in self.validation_results.values() 
                          if isinstance(result, dict) and result.get('status') == 'warning')
        
        if warning_count > 0:
            report['recommendations'].append(f"Address {warning_count} validation warnings for optimal performance")
        
        return report
    
    def run_full_validation(self) -> bool:
        """Run complete infrastructure validation."""
        self.log(f"Starting infrastructure validation for environment: {self.environment}")
        
        # Get Terraform outputs
        outputs = self.get_terraform_outputs()
        if not outputs:
            self.log("Failed to get Terraform outputs", "ERROR")
            return False
        
        validation_steps = [
            ("VPC Infrastructure", self.validate_vpc_infrastructure),
            ("DynamoDB Tables", self.validate_dynamodb_tables),
            ("S3 Buckets", self.validate_s3_buckets),
            ("Lambda Functions", self.validate_lambda_functions),
            ("OpenSearch Serverless", self.validate_opensearch_serverless),
            ("IAM Roles", self.validate_iam_roles),
            ("Step Functions", self.validate_step_functions),
            ("Monitoring Setup", self.validate_monitoring_setup),
            ("Lambda Execution Tests", self.test_lambda_execution)
        ]
        
        all_passed = True
        
        for step_name, validation_func in validation_steps:
            self.log(f"\n--- {step_name} ---")
            try:
                if not validation_func(outputs):
                    all_passed = False
                    self.log(f"{step_name} validation failed", "ERROR")
            except Exception as e:
                self.log(f"{step_name} validation error: {e}", "ERROR")
                all_passed = False
        
        # Generate and save validation report
        report = self.generate_validation_report()
        
        # Save report to file
        report_filename = f"validation-report-{self.environment}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(os.path.dirname(__file__), '..', 'logs', report_filename)
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.log(f"\nValidation report saved to: {report_path}")
        
        # Print summary
        self.log(f"\n{'='*50}")
        self.log(f"VALIDATION SUMMARY")
        self.log(f"{'='*50}")
        self.log(f"Environment: {self.environment}")
        self.log(f"Overall Status: {'PASSED' if all_passed else 'FAILED'}")
        self.log(f"Validation Steps: {len(validation_steps)}")
        self.log(f"Report: {report_path}")
        
        if report['recommendations']:
            self.log(f"\nRecommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                self.log(f"  {i}. {rec}")
        
        return all_passed

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Validate Sentinel infrastructure deployment")
    parser.add_argument('-e', '--environment', required=True, 
                       choices=['dev', 'staging', 'prod'],
                       help='Target environment')
    parser.add_argument('-r', '--region', 
                       help='AWS region (default: from AWS config)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Create validator
    validator = InfrastructureValidator(
        environment=args.environment,
        region=args.region,
        verbose=args.verbose
    )
    
    # Run validation
    success = validator.run_full_validation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()