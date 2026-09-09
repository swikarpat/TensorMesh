# TensorMesh AIS Ingestion

Java 21 Kafka Streams service for rare-earth maritime telemetry. It consumes
`maritime.telemetry.raw`, accumulates 15-minute inactivity sessions by MMSI,
and dispatches qualifying voyages to TensorMesh over gRPC.