class BaseAgent:
    def __init__(self, name, budget):
        self.name = name
        self.budget = budget

    def decide_bid(self):
        raise NotImplementedError

    def update_budget(self, amount):
        self.budget -= amount
