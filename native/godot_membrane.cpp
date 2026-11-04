// Double-precision packed-array bridge. Experimental test project only.
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/godot.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/packed_float64_array.hpp>
#include <godot_cpp/variant/packed_int32_array.hpp>
#include <limits>
#include "embedded_contact.h"

extern "C" int membrane_solve(int,double*,const double*,int,const int*,const int*,
                               const double*,double,int,double,double*);
extern "C" int membrane_fem_solve(int,double*,const double*,int,const int*,const double*,const double*,double,double,double,int,double,double*);
extern "C" int membrane_fem_evaluate(int,const double*,int,const int*,const double*,const double*,double,double,double*,double*,double*);
extern "C" int membrane_fem_solve_grasp(int,double*,const double*,int,const int*,const double*,const double*,double,double,double,int,double,double,
                                      int,const int*,const double*,const double*,double*,double*);
extern "C" int membrane_fem_solve_contact(int,double*,const double*,int,const int*,const double*,const double*,double,double,double,int,double,double,double,
                                        int,const int*,const double*,const double*,double*,int,const int*,const double*,int,const double*,double*,double*);
extern "C" int membrane_fem_solve_trajectory(int,double*,const double*,int,const int*,const double*,const double*,double,double,double,int,double,double,double,
    int,const int*,const double*,const double*,double*,int,const int*,const double*,int,const int*,const double*,const double*,int,const double*,double*,double*);
extern "C" int membrane_solve_contact(int,const double*,double*,const double*,int,const int*,const int*,
    const double*,double,int,const int*,int,const double*,int,double,double,double,double*,double*);
extern "C" int membrane_guard_motion(int,const double*,const double*,int,const int*,int,const int*,
    const double*,int,double,double*);
extern "C" int membrane_guard_motion_witness(int,const double*,const double*,int,const int*,int,const int*,
    const double*,int,double,double*,double*);
extern "C" int membrane_solve_trajectory(int,const double*,double*,const double*,int,const int*,const int*,
    const double*,double,int,const int*,int,const int*,const double*,const double*,int,const double*,int,
    double,double,double,double*,double*);
extern "C" int membrane_solve_trajectory_anatomy(int,const double*,double*,const double*,int,const int*,const int*,
    const double*,double,int,const int*,int,const int*,const double*,const double*,int,const double*,int,const int*,
    const double*,int,double,double,double,double*,double*);

namespace godot {
class MembraneFEMKernel : public RefCounted {
    GDCLASS(MembraneFEMKernel,RefCounted)
    static bool real(const Dictionary& request,const char* key) {
        return request.has(key) && (request[key].get_type()==Variant::FLOAT || request[key].get_type()==Variant::INT);
    }
    static bool geometry(const Dictionary& request) {
        for(const char* key:{"xyz","gradients","areas"})
            if(!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) return false;
        if(!request.has("nodes") || request["nodes"].get_type()!=Variant::PACKED_INT32_ARRAY || !real(request,"mu") || !real(request,"lambda")) return false;
        PackedFloat64Array xyz=request["xyz"],gradients=request["gradients"],areas=request["areas"];
        PackedInt32Array nodes=request["nodes"];
        return xyz.size()>0 && xyz.size()%3==0 && xyz.size()/3<=4096 && areas.size()<=8192 &&
            nodes.size()==areas.size()*3 && gradients.size()==areas.size()*6;
    }
protected:
    static void _bind_methods() {
        ClassDB::bind_method(D_METHOD("solve_fem","request"),&MembraneFEMKernel::solve_fem);
        ClassDB::bind_method(D_METHOD("evaluate_fem","request"),&MembraneFEMKernel::evaluate_fem);
        ClassDB::bind_method(D_METHOD("solve_grasp_fem","request"),&MembraneFEMKernel::solve_grasp_fem);
        ClassDB::bind_method(D_METHOD("contact_fem","request"),&MembraneFEMKernel::contact_fem);
        ClassDB::bind_method(D_METHOD("solve_contact_fem","request"),&MembraneFEMKernel::solve_contact_fem);
        ClassDB::bind_method(D_METHOD("solve_trajectory_fem","request"),&MembraneFEMKernel::solve_trajectory_fem);
    }
public:
    Dictionary solve_contact_fem(const Dictionary& request) {return contact_candidate(request,false);}
    Dictionary solve_trajectory_fem(const Dictionary& request) {return contact_candidate(request,true);}
    Dictionary contact_candidate(const Dictionary& request,bool trajectory) {
        PackedFloat64Array result,reaction,dual,stats;stats.resize(16);stats.fill(0.);
        for(int k:{0,1,8,12,13}) stats.set(k,std::numeric_limits<double>::infinity());
        if(request.has("xyz") && request["xyz"].get_type()==Variant::PACKED_FLOAT64_ARRAY) result=request["xyz"];
        bool valid=geometry(request) && real(request,"dt") && real(request,"force_tolerance") && real(request,"gap_tolerance") && real(request,"complementarity_tolerance") &&
            request.has("budget") && request["budget"].get_type()==Variant::INT;
        for(const char* key:{"inverse","grip_weights","targets","face_weights"})
            if(!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
        for(const char* key:{"grip_nodes","face_nodes"})
            if(!request.has(key) || request[key].get_type()!=Variant::PACKED_INT32_ARRAY) valid=false;
        if(trajectory) {
            for(const char* key:{"previous","times","packets"})
                if(!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
            if(!request.has("kinds") || request["kinds"].get_type()!=Variant::PACKED_INT32_ARRAY) valid=false;
        } else if(!request.has("capsules") || request["capsules"].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
        int status=-1;
        if(valid) {
            PackedFloat64Array inverse=request["inverse"],gradients=request["gradients"],areas=request["areas"],weights=request["grip_weights"],targets=request["targets"],face_weights=request["face_weights"],capsules,previous,times,packets;
            PackedInt32Array nodes=request["nodes"],grip_nodes=request["grip_nodes"],face_nodes=request["face_nodes"];int64_t budget=request["budget"];
            PackedInt32Array kinds;int64_t bodies=0,layers=1;
            if(trajectory) {previous=request["previous"];times=request["times"];packets=request["packets"];kinds=request["kinds"];bodies=kinds.size();layers=times.size();}
            else {capsules=request["capsules"];bodies=capsules.size()/7;}
            valid=inverse.size()==result.size()/3 && targets.size()%3==0 && targets.size()<=6 && grip_nodes.size()==targets.size() && weights.size()==targets.size() &&
                face_nodes.size()%3==0 && face_nodes.size()/3<=8192 && face_weights.size()==face_nodes.size()*3 && bodies<=64 && layers>=1 && layers<=16 &&
                (face_nodes.size()/3)*bodies*layers<=65536 && budget>=0 && budget<=1000 &&
                (trajectory ? previous.size()==result.size() && packets.size()==bodies*41 : capsules.size()%7==0);
            if(valid) {
                PackedFloat64Array next_reaction,next_dual;next_reaction.resize(targets.size());next_dual.resize((face_nodes.size()/3)*bodies*layers);
                if(trajectory) status=membrane_fem_solve_trajectory(static_cast<int>(inverse.size()),result.ptrw(),inverse.ptr(),static_cast<int>(areas.size()),nodes.ptr(),gradients.ptr(),areas.ptr(),
                    static_cast<double>(request["mu"]),static_cast<double>(request["lambda"]),static_cast<double>(request["dt"]),static_cast<int>(budget),
                    static_cast<double>(request["force_tolerance"]),static_cast<double>(request["gap_tolerance"]),static_cast<double>(request["complementarity_tolerance"]),
                    static_cast<int>(targets.size()/3),grip_nodes.ptr(),weights.ptr(),targets.ptr(),next_reaction.ptrw(),static_cast<int>(face_nodes.size()/3),face_nodes.ptr(),face_weights.ptr(),
                    static_cast<int>(bodies),kinds.ptr(),packets.ptr(),previous.ptr(),static_cast<int>(layers),times.ptr(),next_dual.ptrw(),stats.ptrw());
                else status=membrane_fem_solve_contact(static_cast<int>(inverse.size()),result.ptrw(),inverse.ptr(),static_cast<int>(areas.size()),nodes.ptr(),gradients.ptr(),areas.ptr(),
                    static_cast<double>(request["mu"]),static_cast<double>(request["lambda"]),static_cast<double>(request["dt"]),static_cast<int>(budget),
                    static_cast<double>(request["force_tolerance"]),static_cast<double>(request["gap_tolerance"]),static_cast<double>(request["complementarity_tolerance"]),
                    static_cast<int>(targets.size()/3),grip_nodes.ptr(),weights.ptr(),targets.ptr(),next_reaction.ptrw(),static_cast<int>(face_nodes.size()/3),face_nodes.ptr(),face_weights.ptr(),
                    static_cast<int>(capsules.size()/7),capsules.ptr(),next_dual.ptrw(),stats.ptrw());
                if(status==0) {reaction=next_reaction;dual=next_dual;}
            }
        }
        Dictionary answer;answer["status"]=status;answer["xyz"]=result;answer["reaction"]=reaction;answer["dual"]=dual;answer["stats"]=stats;return answer;
    }
    Dictionary contact_fem(const Dictionary& request) {
        PackedFloat64Array values,gradient,hessian;
        int status=-1;bool valid=real(request,"radius");
        for(const char* key:{"controls","weights","segment"})
            if(!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
        if(valid) {
            PackedFloat64Array controls=request["controls"],weights=request["weights"],segment=request["segment"];
            if(controls.size()==9 && weights.size()==9 && segment.size()==6) {
                const auto result=membrane::embedded_contact::distance(segment.ptr(),controls.ptr(),weights.ptr(),static_cast<double>(request["radius"]));
                status=result.status;
                if(status==0) {
                    values.resize(22);gradient.resize(9);hessian.resize(81);
                    for(int k=0;k<22;++k) values.set(k,result.values[k]);
                    for(int k=0;k<9;++k) gradient.set(k,result.gradient[k]);
                    for(int k=0;k<81;++k) hessian.set(k,result.hessian[k]);
                }
            }
        }
        Dictionary answer;answer["status"]=status;answer["values"]=values;answer["gradient"]=gradient;answer["hessian"]=hessian;return answer;
    }
    Dictionary solve_fem(const Dictionary& request) {
        PackedFloat64Array result,stats;stats.resize(8);stats.fill(0.);
        stats.set(0,std::numeric_limits<double>::infinity());stats.set(1,std::numeric_limits<double>::infinity());
        if(request.has("xyz") && request["xyz"].get_type()==Variant::PACKED_FLOAT64_ARRAY) result=request["xyz"];
        int status=-1;
        bool valid=geometry(request) && request.has("inverse") && request["inverse"].get_type()==Variant::PACKED_FLOAT64_ARRAY &&
            request.has("budget") && request["budget"].get_type()==Variant::INT && real(request,"dt") && real(request,"force_tolerance");
        if(valid) {
            PackedFloat64Array inverse=request["inverse"],gradients=request["gradients"],areas=request["areas"];
            PackedInt32Array nodes=request["nodes"];int64_t budget=request["budget"];
            valid=inverse.size()==result.size()/3 && budget>=0 && budget<=1000;
            if(valid) status=membrane_fem_solve(static_cast<int>(inverse.size()),result.ptrw(),inverse.ptr(),static_cast<int>(areas.size()),nodes.ptr(),gradients.ptr(),areas.ptr(),
                static_cast<double>(request["mu"]),static_cast<double>(request["lambda"]),static_cast<double>(request["dt"]),static_cast<int>(budget),static_cast<double>(request["force_tolerance"]),stats.ptrw());
        }
        Dictionary answer;answer["status"]=status;answer["xyz"]=result;answer["stats"]=stats;return answer;
    }
    Dictionary evaluate_fem(const Dictionary& request) {
        PackedFloat64Array gradient;double energy=std::numeric_limits<double>::infinity();int status=-1;
        if(geometry(request)) {
            PackedFloat64Array xyz=request["xyz"],gradients=request["gradients"],areas=request["areas"];
            PackedInt32Array nodes=request["nodes"];gradient.resize(xyz.size());gradient.fill(0.);
            status=membrane_fem_evaluate(static_cast<int>(xyz.size()/3),xyz.ptr(),static_cast<int>(areas.size()),nodes.ptr(),gradients.ptr(),areas.ptr(),
                static_cast<double>(request["mu"]),static_cast<double>(request["lambda"]),&energy,gradient.ptrw(),nullptr);
        }
        Dictionary answer;answer["status"]=status;answer["energy"]=energy;answer["gradient"]=gradient;return answer;
    }
    Dictionary solve_grasp_fem(const Dictionary& request) {
        PackedFloat64Array result,reaction,stats;stats.resize(12);stats.fill(0.);
        for(int index:{0,1,8}) stats.set(index,std::numeric_limits<double>::infinity());
        if(request.has("xyz") && request["xyz"].get_type()==Variant::PACKED_FLOAT64_ARRAY) result=request["xyz"];
        bool valid=geometry(request) && real(request,"dt") && real(request,"force_tolerance") && real(request,"gap_tolerance") &&
            request.has("budget") && request["budget"].get_type()==Variant::INT;
        for(const char* key:{"inverse","grip_weights","targets"})
            if(!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
        if(!request.has("grip_nodes") || request["grip_nodes"].get_type()!=Variant::PACKED_INT32_ARRAY) valid=false;
        int status=-1;
        if(valid) {
            PackedFloat64Array inverse=request["inverse"],gradients=request["gradients"],areas=request["areas"],weights=request["grip_weights"],targets=request["targets"];
            PackedInt32Array nodes=request["nodes"],grip_nodes=request["grip_nodes"];int64_t budget=request["budget"];
            valid=inverse.size()==result.size()/3 && targets.size()%3==0 && targets.size()<=6 &&
                weights.size()==targets.size() && grip_nodes.size()==targets.size() && budget>=0 && budget<=1000;
            if(valid) {
                reaction.resize(targets.size());reaction.fill(0.);
                status=membrane_fem_solve_grasp(static_cast<int>(inverse.size()),result.ptrw(),inverse.ptr(),static_cast<int>(areas.size()),nodes.ptr(),gradients.ptr(),areas.ptr(),
                    static_cast<double>(request["mu"]),static_cast<double>(request["lambda"]),static_cast<double>(request["dt"]),static_cast<int>(budget),
                    static_cast<double>(request["force_tolerance"]),static_cast<double>(request["gap_tolerance"]),static_cast<int>(targets.size()/3),grip_nodes.ptr(),weights.ptr(),targets.ptr(),reaction.ptrw(),stats.ptrw());
            }
        }
        Dictionary answer;answer["status"]=status;answer["xyz"]=result;answer["reaction"]=reaction;answer["stats"]=stats;return answer;
    }
};
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
        ClassDB::bind_method(D_METHOD("solve_trajectory","request"),&MembraneContactKernel::solve_trajectory);
        ClassDB::bind_method(D_METHOD("solve_anatomy","request"),&MembraneContactKernel::solve_anatomy);
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
        double witness=-1.;
        if (valid) {
            PackedFloat64Array previous=request["previous"],current=request["current"],packets=request["packets"];
            PackedInt32Array triangles=request["triangles"],kinds=request["kinds"];
            int64_t budget=request["budget"];
            valid=previous.size()>0 && previous.size()%3==0 && previous.size()==current.size() &&
                previous.size()/3<=4096 && triangles.size()%3==0 && triangles.size()/3<=16384 &&
                kinds.size()<=64 && packets.size()==kinds.size()*41 && (triangles.size()/3)*kinds.size()<=65536 &&
                budget>=0 && budget<=128;
            if (valid) status=membrane_guard_motion_witness(static_cast<int>(previous.size()/3),previous.ptr(),current.ptr(),
                static_cast<int>(triangles.size()/3),triangles.ptr(),static_cast<int>(kinds.size()),kinds.ptr(),
                packets.ptr(),static_cast<int>(budget),static_cast<double>(request["gap_tolerance"]),stats.ptrw(),&witness);
        }
        Dictionary answer; answer["status"]=status; answer["stats"]=stats; answer["witness_t"]=witness; return answer;
    }
    Dictionary solve_trajectory(const Dictionary& request) {
        return trajectory_impl(request,false);
    }
    Dictionary solve_anatomy(const Dictionary& request) {
        return trajectory_impl(request,true);
    }
    Dictionary trajectory_impl(const Dictionary& request,bool with_anatomy) {
        PackedFloat64Array result,dual,stats;
        stats.resize(12); stats.fill(0.);
        for (int i=0;i<4;++i) stats.set(i,std::numeric_limits<double>::infinity());
        stats.set(9,std::numeric_limits<double>::infinity());
        bool valid=true;
        for (const char* key: {"predicted","initial","inverse","rest","previous","packets","times"})
            if (!request.has(key) || request[key].get_type()!=Variant::PACKED_FLOAT64_ARRAY) valid=false;
        for (const char* key: {"a","b","triangles","kinds"})
            if (!request.has(key) || request[key].get_type()!=Variant::PACKED_INT32_ARRAY) valid=false;
        for (const char* key: {"alpha","force_tolerance","gap_tolerance","complementarity_tolerance"})
            if (!request.has(key) || (request[key].get_type()!=Variant::FLOAT && request[key].get_type()!=Variant::INT)) valid=false;
        if (!request.has("budget") || request["budget"].get_type()!=Variant::INT) valid=false;
        if (with_anatomy && (!request.has("anatomy") || request["anatomy"].get_type()!=Variant::PACKED_FLOAT64_ARRAY ||
            !request.has("anatomy_vertices") || request["anatomy_vertices"].get_type()!=Variant::PACKED_INT32_ARRAY)) valid=false;
        if (request.has("initial") && request["initial"].get_type()==Variant::PACKED_FLOAT64_ARRAY) result=request["initial"];
        int status=-1;
        if (valid) {
            PackedFloat64Array predicted=request["predicted"],inverse=request["inverse"],rest=request["rest"],
                previous=request["previous"],packets=request["packets"],times=request["times"];
            PackedInt32Array a=request["a"],b=request["b"],triangles=request["triangles"],kinds=request["kinds"];
            PackedFloat64Array anatomy;
            PackedInt32Array anatomy_vertices;
            if (with_anatomy) { anatomy=request["anatomy"]; anatomy_vertices=request["anatomy_vertices"]; }
            int64_t budget=request["budget"];
            valid=result.size()>0 && result.size()%3==0 && result.size()==predicted.size() && result.size()==previous.size() &&
                inverse.size()==result.size()/3 && inverse.size()<=4096 && a.size()==b.size() && a.size()==rest.size() &&
                a.size()<=16384 && triangles.size()%3==0 && triangles.size()/3<=16384 && kinds.size()<=64 &&
                packets.size()==kinds.size()*41 && times.size()>0 && times.size()<=16 &&
                (triangles.size()/3)*kinds.size()*times.size()<=65536 && budget>=0 && budget<=1000;
            valid=valid && anatomy_vertices.size()<=4096 && anatomy.size()==11*anatomy_vertices.size() &&
                (triangles.size()/3)*kinds.size()*times.size()+anatomy_vertices.size()<=65536;
            if (valid) {
                dual.resize((triangles.size()/3)*kinds.size()*times.size()+anatomy_vertices.size()); dual.fill(0.);
                if (with_anatomy) status=membrane_solve_trajectory_anatomy(static_cast<int>(inverse.size()),predicted.ptr(),result.ptrw(),inverse.ptr(),
                    static_cast<int>(a.size()),a.ptr(),b.ptr(),rest.ptr(),static_cast<double>(request["alpha"]),
                    static_cast<int>(triangles.size()/3),triangles.ptr(),static_cast<int>(kinds.size()),kinds.ptr(),packets.ptr(),
                    previous.ptr(),static_cast<int>(times.size()),times.ptr(),static_cast<int>(anatomy_vertices.size()),anatomy_vertices.ptr(),anatomy.ptr(),
                    static_cast<int>(budget),static_cast<double>(request["force_tolerance"]),static_cast<double>(request["gap_tolerance"]),
                    static_cast<double>(request["complementarity_tolerance"]),dual.ptrw(),stats.ptrw());
                else status=membrane_solve_trajectory(static_cast<int>(inverse.size()),predicted.ptr(),result.ptrw(),inverse.ptr(),
                    static_cast<int>(a.size()),a.ptr(),b.ptr(),rest.ptr(),static_cast<double>(request["alpha"]),
                    static_cast<int>(triangles.size()/3),triangles.ptr(),static_cast<int>(kinds.size()),kinds.ptr(),packets.ptr(),
                    previous.ptr(),static_cast<int>(times.size()),times.ptr(),static_cast<int>(budget),
                    static_cast<double>(request["force_tolerance"]),static_cast<double>(request["gap_tolerance"]),
                    static_cast<double>(request["complementarity_tolerance"]),dual.ptrw(),stats.ptrw());
            }
        }
        Dictionary answer; answer["status"]=status; answer["xyz"]=result; answer["dual"]=dual; answer["stats"]=stats; return answer;
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
        GDREGISTER_CLASS(MembraneFEMKernel);
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
