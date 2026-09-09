package com.tensormesh.ais.topology;

import com.google.protobuf.InvalidProtocolBufferException;
import com.tensormesh.ais.proto.AisPing;
import org.apache.kafka.common.serialization.Deserializer;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serializer;

import java.util.Map;

public final class AisPingSerde implements Serde<AisPing> {
    private static final Serializer<AisPing> SERIALIZER = new Serializer<>() {
        @Override
        public byte[] serialize(String topic, AisPing data) {
            return data == null ? null : data.toByteArray();
        }
    };

    private static final Deserializer<AisPing> DESERIALIZER = new Deserializer<>() {
        @Override
        public AisPing deserialize(String topic, byte[] data) {
            if (data == null) {
                return null;
            }
            try {
                return AisPing.parseFrom(data);
            } catch (InvalidProtocolBufferException exception) {
                throw new IllegalArgumentException("Invalid AisPing payload", exception);
            }
        }
    };

    @Override
    public Serializer<AisPing> serializer() {
        return SERIALIZER;
    }

    @Override
    public Deserializer<AisPing> deserializer() {
        return DESERIALIZER;
    }

    @Override
    public void configure(Map<String, ?> configs, boolean isKey) {
    }

    @Override
    public void close() {
    }
}