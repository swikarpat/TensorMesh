package com.tensormesh.ais;

import com.tensormesh.ais.proto.AisPing;
import com.tensormesh.ais.topology.AisStreamTopology;
import com.tensormesh.ais.topology.VoyageAccumulator;
import org.apache.kafka.common.serialization.StringSerializer;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.TestInputTopic;
import org.apache.kafka.streams.TopologyTestDriver;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AisTopologyTest {
    @Test
    void filtersBulkCarriersAndDispatchesSessionWaypoints() {
        List<VoyageAccumulator> dispatched = new ArrayList<>();
        Properties properties = new Properties();
        properties.put(StreamsConfig.APPLICATION_ID_CONFIG, "ais-test");
        properties.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "dummy:9092");
        properties.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG,
                org.apache.kafka.common.serialization.Serdes.String().getClass());
        properties.put(StreamsConfig.CACHE_MAX_BYTES_BUFFERING_CONFIG, "0");

        try (TopologyTestDriver driver = new TopologyTestDriver(
                AisStreamTopology.buildTopology(dispatched::add), properties, Instant.EPOCH)) {
            TestInputTopic<String, AisPing> input = driver.createInputTopic(
                    AisStreamTopology.INPUT_TOPIC,
                    new StringSerializer(),
                    new com.tensormesh.ais.topology.AisPingSerde().serializer()
            );
            input.pipeInput("ORE-1", ping("ORE-1", 0.0, 80.0, "rare earth ore"), Instant.EPOCH);
            input.pipeInput("ORE-1", ping("ORE-1", 0.1, 80.1, "rare earth ore"), Instant.EPOCH.plusSeconds(60));
            input.pipeInput("OTHER", ping("OTHER", 1.0, 80.0, "container cargo"), Instant.EPOCH.plusSeconds(120));
        }

        assertEquals(1, dispatched.size());
        assertEquals("ORE-1", dispatched.getFirst().mmsi());
        assertEquals(2, dispatched.getFirst().waypoints().size());
        assertTrue(AisStreamTopology.isRareEarthBulkCarrier("monazite concentrate"));
    }

    private static AisPing ping(String mmsi, double latitude, double longitude, String cargo) {
        return AisPing.newBuilder()
                .setMmsi(mmsi)
                .setVesselName("Mineral Carrier")
                .setLatitude(latitude)
                .setLongitude(longitude)
                .setTimestamp(System.currentTimeMillis())
                .setCargoType(cargo)
                .build();
    }
}