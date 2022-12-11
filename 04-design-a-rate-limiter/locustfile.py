from locust import HttpUser, constant, task


class User(HttpUser):
    wait_time = constant(10)

    @task
    def index(self):
        self.client.get("/")
