package com.tensormesh.ais.topology;

import com.tensormesh.ais.client.CorridorDispatcher;
import com.tensormesh.ais.proto.AisPing;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.Topology;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.KStream;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.SessionWindows;

import java.time.Duration;
import java.util.Locale;

public final class AisStreamTopology {
    public static final String INPUT_TOPIC = "maritime.telemetry.raw";
    private static final String RARE_EARTH_CARGO =
            "(?i).*(mineral|ore|rare\\s*-?earth|lithium|cobalt|nickel|monazite|neodymium).*";

    private AisStreamTopology() {
    }

    public static Topology buildTopology(CorridorDispatcher dispatcher) {
        StreamsBuilder builder = new StreamsBuilder();
        KStream<String, AisPing> pings = builder.stream(
                INPUT_TOPIC,
                org.apache.kafka.streams.kstream.Consumed.with(Serdes.String(), new AisPingSerde())
        );

        pings.filter((key, ping) -> ping != null && isRareEarthBulkCarrier(ping.getCargoType()))
                .groupBy(
                        (key, ping) -> ping.getMmsi(),
                        Grouped.with(Serdes.String(), new AisPingSerde())
                )
                .windowedBy(SessionWindows.ofInactivityGapAndGrace(
                        Duration.ofMinutes(15), Duration.ZERO
                ))
                .aggregate(
                        VoyageAccumulator::new,
                        (mmsi, ping, voyage) -> voyage.add(ping),
                        VoyageAccumulator::merge,
                        Materialized.with(Serdes.String(), new VoyageAccumulatorSerde())
                )
                .toStream()
                .filter((window, voyage) -> voyage != null && voyage.waypoints().size() >= 2)
                .foreach((window, voyage) -> dispatcher.dispatch(voyage));

        return builder.build();
    }

    public static boolean isRareEarthBulkCarrier(String cargoType) {
        return cargoType != null && cargoType.toLowerCase(Locale.ROOT).matches(RARE_EARTH_CARGO);
    }
}