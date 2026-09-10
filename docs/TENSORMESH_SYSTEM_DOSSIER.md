# TensorMesh System Dossier

**Audit date:** 2026-09-10  
**Scope:** the complete on-disk TensorMesh workspace, with source/configuration files enumerated individually and generated, dependency, binary, and runtime state classified explicitly.

## Executive Summary & System Topology

TensorMesh is a multi-runtime platform for subsurface mineral evaluation and maritime supply-chain compliance. The primary request path is a Next.js command center calling a FastAPI application. The API performs native seismic/spatial compute, stores traces and agent evidence in RocksDB, queries a Neo4j supply graph through a typed MCP service, and coordinates geochemical, structural, and economic agents through an A2A-gated reasoning mesh. A separate Java 21 Kafka Streams service consumes maritime AIS protobuf messages, groups rare-earth voyages, and calls the Python gRPC compliance service.

```text
Next.js :3000
  -> Axios POST /api/deposits/evaluate
FastAPI / Uvicorn :8000
  -> native pybind11 kernels (C++23)
  -> RocksDB (_rocksdb_bridge; four column families)
  -> MCPToolService -> Neo4j Bolt :7687
  -> GeologicalReasoningMesh -> geochemist + structural -> economic
  -> OpenTelemetry spans and cryptographic trace chain

Kafka maritime.telemetry.raw
  -> Java Kafka Streams session aggregation (15-minute inactivity)
  -> protobuf CorridorAuditRequest over gRPC :50051
  -> MaritimeComplianceServer -> geofence audit + RocksDB checkpoint
  -> CorridorAuditResponse
```

### Runtime components

| Component | Entrypoint/build | Contract | Durable state |
|---|---|---|---|
| Python backend | `uvicorn tensormesh.api.main:app --host 0.0.0.0 --port 8000` | REST, MCP mounted at `/mcp`, Python gRPC server factory | RocksDB, Neo4j, optional OTLP |
| Native compute | `tensormesh-compute/CMakeLists.txt` | pybind11 module `_tensormesh_compute` | none |
| Native storage | `_rocksdb_bridge` | `put/get/delete/scan` | RocksDB column families |
| AIS ingest | Gradle Java 21 application | Kafka input and gRPC client | Kafka Streams state store/materialization |
| Frontend | Next.js App Router | browser calls REST API | browser React state |
| Graph | `SupplyChainGraph` | Neo4j Cypher queries | Neo4j entities/routes |

### Important observed boundaries and risks

- `docker-compose.yml` starts Neo4j, backend, and frontend, but does not start Kafka, the AIS service, RocksDB native build, or an OTLP collector.
- The API module constructs global `TokenVault`, `MCPToolService`, simulator, tracer, and reasoning mesh instances at import time; the native RocksDB bridge must already be importable.
- Python generated protobuf code records Protobuf runtime `7.35.1`; generated gRPC code requires `grpcio >= 1.83.1`, matching `requirements.txt`'s lower bound.
- Native impedance has an Apple NEON path. Spectral decomposition is scalar C++; there is no AVX or explicit GPU path.
- The test import list names `tensormesh.data.gsi_copilot`, which is present on disk but is not in the tracked-file list; `tensormesh/data/token_vault.sqlite` and `tensormesh/data/vault.key` are runtime artifacts and secrets.
- The README describes features beyond currently wired code, including some UI capabilities and “immutable” tracing claims. This dossier describes observed implementation, not marketing intent.

## Complete Directory & File Manifest

The tables below enumerate every source/configuration file found under the requested product trees. For each file, “calls” means direct imports or runtime consumers observed in source; “invariant” records storage, compute, protocol, or execution constraints.

### Workspace root and auxiliary data

| File | Identity and core contracts | Upstream / downstream | Storage / compute invariant |
|---|---|---|---|
| `README.md` | Product architecture, feature claims, local quickstart, stack description. | Operators and developers. | Describes Python 3.11+, Next.js 14, Neo4j, RocksDB, local Apple Silicon operation; some claims exceed currently wired code. |
| `architecture.svg` | Architecture diagram asset. | README. | Static binary/vector asset; no executable contract. |
| `backend.Dockerfile` | Python 3.11-slim image; installs `requirements.txt`, copies `tensormesh`, starts Uvicorn. | `docker-compose.yml`. | Exposes 8000; does not build/copy native extensions or the separate `data/` tree. |
| `docker-compose.yml` | Neo4j, backend, frontend service topology and bridge network. | Docker operators. | Neo4j Bolt 7687/HTTP 7474; backend 8000; frontend 3000; no Kafka or OTLP service. |
| `requirements.txt` | Python dependency contract: Pydantic, FastAPI, NumPy, Neo4j, ML, MCP, OTel, gRPC. | Docker and local Python setup. | Native CMake dependencies are not represented here. |
| `data/ingestion.py` | Root-level `DataIngestionEngine` for UN Comtrade HS 2805 with deterministic fallback. | Standalone data utility; not imported by the package tests. | External HTTPS request with five-second timeout; fallback route records are in memory. |
| `reports/agent_evaluation_scorecard.md` | Generated human-readable evaluation report. | `tensormesh.eval.evaluator`. | Derived artifact; metrics reflect the last evaluator run. |
| `.gitignore` | Ignores environments, secrets, local databases, native outputs, build/dependency trees, IDE files. | Git. | Confirms vault key, RocksDB, CMake, Gradle, and npm products are local state. |

### `tensormesh/`

#### Package roots and configuration

| File | Identity and core contracts | Upstream / downstream | Storage / compute invariant |
|---|---|---|---|
| `tensormesh/__init__.py` | Package marker; no public declarations. | Imported by Python package resolution. | None. |
| `tensormesh/api/__init__.py` | API package marker. | `tensormesh.api.main`. | None. |
| `tensormesh/api/main.py` | FastAPI `app`; `PromptRequest`, `SimulationRequest`, `DepositEvaluationRequest`; routes `/`, `/api/clean-room/redact`, `/api/graph/trace/{entity_name}`, `/api/simulate`, `/api/deposits/evaluate`; mounts MCP. | Frontend calls deposit route; imports security, agents, compute, graph, MCP, simulation, storage, tracer. | Deposit path writes `cf_spatial_voxels`, reads strata, writes A2A checkpoints and secure trace; native compute uses float32 arrays and 10-90 Hz frequencies. |
| `tensormesh/api/__init__.py` | API package marker. | `tensormesh.api.main`. | None. |
| `tensormesh/config/__init__.py` | Configuration package marker. | Settings consumers. | None. |
| `tensormesh/config/settings.py` | Pydantic-settings `Settings`; singleton `settings`. | Imported by security, storage users, hardware, telemetry. | `DATA_DIR=data`; RocksDB at `data/rocksdb`; key at `data/vault.key`; `.env` supported; creates data directory. |
| `tensormesh/compute/__init__.py` | Re-exports inversion and spatial public API. | Agents, API, tests. | Public boundary for native/fallback compute and Morton encoding. |
| `tensormesh/storage/__init__.py` | Re-exports `RocksDBStore`, four `CF_*` constants, `COLUMN_FAMILIES`. | All durable-state consumers. | Column-family order is spatial, borehole, A2A, secure. |
| `tensormesh/grpc/__init__.py` | gRPC package marker. | gRPC service/client imports. | None. |
| `tensormesh/grpc/generated/__init__.py` | Generated package marker. | Generated protobuf modules. | Generated; regenerate from `proto/maritime_telemetry.proto`. |
| `tensormesh/hardware/__init__.py` | Hardware package marker. | Hardware router consumers. | None. |
| `tensormesh/security/__init__.py` | Empty security package marker. | Security modules. | None. |
| `tensormesh/eval/__init__.py` | Evaluation package marker. | Evaluator/tests. | None. |

#### Agents and orchestration

| File | Identity and core contracts | Upstream / downstream | Storage / compute invariant |
|---|---|---|---|
| `agents/a2a_protocol.py` | Pydantic `A2AMessageEnvelope`; `A2ARouter.dispatch`. | Reasoning mesh creates envelopes; supervisor validates them. | Envelope carries confidence, evidence refs, task ID, timestamp; dispatch is in-process and returns `DELIVERED`. |
| `agents/economic_assessor.py` | `EconomicAssessorAgent.analyze` -> `AgentHypothesis`. | Mesh passes geochem/structure; calls shipping audit. | Viability clamps recovery and supply risk to `[0,1]`; optional maritime audit can force `dfars_violation`. |
| `agents/fsm_engine.py` | `DeterministicFSMEngine.execute_workflow`. | Compiler output supplies DAG; HITL governor handles anomaly. | First `ANOMALY_DETECTION` without override persists secure HITL state and stops. |
| `agents/geochemist.py` | `GeochemistAgent.analyze` -> anomaly/benchmark hypothesis. | Mesh invokes in a worker thread. | Aggregates assays case-insensitively; benchmark units are ppm; confidence is bounded by formula. |
| `agents/reasoning_mesh.py` | `GeologicalReasoningMesh.evaluate_deposit` and async variant; private checkpoint/handoff/spatial helpers. | API, evaluator, tests; invokes three agents, compute Morton, OTel. | Geochem and structural run concurrently; every hypothesis/handoff/verdict goes to `cf_a2a_checkpoints`; spatial voxels use 21-bit Morton coordinates. |
| `agents/reasoning_models.py` | Pydantic `AgentHypothesis`, `ReasoningMeshResult`. | All agents and evaluator. | Confidence constrained to `[0,1]`; evidence is arbitrary JSON-like mapping. |
| `agents/structural_geologist.py` | `StructuralGeologistAgent.analyze`. | Mesh; calls minimum-curvature native trajectory. | Gaps and faults form structural risk; trajectory requires non-decreasing measured depth. |
| `agents/supervisor.py` | `MultiAgentSupervisor.evaluate_handoff`. | Mesh handoff gate. | Default minimum confidence `0.85`, mesh default `0.6`; below threshold raises in mesh. |

#### Compute, graph, MCP, security, ML, resilience, and telemetry

| File | Identity and core contracts | Upstream / downstream | Storage / compute invariant |
|---|---|---|---|
| `compute/inversion.py` | `invert_acoustic_impedance`, `compute_spectral_decomposition`, `store_inverted_voxel_trace`, `retrieve_inverted_voxel_trace`; NumPy fallback. | API and compute tests; optionally calls `_tensormesh_compute`. | Impedance recursively applies clipped reflection; spectra are frequency x time Morlet output; traces are raw float32 bytes in `cf_spatial_voxels` under `voxel:`. |
| `compute/spatial.py` | Re-exports `SurveyStation`, trajectory, `encode_morton_3d`, `decode_morton_3d`. | Structural agent and spatial tests. | Native-only import; coordinates are masked to 21 bits by C++. |
| `graph/neo4j_schema.py` | `SupplyChainGraph`: schema initialization, route ingestion, origin/dependency tracing, hybrid knowledge query, close. | MCP service and GraphRAG tests; Neo4j Bolt via `NEO4J_URI`. | Cypher uses `Entity`, `Deposit`, `RockFormation`, `RareEarthMineral`, `Refinery`; dependency query max path is 8 but request limits hops to 8; concentration risk is top quantity share. |
| `mcp/server.py` | Pydantic request/response models for strata, assays, supply, concession, shipping; `MCPToolService`; `create_mcp_server`; shipping hash/distance functions. | API, reasoning/economic agent, gRPC service, tests. | Reads `cf_borehole_telemetry`; writes concessions to `cf_spatial_voxels`, shipping/A2A evidence to `cf_a2a_checkpoints`; SHA-256 canonical JSON audits; configured Indian regions and maritime geofences are static. |
| `security/token_vault.py` | `TokenVault.redact_and_tokenize`, `rehydrate`; Fernet key management. | API clean-room route and guardrails. | Secure records in `cf_secure_state` under `token:`; key file is `data/vault.key`; regex categories supplier, amount, alloy, defense identifier. |
| `security/semantic_cache.py` | `SemanticCache.check_cache`, `add_to_cache`; SentenceTransformer embeddings. | Available utility; no observed API call site. | Cache in `cf_secure_state` under `semantic_cache:`; cosine threshold default `.95`; model downloads/loads `all-MiniLM-L6-v2`. |
| `security/guardrails.py` | `GuardrailViolation`, `enforce_itar_cleanroom`, `enforce_dfars_output_invariant`. | Evaluator/tests; clean-room logic calls TokenVault. | Cleanroom rejects residual CAGE/NSN/ITAR/DFARS strings; viable output requires matching SHA-256 certificate hash and compliance flag. |
| `ml/debiasing.py` | `ShadowTradeDebiaser.apply_debiasing_penalty`. | Ranking engine. | Known transshipment hubs add `.4`; China ownership over 25% adds `.5`; max 1.0. |
| `ml/esg_optimizer.py` | `ESGOptimizer.calculate_esg_score`. | Ranking engine. | Energy profiles coal 25, grid 12.5, solar/hydro 4 kg CO2/kg; recycling reduces emissions; score 0-100. |
| `ml/ranking_engine.py` | `SupplierRankingEngine.rank_suppliers`; trains XGBoost dummy regressor. | Replay simulator and API simulation through simulator. | Features: geo risk, ITAR, purity, lead time, ESG, shadow penalty; defense shadow penalty multiplies score by `.1`; output sorted descending. |
| `ml/drift_detector.py` | `DataDriftDetector.detect_volume_anomaly`. | Utility; no observed caller. | Requires five history points; absolute z-score; thresholds default 2.5 and severity high above 3.5. |
| `simulation/replay_engine.py` | `DeterministicReplaySimulator.run_policy_shock_simulation`. | API `/api/simulate`. | `CHINA_EXPORT_BAN` adds 90 lead-time days and geo risk 1.0 for China-owned suppliers, then defense-ranks. |
| `governance/hitl_pause.py` | `HITLGovernor.suspend_execution`, `hydrate_and_resume`. | FSM engine. | Secure state keys `hitl:<execution_id>`; status transitions `PAUSED_PENDING_HUMAN` to `RESUMED`; webhook is currently a print. |
| `hardware/vram_router.py` | `HardwareRouter.get_system_memory_usage`, `route_model`. | Available routing utility; compiler can provide complexity score. | Uses `psutil` unified-memory percentage; above 85% or complexity >=5 selects configured heavy model, otherwise local SLM. |
| `resilience/circuit_breaker.py` | `APICircuitBreaker.execute` and internal reset/record. | Available utility; no observed caller. | CLOSED/OPEN/HALF_OPEN; 3 failures and 10-second recovery defaults; backup called on failure/open. |
| `telemetry/otel_tracer.py` | `OpenTelemetryTracer`, `get_otel_tracer`; W3C inject/extract and context-managed spans. | MCP and reasoning mesh; OTel tests. | Uses OTLP if reachable, console/none modes, or fallback spans; endpoint defaults `localhost:4317`; no collector service in compose. |
| `telemetry/tracer.py` | `CryptographicTracer.log_span`, `trace_log`, `verify_trace_integrity`. | API routes. | Hash chain stored in `cf_secure_state` under `trace:<time_ns>:<hash>`; initial hash is 64 zeroes; verification depends on scan order. |
| `eval/golden_dataset.py` | `GOLDEN_BENCHMARKS`, five evaluation cases. | Evaluator and agent evaluation test. | Cases cover viable, non-viable, DFARS violation, structural rejection, and supervisor review. |
| `eval/evaluator.py` | `evaluate_golden_dataset`, classification/report helpers. | Test and `reports/agent_evaluation_scorecard.md`. | Temporary RocksDB per case; expected quality gates include grounding >=.95 and perfect DFARS precision/recall. |
| `compiler/agentscript.py` | Pydantic `AgentStep`, `AgentDSLSpec`; `AgentDSLCompiler.compile_yaml_to_fsm`, `profile_complexity`. | FSM/hardware routing conceptually; no observed runtime API caller. | YAML `agent` schema becomes DAG; high-complexity actions add 3 points; tools and states add score. |
| `data/ingestion.py` | `DataIngestionEngine.fetch_rare_earth_trade_data`. | Import test; intended graph ingestion caller absent. | Requests UN Comtrade HS 2805 for India by default; deterministic fallback includes India/Australia/Vietnam routes. |
| `data/gsi_copilot.py` | `GeologicalCopilot.extract_text_from_pdf`, `parse_assay_data`. | Import test; intended local Ollama integration. | Reads first 2,000 PDF characters; POSTs JSON-format prompt to `host.docker.internal:11434`, model `llama3.1:8b`; error returns an error object. |

#### Generated gRPC Python modules

| File | Identity and core contracts | Upstream / downstream | Invariant |
|---|---|---|---|
| `grpc/generated/maritime_telemetry_pb2.py` | protoc-generated `LatLng`, `AisPing`, `CorridorAuditRequest`, `CorridorAuditResponse`, service descriptor. | Generated from `.proto`; imported by Python gRPC service. | Do not edit; embeds serialized descriptor and validates Protobuf runtime 7.35.1. |
| `grpc/generated/maritime_telemetry_pb2_grpc.py` | Generated `MaritimeComplianceServiceStub`, servicer base, registration helper, experimental static client. | `grpc/service.py`, gRPC tests, Java client across network. | Requires grpcio >=1.83.1 as generated. |

### `proto/`

| File | Identity and core contracts | Dependencies | Invariant |
|---|---|---|---|
| `proto/maritime_telemetry.proto` | Source schema: `LatLng`, `AisPing`, `CorridorAuditRequest`, `CorridorAuditResponse`; unary `MaritimeComplianceService.AuditLiveCorridor`. | Python protoc output; Gradle protobuf source set and Java gRPC output. | Package `tensormesh.maritime`; Java package `com.tensormesh.ais.proto`; field numbers are wire compatibility contract. |

### `tensormesh-compute/`

| File | Identity and core contracts | Dependencies / consumers | Invariant |
|---|---|---|---|
| `CMakeLists.txt` | CMake 3.20, C++23, native library, pybind modules, RocksDB discovery, CTest target. | Python headers/pybind11/RocksDB; emits modules into Python package. | Apple defines `TENSORMESH_HAS_NEON`; test name `tensormesh_compute_kernels`. |
| `include/tensormesh_compute/acoustic_impedance.hpp` | `invert_acoustic_impedance(vector<float>, float)`. | `src/acoustic_impedance.cpp`, bindings, C++ test. | Recursive impedance contract. |
| `include/tensormesh_compute/borehole_trajectory.hpp` | `SurveyStation`, `TrajectoryPoint3D`, minimum-curvature function. | source, bindings, agents, tests. | Measured depth is non-decreasing. |
| `include/tensormesh_compute/spatial_morton.hpp` | 3D Morton encode/decode uint64 API. | source, bindings, reasoning mesh, tests. | 21 bits per coordinate. |
| `include/tensormesh_compute/spectral_decomposition.hpp` | Frequency x time spectral decomposition API. | source, bindings, tests. | Positive `dt` and frequencies. |
| `src/acoustic_impedance.cpp` | Scalar recursion plus ARM NEON vector factor path guarded by `TENSORMESH_NEON`. | acoustic header and CMake library. | Clips reflections to `[-.999,.999]`; NEON uses four float lanes, recursive state remains lane-ordered; no AVX. |
| `src/spectral_decomposition.cpp` | Scalar Morlet wavelet bank. | spectral header and library. | Six Morlet cycles, radius `ceil(3*sigma/dt)`, finite normalized output. |
| `src/spatial_morton.cpp` | Bit spread/compact Morton implementation. | spatial header and library. | Masks coordinates at 21 bits; truncates higher bits. |
| `src/borehole_trajectory.cpp` | Minimum-curvature survey integration. | trajectory header and library. | Uses radians, dogleg ratio factor, easting/northing/TVD deltas. |
| `src/bindings.cpp` | pybind11 module `_tensormesh_compute`; binds all four compute functions and two structs. | C++ library, Python wrappers. | Module name and argument names are Python ABI/API. |
| `src/rocksdb_bridge.cpp` | pybind11 `_rocksdb_bridge`, native `RocksDBStore`. | RocksDB library, Python storage facade. | Creates missing DB/column families; scan is prefix-based; handles are destroyed in destructor. |
| `tests/test_kernels.cpp` | C++ executable assertions for impedance, spectrum, Morton, trajectory. | CMake/CTest. | Tests finite output, known impedance, round trip, and trajectory geometry. |

### `services/ais-ingest/`

| File | Identity and core contracts | Upstream / downstream | Invariant |
|---|---|---|---|
| `build.gradle` | Java plugin, protobuf plugin, Java 21, Kafka Streams 3.8.1, gRPC 1.66, JUnit 5.11; generates proto from `../../proto`. | Gradle and Maven Central. | JUnit platform; generated Java sources are build outputs. |
| `settings.gradle` | Gradle repositories and project name. | Gradle invocation. | Root name `tensormesh-ais-ingest`. |
| `README.md` | States the AIS service contract and input topic. | Operators. | Documents `maritime.telemetry.raw`, 15-minute sessions, gRPC dispatch. |
| `src/main/java/com/tensormesh/ais/AisStreamApplication.java` | Java `main`; constructs Kafka Streams and gRPC client. | topology, client, environment. | Application ID `tensormesh-ais-ingest`; bootstrap default `localhost:9092`; client target localhost:50051 and Singapore->Yokohama. |
| `src/main/java/com/tensormesh/ais/client/CorridorDispatcher.java` | Functional `dispatch(VoyageAccumulator)` interface. | topology and gRPC client. | One dispatch per qualifying aggregated voyage. |
| `src/main/java/com/tensormesh/ais/client/TensorMeshGrpcClient.java` | Blocking gRPC client implementing dispatcher and AutoCloseable. | generated Java proto classes; Python gRPC server. | Plaintext channel; maps all waypoints; logs DFARS result. |
| `src/main/java/com/tensormesh/ais/topology/AisStreamTopology.java` | `INPUT_TOPIC`; `buildTopology`; `isRareEarthBulkCarrier`. | Kafka Streams app and test. | Filters cargo regex, groups by MMSI, session gap/grace 15 minutes/0, dispatches only >=2 waypoints; no output Kafka topic. |
| `src/main/java/com/tensormesh/ais/topology/AisPingSerde.java` | Protobuf serializer/deserializer for `AisPing`. | topology. | Null-safe; invalid bytes become `IllegalArgumentException`. |
| `src/main/java/com/tensormesh/ais/topology/VoyageAccumulator.java` | Mutable accumulator with identity, waypoints, add/merge, accessors. | topology, serde, gRPC client. | First ping supplies identity; merge concatenates waypoints. |
| `src/main/java/com/tensormesh/ais/topology/VoyageAccumulatorSerde.java` | Binary DataInput/DataOutput serde. | Kafka materialized session aggregate. | UTF identity strings, count, then latitude/longitude doubles. |
| `src/test/java/com/tensormesh/ais/AisTopologyTest.java` | JUnit topology-driver test for filter/session/dispatch. | Gradle test task. | Rare-earth cargo passes; container cargo excluded; two pings dispatch one voyage. |

### `frontend/`

| File | Identity and core contracts | Dependencies / consumers | Invariant |
|---|---|---|---|
| `package.json` | Next 14, React 18, Axios, React Flow, Lucide, Tailwind; dev/build/start/lint scripts. | npm. | Client depends on backend at `http://localhost:8000`. |
| `package-lock.json` | npm lockfile for exact dependency tree. | npm install/build. | Generated dependency resolution; do not hand-edit. |
| `next-env.d.ts` | Next TypeScript ambient references. | TypeScript. | Generated framework typing. |
| `next.config.mjs` | Empty Next config. | Next build/server. | No rewrites/proxy; browser uses absolute backend URL. |
| `postcss.config.mjs` | PostCSS/Tailwind plugin config. | CSS build. | Tailwind runs through PostCSS. |
| `tailwind.config.ts` | Content globs and CSS variable colors. | Tailwind build. | Scans app/pages/components; no plugins. |
| `tsconfig.json` | TypeScript compiler configuration. | Next/TypeScript. | Framework-managed config. |
| `.eslintrc.json` | Next ESLint preset config. | `npm run lint`. | Lint contract. |
| `.gitignore` | Frontend local/build ignore rules. | Git. | Excludes Next build/dependency artifacts. |
| `Dockerfile` | Multi-stage Node image build/runtime for Next. | Docker compose. | Exposes 3000 and starts production app. |
| `README.md` | Create-next-app operating instructions. | Developers. | Documents `npm run dev` and localhost:3000. |
| `src/app/layout.tsx` | Root layout, metadata, local Geist fonts. | Next App Router. | Applies fonts and global CSS. |
| `src/app/page.tsx` | Client `CommandCenter`; typed evaluation report; input form, API call, metric panels, A2A cards, React Flow supply graph. | Axios to FastAPI; React Flow; Lucide. | Posts deposit ID, borehole, trace, assays, depth range; expects report shape returned by `/api/deposits/evaluate`. |
| `src/app/globals.css` | Tailwind directives and root/body styles. | layout and Tailwind. | Body fallback font is Arial despite local Geist variables. |
| `src/app/favicon.ico` | Browser icon binary. | Next metadata. | Static asset; no runtime contract. |
| `src/app/fonts/GeistVF.woff` | Local variable sans font binary. | layout. | Static asset. |
| `src/app/fonts/GeistMonoVF.woff` | Local variable monospace font binary. | layout. | Static asset. |

### `tests/`

| File | Verification contract | Fixtures / dependencies |
|---|---|---|
| `tests/__init__.py` | Test package marker. | unittest/pytest discovery. |
| `test_a2a_reasoning_mesh.py` | Three hypotheses, two handoffs, six checkpoints; low-confidence gate raises. | Temporary native RocksDB. |
| `test_agent_evaluation.py` | Five golden cases; grounding >=.95; DFARS precision/recall 1.0. | evaluator, temporary stores. |
| `test_compute_kernel.py` | Impedance numerical accuracy, validation, spectrum shape/finiteness, fallback/native parity, voxel round trip. | NumPy and native module. |
| `test_e2e_orchestration.py` | HTTP deposit evaluation end-to-end with fake graph and seeded borehole. | FastAPI TestClient, temporary RocksDB. |
| `test_graphrag_mcp.py` | Hybrid graph/excerpt synthesis and confidence filtering. | Fake Neo4j driver and MCP service. |
| `test_grpc_corridor_bridge.py` | Live in-process gRPC audit, restricted-port violation, checkpoint persistence. | grpc server, temporary RocksDB. |
| `test_guardrails.py` | ITAR redaction and tampered DFARS certificate rejection. | Fake vault, SHA-256. |
| `test_imports.py` | Imports migrated modules including `tensormesh.data.gsi_copilot`. | Full optional dependency environment. |
| `test_mcp_tools.py` | Strata depth filtering, case-insensitive assays, dependency mapping, six FastMCP tools. | Fake graph, temporary RocksDB. |
| `test_otel_telemetry.py` | W3C extraction/injection, child attributes, trace IDs. | OpenTelemetry fallback or SDK. |
| `test_spatial_compute.py` | Morton boundary round trips and minimum-curvature geometry. | Native spatial module. |
| `test_spatial_mcp.py` | Concession verification/persistence and restricted maritime geofence audit. | Temporary RocksDB. |
| `test_storage.py` | Four-family declaration, JSON CRUD, prefix scan, delete. | Native RocksDB bridge. |

### Runtime, generated, and binary files in scope

The workspace also contains files intentionally excluded from the source manifest above because they are generated or stateful rather than authored modules: `data/rocksdb/**` (SST, MANIFEST, OPTIONS, CURRENT, LOCK, LOG files), `tensormesh-compute/build/**`, `services/ais-ingest/build/**`, `services/ais-ingest/.gradle/**`, `frontend/node_modules/**`, Python `__pycache__/**`, native `.so`/`.dylib` outputs, `tensormesh/data/token_vault.sqlite`, and `tensormesh/data/vault.key`. Their roles are: RocksDB runtime state; CMake/Gradle products; npm dependency tree; Python bytecode; native loadable modules; and local secure-cache/key material. They have no additional authored API contracts. The key and database must be treated as sensitive local state.

## Core Storage Invariants

| Column family | Key prefixes observed | Values / owners |
|---|---|---|
| `cf_spatial_voxels` | `voxel:<id>`, `morton:<16-hex>`, `concession:<id>:<hash>` | float32 trace bytes or canonical JSON; inversion, reasoning mesh, MCP concession. |
| `cf_borehole_telemetry` | `strata:<borehole>:...` | JSON `StrataInterval` records; MCP strata query. |
| `cf_a2a_checkpoints` | `<task>:hypothesis:`, `<task>:handoff:`, `<task>:verdict`, `shipping_audit:`, `live_ais:`, `<task>:shipping_audit:` | Pydantic dumps, audit certificates, gRPC audit records. |
| `cf_secure_state` | `token:`, `semantic_cache:`, `hitl:`, `trace:` | encrypted token records, embeddings/responses, paused FSM memory, hash-chain spans. |

`RocksDBStore` is a path-normalized singleton. Its Python facade rejects unknown families before calling the native bridge. The C++ bridge opens all declared families with `create_if_missing` and `create_missing_column_families`, uses prefix seeks for scans, and exposes bytes to Python.

## Runtime & Data Flow

### Browser deposit evaluation

1. `frontend/src/app/page.tsx` parses comma-separated depths and seismic values and sends a JSON POST to `/api/deposits/evaluate`.
2. FastAPI validates `DepositEvaluationRequest`, requiring non-empty IDs, at least one seismic sample, two depths, non-negative assay values, and an increasing depth range.
3. `invert_acoustic_impedance` and `compute_spectral_decomposition` dispatch to C++ when native modules are present, otherwise impedance has a NumPy/Python fallback. The impedance bytes are persisted under `cf_spatial_voxels`.
4. `MCPToolService.query_borehole_strata` scans the borehole family. Empty strata becomes an inferred unclassified interval.
5. Assay element aliases (`Li`, `Co`, `Nd`, `REE`) normalize to canonical names; benchmarks are evaluated by `MCPToolService`.
6. For each canonical element, `SupplyChainGraph.trace_supply_dependency` executes Neo4j Cypher. Failures are converted into `graph_unavailable` records rather than aborting the whole evaluation.
7. `GeologicalReasoningMesh` concurrently runs geochemistry and structural analysis in worker threads, checkpoints each hypothesis, gates A2A handoffs, runs economic assessment, optionally audits a shipping corridor, and persists the final verdict.
8. The API scans checkpoint keys, computes impedance statistics and spectral flags, logs a cryptographic API span, and returns the report consumed by the UI.
9. The UI renders seismic metrics, assay bars, agent hypotheses/checkpoints, and a React Flow graph of bottleneck entities.

### Maritime telemetry flow

1. Kafka Streams consumes `maritime.telemetry.raw` as `AisPing` protobuf values.
2. Cargo is filtered by a case-insensitive rare-earth/mineral regex, grouped by MMSI, and aggregated in session windows with a 15-minute inactivity gap.
3. Sessions with at least two waypoints are sent to `TensorMeshGrpcClient`.
4. The client maps the voyage to `CorridorAuditRequest` and calls unary `AuditLiveCorridor` on Python port 50051.
5. `MaritimeComplianceServer` computes nearest restricted port and geofence compliance, returns a response, and stores `live_ais:<mmsi>:<timestamp>` in `cf_a2a_checkpoints`.

### Security and observability flows

Clean-room requests run regex matching, Fernet-encrypt each original match, store encrypted records in `cf_secure_state`, and return surrogate tokens plus a response-local token map. OTel spans carry W3C context when the SDK is available; otherwise fallback spans remain in memory. API-level `CryptographicTracer` spans form a SHA-256 chain in RocksDB, but chain immutability is an application convention rather than a database ACL.

## Verification Matrix

### Python tests

| Command / target | Coverage | Prerequisites |
|---|---|---|
| `python -m unittest discover -s tests` | All 13 Python test modules listed above. | Python dependencies, native compute and RocksDB extensions, protobuf/grpc/OTel. |
| `python -m pytest` | Equivalent pytest discovery if pytest is installed. | Same as above. |
| `tests/test_a2a_reasoning_mesh.py` | A2A confidence gate, concurrent agent result shape, six persisted checkpoints. | Native RocksDB. |
| `tests/test_agent_evaluation.py` | Golden quality gates and report generation. | Native RocksDB, OTel/security dependencies. |
| `tests/test_compute_kernel.py` | Native/fallback numerical compute and voxel persistence. | Native module recommended; RocksDB bridge required for round trip. |
| `tests/test_e2e_orchestration.py` | FastAPI request through compute, MCP, mesh, persistence. | FastAPI TestClient and native RocksDB; fake graph avoids Neo4j. |
| `tests/test_graphrag_mcp.py` | Neo4j query shaping and confidence filtering with fakes. | Neo4j Python package; no live Neo4j. |
| `tests/test_grpc_corridor_bridge.py` | Real local Python gRPC server/client and checkpoint. | grpcio and native RocksDB. |
| `tests/test_guardrails.py` | Clean-room and certificate invariants. | Cryptography and storage. |
| `tests/test_imports.py` | Import smoke test for migrated/optional modules. | All requirements, including PyPDF2 and sentence-transformers. |
| `tests/test_mcp_tools.py` | Typed service tools and FastMCP registration. | MCP package and storage. |
| `tests/test_otel_telemetry.py` | W3C propagation and span attributes. | OpenTelemetry API/SDK. |
| `tests/test_spatial_compute.py` | Native Morton/trajectory contracts. | Native `_tensormesh_compute`. |
| `tests/test_spatial_mcp.py` | Static spatial and maritime policy rules plus writes. | Native RocksDB. |
| `tests/test_storage.py` | Native RocksDB CRUD/family contract. | `_rocksdb_bridge`. |

### Native and Java tests

| Command / target | Coverage | Prerequisites |
|---|---|---|
| `cmake -S tensormesh-compute -B tensormesh-compute/build && cmake --build tensormesh-compute/build` | Builds C++23 library, pybind compute module, RocksDB bridge, C++ test. | CMake >=3.20, C++ compiler, Python development, pybind11, RocksDB headers/library. |
| `ctest --test-dir tensormesh-compute/build --output-on-failure` | `tensormesh_compute_kernels`. | Successful native build. |
| `cd services/ais-ingest && ./gradlew test` | `AisTopologyTest`: filter, session aggregation, serde/topology dispatch. | Java 21 toolchain, Gradle wrapper or installed Gradle, dependency network. |
| `cd frontend && npm run lint` | Next ESLint configuration and page TypeScript-adjacent lint. | `npm install`/`node_modules`. |
| `cd frontend && npm run build` | Next production compilation and static route generation. | Node/npm, dependencies; backend is not required for compile. |

### Verification gaps and operational checks

- No repository-level pytest configuration, Python packaging metadata, or CI workflow is present in the audited tree.
- No Kafka broker is declared in Docker Compose; the Java topology test is the only Kafka verification present.
- No live Neo4j integration test seeds schema/data; GraphRAG tests use fakes.
- No test asserts `CryptographicTracer.verify_trace_integrity` or concurrent writer behavior.
- No frontend component/e2e test is present; API URL and response shape are coupled directly in `page.tsx`.
- Native C++ tests are assertion-based, not a unit-test framework, and do not test RocksDB C++ bridge directly.
- Generated files must be regenerated from the `.proto`; editing generated Python or Java output is not a supported change path.

### Audit-date execution results

| Check | Result |
|---|---|
| Native `ctest --test-dir tensormesh-compute/build --output-on-failure` | Passed: 1/1 `tensormesh_compute_kernels`. |
| `gradle test` in `services/ais-ingest` | Passed: build successful; Java topology test compiled/executed. Gradle reported deprecation warnings. |
| `npm run lint` in `frontend` | Passed: no ESLint warnings or errors. |
| `npm run build` in `frontend` | Passed: Next 14 production build, type check, lint, and static generation completed. |
| `python3 -m unittest discover -s tests` | Blocked at import time because the selected global Python 3.14 environment lacks declared dependencies such as PyYAML, requests, NumPy, Neo4j, MCP, and cryptography. No Python test result is treated as a product failure until the requirements environment is installed. |

## Reference Commands

```bash
python -m unittest discover -s tests
cmake -S tensormesh-compute -B tensormesh-compute/build
cmake --build tensormesh-compute/build
ctest --test-dir tensormesh-compute/build --output-on-failure
cd services/ais-ingest && ./gradlew test
cd frontend && npm run lint && npm run build
```