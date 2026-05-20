"""
Bastion: Resilienz-Tools für Python Async Services.

Hab das gebaut, weil ich keine riesigen Frameworks installieren wollte, nur um
einen simplen Circuit Breaker oder Rate Limiter zu haben.
Komplett ohne Dependencies (nur Standard-Lib) und einfach einzubauen.

Benutzung:
    from bastion import CircuitBreaker, Retry
    
    @Retry(max_attempts=3)
    @CircuitBreaker("api-call", failure_threshold=5)
    async def fetch_data():
        ...
"""

__version__ = "0.1.0"
__author__ = "chrismaghuhn"
__all__ = [
    "CircuitBreaker", "RateLimiter", "Bulkhead", "Retry", "Timeout", 
    "Fallback", "compose", "Metric", "MetricType", "set_metrics_collector"
]

import asyncio
import functools
import random
import time
from abc import ABC, abstractmethod
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any, Awaitable, Callable, Deque, Generic, Hashable, 
    Optional, ParamSpec, TypeVar, Union
)

# Generische Typen für die Decorators
T = TypeVar("T")
P = ParamSpec("P")
ExceptionTypes = tuple[type[BaseException], ...]

# -----------------------------------------------------------------------------
# Metriken (Pluggable Backend)
# -----------------------------------------------------------------------------

class MetricType(Enum):
    COUNTER = auto()
    GAUGE = auto()
    HISTOGRAM = auto()

@dataclass(frozen=True, slots=True)
class Metric:
    """Ein Datenpunkt. 'Slotted' damit der Speicher nicht vollläuft."""
    name: str
    value: float
    metric_type: MetricType
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class MetricsCollector(ABC):
    @abstractmethod
    def emit(self, metric: Metric) -> None:
        ...

class NoOpCollector(MetricsCollector):
    """Standard: Macht gar nichts, um Overhead zu vermeiden."""
    def emit(self, metric: Metric) -> None:
        pass

class InMemoryCollector(MetricsCollector):
    """Nur für lokale Tests oder Debugging gedacht."""
    def __init__(self, max_size: int = 10_000):
        self._metrics: Deque[Metric] = deque(maxlen=max_size)
    
    def emit(self, metric: Metric) -> None:
        self._metrics.append(metric)
    
    def get_all(self) -> list[Metric]:
        return list(self._metrics)

# Globales Singleton - simpel, reicht aber völlig.
_metrics_collector: MetricsCollector = NoOpCollector()

def set_metrics_collector(collector: MetricsCollector) -> None:
    global _metrics_collector
    _metrics_collector = collector

def _emit(name: str, value: float, mtype: MetricType, **tags: str) -> None:
    _metrics_collector.emit(Metric(name, value, mtype, tags))


# -----------------------------------------------------------------------------
# Circuit Breaker (Die Sicherung)
# -----------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"       # Alles normal
    OPEN = "open"           # Fehler erkannt, blockiert Anfragen
    HALF_OPEN = "half_open" # Testen, ob der Service wieder da ist

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    # Fehler, die wir ignorieren (z.B. User-Input Fehler)
    excluded_exceptions: ExceptionTypes = ()

class CircuitBreakerError(Exception):
    def __init__(self, name: str, retry_in: Optional[float] = None):
        msg = f"Circuit '{name}' ist OFFEN"
        if retry_in:
            msg += f" (Versuch's in {retry_in:.1f}s wieder)"
        super().__init__(msg)
        self.retry_in = retry_in

class CircuitBreaker:
    """
    Verhindert kaskadierende Fehler, indem kaputte Services blockiert werden.
    State Machine: Closed -> (Fehler) -> Open -> (Zeit vorbei) -> Half-Open -> ...
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._successes = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        
        # Lock ist wichtig, damit State-Wechsel sauber ("atomic") sind
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def _check_state(self) -> None:
        # Optimierung: Wenn alles läuft (CLOSED), sofort raus hier.
        if self._state == CircuitState.CLOSED:
            return

        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - (self._last_failure_time or 0)
            
            # Recovery-Zeit noch nicht um? Blockieren.
            if elapsed < self.config.recovery_timeout:
                _emit("bastion.cb.rejected", 1, MetricType.COUNTER, name=self.name)
                raise CircuitBreakerError(self.name, self.config.recovery_timeout - elapsed)
            
            # Zeit um? Wir versuchen den Übergang zu HALF_OPEN.
            async with self._lock:
                if self._state == CircuitState.OPEN:  # Nochmal checken im Lock
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._successes = 0
                    _emit("bastion.cb.state_change", 1, MetricType.COUNTER, 
                          name=self.name, to="half_open")

        if self._state == CircuitState.HALF_OPEN:
            # Nur ein paar Test-Anfragen durchlassen
            if self._half_open_calls >= self.config.half_open_max_calls:
                _emit("bastion.cb.rejected", 1, MetricType.COUNTER, name=self.name)
                raise CircuitBreakerError(self.name)
            self._half_open_calls += 1

    async def _on_success(self):
        if self._state == CircuitState.CLOSED:
            # Wenn alles stabil ist, sparen wir uns das Lock (Performance).
            if self._failures > 0:
                async with self._lock:
                    self._failures = 0
            return

        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self.config.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failures = 0
                    _emit("bastion.cb.state_change", 1, MetricType.COUNTER, 
                          name=self.name, to="closed")

    async def _on_failure(self, exc: BaseException):
        if isinstance(exc, self.config.excluded_exceptions):
            return

        async with self._lock:
            self._failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                _emit("bastion.cb.state_change", 1, MetricType.COUNTER, 
                      name=self.name, to="open")
            
            elif self._state == CircuitState.CLOSED:
                if self._failures >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    _emit("bastion.cb.state_change", 1, MetricType.COUNTER, 
                          name=self.name, to="open")

    def __call__(self, func: Optional[Callable[P, Awaitable[T]]] = None):
        """Unterstützt sowohl @decorator als auch @decorator() Schreibweise."""
        if func is None:
            return self._make_cm()
        
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            await self._check_state()
            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception as e:
                await self._on_failure(e)
                raise
        return wrapper

    def _make_cm(self):
        # Helfer für 'async with circuit():'
        @asynccontextmanager
        async def cm():
            await self._check_state()
            try:
                yield
                await self._on_success()
            except Exception as e:
                await self._on_failure(e)
                raise
        return cm()


# -----------------------------------------------------------------------------
# Rate Limiter (Der Türsteher)
# -----------------------------------------------------------------------------

class RateLimitExceeded(Exception):
    def __init__(self, name: str, retry_after: float):
        super().__init__(f"Limit '{name}' überschritten. Warte {retry_after:.2f}s")
        self.retry_after = retry_after

@dataclass
class RateLimiterConfig:
    capacity: float = 100.0   # Burst-Größe
    refill_rate: float = 10.0 # Tokens pro Sekunde

class RateLimiter:
    """
    Klassischer Token Bucket Algorithmus.
    Erlaubt Bursts, erzwingt aber langfristig die Rate.
    """
    
    def __init__(self, name: str, config: Optional[RateLimiterConfig] = None):
        self.name = name
        self.config = config or RateLimiterConfig()
        self._tokens = self.config.capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0, wait: bool = False, timeout: float = None):
        async with self._lock:
            # Token auffüllen
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self.config.capacity,
                self._tokens + (elapsed * self.config.refill_rate)
            )
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                _emit("bastion.rate.acquired", tokens, MetricType.COUNTER, name=self.name)
                return True
            
            # Nicht genug Tokens da
            missing = tokens - self._tokens
            wait_time = missing / self.config.refill_rate

            if not wait:
                _emit("bastion.rate.rejected", 1, MetricType.COUNTER, name=self.name)
                raise RateLimitExceeded(self.name, wait_time)

        # Warte-Modus (Wichtig: Lock freigeben während wir schlafen!)
        if timeout and wait_time > timeout:
            raise asyncio.TimeoutError(f"Müsste {wait_time:.2f}s warten, Timeout ist aber {timeout}s")
        
        await asyncio.sleep(wait_time)
        
        # Theoretisch könnte uns jetzt jemand die Tokens weggeschnappt haben,
        # aber wir nehmen an, sie sind reserviert.
        return True

    def decorate(self, tokens: float = 1.0, wait: bool = False):
        def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                await self.acquire(tokens, wait)
                return await func(*args, **kwargs)
            return wrapper
        return decorator


# -----------------------------------------------------------------------------
# Retry (Der Hartnäckige)
# -----------------------------------------------------------------------------

class BackoffStrategy(ABC):
    @abstractmethod
    def get_delay(self, attempt: int) -> float: ...

class ExponentialBackoff(BackoffStrategy):
    """
    Exponentiell mit 'Full Jitter'.
    Siehe AWS Blog: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
    """
    def __init__(self, base: float = 1.0, max_delay: float = 60.0):
        self.base = base
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        cap = min(self.max_delay, self.base * (2 ** attempt))
        return random.uniform(0, cap)

@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff: BackoffStrategy = field(default_factory=ExponentialBackoff)
    retryable_exceptions: ExceptionTypes = (Exception,)

class Retry:
    def __init__(self, name: str, config: Optional[RetryConfig] = None):
        self.name = name
        self.config = config or RetryConfig()

    def __call__(self, func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            attempts = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    
                    # Aufgeben?
                    if (attempts >= self.config.max_attempts or 
                        not isinstance(e, self.config.retryable_exceptions)):
                        _emit("bastion.retry.gave_up", 1, MetricType.COUNTER, name=self.name)
                        raise
                    
                    delay = self.config.backoff.get_delay(attempts)
                    _emit("bastion.retry.wait", delay, MetricType.GAUGE, name=self.name)
                    
                    await asyncio.sleep(delay)
        return wrapper


# -----------------------------------------------------------------------------
# Bulkhead & Timeout (Wrapper)
# -----------------------------------------------------------------------------

class BulkheadFullError(Exception): pass

class Bulkhead:
    """Begrenzt gleichzeitige Ausführungen mit einer Semaphore."""
    def __init__(self, name: str, limit: int):
        self.name = name
        self._sem = asyncio.Semaphore(limit)

    @asynccontextmanager
    async def __call__(self):
        try:
            # Quick check: Ist schon voll?
            if self._sem.locked():
                # Nicht 100% race-free, verhindert aber unnötiges Warten bei voller Queue.
                raise BulkheadFullError(f"Bulkhead '{self.name}' ist voll")
            
            await self._sem.acquire()
            _emit("bastion.bulkhead.entered", 1, MetricType.COUNTER, name=self.name)
            try:
                yield
            finally:
                self._sem.release()
        except BulkheadFullError:
            _emit("bastion.bulkhead.rejected", 1, MetricType.COUNTER, name=self.name)
            raise

class Timeout:
    """Einfacher Wrapper um asyncio.wait_for."""
    def __init__(self, name: str, seconds: float):
        self.name = name
        self.seconds = seconds

    def __call__(self, func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=self.seconds)
            except asyncio.TimeoutError:
                _emit("bastion.timeout", 1, MetricType.COUNTER, name=self.name)
                raise
        return wrapper


# -----------------------------------------------------------------------------
# Fallback
# -----------------------------------------------------------------------------

class Fallback:
    """Gibt einen Default-Wert zurück, wenn's knallt."""
    def __init__(self, default: Any):
        self.default = default

    def __call__(self, func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception:
                _emit("bastion.fallback", 1, MetricType.COUNTER)
                return self.default
        return wrapper


# -----------------------------------------------------------------------------
# Composition Helper
# -----------------------------------------------------------------------------

def compose(*decorators):
    """
    Klebt mehrere Decorators zusammen.
    Benutzung: @compose(Retry(), CircuitBreaker())
    """
    def composition(func):
        for dec in reversed(decorators):
            func = dec(func)
        return func
    return composition