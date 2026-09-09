package com.tensormesh.ais.client;

import com.tensormesh.ais.proto.CorridorAuditRequest;
import com.tensormesh.ais.proto.CorridorAuditResponse;
import com.tensormesh.ais.proto.LatLng;
import com.tensormesh.ais.proto.MaritimeComplianceServiceGrpc;
import com.tensormesh.ais.topology.VoyageAccumulator;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

public final class TensorMeshGrpcClient implements CorridorDispatcher, AutoCloseable {
    private static final Logger LOGGER = LoggerFactory.getLogger(TensorMeshGrpcClient.class);
    private final ManagedChannel channel;
    private final MaritimeComplianceServiceGrpc.MaritimeComplianceServiceBlockingStub stub;
    private final String originPort;
    private final String destinationPort;

    public TensorMeshGrpcClient(String host, int port, String originPort, String destinationPort) {
        channel = ManagedChannelBuilder.forAddress(host, port).usePlaintext().build();
        stub = MaritimeComplianceServiceGrpc.newBlockingStub(channel);
        this.originPort = originPort;
        this.destinationPort = destinationPort;
    }

    @Override
    public void dispatch(VoyageAccumulator voyage) {
        CorridorAuditRequest request = CorridorAuditRequest.newBuilder()
                .setMmsi(voyage.mmsi())
                .setVesselName(voyage.vesselName())
                .setOriginPort(originPort)
                .setDestinationPort(destinationPort)
                .setCargoManifest(voyage.cargoType())
                .addAllWaypoints(voyage.waypoints().stream().map(point -> LatLng.newBuilder()
                        .setLatitude(point.getLatitude())
                        .setLongitude(point.getLongitude())
                        .build()).collect(Collectors.toList()))
                .build();
        CorridorAuditResponse response = stub.auditLiveCorridor(request);
        if (!response.getDfarsCompliant()) {
            LOGGER.warn("DFARS violation for MMSI {}: {} ({})", voyage.mmsi(), response.getStatus(), response.getAuditHash());
        } else {
            LOGGER.info("DFARS compliant corridor for MMSI {}: {}", voyage.mmsi(), response.getAuditHash());
        }
    }

    @Override
    public void close() throws InterruptedException {
        channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
    }
}