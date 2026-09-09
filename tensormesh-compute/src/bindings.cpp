#include "tensormesh_compute/acoustic_impedance.hpp"
#include "tensormesh_compute/spectral_decomposition.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

PYBIND11_MODULE(_tensormesh_compute, module) {
    module.doc() = "TensorMesh native subsurface seismic compute kernels";
    module.def(
        "invert_acoustic_impedance",
        &tensormesh::compute::invert_acoustic_impedance,
        pybind11::arg("trace"),
        pybind11::arg("z0"));
    module.def(
        "compute_spectral_decomposition",
        &tensormesh::compute::compute_spectral_decomposition,
        pybind11::arg("trace"),
        pybind11::arg("freqs"),
        pybind11::arg("dt"));
}