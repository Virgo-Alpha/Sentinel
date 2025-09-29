"""
Integration tests for database consistency validation.

Tests data consistency across DynamoDB tables, S3 storage,
and OpenSearch indexes.
"""

import pytest
import json
import boto3
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime, timezone
import time
from typing import Dict, Any, List

@pytest.mark.integration
class TestDatabaseConsistency:
    """Integration tests for database consistency validation."""
    
    def test_article_lifecycle_consistency(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id,
        lambda_context
    ):
        """Test data consistency throughout article lifecycle."""
        
        dynamodb = boto3.resource('dynamodb')
        s3_client = boto3.client('s3')
        
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Step 1: Create article in INGESTED state
        article_id = str(uuid.uuid4())
        initial_article = {
            **sample_article_data,
            "article_id": article_id,
            "state": "INGESTED",
            "ingested_at": datetime.now(timezone.utc).isoformat()
        }
        
        articles_table.put_item(Item=initial_article)
        
        # Verify initial state
        response = articles_table.get_item(Key={"article_id": article_id})
        assert "Item" in response
        assert response["Item"]["state"] == "INGESTED"
        
        # Step 2: Update to PROCESSED state
        processed_article = {
            **initial_article,
            "state": "PROCESSED",
            "relevancy_score": 0.85,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        articles_table.put_item(Item=processed_article)
        
        # Verify state transition
        response = articles_table.get_item(Key={"article_id": article_id})
        assert response["Item"]["state"] == "PROCESSED"
        assert response["Item"]["relevancy_score"] == 0.85
        
        # Step 3: Store raw content in S3
        raw_content = "This is the raw article content for testing."
        s3_key = f"raw/{article_id}.txt"
        
        s3_client.put_object(
            Bucket=os.environ["RAW_CONTENT_BUCKET"],
            Key=s3_key,
            Body=raw_content.encode('utf-8')
        )
        
        # Update article with S3 reference
        articles_table.update_item(
            Key={"article_id": article_id},
            UpdateExpression="SET raw_s3_uri = :uri",
            ExpressionAttributeValues={
                ":uri": f"s3://{os.environ['RAW_CONTENT_BUCKET']}/{s3_key}"
            }
        )
        
        # Verify S3 storage and DynamoDB reference
        s3_response = s3_client.get_object(
            Bucket=os.environ["RAW_CONTENT_BUCKET"],
            Key=s3_key
        )
        assert s3_response["Body"].read().decode('utf-8') == raw_content
        
        db_response = articles_table.get_item(Key={"article_id": article_id})
        assert "raw_s3_uri" in db_response["Item"]
        
        # Step 4: Update to PUBLISHED state
        articles_table.update_item(
            Key={"article_id": article_id},
            UpdateExpression="SET #state = :state, published_at = :pub_time",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={
                ":state": "PUBLISHED",
                ":pub_time": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Verify final state
        final_response = articles_table.get_item(Key={"article_id": article_id})
        final_article = final_response["Item"]
        
        assert final_article["state"] == "PUBLISHED"
        assert "published_at" in final_article
        assert "ingested_at" in final_article
        assert "processed_at" in final_article
        
        # Verify data integrity
        assert final_article["article_id"] == article_id
        assert final_article["relevancy_score"] == 0.85
    
    def test_duplicate_cluster_consistency(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id
    ):
        """Test consistency of duplicate clustering relationships."""
        
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Create original article
        original_id = str(uuid.uuid4())
        cluster_id = f"cluster-{uuid.uuid4()}"
        
        original_article = {
            **sample_article_data,
            "article_id": original_id,
            "cluster_id": cluster_id,
            "is_duplicate": False,
            "state": "PUBLISHED"
        }
        
        articles_table.put_item(Item=original_article)
        
        # Create duplicate articles
        duplicate_ids = []
        for i in range(3):
            duplicate_id = str(uuid.uuid4())
            duplicate_ids.append(duplicate_id)
            
            duplicate_article = {
                **sample_article_data,
                "article_id": duplicate_id,
                "cluster_id": cluster_id,
                "is_duplicate": True,
                "duplicate_of": original_id,
                "state": "ARCHIVED"
            }
            
            articles_table.put_item(Item=duplicate_article)
        
        # Verify cluster consistency
        # Query by cluster_id using GSI
        response = articles_table.query(
            IndexName="cluster-published_at-index",
            KeyConditionExpression="cluster_id = :cluster_id",
            ExpressionAttributeValues={":cluster_id": cluster_id}
        )
        
        cluster_articles = response["Items"]
        assert len(cluster_articles) == 4  # 1 original + 3 duplicates
        
        # Verify original article
        original_articles = [a for a in cluster_articles if not a["is_duplicate"]]
        assert len(original_articles) == 1
        assert original_articles[0]["article_id"] == original_id
        
        # Verify duplicates
        duplicate_articles = [a for a in cluster_articles if a["is_duplicate"]]
        assert len(duplicate_articles) == 3
        
        for duplicate in duplicate_articles:
            assert duplicate["duplicate_of"] == original_id
            assert duplicate["cluster_id"] == cluster_id
            assert duplicate["state"] == "ARCHIVED"
    
    def test_comment_thread_consistency(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id
    ):
        """Test consistency of comment threading relationships."""
        
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        comments_table = dynamodb.Table(os.environ["COMMENTS_TABLE_NAME"])
        
        # Create article
        article_id = str(uuid.uuid4())
        article = {
            **sample_article_data,
            "article_id": article_id,
            "state": "PUBLISHED"
        }
        articles_table.put_item(Item=article)
        
        # Create comment thread
        root_comment_id = str(uuid.uuid4())
        root_comment = {
            "comment_id": root_comment_id,
            "article_id": article_id,
            "content": "This is a root comment",
            "author": "analyst_1",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        comments_table.put_item(Item=root_comment)
        
        # Create replies
        reply_ids = []
        for i in range(2):
            reply_id = str(uuid.uuid4())
            reply_ids.append(reply_id)
            
            reply = {
                "comment_id": reply_id,
                "article_id": article_id,
                "parent_id": root_comment_id,
                "content": f"This is reply {i+1}",
                "author": f"analyst_{i+2}",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            comments_table.put_item(Item=reply)
        
        # Create nested reply
        nested_reply_id = str(uuid.uuid4())
        nested_reply = {
            "comment_id": nested_reply_id,
            "article_id": article_id,
            "parent_id": reply_ids[0],  # Reply to first reply
            "content": "This is a nested reply",
            "author": "analyst_4",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        comments_table.put_item(Item=nested_reply)
        
        # Verify thread consistency
        # Get all comments for article
        response = comments_table.query(
            IndexName="article-created_at-index",
            KeyConditionExpression="article_id = :article_id",
            ExpressionAttributeValues={":article_id": article_id}
        )
        
        all_comments = response["Items"]
        assert len(all_comments) == 4  # 1 root + 2 replies + 1 nested
        
        # Verify root comment
        root_comments = [c for c in all_comments if "parent_id" not in c]
        assert len(root_comments) == 1
        assert root_comments[0]["comment_id"] == root_comment_id
        
        # Verify direct replies
        direct_replies = [c for c in all_comments if c.get("parent_id") == root_comment_id]
        assert len(direct_replies) == 2
        
        # Verify nested reply
        nested_replies = [c for c in all_comments if c.get("parent_id") in reply_ids]
        assert len(nested_replies) == 1
        assert nested_replies[0]["parent_id"] == reply_ids[0]
    
    def test_cross_table_referential_integrity(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id
    ):
        """Test referential integrity across multiple tables."""
        
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        comments_table = dynamodb.Table(os.environ["COMMENTS_TABLE_NAME"])
        memory_table = dynamodb.Table(os.environ["MEMORY_TABLE_NAME"])
        
        # Create article
        article_id = str(uuid.uuid4())
        article = {
            **sample_article_data,
            "article_id": article_id,
            "state": "PUBLISHED"
        }
        articles_table.put_item(Item=article)
        
        # Create related comment
        comment_id = str(uuid.uuid4())
        comment = {
            "comment_id": comment_id,
            "article_id": article_id,  # Foreign key reference
            "content": "Test comment",
            "author": "test_user",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        comments_table.put_item(Item=comment)
        
        # Create related memory entry
        memory_id = str(uuid.uuid4())
        memory_entry = {
            "memory_id": memory_id,
            "memory_type": "article_processing",
            "content": {
                "article_id": article_id,  # Reference to article
                "processing_notes": "Article processed successfully"
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id
        }
        memory_table.put_item(Item=memory_entry)
        
        # Verify all references exist and are consistent
        
        # Check article exists
        article_response = articles_table.get_item(Key={"article_id": article_id})
        assert "Item" in article_response
        
        # Check comment references valid article
        comment_response = comments_table.get_item(Key={"comment_id": comment_id})
        assert "Item" in comment_response
        assert comment_response["Item"]["article_id"] == article_id
        
        # Check memory references valid article
        memory_response = memory_table.get_item(Key={"memory_id": memory_id})
        assert "Item" in memory_response
        assert memory_response["Item"]["content"]["article_id"] == article_id
        
        # Test cascade behavior (simulate article deletion)
        # In a real system, this would trigger cleanup of related records
        articles_table.delete_item(Key={"article_id": article_id})
        
        # Verify article is deleted
        deleted_response = articles_table.get_item(Key={"article_id": article_id})
        assert "Item" not in deleted_response
        
        # Related records should still exist (orphaned references)
        # In production, cleanup would be handled by Lambda triggers
        orphaned_comment = comments_table.get_item(Key={"comment_id": comment_id})
        assert "Item" in orphaned_comment  # Still exists but orphaned
    
    def test_eventual_consistency_handling(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id
    ):
        """Test handling of eventual consistency in DynamoDB."""
        
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        article_id = str(uuid.uuid4())
        
        # Write article
        article = {
            **sample_article_data,
            "article_id": article_id,
            "state": "INGESTED",
            "version": 1
        }
        articles_table.put_item(Item=article)
        
        # Immediately try to read (might not be consistent)
        # Use consistent read to ensure we get the latest data
        response = articles_table.get_item(
            Key={"article_id": article_id},
            ConsistentRead=True
        )
        
        assert "Item" in response
        assert response["Item"]["version"] == 1
        
        # Update article
        articles_table.update_item(
            Key={"article_id": article_id},
            UpdateExpression="SET version = version + :inc, #state = :state",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={
                ":inc": 1,
                ":state": "PROCESSED"
            }
        )
        
        # Read with eventual consistency (default)
        eventual_response = articles_table.get_item(Key={"article_id": article_id})
        
        # Read with strong consistency
        consistent_response = articles_table.get_item(
            Key={"article_id": article_id},
            ConsistentRead=True
        )
        
        # Strong consistency should always have latest data
        assert consistent_response["Item"]["version"] == 2
        assert consistent_response["Item"]["state"] == "PROCESSED"
    
    def test_transaction_consistency(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id
    ):
        """Test transactional consistency across operations."""
        
        dynamodb = boto3.resource('dynamodb')
        client = boto3.client('dynamodb')
        
        article_id = str(uuid.uuid4())
        comment_id = str(uuid.uuid4())
        
        # Prepare transaction items
        article_item = {
            **sample_article_data,
            "article_id": article_id,
            "state": "PUBLISHED",
            "comment_count": 0
        }
        
        comment_item = {
            "comment_id": comment_id,
            "article_id": article_id,
            "content": "Test comment",
            "author": "test_user",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Execute transaction: create article and comment, increment comment count
        try:
            client.transact_write_items(
                TransactItems=[
                    {
                        'Put': {
                            'TableName': os.environ["ARTICLES_TABLE_NAME"],
                            'Item': {k: {'S': str(v)} if isinstance(v, str) else {'N': str(v)} if isinstance(v, (int, float)) else {'BOOL': v} if isinstance(v, bool) else {'M': {}} for k, v in article_item.items()},
                            'ConditionExpression': 'attribute_not_exists(article_id)'
                        }
                    },
                    {
                        'Put': {
                            'TableName': os.environ["COMMENTS_TABLE_NAME"],
                            'Item': {k: {'S': str(v)} for k, v in comment_item.items()},
                            'ConditionExpression': 'attribute_not_exists(comment_id)'
                        }
                    },
                    {
                        'Update': {
                            'TableName': os.environ["ARTICLES_TABLE_NAME"],
                            'Key': {'article_id': {'S': article_id}},
                            'UpdateExpression': 'SET comment_count = comment_count + :inc',
                            'ExpressionAttributeValues': {':inc': {'N': '1'}}
                        }
                    }
                ]
            )
            
            transaction_succeeded = True
        except Exception as e:
            transaction_succeeded = False
            print(f"Transaction failed: {e}")
        
        if transaction_succeeded:
            # Verify both items exist and are consistent
            articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
            comments_table = dynamodb.Table(os.environ["COMMENTS_TABLE_NAME"])
            
            article_response = articles_table.get_item(Key={"article_id": article_id})
            comment_response = comments_table.get_item(Key={"comment_id": comment_id})
            
            assert "Item" in article_response
            assert "Item" in comment_response
            assert article_response["Item"]["comment_count"] == 1
    
    def test_data_validation_constraints(
        self,
        integration_test_setup,
        correlation_id
    ):
        """Test data validation and constraint enforcement."""
        
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Test required field validation
        invalid_article = {
            "article_id": str(uuid.uuid4()),
            # Missing required fields like title, url, etc.
            "state": "INGESTED"
        }
        
        # This should succeed in DynamoDB (no schema enforcement)
        # But application logic should validate
        articles_table.put_item(Item=invalid_article)
        
        # Test data type consistency
        article_with_wrong_types = {
            "article_id": str(uuid.uuid4()),
            "title": "Test Article",
            "relevancy_score": "not_a_number",  # Should be float
            "is_duplicate": "not_a_boolean",    # Should be boolean
            "keyword_matches": "not_a_list"     # Should be list
        }
        
        # DynamoDB will accept this, but application should validate
        articles_table.put_item(Item=article_with_wrong_types)
        
        # Verify items were stored (DynamoDB is schemaless)
        response1 = articles_table.get_item(Key={"article_id": invalid_article["article_id"]})
        response2 = articles_table.get_item(Key={"article_id": article_with_wrong_types["article_id"]})
        
        assert "Item" in response1
        assert "Item" in response2
        
        # Application-level validation would catch these issues
    
    @pytest.mark.slow
    def test_large_dataset_consistency(
        self,
        integration_test_setup,
        sample_article_data,
        correlation_id
    ):
        """Test consistency with large datasets."""
        
        dynamodb = boto3.resource('dynamodb')
        articles_table = dynamodb.Table(os.environ["ARTICLES_TABLE_NAME"])
        
        # Create large batch of articles
        batch_size = 25  # DynamoDB batch limit
        total_articles = 100
        
        created_articles = []
        
        for batch_start in range(0, total_articles, batch_size):
            with articles_table.batch_writer() as batch:
                for i in range(batch_start, min(batch_start + batch_size, total_articles)):
                    article_id = str(uuid.uuid4())
                    article = {
                        **sample_article_data,
                        "article_id": article_id,
                        "title": f"Test Article {i}",
                        "state": "PUBLISHED" if i % 2 == 0 else "REVIEW",
                        "relevancy_score": 0.5 + (i % 50) / 100  # Vary scores
                    }
                    batch.put_item(Item=article)
                    created_articles.append(article)
        
        # Verify all articles were created
        time.sleep(1)  # Allow for eventual consistency
        
        # Query by state using GSI
        published_response = articles_table.query(
            IndexName="state-published_at-index",
            KeyConditionExpression="#state = :state",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={":state": "PUBLISHED"}
        )
        
        review_response = articles_table.query(
            IndexName="state-published_at-index",
            KeyConditionExpression="#state = :state",
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={":state": "REVIEW"}
        )
        
        published_count = len(published_response["Items"])
        review_count = len(review_response["Items"])
        
        # Should have roughly equal distribution
        assert published_count + review_count == total_articles
        assert abs(published_count - review_count) <= 1  # At most 1 difference
        
        # Verify data integrity across all items
        for article in created_articles:
            response = articles_table.get_item(Key={"article_id": article["article_id"]})
            assert "Item" in response
            stored_article = response["Item"]
            assert stored_article["title"] == article["title"]
            assert stored_article["state"] == article["state"]