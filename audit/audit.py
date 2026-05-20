#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   █████╗ ██╗   ██╗██████╗ ██╗████████╗                                        ║
║  ██╔══██╗██║   ██║██╔══██╗██║╚══██╔══╝                                        ║
║  ███████║██║   ██║██║  ██║██║   ██║                                           ║
║  ██╔══██║██║   ██║██║  ██║██║   ██║                                           ║
║  ██║  ██║╚██████╔╝██████╔╝██║   ██║                                           ║
║  ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝   ╚═╝                                           ║
║                                                                               ║
║     The Selective Verification Game                                           ║
║                                                                               ║
║  THE LIE PLAYERS BELIEVE:                                                     ║
║  "If I play honestly, the system will reward me."                             ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

THE MECHANIC: AUDIT SCARCITY

Every action has TWO parts:
    1. COMMITMENT: What you actually did (cryptographically sealed)
    2. CLAIM: What you say you did (public)

These can differ. That's called lying.

The system has LIMITED AUDIT TOKENS. When a claim is audited:
    - The commitment is revealed
    - If claim ≠ commitment → FRAUD (penalty)
    - If claim = commitment → VERIFIED (no penalty)

Unaudited claims are ACCEPTED AS STATED.
Even if they are lies.

THE INVARIANT THIS GAME PROTECTS:
    Verified claims are always true.
    The audit system has perfect accuracy.

THE INJUSTICE IT ALLOWS:
    Unverified lies succeed.
    Honest players lose to strategic liars.
    The system is correct but incomplete.

WHY THIS IS INTENTIONAL:
    This is how real audit systems work.
    Tax audits, financial compliance, fact-checking.
    Truth requires resources. Resources are scarce.
    What you choose not to verify becomes true.

Author: chrismaghuhn
License: MIT
"""

from __future__ import annotations

import hashlib
import secrets
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict


# =============================================================================
# CRYPTOGRAPHIC COMMITMENT
# =============================================================================

@dataclass(frozen=True)
class Commitment:
    """
    A cryptographic commitment to a value.
    
    PROPERTY: You cannot change the committed value after creation.
    PROPERTY: The value is hidden until revealed.
    PROPERTY: When revealed, anyone can verify it matches the commitment.
    
    This is what makes lying POSSIBLE but RISKY.
    You commit to the truth. You claim something else.
    If audited, the truth emerges.
    """
    value: int  # The actual value (hidden until reveal)
    salt: str   # Random salt (prevents guessing)
    hash: str   # Hash of value + salt (public commitment)
    
    @classmethod
    def create(cls, value: int) -> 'Commitment':
        salt = secrets.token_hex(16)
        hash_input = f"{value}:{salt}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return cls(value=value, salt=salt, hash=hash_value)
    
    def verify(self, claimed_value: int) -> bool:
        """Verify if claimed value matches commitment."""
        hash_input = f"{claimed_value}:{self.salt}"
        expected = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return expected == self.hash
    
    @property
    def hidden_str(self) -> str:
        """What others see before reveal."""
        return f"[sealed:{self.hash}]"


# =============================================================================
# GAME ACTIONS
# =============================================================================

class ActionType(Enum):
    WORK = auto()      # Generates 1-3 points based on effort
    TRADE = auto()     # Transfer points to another player
    INVEST = auto()    # Risk points for multiplied return


@dataclass
class Action:
    """
    An action with commitment and claim.
    
    The action is COMMITTED (sealed, true).
    The CLAIM is what the player says they did.
    These can differ.
    """
    player_id: str
    round_num: int
    action_type: ActionType
    
    # The truth (sealed)
    committed_value: Commitment  # What actually happened
    
    # The claim (public)
    claimed_value: int  # What player says happened
    
    # Audit state
    audited: bool = False
    fraud_detected: bool = False
    
    @property
    def is_lie(self) -> bool:
        """Did the player lie? (Only knowable after audit or game end)"""
        return self.committed_value.value != self.claimed_value
    
    @property
    def lie_amount(self) -> int:
        """How much did they lie by?"""
        return self.claimed_value - self.committed_value.value


# =============================================================================
# PLAYER
# =============================================================================

class PlayerStrategy(Enum):
    HONEST = auto()      # Never lies
    STRATEGIC = auto()   # Lies when audit probability is low
    AGGRESSIVE = auto()  # Always lies maximum amount
    RANDOM = auto()      # Randomly honest or dishonest


@dataclass
class Player:
    """
    A player in the audit game.
    
    Players have:
    - Points (their score)
    - Audit tokens (to verify others' claims)
    - A strategy (how they decide to lie)
    """
    player_id: str
    strategy: PlayerStrategy
    
    points: int = 0
    audit_tokens: int = 0
    
    actions: List[Action] = field(default_factory=list)
    audits_performed: List[str] = field(default_factory=list)
    times_audited: int = 0
    times_caught: int = 0
    successful_lies: int = 0
    
    def decide_action(self, round_num: int, audit_pressure: float) -> Action:
        """
        Decide what to do and whether to lie about it.
        
        audit_pressure: Estimated probability of being audited (0-1)
        """
        # Actual work done (1-3 points of effort)
        actual_work = random.randint(1, 3)
        commitment = Commitment.create(actual_work)
        
        # Decide whether to lie
        if self.strategy == PlayerStrategy.HONEST:
            claimed = actual_work
        
        elif self.strategy == PlayerStrategy.STRATEGIC:
            # Lie more when audit pressure is low
            if audit_pressure < 0.4:
                # Low audit pressure: lie big
                claimed = min(actual_work + 2, 5)
            elif audit_pressure < 0.7:
                # Medium pressure: small lie
                claimed = min(actual_work + 1, 5)
            else:
                # High pressure: be honest
                claimed = actual_work
        
        elif self.strategy == PlayerStrategy.AGGRESSIVE:
            # Always claim maximum
            claimed = 5
        
        else:  # RANDOM
            if random.random() < 0.5:
                claimed = actual_work
            else:
                claimed = min(actual_work + random.randint(1, 2), 5)
        
        return Action(
            player_id=self.player_id,
            round_num=round_num,
            action_type=ActionType.WORK,
            committed_value=commitment,
            claimed_value=claimed,
        )
    
    def decide_audit(self, actions: List[Action], own_tokens: int) -> Optional[Action]:
        """Decide which action to audit, if any."""
        if own_tokens <= 0:
            return None
        
        # Don't audit own actions
        others = [a for a in actions if a.player_id != self.player_id and not a.audited]
        
        if not others:
            return None
        
        if self.strategy == PlayerStrategy.HONEST:
            # Audit highest claims (suspicious)
            return max(others, key=lambda a: a.claimed_value)
        
        elif self.strategy == PlayerStrategy.STRATEGIC:
            # Audit claims that seem too high for the player's history
            return max(others, key=lambda a: a.claimed_value)
        
        else:
            # Random audit
            return random.choice(others) if random.random() < 0.5 else None


# =============================================================================
# THE GAME
# =============================================================================

class AuditGame:
    """
    THE AUDIT GAME
    
    RULES:
        1. Each round, players work and CLAIM how much they produced
        2. Claims are backed by cryptographic COMMITMENTS
        3. The system has LIMITED AUDIT TOKENS distributed to players
        4. Players can spend tokens to AUDIT others' claims
        5. Audited claims are VERIFIED (fraud detected if lie)
        6. Unaudited claims are ACCEPTED AS STATED
        7. At game end, all commitments are revealed (but it's too late)
    
    FRAUD PENALTY:
        If audited and caught lying: Lose 2x the lie amount
    
    WINNING:
        Most points at game end (claimed points, adjusted for caught fraud)
    
    THE LESSON:
        Honest players lose.
        The system rewards lying about what won't be checked.
        Verification accuracy is 100%. Verification coverage is not.
    """
    
    FRAUD_PENALTY_MULTIPLIER = 3  # Lose 3x what you lied about
    AUDIT_TOKENS_PER_ROUND = 0.5  # Players get 1 token every 2 rounds (scarce!)
    
    def __init__(
        self,
        player_configs: List[Tuple[str, PlayerStrategy]],
        rounds: int = 5
    ):
        self.players = {
            pid: Player(player_id=pid, strategy=strat)
            for pid, strat in player_configs
        }
        self.rounds = rounds
        self.current_round = 0
        self.all_actions: List[Action] = []
        self.log: List[str] = []
    
    def _log(self, msg: str):
        self.log.append(msg)
    
    def play_round(self) -> Dict[str, int]:
        """
        Play one round of the game.
        
        Returns claimed scores for this round.
        """
        self.current_round += 1
        self._log(f"\n{'='*60}")
        self._log(f"ROUND {self.current_round}")
        self._log(f"{'='*60}")
        
        # Distribute audit tokens (scarce - only every other round)
        if self.current_round % 2 == 1:  # Odd rounds only
            for player in self.players.values():
                player.audit_tokens += 1
        
        # Calculate audit pressure (how likely is an audit?)
        total_tokens = sum(p.audit_tokens for p in self.players.values())
        num_players = len(self.players)
        audit_pressure = min(1.0, total_tokens / num_players)
        
        # Phase 1: All players commit to actions
        round_actions = []
        for player in self.players.values():
            action = player.decide_action(self.current_round, audit_pressure)
            player.actions.append(action)
            round_actions.append(action)
            self.all_actions.append(action)
            
            # Player sees their own truth
            self._log(f"  {player.player_id}: Works, claims {action.claimed_value} points")
            self._log(f"    [Actual: {action.committed_value.value}, Commitment: {action.committed_value.hidden_str}]")
        
        # Phase 2: Audit phase
        self._log(f"\n  AUDIT PHASE:")
        
        # Collect audit decisions
        audits_to_perform = []
        for player in self.players.values():
            if player.audit_tokens > 0:
                target = player.decide_audit(round_actions, player.audit_tokens)
                if target:
                    audits_to_perform.append((player, target))
        
        # Execute audits
        for auditor, target_action in audits_to_perform:
            auditor.audit_tokens -= 1
            target_action.audited = True
            
            target_player = self.players[target_action.player_id]
            target_player.times_audited += 1
            
            # Reveal the truth
            actual = target_action.committed_value.value
            claimed = target_action.claimed_value
            
            if actual != claimed:
                # FRAUD DETECTED
                target_action.fraud_detected = True
                target_player.times_caught += 1
                
                lie_amount = claimed - actual
                penalty = lie_amount * self.FRAUD_PENALTY_MULTIPLIER
                
                self._log(f"    {auditor.player_id} audits {target_player.player_id}:")
                self._log(f"      FRAUD! Claimed {claimed}, actually {actual}")
                self._log(f"      Penalty: -{penalty} points")
                
                target_player.points -= penalty
            else:
                self._log(f"    {auditor.player_id} audits {target_player.player_id}: VERIFIED (honest)")
        
        if not audits_to_perform:
            self._log(f"    No audits performed this round.")
        
        # Phase 3: Credit claimed points for unaudited actions
        self._log(f"\n  SCORING:")
        round_scores = {}
        for action in round_actions:
            player = self.players[action.player_id]
            
            if action.audited and action.fraud_detected:
                # Already penalized, no points
                points = 0
            else:
                # Claim accepted (whether true or not!)
                points = action.claimed_value
                if action.is_lie and not action.audited:
                    player.successful_lies += 1
            
            player.points += points
            round_scores[player.player_id] = points
            
            status = ""
            if action.audited:
                status = " [AUDITED]"
            elif action.is_lie:
                status = " [UNDETECTED LIE]"
            
            self._log(f"    {player.player_id}: +{points} points{status} (Total: {player.points})")
        
        return round_scores
    
    def play_game(self) -> None:
        """Play the complete game."""
        self._log("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  AUDIT: The Selective Verification Game                                       ║
║  "If I play honestly, the system will reward me."                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
        
        self._log(f"Players: {', '.join(f'{p.player_id} ({p.strategy.name})' for p in self.players.values())}")
        self._log(f"Rounds: {self.rounds}")
        self._log(f"Audit tokens: 1 per player every OTHER round (scarce!)")
        
        for _ in range(self.rounds):
            self.play_round()
        
        self._log(self._final_revelation())
    
    def _final_revelation(self) -> str:
        """Reveal all truths at game end."""
        lines = [
            "\n" + "=" * 70,
            "  GAME OVER — THE TRUTH IS REVEALED",
            "=" * 70,
        ]
        
        # Final scores
        lines.append("\n  FINAL SCORES (based on accepted claims):")
        for player in sorted(self.players.values(), key=lambda p: p.points, reverse=True):
            lines.append(f"    {player.player_id}: {player.points} points")
        
        # Now reveal all lies
        lines.append("\n  " + "-" * 60)
        lines.append("  COMPLETE TRUTH REVELATION")
        lines.append("  " + "-" * 60)
        
        for player in self.players.values():
            lines.append(f"\n  {player.player_id} ({player.strategy.name}):")
            
            total_claimed = 0
            total_actual = 0
            total_lies = 0
            undetected_lies = 0
            
            for action in player.actions:
                claimed = action.claimed_value
                actual = action.committed_value.value
                total_claimed += claimed
                total_actual += actual
                
                if action.is_lie:
                    total_lies += 1
                    if not action.audited:
                        undetected_lies += 1
                
                status = ""
                if action.audited and action.fraud_detected:
                    status = " ← CAUGHT"
                elif action.is_lie:
                    status = " ← GOT AWAY WITH IT"
                
                lines.append(f"    Round {action.round_num}: Claimed {claimed}, Actual {actual}{status}")
            
            profit_from_lies = total_claimed - total_actual
            lines.append(f"    ---")
            lines.append(f"    Total claimed: {total_claimed}")
            lines.append(f"    Total actual:  {total_actual}")
            lines.append(f"    Lies told: {total_lies}, Undetected: {undetected_lies}")
            lines.append(f"    Profit from undetected lies: +{max(0, profit_from_lies - (player.times_caught * 4))}")
        
        # The lesson
        lines.append("\n" + "=" * 70)
        lines.append("  THE LESSON")
        lines.append("=" * 70)
        
        # Find winner and honest player
        winner = max(self.players.values(), key=lambda p: p.points)
        honest_players = [p for p in self.players.values() if p.strategy == PlayerStrategy.HONEST]
        
        lines.append(f"""
  Winner: {winner.player_id} ({winner.strategy.name}) with {winner.points} points
        """)
        
        if honest_players:
            honest = honest_players[0]
            if honest.player_id != winner.player_id:
                lines.append(f"""
  The honest player ({honest.player_id}) finished with {honest.points} points.
  
  They followed all the rules.
  They never lied.
  They lost.
  
  The audit system was PERFECT — 100% accurate.
  But accuracy is not coverage.
  What you choose not to verify becomes true.
        """)
            else:
                lines.append(f"""
  The honest player won — but only because other players
  were caught lying often enough.
  
  In a larger population, with lower audit coverage,
  honesty becomes increasingly irrational.
        """)
        
        return "\n".join(lines)
    
    def get_log(self) -> str:
        return "\n".join(self.log)


# =============================================================================
# DEMO
# =============================================================================

def demo():
    """Run a demonstration game."""
    
    random.seed(123)  # Seed chosen to show lies succeeding
    
    game = AuditGame(
        player_configs=[
            ("Alice", PlayerStrategy.HONEST),
            ("Bob", PlayerStrategy.STRATEGIC),
            ("Carol", PlayerStrategy.STRATEGIC),
            ("Dave", PlayerStrategy.AGGRESSIVE),
        ],
        rounds=6
    )
    
    game.play_game()
    print(game.get_log())


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'AuditGame',
    'Player',
    'PlayerStrategy',
    'Action',
    'Commitment',
]


if __name__ == "__main__":
    demo()
