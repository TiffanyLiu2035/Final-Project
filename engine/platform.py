class Platform:
    def select_winner(self, bids):
        bids = [(name, bid) for name, bid in bids if bid > 0]
        if not bids:
            return None
        return max(bids, key=lambda x: x[1])  # (name, bid)
