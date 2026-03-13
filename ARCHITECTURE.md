# Service Registry Architecture

## 📐 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Service Registry System                      │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Service Registry (Port 5000)               │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │         In-Memory Registry Storage               │  │    │
│  │  │                                                   │  │    │
│  │  │  {                                                │  │    │
│  │  │    "user-service": [                             │  │    │
│  │  │      {                                            │  │    │
│  │  │        "address": "http://localhost:8001",       │  │    │
│  │  │        "registered_at": "2026-03-11T10:00:00",  │  │    │
│  │  │        "last_heartbeat": "2026-03-11T10:05:30"  │  │    │
│  │  │      }                                            │  │    │
│  │  │    ],                                             │  │    │
│  │  │    "payment-service": [...]                      │  │    │
│  │  │  }                                                │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │         Background Cleanup Thread                │  │    │
│  │  │  • Runs every 10 seconds                         │  │    │
│  │  │  • Removes stale services (no heartbeat > 30s)   │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ User Service  │     │ User Service  │     │Payment Service│
│  Instance 1   │     │  Instance 2   │     │  Instance 1   │
│ Port 8001     │     │ Port 8003     │     │ Port 8002     │
└───────────────┘     └───────────────┘     └───────────────┘
```

## 🧭 High-Level Architecture (Client + Services)

```mermaid
flowchart LR
  Client[Client CLI]
  Registry[Service Registry<br/>Flask :5001]
  Cart1[Cart Service<br/>Instance A :8001]
  Cart2[Cart Service<br/>Instance B :8003]
  Pay1[Payment Service<br/>Instance A :8002]
  Pay2[Payment Service<br/>Instance B :8004]

  Cart1 -->|Register + Heartbeat| Registry
  Cart2 -->|Register + Heartbeat| Registry
  Pay1 -->|Register + Heartbeat| Registry
  Pay2 -->|Register + Heartbeat| Registry

  Client -->|Discover| Registry
  Client -->|Call Random Instance| Cart1
  Client -->|Call Random Instance| Cart2
  Client -->|Call Random Instance| Pay1
  Client -->|Call Random Instance| Pay2
```

## 🔄 Request Flow Diagrams

### 1. Service Registration Flow

```
Service                          Registry
  │                                 │
  │  POST /register                 │
  │  {                              │
  │    "service": "user-service",   │
  │    "address": "http://...:8001" │
  │  }                              │
  ├────────────────────────────────>│
  │                                 │
  │                                 │ 1. Validate request
  │                                 │ 2. Acquire lock
  │                                 │ 3. Check if exists
  │                                 │ 4. Add to registry
  │                                 │ 5. Release lock
  │                                 │
  │  200 OK                         │
  │  {                              │
  │    "status": "registered"       │
  │  }                              │
  │<────────────────────────────────┤
  │                                 │
  │  Start heartbeat loop           │
  │  (every 10 seconds)             │
  │                                 │
```

### 2. Service Discovery Flow

```
Client                           Registry
  │                                 │
  │  GET /discover/user-service     │
  ├────────────────────────────────>│
  │                                 │
  │                                 │ 1. Acquire lock
  │                                 │ 2. Find service
  │                                 │ 3. Filter active instances
  │                                 │    (heartbeat < 30s ago)
  │                                 │ 4. Release lock
  │                                 │
  │  200 OK                         │
  │  {                              │
  │    "service": "user-service",   │
  │    "instances": [               │
  │      {                          │
  │        "address": "http://...", │
  │        "uptime_seconds": 120    │
  │      }                          │
  │    ],                           │
  │    "count": 1                   │
  │  }                              │
  │<────────────────────────────────┤
  │                                 │
  │  Choose instance                │
  │  Make request to service        │
  │                                 │
```

### 3. Heartbeat Flow

```
Service                          Registry
  │                                 │
  │  (Every 10 seconds)             │
  │                                 │
  │  POST /heartbeat                │
  │  {                              │
  │    "service": "user-service",   │
  │    "address": "http://...:8001" │
  │  }                              │
  ├────────────────────────────────>│
  │                                 │
  │                                 │ 1. Acquire lock
  │                                 │ 2. Find instance
  │                                 │ 3. Update last_heartbeat
  │                                 │ 4. Release lock
  │                                 │
  │  200 OK                         │
  │  {                              │
  │    "status": "ok"               │
  │  }                              │
  │<────────────────────────────────┤
  │                                 │
```

### 4. Cleanup Flow

```
Registry Background Thread
  │
  │  (Every 10 seconds)
  │
  ├─> Acquire lock
  │
  ├─> For each service:
  │     For each instance:
  │       If (now - last_heartbeat) > 30s:
  │         Remove instance
  │
  ├─> Remove empty services
  │
  ├─> Release lock
  │
  └─> Sleep 10 seconds
```

## 🏗️ Component Architecture

### Registry Core Components

```
┌─────────────────────────────────────────────────────────┐
│                   Flask Application                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │              API Endpoints Layer                 │   │
│  │                                                   │   │
│  │  • POST /register      - Register service        │   │
│  │  • GET  /discover/:id  - Find service            │   │
│  │  • POST /heartbeat     - Update heartbeat        │   │
│  │  • POST /deregister    - Remove service          │   │
│  │  • GET  /services      - List all services       │   │
│  │  • GET  /health        - Registry health         │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Business Logic Layer                   │   │
│  │                                                   │   │
│  │  • Validation                                     │   │
│  │  • Error handling                                 │   │
│  │  • Instance filtering (active vs stale)          │   │
│  │  • Timestamp management                           │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │            Data Access Layer                     │   │
│  │                                                   │   │
│  │  • Thread-safe registry access                   │   │
│  │  • Lock management                                │   │
│  │  • CRUD operations                                │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Storage Layer                       │   │
│  │                                                   │   │
│  │  registry = {}  (In-memory dictionary)           │   │
│  │  registry_lock = threading.Lock()                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Background Cleanup Thread                   │
│                                                           │
│  while True:                                             │
│    sleep(10)                                             │
│    cleanup_stale_services()                              │
└─────────────────────────────────────────────────────────┘
```

### Service Client Components

```
┌─────────────────────────────────────────────────────────┐
│                  Service Application                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Business Logic                         │   │
│  │  (Your actual service code)                      │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                               │
│                          ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │         ServiceClient (Registry Client)          │   │
│  │                                                   │   │
│  │  • register()      - Register on startup         │   │
│  │  • deregister()    - Cleanup on shutdown         │   │
│  │  • send_heartbeat()- Keep alive                  │   │
│  │  • discover()      - Find other services         │   │
│  │                                                   │   │
│  │  ┌───────────────────────────────────────────┐  │   │
│  │  │    Heartbeat Thread                       │  │   │
│  │  │                                           │  │   │
│  │  │  while not stopped:                       │  │   │
│  │  │    send_heartbeat()                       │  │   │
│  │  │    sleep(10)                              │  │   │
│  │  └───────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## 🔐 Thread Safety

### Lock Usage Pattern

```python
# Global lock
registry_lock = threading.Lock()

# Safe read/write pattern
with registry_lock:
    # Critical section - only one thread at a time
    if service in registry:
        registry[service].append(instance)
    # Lock automatically released here
```

### Concurrent Request Handling

```
Time →
─────────────────────────────────────────────────────────>

Thread 1: [Register user-service    ]
Thread 2:         [Heartbeat payment-service]
Thread 3:                  [Discover user-service]
Cleanup:                            [Cleanup stale]

With Lock:
Thread 1: [──────────────]
Thread 2:                 [──────────────]
Thread 3:                                 [──────────]
Cleanup:                                            [────]
          ▲               ▲                         ▲
          Lock acquired   Lock acquired             Lock acquired
```

## 📊 Data Structure

### Registry Structure

```python
registry = {
    "user-service": [
        {
            "address": "http://localhost:8001",
            "registered_at": datetime(2026, 3, 11, 10, 0, 0),
            "last_heartbeat": datetime(2026, 3, 11, 10, 5, 30)
        },
        {
            "address": "http://localhost:8003",
            "registered_at": datetime(2026, 3, 11, 10, 2, 0),
            "last_heartbeat": datetime(2026, 3, 11, 10, 5, 25)
        }
    ],
    "payment-service": [
        {
            "address": "http://localhost:8002",
            "registered_at": datetime(2026, 3, 11, 10, 1, 0),
            "last_heartbeat": datetime(2026, 3, 11, 10, 5, 28)
        }
    ]
}
```

### Time Complexity

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| Register | O(n) | n = instances of service |
| Discover | O(n) | n = instances of service |
| Heartbeat | O(n) | n = instances of service |
| Deregister | O(n) | n = instances of service |
| List Services | O(s*n) | s = services, n = avg instances |
| Cleanup | O(s*n) | s = services, n = avg instances |

### Space Complexity

```
Total Memory = O(s * n * m)

Where:
  s = number of services
  n = average instances per service
  m = memory per instance (~200 bytes)

Example:
  10 services × 5 instances × 200 bytes = 10 KB
  100 services × 10 instances × 200 bytes = 200 KB
  1000 services × 20 instances × 200 bytes = 4 MB
```

## 🔄 State Transitions

### Service Instance Lifecycle

```
┌─────────┐
│ Unknown │
└────┬────┘
     │ POST /register
     ▼
┌─────────┐
│Registered│◄──────────┐
└────┬────┘            │
     │                 │ POST /heartbeat
     │ Time passes     │ (within 30s)
     ▼                 │
┌─────────┐            │
│ Active  │────────────┘
└────┬────┘
     │
     │ No heartbeat for 30s
     ▼
┌─────────┐
│  Stale  │
└────┬────┘
     │ Cleanup thread
     ▼
┌─────────┐
│ Removed │
└─────────┘
```

## 🌐 Network Communication

### HTTP Request/Response Flow

```
Client                    Network                   Registry
  │                          │                          │
  │  1. Create HTTP request  │                          │
  │  POST /register          │                          │
  │  Content-Type: json      │                          │
  ├─────────────────────────>│                          │
  │                          │  2. TCP connection       │
  │                          │  established             │
  │                          ├─────────────────────────>│
  │                          │                          │
  │                          │  3. Process request      │
  │                          │  Validate, store data    │
  │                          │                          │
  │                          │  4. Generate response    │
  │                          │<─────────────────────────┤
  │  5. Receive response     │                          │
  │<─────────────────────────┤                          │
  │                          │                          │
```

## 🎯 Scalability Considerations

### Single Registry Limitations

```
Current Architecture:
┌─────────┐
│ Registry│ ← Single point of failure
└────┬────┘
     │
     ├─── Service 1
     ├─── Service 2
     ├─── Service 3
     └─── Service N

Limitations:
• Max ~1000 services
• Max ~10,000 instances
• Max ~1000 requests/sec
• No redundancy
```

### Scaled Architecture (Future)

```
Load Balancer
     │
     ├─── Registry 1 ◄──┐
     ├─── Registry 2 ◄──┼── Replication
     └─── Registry 3 ◄──┘
          │
          └─── Shared Database
               (PostgreSQL/Redis)

Benefits:
• High availability
• Horizontal scaling
• No single point of failure
• 10,000+ services
• 100,000+ instances
```

## 📈 Monitoring Points

```
┌─────────────────────────────────────────┐
│         Metrics to Monitor              │
├─────────────────────────────────────────┤
│                                         │
│ • Total services registered             │
│ • Total instances registered            │
│ • Active vs stale instances             │
│ • Registration rate (per second)        │
│ • Discovery rate (per second)           │
│ • Heartbeat rate (per second)           │
│ • Average response time                 │
│ • Error rate                            │
│ • Memory usage                          │
│ • CPU usage                             │
│                                         │
└─────────────────────────────────────────┘
```

This architecture provides a solid foundation for understanding distributed service discovery! 🚀
