"""
Locust load testing script for Sentinel web application.
Run with: locust -f tests/performance/locustfile.py --host=http://localhost:3000
"""

from locust import HttpUser, task, between, events
import json
import random
import uuid
from datetime import datetime, timezone

class SentinelWebUser(HttpUser):
    """Simulates a user interacting with the Sentinel web application."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Called when a user starts. Perform login/setup here."""
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"
        self.session_id = str(uuid.uuid4())
        
        # Simulate login
        self.login()
        
        # Initialize user preferences
        self.preferred_sources = random.sample(['CISA', 'NCSC', 'Microsoft', 'ANSSI', 'GoogleTAG'], 3)
        self.relevancy_threshold = random.uniform(0.6, 0.9)
    
    def login(self):
        """Simulate user login."""
        login_data = {
            "username": self.user_id,
            "password": "test_password",
            "session_id": self.session_id
        }
        
        with self.client.post("/api/auth/login", 
                            json=login_data,
                            headers={"Content-Type": "application/json"},
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Store auth token if provided
                if response.json().get("token"):
                    self.client.headers.update({
                        "Authorization": f"Bearer {response.json()['token']}"
                    })
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    @task(3)
    def view_dashboard(self):
        """View the main dashboard - most common action."""
        with self.client.get("/api/dashboard",
                           headers={"X-User-ID": self.user_id},
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Validate response structure
                data = response.json()
                if not all(key in data for key in ['summary', 'recent_articles', 'alerts']):
                    response.failure("Invalid dashboard response structure")
            else:
                response.failure(f"Dashboard request failed: {response.status_code}")
    
    @task(5)
    def search_articles(self):
        """Search for articles - primary user action."""
        search_queries = [
            "AWS security vulnerability",
            "Microsoft 365 update",
            "ransomware attack",
            "phishing campaign",
            "zero-day exploit",
            "security patch",
            "CVE-2024",
            "Fortinet advisory",
            "critical vulnerability",
            "malware analysis"
        ]
        
        query_data = {
            "query": random.choice(search_queries),
            "filters": {
                "date_range": random.choice(["1d", "7d", "30d"]),
                "sources": random.sample(self.preferred_sources, random.randint(1, len(self.preferred_sources))),
                "relevancy_threshold": self.relevancy_threshold,
                "status": random.choice(["all", "pending_review", "reviewed"])
            },
            "pagination": {
                "page": random.randint(1, 5),
                "limit": random.choice([10, 20, 50])
            },
            "sort": {
                "field": random.choice(["relevancy_score", "published_at", "created_at"]),
                "order": random.choice(["asc", "desc"])
            }
        }
        
        with self.client.post("/api/articles/search",
                            json=query_data,
                            headers={
                                "Content-Type": "application/json",
                                "X-User-ID": self.user_id,
                                "X-Correlation-ID": str(uuid.uuid4())
                            },
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Validate search results
                data = response.json()
                if "results" not in data:
                    response.failure("Invalid search response structure")
                elif len(data["results"]) > query_data["pagination"]["limit"]:
                    response.failure("Too many results returned")
            else:
                response.failure(f"Search request failed: {response.status_code}")
    
    @task(2)
    def view_article_details(self):
        """View detailed article information."""
        # Simulate getting an article ID from previous search
        article_id = f"article_{uuid.uuid4().hex[:12]}"
        
        with self.client.get(f"/api/articles/{article_id}",
                           headers={"X-User-ID": self.user_id},
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Validate article structure
                data = response.json()
                required_fields = ['article_id', 'title', 'content', 'relevancy_score']
                if not all(field in data for field in required_fields):
                    response.failure("Invalid article response structure")
            elif response.status_code == 404:
                response.success()  # Expected for random article IDs
            else:
                response.failure(f"Article request failed: {response.status_code}")
    
    @task(1)
    def submit_review(self):
        """Submit article review - less frequent action."""
        article_id = f"article_{uuid.uuid4().hex[:12]}"
        
        review_data = {
            "article_id": article_id,
            "decision": random.choice(["relevant", "irrelevant", "needs_escalation"]),
            "confidence": random.uniform(0.7, 1.0),
            "comments": f"Review by {self.user_id} at {datetime.now(timezone.utc).isoformat()}",
            "tags": random.sample(["critical", "informational", "false_positive", "duplicate"], 
                                random.randint(0, 2))
        }
        
        with self.client.post("/api/articles/review",
                            json=review_data,
                            headers={
                                "Content-Type": "application/json",
                                "X-User-ID": self.user_id,
                                "X-Correlation-ID": str(uuid.uuid4())
                            },
                            catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                response.success()  # Expected for random article IDs
            else:
                response.failure(f"Review submission failed: {response.status_code}")
    
    @task(1)
    def generate_report(self):
        """Generate report - resource-intensive action."""
        report_config = {
            "title": f"Security Report {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "date_range": random.choice(["7d", "30d", "90d"]),
            "filters": {
                "sources": random.sample(self.preferred_sources, random.randint(1, len(self.preferred_sources))),
                "relevancy_threshold": self.relevancy_threshold,
                "categories": random.sample(["vulnerability", "threat", "advisory", "update"], 
                                          random.randint(1, 3))
            },
            "format": random.choice(["xlsx", "pdf", "json"]),
            "include_details": random.choice([True, False])
        }
        
        with self.client.post("/api/reports/generate",
                            json=report_config,
                            headers={
                                "Content-Type": "application/json",
                                "X-User-ID": self.user_id,
                                "X-Correlation-ID": str(uuid.uuid4())
                            },
                            catch_response=True,
                            timeout=30) as response:  # Longer timeout for reports
            if response.status_code in [200, 202]:  # 202 for async processing
                response.success()
            else:
                response.failure(f"Report generation failed: {response.status_code}")
    
    @task(1)
    def check_system_status(self):
        """Check system health status."""
        with self.client.get("/api/health",
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Validate health response
                data = response.json()
                if "status" not in data:
                    response.failure("Invalid health response structure")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def update_user_preferences(self):
        """Update user preferences - occasional action."""
        preferences = {
            "preferred_sources": random.sample(['CISA', 'NCSC', 'Microsoft', 'ANSSI', 'GoogleTAG'], 
                                             random.randint(2, 4)),
            "relevancy_threshold": random.uniform(0.5, 0.95),
            "notification_settings": {
                "email_alerts": random.choice([True, False]),
                "high_priority_only": random.choice([True, False]),
                "digest_frequency": random.choice(["daily", "weekly", "never"])
            },
            "dashboard_layout": {
                "show_summary": True,
                "articles_per_page": random.choice([10, 20, 50]),
                "default_sort": random.choice(["relevancy", "date", "source"])
            }
        }
        
        with self.client.put(f"/api/users/{self.user_id}/preferences",
                           json=preferences,
                           headers={
                               "Content-Type": "application/json",
                               "X-User-ID": self.user_id
                           },
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Update local preferences
                self.preferred_sources = preferences["preferred_sources"]
                self.relevancy_threshold = preferences["relevancy_threshold"]
            else:
                response.failure(f"Preferences update failed: {response.status_code}")

class AdminUser(HttpUser):
    """Simulates an admin user with different access patterns."""
    
    wait_time = between(2, 8)  # Admins typically have longer think times
    weight = 1  # Lower weight - fewer admin users
    
    def on_start(self):
        """Admin user setup."""
        self.user_id = f"admin_{uuid.uuid4().hex[:8]}"
        self.session_id = str(uuid.uuid4())
        self.login()
    
    def login(self):
        """Admin login with elevated privileges."""
        login_data = {
            "username": self.user_id,
            "password": "admin_password",
            "role": "admin",
            "session_id": self.session_id
        }
        
        with self.client.post("/api/auth/login",
                            json=login_data,
                            headers={"Content-Type": "application/json"},
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                if response.json().get("token"):
                    self.client.headers.update({
                        "Authorization": f"Bearer {response.json()['token']}"
                    })
            else:
                response.failure(f"Admin login failed: {response.status_code}")
    
    @task(3)
    def view_admin_dashboard(self):
        """View admin dashboard with system metrics."""
        with self.client.get("/api/admin/dashboard",
                           headers={"X-User-ID": self.user_id},
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Admin dashboard failed: {response.status_code}")
    
    @task(2)
    def manage_feed_sources(self):
        """Manage RSS feed sources."""
        # Get current feeds
        with self.client.get("/api/admin/feeds",
                           headers={"X-User-ID": self.user_id},
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Feed management failed: {response.status_code}")
    
    @task(1)
    def view_system_metrics(self):
        """View detailed system performance metrics."""
        with self.client.get("/api/admin/metrics",
                           headers={"X-User-ID": self.user_id},
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics request failed: {response.status_code}")
    
    @task(1)
    def bulk_article_operations(self):
        """Perform bulk operations on articles."""
        bulk_operation = {
            "operation": random.choice(["bulk_review", "bulk_tag", "bulk_export"]),
            "filters": {
                "date_range": "7d",
                "status": "pending_review",
                "relevancy_threshold": 0.8
            },
            "parameters": {
                "decision": "relevant" if random.random() > 0.3 else "irrelevant",
                "tags": ["bulk_processed", f"batch_{datetime.now().strftime('%Y%m%d')}"]
            }
        }
        
        with self.client.post("/api/admin/articles/bulk",
                            json=bulk_operation,
                            headers={
                                "Content-Type": "application/json",
                                "X-User-ID": self.user_id,
                                "X-Correlation-ID": str(uuid.uuid4())
                            },
                            catch_response=True,
                            timeout=60) as response:  # Longer timeout for bulk operations
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Bulk operation failed: {response.status_code}")

# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Custom request handler for additional metrics."""
    if exception:
        print(f"Request failed: {request_type} {name} - {exception}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("Starting Sentinel load test...")
    print(f"Target host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("Sentinel load test completed.")
    
    # Print summary statistics
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")
    
    # Check if performance thresholds are met
    error_rate = stats.total.num_failures / max(stats.total.num_requests, 1)
    if error_rate > 0.01:  # 1% error threshold
        print(f"WARNING: Error rate ({error_rate:.2%}) exceeds threshold (1%)")
    
    if stats.total.avg_response_time > 2000:  # 2 second threshold
        print(f"WARNING: Average response time ({stats.total.avg_response_time:.2f}ms) exceeds threshold (2000ms)")

# Custom user classes for different load patterns
class BurstUser(SentinelWebUser):
    """User that creates burst traffic patterns."""
    wait_time = between(0.1, 1)  # Very short wait times
    weight = 2

class SlowUser(SentinelWebUser):
    """User that simulates slow/careful usage."""
    wait_time = between(5, 15)  # Longer wait times
    weight = 1