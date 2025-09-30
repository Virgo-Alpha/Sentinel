# Design Document

## Overview

This design addresses systematic Terraform infrastructure configuration errors across multiple modules and variable declarations. The errors fall into six main categories: missing variable declarations, deprecated resource attributes, unsupported resource types, inconsistent conditional logic, invalid block types, and S3 lifecycle configuration issues.

The solution involves a methodical approach to fix each category of errors while maintaining infrastructure functionality and following AWS provider best practices.

## Architecture

### Error Categories and Solutions

#### 1. Variable Declaration Issues
**Problem**: 52 variables defined in tfvars files but not declared in variables.tf
**Solution**: Add missing variable declarations with proper types, descriptions, and validation rules

#### 2. API Gateway Configuration Issues  
**Problem**: Deprecated attributes `access_log_destination_arn` and `access_log_format` in aws_api_gateway_stage
**Solution**: Replace with proper `access_log_settings` block structure

#### 3. Monitoring Module Issues
**Problem**: 
- Unsupported resource type `aws_ce_anomaly_detector` 
- Missing resource reference `aws_xray_sampling_rule.main`
**Solution**: 
- Use correct resource type `aws_ce_anomaly_detector` (verify provider version)
- Add missing X-Ray sampling rule resource

#### 4. Step Functions Conditional Logic Issues
**Problem**: Inconsistent object structures in conditional expressions for agent vs non-agent workflows
**Solution**: Ensure both branches of conditional expressions have consistent object attribute structures

#### 5. WAF Configuration Issues
**Problem**: Invalid `excluded_rule` block type in aws_wafv2_web_acl
**Solution**: Use correct `rule_action_override` structure for excluding rules

#### 6. S3 Lifecycle Configuration Issues
**Problem**: Missing required filter or prefix attributes in lifecycle rules
**Solution**: Add proper filter blocks to lifecycle configuration rules

## Components and Interfaces

### 1. Variable Declaration Component
- **Input**: tfvars files with variable assignments
- **Output**: Complete variables.tf with all required declarations
- **Interface**: Terraform variable validation and type checking

### 2. API Gateway Configuration Component
- **Input**: Current stage configuration with deprecated attributes
- **Output**: Updated stage configuration with access_log_settings block
- **Interface**: AWS API Gateway service compatibility

### 3. Monitoring Configuration Component
- **Input**: Current monitoring module with invalid resources
- **Output**: Fixed monitoring module with correct resource types and references
- **Interface**: AWS CloudWatch and X-Ray services

### 4. Step Functions Workflow Component
- **Input**: Conditional state machine definitions with type inconsistencies
- **Output**: Consistent conditional logic with proper object structures
- **Interface**: AWS Step Functions state machine validation

### 5. WAF Security Component
- **Input**: WAF configuration with invalid block types
- **Output**: Corrected WAF configuration with proper rule structures
- **Interface**: AWS WAFv2 service compatibility

### 6. S3 Storage Component
- **Input**: S3 lifecycle configurations missing required attributes
- **Output**: Complete lifecycle configurations with proper filter blocks
- **Interface**: AWS S3 service lifecycle management

## Data Models

### Variable Declaration Model
```hcl
variable "variable_name" {
  description = "Clear description of purpose"
  type        = appropriate_type
  default     = sensible_default
  
  validation {
    condition     = validation_rule
    error_message = "Clear error message"
  }
}
```

### API Gateway Access Logging Model
```hcl
access_log_settings {
  destination_arn = log_group_arn
  format = jsonencode({
    # Log format specification
  })
}
```

### Step Functions State Model
```hcl
States = merge(
  condition ? {
    # Consistent object structure
    StateA = { /* definition */ }
    StateB = { /* definition */ }
  } : {},
  !condition ? {
    # Matching object structure
    StateA = { /* alternative definition */ }
    StateB = { /* alternative definition */ }
  } : {}
)
```

### WAF Rule Override Model
```hcl
rule_action_override {
  action_to_use {
    allow {}
  }
  name = "rule_name"
}
```

### S3 Lifecycle Filter Model
```hcl
rule {
  id     = "rule_id"
  status = "Enabled"
  
  filter {
    prefix = "path/prefix/"
  }
  
  # Lifecycle actions
}
```

## Error Handling

### Variable Validation Errors
- **Detection**: Terraform plan warnings about undeclared variables
- **Handling**: Add variable declarations with appropriate types and validation
- **Recovery**: Validate all variables are properly declared and typed

### Resource Configuration Errors
- **Detection**: Terraform plan errors about unsupported attributes/resources
- **Handling**: Update to current AWS provider syntax and supported resources
- **Recovery**: Verify all resources use current provider specifications

### Conditional Logic Errors
- **Detection**: Type inconsistency errors in conditional expressions
- **Handling**: Ensure both branches have matching object structures
- **Recovery**: Test both conditional paths for proper execution

### Syntax Validation Errors
- **Detection**: Invalid block type or attribute errors
- **Handling**: Update to correct Terraform and AWS provider syntax
- **Recovery**: Run terraform validate to confirm syntax correctness

## Testing Strategy

### 1. Syntax Validation Testing
- Run `terraform validate` after each fix
- Verify no syntax errors remain
- Test in isolated module environments

### 2. Plan Validation Testing  
- Run `terraform plan` with fixed configurations
- Verify no errors or warnings
- Confirm all resources can be planned successfully

### 3. Provider Compatibility Testing
- Verify all resources use supported AWS provider features
- Test with current provider version constraints
- Validate resource attribute compatibility

### 4. Conditional Logic Testing
- Test both enabled and disabled feature flag scenarios
- Verify state machine definitions work in both modes
- Validate consistent object structures

### 5. Integration Testing
- Test module interactions after fixes
- Verify data flow between fixed components
- Confirm end-to-end infrastructure provisioning

### 6. Regression Testing
- Ensure fixes don't break existing functionality
- Validate backward compatibility where possible
- Test with existing state files

## Implementation Approach

### Phase 1: Variable Declarations
1. Analyze all tfvars files to identify missing variables
2. Add variable declarations with proper types and validation
3. Organize variables by functional groups
4. Test variable validation rules

### Phase 2: Resource Configuration Fixes
1. Fix API Gateway stage configuration
2. Update monitoring module resources
3. Correct WAF rule configurations
4. Fix S3 lifecycle configurations

### Phase 3: Conditional Logic Fixes
1. Analyze Step Functions conditional expressions
2. Ensure consistent object structures in both branches
3. Test agent and non-agent workflow paths
4. Validate state machine definitions

### Phase 4: Validation and Testing
1. Run comprehensive terraform validate
2. Execute terraform plan without errors
3. Verify all modules work together
4. Test with different environment configurations

## Dependencies

- AWS Provider version ~> 5.0 compatibility
- Terraform version compatibility for conditional expressions
- Existing infrastructure state compatibility
- Module interdependency management

## Risk Mitigation

- **State File Safety**: Test changes in isolated environments first
- **Backward Compatibility**: Ensure existing deployments aren't broken
- **Incremental Deployment**: Fix and test one module at a time
- **Rollback Plan**: Maintain ability to revert to previous working state
- **Documentation**: Document all changes for future maintenance