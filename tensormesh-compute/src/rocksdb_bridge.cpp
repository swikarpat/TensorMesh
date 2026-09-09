#include <rocksdb/db.h>
#include <rocksdb/options.h>
#include <rocksdb/slice.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace py = pybind11;

class RocksDBStore {
public:
    RocksDBStore(const std::string& path, const std::vector<std::string>& column_families) {
        rocksdb::Options options;
        options.create_if_missing = true;
        options.create_missing_column_families = true;

        std::vector<rocksdb::ColumnFamilyDescriptor> descriptors;
        descriptors.emplace_back(rocksdb::kDefaultColumnFamilyName, rocksdb::ColumnFamilyOptions());
        for (const auto& name : column_families) {
            descriptors.emplace_back(name, rocksdb::ColumnFamilyOptions());
        }

        std::vector<rocksdb::ColumnFamilyHandle*> handles;
        std::unique_ptr<rocksdb::DB> database;
        const auto status = rocksdb::DB::Open(options, path, descriptors, &handles, &database);
        if (!status.ok()) {
            throw std::runtime_error("Unable to open RocksDB: " + status.ToString());
        }

        db_ = std::move(database);
        for (std::size_t index = 0; index < descriptors.size(); ++index) {
            handles_[descriptors[index].name] = handles[index];
        }
    }

    ~RocksDBStore() {
        for (auto& [name, handle] : handles_) {
            db_->DestroyColumnFamilyHandle(handle);
        }
    }

    void put(const std::string& column_family, const std::string& key, const std::string& value) {
        check_column_family(column_family);
        const auto status = db_->Put(rocksdb::WriteOptions(), handles_.at(column_family), key, value);
        if (!status.ok()) {
            throw std::runtime_error("RocksDB put failed: " + status.ToString());
        }
    }

    py::object get(const std::string& column_family, const std::string& key) const {
        check_column_family(column_family);
        std::string value;
        const auto status = db_->Get(rocksdb::ReadOptions(), handles_.at(column_family), key, &value);
        if (status.IsNotFound()) {
            return py::none();
        }
        if (!status.ok()) {
            throw std::runtime_error("RocksDB get failed: " + status.ToString());
        }
        return py::bytes(value);
    }

    void remove(const std::string& column_family, const std::string& key) {
        check_column_family(column_family);
        const auto status = db_->Delete(rocksdb::WriteOptions(), handles_.at(column_family), key);
        if (!status.ok()) {
            throw std::runtime_error("RocksDB delete failed: " + status.ToString());
        }
    }

    std::vector<std::pair<std::string, py::bytes>> scan(const std::string& column_family, const std::string& prefix) const {
        check_column_family(column_family);
        std::vector<std::pair<std::string, py::bytes>> records;
        std::unique_ptr<rocksdb::Iterator> iterator(db_->NewIterator(rocksdb::ReadOptions(), handles_.at(column_family)));
        for (iterator->Seek(prefix); iterator->Valid(); iterator->Next()) {
            const auto key = iterator->key().ToString();
            if (key.compare(0, prefix.size(), prefix) != 0) {
                break;
            }
            records.emplace_back(key, py::bytes(iterator->value().data(), iterator->value().size()));
        }
        if (!iterator->status().ok()) {
            throw std::runtime_error("RocksDB scan failed: " + iterator->status().ToString());
        }
        return records;
    }

private:
    void check_column_family(const std::string& column_family) const {
        if (!handles_.contains(column_family)) {
            throw std::invalid_argument("Unknown TensorMesh column family: " + column_family);
        }
    }

    std::unique_ptr<rocksdb::DB> db_;
    std::unordered_map<std::string, rocksdb::ColumnFamilyHandle*> handles_;
};

PYBIND11_MODULE(_rocksdb_bridge, module) {
    py::class_<RocksDBStore>(module, "RocksDBStore")
        .def(py::init<const std::string&, const std::vector<std::string>&>())
        .def("put", &RocksDBStore::put)
        .def("get", &RocksDBStore::get)
        .def("delete", &RocksDBStore::remove)
        .def("scan", &RocksDBStore::scan);
}
