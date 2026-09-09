package com.tensormesh.ais.topology;

import com.tensormesh.ais.proto.LatLng;
import org.apache.kafka.common.serialization.Deserializer;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serializer;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.util.Map;

public final class VoyageAccumulatorSerde implements Serde<VoyageAccumulator> {
    @Override
    public Serializer<VoyageAccumulator> serializer() {
        return (topic, value) -> {
            if (value == null) return null;
            try {
                ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                DataOutputStream output = new DataOutputStream(bytes);
                output.writeUTF(value.mmsi());
                output.writeUTF(value.vesselName());
                output.writeUTF(value.cargoType());
                output.writeInt(value.waypoints().size());
                for (LatLng point : value.waypoints()) {
                    output.writeDouble(point.getLatitude());
                    output.writeDouble(point.getLongitude());
                }
                output.flush();
                return bytes.toByteArray();
            } catch (IOException exception) {
                throw new IllegalStateException("Unable to serialize voyage accumulator", exception);
            }
        };
    }

    @Override
    public Deserializer<VoyageAccumulator> deserializer() {
        return (topic, data) -> {
            if (data == null) return null;
            try {
                DataInputStream input = new DataInputStream(new ByteArrayInputStream(data));
                VoyageAccumulator value = new VoyageAccumulator();
                value.restoreIdentity(input.readUTF(), input.readUTF(), input.readUTF());
                int count = input.readInt();
                for (int index = 0; index < count; index++) {
                    value.restoreWaypoint(input.readDouble(), input.readDouble());
                }
                return value;
            } catch (IOException exception) {
                throw new IllegalArgumentException("Unable to deserialize voyage accumulator", exception);
            }
        };
    }

    @Override
    public void configure(Map<String, ?> configs, boolean isKey) {
    }

    @Override
    public void close() {
    }
}