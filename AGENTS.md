# TensorMesh Master Blueprint & Agent Memory Store

> **CRITICAL DIRECTIVE FOR ALL AI AGENTS**:
> This document is the **single source of truth** and **persistent memory** for the TensorMesh codebase.
> Whenever you (the AI assistant) introduce new modules, refactor existing components, modify ports, or update ML/FSM logic, **you are strictly required to update this file in the same turn**.
> Before responding to architectural inquiries, cross-verify this document against the physical workspace (`docker-compose.yml`, `requirements.txt`, `tensormesh/`, `tensormesh-compute/`) to ensure zero hallucinations.

---

## 1. System Design & Architecture Overview

TensorMesh is an enterprise-grade **Zero-Trust Agentic Mesh and Subsurface Mineral Supply Chain Intelligence Platform**. It coordinates defense-grade mineral exploration, geopolitical trade debiasing, and maritime compliance routing across specialized AI agents, native C++23 SIMD compute kernels, and graph databases.

### High-Level System Topology

```
                               ┌────────────────────────────────────────────────────────┐
                               │   Command Center Frontend (Next.js 14 App Router)       │
                               │   • Port: :3000                                        │
                               │   • React Flow (@xyflow/react) Visual Supply Graph     │
                               │   • Live Clean Room TokenVault Auditor & Policy Sim    │
                               └───────────────────────────┬────────────────────────────┘
                                                           │ Axios REST (POST /api/deposits/evaluate)
                                                           ▼
                               ┌────────────────────────────────────────────────────────┐
                               │   Python 3.11+ FastAPI Backend Runtime                 │
                               │   • Port: :8000 (Uvicorn)                              │
                               │   • TokenVault: AES-256 PII/ITAR Entity Clean Room     │
                               │   • Model Context Protocol (MCP) Tool Service (/mcp)   │
                               │   • Multi-Factor XGBoost Learning-to-Rank (LTR) Engine │
                               │   • GeologicalReasoningMesh (Geochem, Structural, Econ)│
                               └───────┬──────────────┬───────────────┬─────────────────┘
                                       │              │               │
                  pybind11 IPC (< 1µs) │              │ Bolt (:7687)  │ Embedded RocksDB API
                                       ▼              ▼               ▼
 ┌──────────────────────────────────────────────┐  ┌──────────────┐  ┌──────────────────────────────┐
 │ Native Compute Engine (C++23)                │  │ Neo4j Graph  │  │ Embedded RocksDB Storage     │
 │ • pybind11 module: _tensormesh_compute       │  │ • Ports:     │  │ • module: _rocksdb_bridge    │
 │ • Apple NEON SIMD accelerated impedance      │  │   :7474 HTTP │  │ • 4 Column Families:         │
 │ • Spectral decomposition & spatial inversion │  │   :7687 Bolt │  │   default, traces,           │
 │ • Sub-surface seismic scalar/vector math     │  │ • Multi-hop  │  │   agent_state, telemetry     │
 └──────────────────────────────────────────────┘  │   Supply DAG │  └──────────────────────────────┘
                                                   └──────────────┘
                                                          ▲
                                                          │ gRPC CorridorAuditRequest (:50051)
                                                          │
                               ┌──────────────────────────┴─────────────────────────────┐
                               │   Maritime AIS Ingestion & Compliance Engine            │
                               │   • Java 21 Kafka Streams: Consumes maritime.telemetry  │
                               │   • Python gRPC MaritimeComplianceServer (:50051)       │
                               │   • 15-min Inactivity Sessionization & Geofence Auditing│
                               └────────────────────────────────────────────────────────┘
```

---

## 2. Core Component Map

| Component | Path | Language / Runtime | Primary Port | Core Responsibilities |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | `/frontend` | Next.js 14, React, Tailwind CSS, Shadcn UI, React Flow | `:3000` | Interactive defense command center, animated Neo4j supply chain graph, live Clean Room encryption auditor, and real-time policy shock simulator. |
| **API & Reasoning Backend** | `/tensormesh` | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 | `:8000` | Core orchestration: REST endpoints, Model Context Protocol (MCP) tool server, geological agent mesh, ML ranking, cryptographic trace hashing. |
| **Native Compute** | `/tensormesh-compute` | C++23, pybind11, CMake, Apple NEON SIMD | In-process | Hardware-accelerated seismic computation, acoustic impedance matrix inversion, and spectral decomposition routines. |
| **Graph Database** | `docker: neo4j` | Neo4j Community / Enterprise | `:7474` / `:7687` | Multi-hop supply chain knowledge graph (Mines, Refineries, Transshipment Ports, Defense Tier-1 OEMs). |
| **Embedded Storage** | `/tensormesh/storage` | RocksDB C++ Bridge (`_rocksdb_bridge`) | In-process | Sub-millisecond persistence across 4 column families: default, traces, agent_state, and telemetry. |
| **Maritime AIS Ingest** | `/services` & `/tensormesh/grpc` | Java 21 (Kafka Streams) + Python gRPC | `:50051` | Maritime AIS vessel tracking, shadow transshipment geofencing, Kafka voyage sessionization, and gRPC corridor audits. |
| **Observability** | `/infra` | Grafana, Tempo, Loki, Prometheus | `:3001` (Grafana), `:4317` (Tempo), `:3100` (Loki) | Cryptographic OTel trace chaining, structured audit logging, and latency/memory metrics. |

---

## 3. End-to-End Workflow Lifecycles

### A. Subsurface Mineral Evaluation & Geopolitical Rerouting
1. **Payload Ingestion & Clean Room Masking**: The user initiates a deposit evaluation via the Next.js UI. The `TokenVault` intercepts the payload, extracts sensitive entity names (supplier names, proprietary defense alloy ratios), and substitutes them with surrogate tokens via deterministic AES-256 envelope encryption.
2. **Native Seismic Compute**: High-volume geophysical arrays pass through pybind11 to the C++23 native compute engine (`_tensormesh_compute`), leveraging Apple NEON SIMD for vector-accelerated impedance inversion.
3. **GraphRAG via MCP Isolation**: Agents query the Neo4j supply chain graph exclusively through typed Model Context Protocol (MCP) endpoints mounted at `/mcp`, never via raw unvalidated Cypher queries.
4. **Learning-to-Rank (LTR) Scoring**: An XGBoost ML engine computes supplier ranking scores factoring in geopolitical sanctions, ESG green-refining ratings, and transshipment hub debiasing.
5. **Agent-to-Agent (A2A) Governance**: The `GeologicalReasoningMesh` coordinates specialized agents (Geochemist, Structural, Economic). The Anti-Amplification supervisor monitors confidence scores: if confidence drops below 0.85 or a sanction risk is detected, execution asynchronously suspends to RocksDB awaiting Human-in-the-Loop (HITL) clearance.

### B. Maritime AIS Shadow Trade Audit
1. **Kafka Stream Aggregation**: Raw vessel AIS pings stream into Kafka topic `maritime.telemetry.raw`. A Java 21 Kafka Streams engine groups pings into 15-minute inactivity session windows.
2. **gRPC Corridor Verification**: The streaming pipeline transmits a `CorridorAuditRequest` over gRPC (`:50051`) to the `MaritimeComplianceServer`.
3. **Geofence & Flag Inspection**: The compliance engine detects spoofed AIS signals, unauthorized ship-to-ship (STS) transfers, and shadow port stops, recording audit checkpoints in RocksDB.

---

## 4. Architectural Decision Records (ADRs)

### ADR-001: Zero-Trust Data Clean Room (TokenVault) for ITAR/CUI Compliance
* **Status**: Accepted & Enforced
* **Decision**: Enforce client-side/local AES-256 tokenization on all sensitive defense entities prior to passing data to any LLM or external reasoning provider.
* **Engineering Rationale**: Defense OEMs cannot legally transmit proprietary alloy requirements or classified supply chains to third-party model endpoints. TokenVault rehydrates encrypted entities only within trusted boundaries.

### ADR-002: Model Context Protocol (MCP) for Graph Isolation over Direct Cypher
* **Status**: Accepted & Enforced
* **Decision**: Strictly isolate LLM agents from direct Neo4j database drivers using the **Model Context Protocol (MCP)** at `/mcp`.
* **Engineering Rationale**: Direct prompt-to-Cypher generation introduces severe prompt injection, catastrophic database mutation, and non-deterministic traversal bugs. MCP exposes rigid, typed JSON-RPC tool endpoints with schema validation.

### ADR-003: Native C++23 Pybind11 Kernels with Apple NEON SIMD Acceleration
* **Status**: Accepted & Enforced
* **Decision**: Implement heavy seismic matrix operations, acoustic impedance, and spectral decomposition in **C++23** using **pybind11** and ARM Apple NEON SIMD instructions.
* **Engineering Rationale**: Python NumPy/SciPy loops introduce memory allocations and GIL contention during deep tensor spatial inversion. C++23 SIMD vectorization completes computations sub-millisecond on local Apple Silicon hardware.

### ADR-004: Embedded RocksDB with Column Families over Networked Databases for State
* **Status**: Accepted & Enforced
* **Decision**: Use embedded **RocksDB** via a native bridge (`_rocksdb_bridge`) with 4 dedicated column families (`default`, `traces`, `agent_state`, `telemetry`) for agent execution checkpoints and trace logging.
* **Engineering Rationale**: Eliminates network hop latencies (1.5-5.0 ms) during high-throughput agent state serialization and cryptographic trace hashing. RocksDB writes directly to local storage in microseconds.

### ADR-005: A2A Anti-Amplification Supervisor & HITL Sanction Suspension
* **Status**: Accepted & Enforced
* **Decision**: Implement an **Anti-Amplification Supervisor** governing all Agent-to-Agent (A2A) communications, with automatic state suspension upon sanction detection.
* **Engineering Rationale**: Prevents runaway recursive hallucination loops between autonomous agents. If an entity triggers OFAC/ITAR sanctions, the system serializes execution state to RocksDB and dispatches a webhook for human verification before proceeding.

### ADR-006: Learning-to-Rank (LTR) XGBoost Regressor for Supply Route Debiasing
* **Status**: Accepted & Enforced
* **Decision**: Deploy an **XGBoost Regressor** trained on historical trade routes to score and debias critical mineral sourcing.
* **Engineering Rationale**: Simple heuristics fail to detect sophisticated transshipment hubs (e.g., masking Chinese rare-earth minerals through third-party nations). XGBoost multi-factor scoring evaluates carbon intensity, route latency, and jurisdictional risk simultaneously.

---

## 5. Development & Automation Commands

* **Launch Backing Infrastructure**: `docker compose up -d neo4j redis tempo loki prometheus grafana`
* **Run Python Backend**: `uvicorn tensormesh.api.main:app --host 0.0.0.0 --port 8000 --reload`
* **Compile Native Compute**: `cmake -B tensormesh-compute/build -S tensormesh-compute && cmake --build tensormesh-compute/build`
* **Run Frontend**: `cd frontend && npm run dev` (accessible at `http://localhost:3000`)
* **Execute Test Suite**: `pytest tests/`
