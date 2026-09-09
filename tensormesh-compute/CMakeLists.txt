cmake_minimum_required(VERSION 3.20)
project(tensormesh_compute VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
find_path(ROCKSDB_INCLUDE_DIR rocksdb/db.h REQUIRED)
find_library(ROCKSDB_LIBRARY NAMES rocksdb REQUIRED)

add_library(tensormesh_compute SHARED
    src/acoustic_impedance.cpp
    src/spectral_decomposition.cpp
    src/spatial_morton.cpp
    src/borehole_trajectory.cpp
)
target_include_directories(tensormesh_compute PUBLIC include)
target_compile_features(tensormesh_compute PUBLIC cxx_std_23)
set_target_properties(tensormesh_compute PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../tensormesh/compute"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../tensormesh/compute"
)

pybind11_add_module(_tensormesh_compute MODULE src/bindings.cpp)
target_include_directories(_tensormesh_compute PRIVATE include)
target_link_libraries(_tensormesh_compute PRIVATE tensormesh_compute)
target_compile_features(_tensormesh_compute PRIVATE cxx_std_23)
set_target_properties(_tensormesh_compute PROPERTIES
    BUILD_RPATH "@loader_path"
    INSTALL_RPATH "@loader_path"
)

set_target_properties(_tensormesh_compute PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../tensormesh/compute"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../tensormesh/compute"
)

if(APPLE)
    target_compile_definitions(tensormesh_compute PRIVATE TENSORMESH_HAS_NEON=1)
endif()

pybind11_add_module(_rocksdb_bridge MODULE src/rocksdb_bridge.cpp)
target_include_directories(_rocksdb_bridge PRIVATE ${ROCKSDB_INCLUDE_DIR})
target_link_libraries(_rocksdb_bridge PRIVATE ${ROCKSDB_LIBRARY})
target_compile_features(_rocksdb_bridge PRIVATE cxx_std_23)

set_target_properties(_rocksdb_bridge PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../tensormesh/storage"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/../tensormesh/storage"
)

if(APPLE)
    target_link_options(_rocksdb_bridge PRIVATE "-Wl,-undefined,dynamic_lookup")
endif()

enable_testing()

add_executable(test_kernels tests/test_kernels.cpp)
target_include_directories(test_kernels PRIVATE include)
target_link_libraries(test_kernels PRIVATE tensormesh_compute)
target_compile_features(test_kernels PRIVATE cxx_std_23)
add_test(NAME tensormesh_compute_kernels COMMAND test_kernels)
