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
extern "C" int membrane_solve_contact(int,const double*,double*,const double*,int,const int*,const int*,
    const double*,double,int,const int*,int,const double*,int,double,double,double,double*,double*);
extern "C" int membrane_guard_motion(int,const double*,const double*,int,const int*,int,const int*,
    const double*,int,double,double*);

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

class MembraneContactKernel : public RefCounted {
    GDCLASS(MembraneContactKernel,RefCounted)
protected:
    static void _bind_methods() {
        ClassDB::bind_method(D_METHOD("solve_contact","request"),&MembraneContactKernel::solve_contact);
        ClassDB::bind_method(D_METHOD("guard_motion","request"),&MembraneContactKernel::guard_motion);
    }
public:
    Dictionary guard_motion(const Dictionary& request) {
        PackedFloat64Array stats; stats.resize(8); stats.fill(0.);
        stats.set(2,-1.); stats.set(3,-1.); stats.set(4,std::numeric_limits<double>::infinity());
        bool valid=true;
        for (const char* key: {"previous","current","packets"})
            if (!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
        for (const char* key: {"triangles","kinds"})
            if (!request.has(key) || request[key].get_type()!=Variant::PACKED_INT32_ARRAY) valid=false;
        if (!request.has("budget") || request["budget"].get_type()!=Variant::INT) valid=false;
        if (!request.has("gap_tolerance") || (request["gap_tolerance"].get_type()!=Variant::FLOAT && request["gap_tolerance"].get_type()!=Variant::INT)) valid=false;
        int status=-1;
        if (valid) {
            PackedFloat64Array previous=request["previous"],current=request["current"],packets=request["packets"];
            PackedInt32Array triangles=request["triangles"],kinds=request["kinds"];
            int64_t budget=request["budget"];
            valid=previous.size()>0 && previous.size()%3==0 && previous.size()==current.size() &&
                previous.size()/3<=4096 && triangles.size()%3==0 && triangles.size()/3<=16384 &&
                kinds.size()<=64 && packets.size()==kinds.size()*41 && (triangles.size()/3)*kinds.size()<=65536 &&
                budget>=0 && budget<=128;
            if (valid) status=membrane_guard_motion(static_cast<int>(previous.size()/3),previous.ptr(),current.ptr(),
                static_cast<int>(triangles.size()/3),triangles.ptr(),static_cast<int>(kinds.size()),kinds.ptr(),
                packets.ptr(),static_cast<int>(budget),static_cast<double>(request["gap_tolerance"]),stats.ptrw());
        }
        Dictionary answer; answer["status"]=status; answer["stats"]=stats; return answer;
    }
    Dictionary solve_contact(const Dictionary& request) {
        PackedFloat64Array result,dual,stats;
        stats.resize(12); stats.fill(0.);
        for (int i=0;i<4;++i) stats.set(i,std::numeric_limits<double>::infinity());
        stats.set(9,std::numeric_limits<double>::infinity());
        bool valid=true;
        for (const char* key: {"predicted","initial","inverse","rest","capsules"})
            if (!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
        for (const char* key: {"a","b","triangles"})
            if (!request.has(key) || request[key].get_type()!=Variant::PACKED_INT32_ARRAY) valid=false;
        for (const char* key: {"alpha","force_tolerance","gap_tolerance","complementarity_tolerance"})
            if (!request.has(key) || (request[key].get_type()!=Variant::FLOAT && request[key].get_type()!=Variant::INT)) valid=false;
        if (!request.has("budget") || request["budget"].get_type()!=Variant::INT) valid=false;
        if (request.has("initial") && request["initial"].get_type()==Variant::PACKED_FLOAT64_ARRAY) result=request["initial"];
        int status=-1;
        if (valid) {
            PackedFloat64Array predicted=request["predicted"],inverse=request["inverse"],rest=request["rest"],capsules=request["capsules"];
            PackedInt32Array a=request["a"],b=request["b"],triangles=request["triangles"];
            int64_t budget=request["budget"];
            valid=result.size()>0 && result.size()%3==0 && result.size()==predicted.size() &&
                inverse.size()==result.size()/3 && inverse.size()<=4096 && a.size()==b.size() &&
                a.size()==rest.size() && a.size()<=16384 && triangles.size()%3==0 && triangles.size()/3<=16384 &&
                capsules.size()%7==0 && capsules.size()/7<=64 && (triangles.size()/3)*(capsules.size()/7)<=65536 &&
                budget>=0 && budget<=1000;
            if (valid) {
                dual.resize((triangles.size()/3)*(capsules.size()/7)); dual.fill(0.);
                status=membrane_solve_contact(static_cast<int>(inverse.size()),predicted.ptr(),result.ptrw(),inverse.ptr(),
                    static_cast<int>(a.size()),a.ptr(),b.ptr(),rest.ptr(),static_cast<double>(request["alpha"]),
                    static_cast<int>(triangles.size()/3),triangles.ptr(),static_cast<int>(capsules.size()/7),capsules.ptr(),
                    static_cast<int>(budget),static_cast<double>(request["force_tolerance"]),static_cast<double>(request["gap_tolerance"]),
                    static_cast<double>(request["complementarity_tolerance"]),dual.ptrw(),stats.ptrw());
            }
        }
        Dictionary answer;
        answer["status"]=status; answer["xyz"]=result; answer["dual"]=dual; answer["stats"]=stats;
        return answer;
    }
};

void initialize_membrane(ModuleInitializationLevel level) {
    if (level == MODULE_INITIALIZATION_LEVEL_SCENE) {
        GDREGISTER_CLASS(MembraneKernel);
        GDREGISTER_CLASS(MembraneContactKernel);
    }
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
