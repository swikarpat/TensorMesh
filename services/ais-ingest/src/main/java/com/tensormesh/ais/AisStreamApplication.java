package com.tensormesh.ais;

import com.tensormesh.ais.client.TensorMeshGrpcClient;
import com.tensormesh.ais.topology.AisStreamTopology;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsConfig;

import java.util.Properties;

public final class AisStreamApplication {
    private AisStreamApplication() {
    }

    public static void main(String[] args) {
        Properties properties = new Properties();
        properties.put(StreamsConfig.APPLICATION_ID_CONFIG, "tensormesh-ais-ingest");
        properties.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, System.getenv().getOrDefault(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"));
        properties.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
        TensorMeshGrpcClient client = new TensorMeshGrpcClient(
                "localhost", 50051, "Singapore", "Yokohama");
        KafkaStreams streams = new KafkaStreams(AisStreamTopology.buildTopology(client), properties);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            streams.close();
            try {
                client.close();
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
            }
        }));
        streams.start();
    }
}