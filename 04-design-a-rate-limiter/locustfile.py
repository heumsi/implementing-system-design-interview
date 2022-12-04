from locust import HttpUser, task, constant


class User(HttpUser):
    wait_time = constant(1)

    @task
    def index(self):
        self.client.get("/")
