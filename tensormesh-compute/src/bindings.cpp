#include "tensormesh_compute/acoustic_impedance.hpp"
#include "tensormesh_compute/spectral_decomposition.hpp"
#include "tensormesh_compute/spatial_morton.hpp"
#include "tensormesh_compute/borehole_trajectory.hpp"

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
    module.def("encode_morton_3d", &tensormesh::compute::encode_morton_3d,
               pybind11::arg("x"), pybind11::arg("y"), pybind11::arg("z"));
    module.def("decode_morton_3d", [](std::uint64_t code) {
        std::uint32_t x;
        std::uint32_t y;
        std::uint32_t z;
        tensormesh::compute::decode_morton_3d(code, x, y, z);
        return pybind11::make_tuple(x, y, z);
    }, pybind11::arg("code"));
    pybind11::class_<tensormesh::compute::SurveyStation>(module, "SurveyStation")
        .def(pybind11::init<double, double, double>(), pybind11::arg("measured_depth_m"),
             pybind11::arg("inclination_deg"), pybind11::arg("azimuth_deg"))
        .def_readwrite("measured_depth_m", &tensormesh::compute::SurveyStation::measured_depth_m)
        .def_readwrite("inclination_deg", &tensormesh::compute::SurveyStation::inclination_deg)
        .def_readwrite("azimuth_deg", &tensormesh::compute::SurveyStation::azimuth_deg);
    pybind11::class_<tensormesh::compute::TrajectoryPoint3D>(module, "TrajectoryPoint3D")
        .def_readonly("measured_depth_m", &tensormesh::compute::TrajectoryPoint3D::measured_depth_m)
        .def_readonly("easting_m", &tensormesh::compute::TrajectoryPoint3D::easting_m)
        .def_readonly("northing_m", &tensormesh::compute::TrajectoryPoint3D::northing_m)
        .def_readonly("true_vertical_depth_m", &tensormesh::compute::TrajectoryPoint3D::true_vertical_depth_m);
    module.def("compute_minimum_curvature_trajectory",
               &tensormesh::compute::compute_minimum_curvature_trajectory,
               pybind11::arg("stations"));
}