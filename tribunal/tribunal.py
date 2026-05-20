#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║  ████████╗██████╗ ██╗██████╗ ██╗   ██╗███╗   ██╗ █████╗ ██╗                   ║
║  ╚══██╔══╝██╔══██╗██║██╔══██╗██║   ██║████╗  ██║██╔══██╗██║                   ║
║     ██║   ██████╔╝██║██████╔╝██║   ██║██╔██╗ ██║███████║██║                   ║
║     ██║   ██╔══██╗██║██╔══██╗██║   ██║██║╚██╗██║██╔══██║██║                   ║
║     ██║   ██║  ██║██║██████╔╝╚██████╔╝██║ ╚████║██║  ██║███████╗              ║
║     ╚═╝   ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝              ║
║                                                                               ║
║     The Performance Review Game                                               ║
║                                                                               ║
║  "This game makes players feel the helplessness of being judged              ║
║   by rules they cannot see, verify, or enforce."                             ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

TRIBUNAL: A game where one player (Manager) evaluates others (Workers).

THE ASYMMETRY:
    - Manager sees ALL performance data
    - Workers see ONLY their own evaluation
    - Manager has a BUDGET (average rating ≤ 3.0)
    - Manager can give ANY justification

WHAT THIS EXPOSES:
    Performance reviews are not measurements.
    They are negotiations where one side has all the information.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set
from collections import defaultdict


# =============================================================================
# GAME TYPES
# =============================================================================

class TaskDifficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    
    @property
    def risk(self) -> float:
        return {TaskDifficulty.EASY: 0.1, TaskDifficulty.MEDIUM: 0.25, TaskDifficulty.HARD: 0.4}[self]


class Rating(Enum):
    UNSATISFACTORY = 1
    BELOW_EXPECTATIONS = 2
    MEETS_EXPECTATIONS = 3
    EXCEEDS_EXPECTATIONS = 4
    EXCEPTIONAL = 5


class ManagerBehavior(Enum):
    FAIR = auto()
    FAVORITES = auto()
    BUDGET_FIRST = auto()


# =============================================================================
# GAME STATE
# =============================================================================

@dataclass
class TaskResult:
    worker_id: str
    difficulty: TaskDifficulty
    succeeded: bool


@dataclass
class Evaluation:
    worker_id: str
    rating: Rating
    justification: str
    round_num: int
    _actual_task: Optional[TaskDifficulty] = None
    _task_succeeded: Optional[bool] = None


@dataclass
class WorkerState:
    worker_id: str
    total_points: int = 0
    evaluations: List[Evaluation] = field(default_factory=list)


# =============================================================================
# JUSTIFICATION GENERATOR
# =============================================================================

class JustificationGenerator:
    POSITIVE = ["demonstrated strong initiative", "showed excellent problem-solving", "exceeded expectations"]
    NEGATIVE = ["opportunities for growth", "could be more proactive", "room for improvement"]
    NEUTRAL = ["met requirements", "performed at expected level", "fulfilled basic expectations"]
    
    @classmethod
    def generate(cls, rating: Rating, task: TaskDifficulty, succeeded: bool) -> str:
        if rating.value >= 4:
            base = random.choice(cls.POSITIVE)
            return f"{base.capitalize()}." + (" Despite challenges, showed valuable learning." if not succeeded else "")
        elif rating.value <= 2:
            base = random.choice(cls.NEGATIVE)
            return f"{base.capitalize()}." + (" Task outcome reflects this." if not succeeded else " Impact was limited.")
        return random.choice(cls.NEUTRAL).capitalize() + "."


# =============================================================================
# MANAGER AI
# =============================================================================

class ManagerAI:
    def __init__(self, behavior: ManagerBehavior, favorites: Optional[List[str]] = None):
        self.behavior = behavior
        self.favorites = set(favorites or [])
    
    def evaluate(self, results: List[TaskResult], round_num: int, budget_limit: float = 3.0) -> List[Evaluation]:
        ideal = {r.worker_id: self._ideal_rating(r) for r in results}
        adjusted = self._adjust_for_budget(ideal, budget_limit)
        
        evaluations = []
        for result in results:
            rating = Rating(adjusted[result.worker_id])
            evaluations.append(Evaluation(
                worker_id=result.worker_id,
                rating=rating,
                justification=JustificationGenerator.generate(rating, result.difficulty, result.succeeded),
                round_num=round_num,
                _actual_task=result.difficulty,
                _task_succeeded=result.succeeded,
            ))
        return evaluations
    
    def _ideal_rating(self, result: TaskResult) -> int:
        if self.behavior == ManagerBehavior.FAIR:
            base = result.difficulty.value + 1
            return min(5, base + 1) if result.succeeded else max(1, base - 1)
        elif self.behavior == ManagerBehavior.FAVORITES:
            if result.worker_id in self.favorites:
                return 5 if result.succeeded else 4
            return 2 if result.succeeded else 1
        else:  # BUDGET_FIRST
            return 2 if result.succeeded else 1
    
    def _adjust_for_budget(self, ideal: Dict[str, int], budget_limit: float) -> Dict[str, int]:
        adjusted = dict(ideal)
        while sum(adjusted.values()) / len(adjusted) > budget_limit:
            max_worker = max(adjusted, key=adjusted.get)
            if adjusted[max_worker] > 1:
                adjusted[max_worker] -= 1
            else:
                break
        return adjusted


# =============================================================================
# THE GAME
# =============================================================================

class TribunalGame:
    def __init__(
        self,
        worker_ids: List[str],
        manager_behavior: ManagerBehavior = ManagerBehavior.FAVORITES,
        favorites: Optional[List[str]] = None,
        rounds: int = 3,
        budget_limit: float = 3.0
    ):
        self.worker_ids = worker_ids
        self.rounds = rounds
        self.current_round = 0
        self.budget_limit = budget_limit
        self.worker_states = {wid: WorkerState(worker_id=wid) for wid in worker_ids}
        self.all_evaluations: List[Evaluation] = []
        self.manager_ai = ManagerAI(manager_behavior, favorites)
        self._manager_behavior = manager_behavior
        self._favorites = set(favorites or [])
    
    def get_rules(self) -> str:
        return """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    TRIBUNAL: OFFICIAL RULES                       ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  TASKS:                                                           ║
    ║    EASY   - Low risk (expected rating: 2-3)                       ║
    ║    MEDIUM - Balanced (expected rating: 2-4)                       ║
    ║    HARD   - High risk, high reward (expected rating: 3-5)         ║
    ║                                                                   ║
    ║  RATINGS: 1-5 stars. Higher = more points.                        ║
    ║  WINNING: Most total points after all rounds.                     ║
    ╚═══════════════════════════════════════════════════════════════════╝
        """
    
    def play_round(self, choices: Dict[str, TaskDifficulty]) -> Dict[str, str]:
        self.current_round += 1
        
        results = []
        for worker_id, difficulty in choices.items():
            succeeded = random.random() > difficulty.risk
            results.append(TaskResult(worker_id, difficulty, succeeded))
        
        evaluations = self.manager_ai.evaluate(results, self.current_round, self.budget_limit)
        
        worker_views = {}
        for eval in evaluations:
            self.all_evaluations.append(eval)
            self.worker_states[eval.worker_id].evaluations.append(eval)
            self.worker_states[eval.worker_id].total_points += eval.rating.value
            
            stars = "★" * eval.rating.value + "☆" * (5 - eval.rating.value)
            worker_views[eval.worker_id] = f"""
    ┌───────────────────────────────────────────────────┐
    │ YOUR REVIEW: {stars}                 │
    │ Feedback: {eval.justification[:35]:<35} │
    │ Points: +{eval.rating.value} (Total: {self.worker_states[eval.worker_id].total_points})                          │
    └───────────────────────────────────────────────────┘"""
        
        return worker_views
    
    def get_standings(self) -> str:
        standings = sorted(self.worker_states.values(), key=lambda w: w.total_points, reverse=True)
        lines = ["\n  STANDINGS:"]
        for i, w in enumerate(standings, 1):
            lines.append(f"    {i}. {w.worker_id}: {w.total_points} points")
        return "\n".join(lines)
    
    def reveal_truth(self) -> str:
        lines = [
            "\n" + "=" * 60,
            "  ▓▓▓ THE TRUTH IS REVEALED ▓▓▓",
            "=" * 60,
            f"\n  MANAGER TYPE: {self._manager_behavior.name}",
        ]
        
        if self._favorites:
            lines.append(f"  SECRET FAVORITES: {', '.join(self._favorites)}")
        
        lines.append("\n  COMPLETE HISTORY:")
        lines.append("  " + "-" * 55)
        
        by_round = defaultdict(list)
        for e in self.all_evaluations:
            by_round[e.round_num].append(e)
        
        for rnd in sorted(by_round.keys()):
            lines.append(f"\n  Round {rnd}:")
            for e in by_round[rnd]:
                fav = "♥" if e.worker_id in self._favorites else " "
                task = e._actual_task.name if e._actual_task else "?"
                success = "✓" if e._task_succeeded else "✗"
                lines.append(f"    {fav} {e.worker_id:10} | {task:6} {success} | Rating: {e.rating.value}")
        
        lines.append("\n  " + "-" * 55)
        lines.append("  WHO GOT SCREWED?")
        lines.append("  " + "-" * 55)
        
        for wid in self.worker_ids:
            evals = [e for e in self.all_evaluations if e.worker_id == wid]
            actual = sum(e.rating.value for e in evals)
            deserved = 0
            for e in evals:
                if e._actual_task and e._task_succeeded is not None:
                    base = e._actual_task.value + 1
                    deserved += min(5, base + 1) if e._task_succeeded else max(1, base - 1)
            
            diff = actual - deserved
            verdict = f"+{diff} FAVORED" if diff > 0 else (f"{diff} SCREWED" if diff < 0 else "FAIR")
            fav = "♥" if wid in self._favorites else " "
            lines.append(f"    {fav} {wid:10}: Got {actual}, Deserved {deserved} → {verdict}")
        
        lines.append("\n" + "=" * 60)
        lines.append("""
  THE LESSON:
  
    You optimized for STATED rules.
    Manager played by HIDDEN rules.
    You couldn't verify fairness.
    Until now. When it's too late.
    
    This is how performance reviews work.
        """)
        
        return "\n".join(lines)


# =============================================================================
# DEMO
# =============================================================================

def demo():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  TRIBUNAL: The Performance Review Game                                        ║
║  "Feel the helplessness of being judged by hidden rules."                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    random.seed(42)
    
    game = TribunalGame(
        worker_ids=["Alice", "Bob", "Carol", "Dave"],
        manager_behavior=ManagerBehavior.FAVORITES,
        favorites=["Bob"],
        rounds=3
    )
    
    print(game.get_rules())
    
    print("\n  Players: Alice, Bob, Carol, Dave")
    print("  Manager behavior: [HIDDEN]")
    
    # Round 1
    print("\n" + "=" * 60)
    print("  ROUND 1: Everyone chooses HARD (following the rules)")
    print("=" * 60)
    
    views = game.play_round({
        "Alice": TaskDifficulty.HARD,
        "Bob": TaskDifficulty.HARD,
        "Carol": TaskDifficulty.HARD,
        "Dave": TaskDifficulty.HARD,
    })
    
    for wid, view in views.items():
        print(f"\n  {wid} sees:{view}")
    
    # Round 2
    print("\n" + "=" * 60)
    print("  ROUND 2: Alice/Carol got low ratings → play safer")
    print("=" * 60)
    
    views = game.play_round({
        "Alice": TaskDifficulty.EASY,
        "Bob": TaskDifficulty.HARD,
        "Carol": TaskDifficulty.MEDIUM,
        "Dave": TaskDifficulty.HARD,
    })
    
    for wid, view in views.items():
        print(f"\n  {wid} sees:{view}")
    
    # Round 3
    print("\n" + "=" * 60)
    print("  ROUND 3: Final round")
    print("=" * 60)
    
    views = game.play_round({
        "Alice": TaskDifficulty.HARD,
        "Bob": TaskDifficulty.MEDIUM,
        "Carol": TaskDifficulty.HARD,
        "Dave": TaskDifficulty.HARD,
    })
    
    for wid, view in views.items():
        print(f"\n  {wid} sees:{view}")
    
    print(game.get_standings())
    
    print("\n  The game is over. Workers suspect unfairness but cannot prove it.")
    print("\n  [Press Enter to reveal the truth...]")
    
    try:
        input()
    except EOFError:
        pass
    
    print(game.reveal_truth())


if __name__ == "__main__":
    demo()
