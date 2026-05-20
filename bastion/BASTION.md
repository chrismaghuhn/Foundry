# 🏰 Bastion

**Resilienz-Toolkit für Python Async Services**

> Komplett ohne externe Dependencies. Nur Python Standard-Library.

---

## Was ist Bastion?

Bastion ist eine Sammlung von **Fehlertoleranz-Primitiven** für async Python-Anwendungen. Es schützt deine Services vor Kaskadenausfällen, wenn externe APIs oder Datenbanken Probleme haben.

**Das Problem:**
```
Dein Service → API ist down → 30s Timeout pro Request → Alle Worker blockiert → Dein Service ist auch down
```

**Mit Bastion:**
```
Dein Service → API ist down → Circuit Breaker öffnet → Sofortiges Fail → Andere Requests laufen weiter
```

---

## Installation

```bash
# Einfach die Datei kopieren - keine pip install nötig
cp bastion.py dein_projekt/
```

---

## Die 6 Bausteine

| Baustein | Problem | Lösung |
|----------|---------|--------|
| **CircuitBreaker** | API ist down, aber du wartest bei jedem Request 30s auf Timeout | Nach N Fehlern wird der "Schalter" geöffnet → sofortiges Fail |
| **RateLimiter** | Du darfst nur 100 Requests/Sekunde an eine API senden | Token-Bucket begrenzt automatisch |
| **Bulkhead** | Ein langsamer DB-Query blockiert alle deine Worker | Max N gleichzeitige Calls erlaubt |
| **Retry** | Netzwerk-Glitches verursachen sporadische Fehler | Automatische Wiederholung mit Backoff |
| **Timeout** | Ein Request hängt ewig | Nach N Sekunden wird abgebrochen |
| **Fallback** | API nicht erreichbar | Liefere gecachten/default Wert statt Fehler |

---

## Schnellstart

```python
from bastion import CircuitBreaker, Retry, Timeout, compose

# Einzeln verwenden
@CircuitBreaker("payment-api")
async def charge_customer(amount: float):
    return await payment_api.charge(amount)

# Oder kombiniert
@compose(
    Retry("api", RetryConfig(max_attempts=3)),
    CircuitBreaker("api", CircuitBreakerConfig(failure_threshold=5)),
    Timeout("api", 5.0),
)
async def fetch_weather():
    return await weather_api.get("/forecast")
```

---

## 1. Circuit Breaker (Die Sicherung)

### Konzept

Der Circuit Breaker ist wie eine elektrische Sicherung: Wenn zu viel Strom fließt (= zu viele Fehler), schaltet er ab.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CIRCUIT BREAKER STATE MACHINE                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    ┌──────────┐     N Fehler      ┌──────────┐                      │
│    │  CLOSED  │ ─────────────────>│   OPEN   │                      │
│    │ (normal) │                   │(blockiert)│                     │
│    └────┬─────┘                   └─────┬────┘                      │
│         │                               │                           │
│         │ Success                       │ Nach timeout Sekunden     │
│         │                               ▼                           │
│         │                        ┌───────────┐                      │
│         └────────────────────────│ HALF_OPEN │                      │
│              N Successes         │  (testen) │                      │
│                                  └───────────┘                      │
│                                        │                            │
│                                        │ 1 Fehler → zurück zu OPEN  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Verwendung

```python
from bastion import CircuitBreaker, CircuitBreakerConfig

# Mit Default-Config
cb = CircuitBreaker("my-api")

@cb
async def call_api():
    return await api.get("/data")

# Mit Custom-Config
config = CircuitBreakerConfig(
    failure_threshold=5,       # Nach 5 Fehlern: OPEN
    recovery_timeout=30.0,     # 30s warten, dann HALF_OPEN
    half_open_max_calls=3,     # 3 Test-Calls in HALF_OPEN
    excluded_exceptions=(ValueError,)  # Diese Fehler ignorieren
)

cb = CircuitBreaker("payment", config)
```

### State abfragen

```python
cb = CircuitBreaker("api")

# Aktueller State
print(cb.state)  # CircuitState.CLOSED / OPEN / HALF_OPEN
```

### Exceptions

```python
from bastion import CircuitBreakerError

try:
    await call_api()
except CircuitBreakerError as e:
    print(f"Circuit ist offen! Retry in {e.retry_in:.1f}s")
```

---

## 2. Rate Limiter (Der Türsteher)

### Konzept: Token Bucket

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TOKEN BUCKET                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    Bucket: [●●●●●●●●○○]     capacity = 10                           │
│                              refill_rate = 2/s                      │
│                                                                     │
│    Request kommt an:                                                │
│      - Token verfügbar? → Nimm Token, Request geht durch            │
│      - Kein Token? → RateLimitExceeded!                             │
│                                                                     │
│    Jede Sekunde: 2 neue Tokens (bis capacity erreicht)              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Verwendung

```python
from bastion import RateLimiter, RateLimiterConfig, RateLimitExceeded

# Config
config = RateLimiterConfig(
    capacity=100.0,     # Max 100 Requests auf einmal (Burst)
    refill_rate=10.0    # 10 Requests pro Sekunde langfristig
)

limiter = RateLimiter("api", config)

# Als Decorator
@limiter.decorate(tokens=1.0)
async def call_api():
    return await api.get("/data")

# Oder manuell
async def manual_call():
    await limiter.acquire(tokens=1.0)
    return await api.get("/data")

# Mit Warten statt Exception
await limiter.acquire(tokens=1.0, wait=True)  # Wartet bis Token da
await limiter.acquire(tokens=1.0, wait=True, timeout=5.0)  # Max 5s warten
```

### Exception

```python
try:
    await limiter.acquire()
except RateLimitExceeded as e:
    print(f"Limit erreicht! Warte {e.retry_after:.2f}s")
```

---

## 3. Retry (Der Hartnäckige)

### Konzept: Exponential Backoff mit Jitter

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXPONENTIAL BACKOFF + JITTER                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    Versuch 1: Fehler → Warte random(0, 1s)                          │
│    Versuch 2: Fehler → Warte random(0, 2s)                          │
│    Versuch 3: Fehler → Warte random(0, 4s)                          │
│    Versuch 4: Fehler → Warte random(0, 8s)                          │
│    ...                                                              │
│    Max: random(0, 60s)                                              │
│                                                                     │
│    Jitter verhindert, dass alle Clients gleichzeitig retrien        │
│    ("Thundering Herd Problem")                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Verwendung

```python
from bastion import Retry, RetryConfig, ExponentialBackoff

# Einfach
@Retry("api")
async def call_api():
    return await api.get("/data")

# Mit Config
config = RetryConfig(
    max_attempts=5,
    backoff=ExponentialBackoff(base=1.0, max_delay=60.0),
    retryable_exceptions=(ConnectionError, TimeoutError),  # Nur diese retrien
)

@Retry("api", config)
async def call_api():
    return await api.get("/data")
```

### Custom Backoff Strategy

```python
from bastion import BackoffStrategy

class LinearBackoff(BackoffStrategy):
    def __init__(self, delay: float = 1.0):
        self.delay = delay
    
    def get_delay(self, attempt: int) -> float:
        return self.delay * attempt

config = RetryConfig(backoff=LinearBackoff(delay=2.0))
```

---

## 4. Bulkhead (Das Schott)

### Konzept

Wie auf einem Schiff: Wenn ein Bereich voll Wasser läuft, schließt das Schott und der Rest bleibt trocken.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           BULKHEAD                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    Limit: 3 gleichzeitige Calls                                     │
│                                                                     │
│    [Call 1] [Call 2] [Call 3]  ← Alle Slots belegt                  │
│                                                                     │
│    Call 4 kommt an → BulkheadFullError!                             │
│                                                                     │
│    Verhindert, dass ein langsamer Service alle Worker blockiert     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Verwendung

```python
from bastion import Bulkhead, BulkheadFullError

bulkhead = Bulkhead("db-queries", limit=10)

# Als Context Manager
async def query_db():
    async with bulkhead():
        return await db.execute("SELECT ...")

# Exception handling
try:
    async with bulkhead():
        await slow_operation()
except BulkheadFullError:
    print("Zu viele gleichzeitige Requests!")
```

---

## 5. Timeout

### Verwendung

```python
from bastion import Timeout
import asyncio

@Timeout("api", seconds=5.0)
async def call_api():
    return await api.get("/slow-endpoint")

# Exception
try:
    await call_api()
except asyncio.TimeoutError:
    print("Timeout nach 5 Sekunden!")
```

---

## 6. Fallback

### Verwendung

```python
from bastion import Fallback

@Fallback(default={"status": "unknown"})
async def get_status():
    return await api.get("/status")

# Wenn api.get() fehlschlägt, wird {"status": "unknown"} zurückgegeben
```

---

## Kombinieren mit `compose()`

Die wahre Power von Bastion: Alle Bausteine kombinieren.

```python
from bastion import compose, Retry, CircuitBreaker, Timeout, Fallback

@compose(
    Fallback(default=None),           # 4. Wenn alles fehlschlägt: None
    Retry("api"),                     # 3. Bei Fehler: Retry
    CircuitBreaker("api"),            # 2. Bei zu vielen Fehlern: Blockieren
    Timeout("api", seconds=5.0),      # 1. Max 5s pro Versuch
)
async def fetch_data():
    return await api.get("/data")
```

**Reihenfolge ist wichtig!** `compose()` wendet Decorators von unten nach oben an:

```
Request
    ↓
Fallback (fängt alle Fehler)
    ↓
Retry (wiederholt bei Fehler)
    ↓
CircuitBreaker (blockt wenn zu viele Fehler)
    ↓
Timeout (bricht nach 5s ab)
    ↓
fetch_data()
```

---

## Metriken

Bastion hat ein pluggable Metrics-System.

### In-Memory (für Tests/Debugging)

```python
from bastion import set_metrics_collector, InMemoryCollector

collector = InMemoryCollector()
set_metrics_collector(collector)

# ... dein Code ...

# Metriken abrufen
for metric in collector.get_all():
    print(f"{metric.name}: {metric.value} ({metric.tags})")
```

### Custom Collector (z.B. Prometheus)

```python
from bastion import MetricsCollector, Metric, set_metrics_collector
from prometheus_client import Counter, Gauge

class PrometheusCollector(MetricsCollector):
    def __init__(self):
        self._counters = {}
        self._gauges = {}
    
    def emit(self, metric: Metric) -> None:
        if metric.metric_type == MetricType.COUNTER:
            if metric.name not in self._counters:
                self._counters[metric.name] = Counter(
                    metric.name.replace(".", "_"),
                    f"Bastion {metric.name}",
                    list(metric.tags.keys())
                )
            self._counters[metric.name].labels(**metric.tags).inc(metric.value)

set_metrics_collector(PrometheusCollector())
```

### Emittierte Metriken

| Metrik | Typ | Beschreibung |
|--------|-----|--------------|
| `bastion.cb.rejected` | Counter | Circuit Breaker hat Request abgelehnt |
| `bastion.cb.state_change` | Counter | Circuit Breaker State-Wechsel |
| `bastion.rate.acquired` | Counter | Rate Limiter Token vergeben |
| `bastion.rate.rejected` | Counter | Rate Limiter hat abgelehnt |
| `bastion.retry.gave_up` | Counter | Alle Retries aufgebraucht |
| `bastion.retry.wait` | Gauge | Aktuelle Wartezeit vor Retry |
| `bastion.bulkhead.entered` | Counter | Bulkhead betreten |
| `bastion.bulkhead.rejected` | Counter | Bulkhead war voll |
| `bastion.timeout` | Counter | Timeout aufgetreten |
| `bastion.fallback` | Counter | Fallback wurde verwendet |

---

## Vollständiges Beispiel

```python
import asyncio
import aiohttp
from bastion import (
    compose, CircuitBreaker, CircuitBreakerConfig,
    RateLimiter, RateLimiterConfig, Retry, RetryConfig,
    Timeout, Fallback, set_metrics_collector, InMemoryCollector
)

# Metrics aktivieren
metrics = InMemoryCollector()
set_metrics_collector(metrics)

# Configs
cb_config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=10.0)
rate_config = RateLimiterConfig(capacity=50, refill_rate=10)
retry_config = RetryConfig(max_attempts=3)

# Instanzen (werden geteilt über alle Calls)
circuit_breaker = CircuitBreaker("weather-api", cb_config)
rate_limiter = RateLimiter("weather-api", rate_config)

@compose(
    Fallback(default={"temp": "N/A", "status": "offline"}),
    Retry("weather", retry_config),
    circuit_breaker,
    Timeout("weather", seconds=3.0),
)
async def get_weather(city: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.weather.com/{city}") as resp:
            return await resp.json()

async def main():
    # Rate Limiter separat, weil er acquire() braucht
    await rate_limiter.acquire()
    result = await get_weather("berlin")
    print(f"Wetter: {result}")
    
    # Circuit Breaker State checken
    print(f"Circuit State: {circuit_breaker.state}")

asyncio.run(main())
```

---

## Best Practices

### 1. Circuit Breaker pro Service

```python
# Gut: Eigener Circuit Breaker pro externem Service
payment_cb = CircuitBreaker("payment-api")
weather_cb = CircuitBreaker("weather-api")

# Schlecht: Ein Circuit Breaker für alles
global_cb = CircuitBreaker("all-apis")  # Wenn einer down ist, sind alle blockiert!
```

### 2. Retry nur für transiente Fehler

```python
# Gut: Nur Netzwerkfehler retrien
config = RetryConfig(
    retryable_exceptions=(ConnectionError, TimeoutError, aiohttp.ClientError)
)

# Schlecht: Alle Exceptions retrien (inkl. 400 Bad Request)
config = RetryConfig(retryable_exceptions=(Exception,))
```

### 3. Timeout immer setzen

```python
# Gut
@Timeout("api", seconds=5.0)
async def call_api(): ...

# Schlecht: Kein Timeout → kann ewig hängen
async def call_api(): ...
```

### 4. Sinnvolle Fallback-Werte

```python
# Gut: Gecachter Wert oder degraded response
@Fallback(default={"status": "cached", "data": last_known_data})
async def get_data(): ...

# Schlecht: Einfach None zurückgeben
@Fallback(default=None)
async def get_data(): ...
```

---

## Vergleich mit Alternativen

| Feature | Bastion | Tenacity | aiobreaker | Polly (C#) |
|---------|---------|----------|------------|------------|
| Zero Dependencies | ✅ | ❌ | ❌ | ❌ |
| Async Native | ✅ | ✅ | ✅ | ✅ |
| Circuit Breaker | ✅ | ❌ | ✅ | ✅ |
| Rate Limiter | ✅ | ❌ | ❌ | ✅ |
| Bulkhead | ✅ | ❌ | ❌ | ✅ |
| Retry | ✅ | ✅ | ❌ | ✅ |
| Composable | ✅ | ✅ | ❌ | ✅ |
| Metrics | ✅ | ❌ | ❌ | ✅ |
| Lines of Code | ~450 | ~2000 | ~500 | ~10000 |

---

## API Referenz

### CircuitBreaker

```python
CircuitBreaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
)

CircuitBreakerConfig(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    half_open_max_calls: int = 3,
    excluded_exceptions: tuple = ()
)
```

### RateLimiter

```python
RateLimiter(
    name: str,
    config: Optional[RateLimiterConfig] = None
)

RateLimiterConfig(
    capacity: float = 100.0,
    refill_rate: float = 10.0
)

# Methods
await limiter.acquire(tokens=1.0, wait=False, timeout=None)
limiter.decorate(tokens=1.0, wait=False)
```

### Retry

```python
Retry(
    name: str,
    config: Optional[RetryConfig] = None
)

RetryConfig(
    max_attempts: int = 3,
    backoff: BackoffStrategy = ExponentialBackoff(),
    retryable_exceptions: tuple = (Exception,)
)

ExponentialBackoff(
    base: float = 1.0,
    max_delay: float = 60.0
)
```

### Bulkhead

```python
Bulkhead(name: str, limit: int)

# Usage: async context manager
async with bulkhead():
    ...
```

### Timeout

```python
Timeout(name: str, seconds: float)

# Usage: decorator
@Timeout("name", 5.0)
async def func(): ...
```

### Fallback

```python
Fallback(default: Any)

# Usage: decorator
@Fallback({"error": True})
async def func(): ...
```

### compose

```python
compose(*decorators)

# Usage
@compose(Retry("r"), CircuitBreaker("cb"), Timeout("t", 5.0))
async def func(): ...
```

---

## Lizenz

MIT

---

## Autor

chrismaghuhn
