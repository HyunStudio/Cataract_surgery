// Double-precision packed-array bridge. Experimental test project only.
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/godot.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/packed_float64_array.hpp>
#include <godot_cpp/variant/packed_int32_array.hpp>
#include <limits>

extern "C" int membrane_solve(int,double*,const double*,int,const int*,const int*,
                               const double*,double,int,double,double*);

namespace godot {
class MembraneKernel : public RefCounted {
    GDCLASS(MembraneKernel,RefCounted)
protected:
    static void _bind_methods() {
        ClassDB::bind_method(D_METHOD("solve","xyz","inverse","a","b","rest","alpha","budget","tolerance"),
                             &MembraneKernel::solve);
    }
public:
    Dictionary solve(const PackedFloat64Array& xyz,const PackedFloat64Array& inverse,
                     const PackedInt32Array& a,const PackedInt32Array& b,
                     const PackedFloat64Array& rest,double alpha,int64_t budget,double tolerance) {
        PackedFloat64Array result = xyz, stats;
        stats.resize(8); stats.fill(0.);
        stats.set(0,std::numeric_limits<double>::infinity());
        stats.set(1,std::numeric_limits<double>::infinity());
        int status = -1;
        if (xyz.size() > 0 && xyz.size()%3 == 0 && inverse.size() == xyz.size()/3 &&
            inverse.size() <= 4096 && a.size() == b.size() && a.size() == rest.size() &&
            a.size() <= 16384 && budget >= 0 && budget <= 1000) {
            status = membrane_solve(static_cast<int>(inverse.size()),result.ptrw(),inverse.ptr(),
                static_cast<int>(a.size()),a.ptr(),b.ptr(),rest.ptr(),alpha,static_cast<int>(budget),tolerance,stats.ptrw());
        }
        Dictionary answer;
        answer["status"] = status; answer["xyz"] = result; answer["stats"] = stats;
        return answer;
    }
};

void initialize_membrane(ModuleInitializationLevel level) {
    if (level == MODULE_INITIALIZATION_LEVEL_SCENE) GDREGISTER_CLASS(MembraneKernel);
}
void uninitialize_membrane(ModuleInitializationLevel) {}
} // namespace godot

extern "C" GDExtensionBool GDE_EXPORT membrane_library_init(
    GDExtensionInterfaceGetProcAddress get_proc,GDExtensionClassLibraryPtr library,
    GDExtensionInitialization* initialization) {
    godot::GDExtensionBinding::InitObject init(get_proc,library,initialization);
    init.register_initializer(godot::initialize_membrane);
    init.register_terminator(godot::uninitialize_membrane);
    init.set_minimum_library_initialization_level(godot::MODULE_INITIALIZATION_LEVEL_SCENE);
    return init.init();
}
