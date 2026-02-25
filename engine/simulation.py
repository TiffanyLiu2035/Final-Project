import csv
import os
import random
import inspect
from datetime import datetime
from typing import List, Dict, Any, Optional
from engine.platform import Platform

class SimulationEngine:
    def __init__(self, agents, total_rounds=10, verbose: bool = False, impression_pool=None, random_seed: Optional[int] = None):
        self.agents = agents
        self.total_rounds = total_rounds
        self.platform = Platform()
        self.verbose = verbose
        self.impression_pool = impression_pool
        self.random_seed = random_seed

        # Initialize logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging directory and CSV file"""
        # Create logs directory if not exists
        os.makedirs("logs", exist_ok=True)
        
        # Create CSV file with headers
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/results_{timestamp}.csv"
        
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Round", "Agent", "Bid", "Win", "CTR", "ROI", 
                "DecisionType", "Budget", "Impressions", "WinCount"
            ])
    
    def log_round_results(self, round_num: int, agent_name: str, bid: float, 
                         won: bool, metrics: Dict[str, Any]):
        """Log round results to CSV file"""
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                round_num,
                agent_name,
                bid,
                won,
                metrics.get("ctr", 0),
                metrics.get("roi", 0),
                metrics.get("decision_type", "N/A"),
                metrics.get("budget", 0),
                metrics.get("total_impressions", 0),
                metrics.get("win_count", 0)
            ])

    def run(self):
        self.round_history = []
        for round_num in range(1, self.total_rounds + 1):
            if self.verbose:
                print(f"\n--- Round {round_num} ---")
            
            # Get current round impression (all agents bid on same impression)
            current_impression = None
            if self.impression_pool:
                current_impression = self.impression_pool.get_next_impression()
                for agent in self.agents:
                    if hasattr(agent, "set_current_impression"):
                        agent.set_current_impression(current_impression)
            
            # [1] Update round information for agents that support it
            for agent in self.agents:
                if hasattr(agent, "set_round_info"):
                    agent.set_round_info(
                        current_round=round_num,
                        total_rounds=self.total_rounds
                    )
            
            # Collect bids from all agents
            bids = [(agent.name, agent.decide_bid()) for agent in self.agents]
            if self.verbose:
                print("Bids:", bids)
            bid_dict = dict(bids)

            # Select winner
            # Pass current_impression to mechanism if it supports it
            try:
                # Try with impression parameter
                if hasattr(self.platform, 'select_winner'):
                    sig = inspect.signature(self.platform.select_winner)
                    if 'impression' in sig.parameters:
                        winner = self.platform.select_winner(bids, self.agents, impression=current_impression)
                    else:
                        winner = self.platform.select_winner(bids, self.agents)
                else:
                    winner = self.platform.select_winner(bids)
            except (TypeError, AttributeError):
                # Fallback: try without agents parameter
                try:
                    winner = self.platform.select_winner(bids, impression=current_impression)
                except (TypeError, AttributeError):
                    winner = self.platform.select_winner(bids)
            
            # Safety: Handle None return (only for invalid bids, not for unknown gender)
            # Unknown gender impressions proceed normally - filtering is done in metrics
            if winner is None:
                if self.verbose:
                    print(f"Round {round_num}: No winner (no valid bids)")
                # Log results for skipped round (all agents bid but no winner - e.g., all bids too low)
                for agent in self.agents:
                    agent_bid = bid_dict.get(agent.name, 0.0)
                    self.log_round_results(
                        round_num=round_num,
                        agent_name=agent.name,
                        bid=agent_bid,
                        won=False,
                        metrics={}
                    )
                # Record round history for skipped round (no valid bids, not gender-related)
                self.round_history.append({
                    "round": round_num,
                    "bids": bids,
                    "winner": None,
                    "payment": None,
                    "impression": current_impression,  # Record impression for gender extraction
                    "agent_stats": {
                        agent.name: {
                            "bid": bid_dict.get(agent.name, 0.0),
                            "won": False,
                            "budget": agent.budget,
                            "agent_type": type(agent).__name__,
                            "group": getattr(agent, "group", "unknown")
                        } for agent in self.agents
                    },
                    "skipped": True  # Mark as skipped (no valid bids)
                })
                continue  # Skip to next round
            
            # Handle both single winner (tuple) and multiple winners (list)
            winner_name = winner_bid = None
            if winner:
                if isinstance(winner, list):
                    # Multiple winners (multi-slot): use first winner for now
                    if len(winner) > 0:
                        winner_name, winner_bid = winner[0]
                else:
                    # Single winner (tuple)
                    winner_name, winner_bid = winner
            
            # [2] Share bid information with agents that support it
            bid_values = [bid for _, bid in bids]
            for agent in self.agents:
                if hasattr(agent, "observe_other_bids"):
                    agent.observe_other_bids(bid_values)
            
            # Process winner and update metrics
            if winner_name:
                # [3] Update metrics for all agents
                for agent in self.agents:
                    agent_won = agent.name == winner_name
                    agent_bid = bid_dict[agent.name]
                    
                    # Update budget for winner
                    if agent_won:
                        agent.update_budget(winner_bid)
                    
                    # Update performance metrics
                    if hasattr(agent, "update_metrics"):
                        agent.update_metrics(
                            won=agent_won,
                            bid=agent_bid,
                            impressions=1 if agent_won else 0
                        )
                    
                    # Get agent's current metrics
                    metrics = {}
                    if hasattr(agent, "get_performance_metrics"):
                        metrics = agent.get_performance_metrics()
                    
                    # [4] Log results
                    self.log_round_results(
                        round_num=round_num,
                        agent_name=agent.name,
                        bid=agent_bid,
                        won=agent_won,
                        metrics=metrics
                    )
                    
                    if self.verbose:
                        print(f"{agent.name} bid {agent_bid} - "
                              f"Win: {agent_won} - "
                              f"CTR: {metrics.get('ctr', 0):.2f} - "
                              f"ROI: {metrics.get('roi', 0):.2f}")
            else:
                if self.verbose:
                    print("No winner this round.")
                
                # Log results for no-winner round
                for agent in self.agents:
                    agent_bid = bid_dict[agent.name]
                    self.log_round_results(
                        round_num=round_num,
                        agent_name=agent.name,
                        bid=agent_bid,
                        won=False,
                        metrics={}
                    )
            self.round_history.append({
                "round": round_num,
                "bids": bids,
                "winner": winner_name,
                "payment": winner_bid,
                "impression": current_impression,  # Record impression for gender extraction
                "agent_stats": {
                    agent.name: {
                        "bid": bid_dict[agent.name],
                        "won": agent.name == winner_name,
                        "budget": agent.budget,
                        "agent_type": type(agent).__name__,
                        "group": getattr(agent, "group", "unknown")
                    } for agent in self.agents
                }
            })
        return self.round_history