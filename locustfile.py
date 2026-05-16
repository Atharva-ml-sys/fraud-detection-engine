from locust import HttpUser, task, between

class FraudDetectionUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def health_check(self):
        self.client.get("/api/v1/health")

    @task(3)
    def get_stats(self):
        self.client.get("/api/v1/stats")

    @task(5)
    def score_transaction(self):
        self.client.post("/api/v1/score", json={
            "transaction_type": "UPI",
            "amount": 15000,
            "sender_account": "ACC_001",
            "receiver_account": "ACC_002",
            "city": "Mumbai"
        })
