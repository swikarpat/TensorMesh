package com.tensormesh.ais.topology;

import com.tensormesh.ais.proto.AisPing;
import com.tensormesh.ais.proto.LatLng;

import java.util.ArrayList;
import java.util.List;

public final class VoyageAccumulator {
    private String mmsi = "";
    private String vesselName = "";
    private String cargoType = "";
    private final List<LatLng> waypoints = new ArrayList<>();

    public VoyageAccumulator add(AisPing ping) {
        if (mmsi.isEmpty()) {
            mmsi = ping.getMmsi();
            vesselName = ping.getVesselName();
            cargoType = ping.getCargoType();
        }
        waypoints.add(LatLng.newBuilder()
                .setLatitude(ping.getLatitude())
                .setLongitude(ping.getLongitude())
                .build());
        return this;
    }

    void restoreIdentity(String mmsi, String vesselName, String cargoType) {
        this.mmsi = mmsi;
        this.vesselName = vesselName;
        this.cargoType = cargoType;
    }

    void restoreWaypoint(double latitude, double longitude) {
        waypoints.add(LatLng.newBuilder().setLatitude(latitude).setLongitude(longitude).build());
    }

    public static VoyageAccumulator merge(String mmsi, VoyageAccumulator left, VoyageAccumulator right) {
        VoyageAccumulator merged = new VoyageAccumulator();
        merged.mmsi = left.mmsi.isEmpty() ? right.mmsi : left.mmsi;
        merged.vesselName = left.vesselName.isEmpty() ? right.vesselName : left.vesselName;
        merged.cargoType = left.cargoType.isEmpty() ? right.cargoType : left.cargoType;
        merged.waypoints.addAll(left.waypoints);
        merged.waypoints.addAll(right.waypoints);
        return merged;
    }

    public String mmsi() { return mmsi; }
    public String vesselName() { return vesselName; }
    public String cargoType() { return cargoType; }
    public List<LatLng> waypoints() { return List.copyOf(waypoints); }
}