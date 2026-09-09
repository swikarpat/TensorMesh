package com.tensormesh.ais.client;

import com.tensormesh.ais.topology.VoyageAccumulator;

@FunctionalInterface
public interface CorridorDispatcher {
    void dispatch(VoyageAccumulator voyage);
}