// Included inside membrane_fem.cpp's private namespace to share its unchanged
// original energy, sparse cell factors and equality machinery. Static candidate
// only: a separate whole-interval guard is mandatory before engine acceptance.
struct ContactState {
    double energy=0.,penetration=0.,complementarity=0.,force_error=0.;
    Vec gradient,blocks,updated;
};
struct FineContacts {
    int faces,bodies;
    const int* nodes;
    const double *weights,*capsules;
    int layers=1;
    const double *previous=nullptr,*times=nullptr;
    int pairs() const {return faces*bodies*layers;}
    int face_index(int pair) const {return (pair/bodies)%faces;}
    double time(int pair) const {return previous ? times[pair/(faces*bodies)] : 1.;}
    const double* body(int pair) const {return capsules+7*((pair/(faces*bodies))*bodies+pair%bodies);}
    void local(const Vec& x,int pair,double* controls,double* triangle) const {
        const int face=face_index(pair);const double t=time(pair);
        for(int j=0;j<3;++j) for(int a=0;a<3;++a) {
            const int k=nodes[face*3+j]*3+a;
            controls[3*j+a]=previous && t!=1. ? static_cast<double>(static_cast<long double>(previous[k])+t*(static_cast<long double>(x[k])-previous[k])) : x[k];
        }
        for(int j=0;j<3;++j) {
            const double* w=weights+face*9+j*3;
            const long double sum=static_cast<long double>(w[0])+w[1]+w[2];
            for(int a=0;a<3;++a) triangle[j*3+a]=static_cast<double>(static_cast<long double>(controls[a])+
                (w[1]*(static_cast<long double>(controls[3+a])-controls[a])+w[2]*(static_cast<long double>(controls[6+a])-controls[a]))/sum);
        }
    }
    bool evaluate(const Problem& problem,const Vec& x,const Vec& dual,double rho,ContactState& out,bool physical_dual=false) const {
        out.penetration=out.complementarity=out.force_error=0.;
        if(!problem.evaluate(x,out.energy,out.gradient,&out.blocks)) return false;
        const size_t offset=out.blocks.size();out.blocks.resize(offset+size_t(pairs())*81,0.);
        out.updated.resize(pairs());
        Vec uncertainty(previous ? x.size() : 0,0.);
        for(int p=0;p<pairs();++p) {
            double controls[9],triangle[9];local(x,p,controls,triangle);
            const double* capsule=body(p);const double r2=capsule[6]*capsule[6];
#ifdef FEM_CONTACT_OBSERVER
            observe_contact_query(false);
#endif
            const auto query=membrane::contact::distance(capsule,triangle,capsule[6]);
            if(query.status!=0 && query.status!=3) return false;
            double g=query.values[0]/r2-1.,u=std::max(0.,dual[p]-rho*g),u_error=0.;
            if(!std::isfinite(g) || !std::isfinite(u)) return false;
            if(previous) {
                double old[9],end[9];const int face=face_index(p);
                for(int j=0;j<3;++j) for(int axis=0;axis<3;++axis) {
                    const int k=nodes[face*3+j]*3+axis;old[j*3+axis]=previous[k];end[j*3+axis]=x[k];
                }
                // The full geometry query above remains mandatory. This strict
                // unrounded hull certificate only avoids refining a known-zero
                // PHR multiplier; it never clears the complete physical path.
                if(!physical_dual && u==0. && membrane::fem_trajectory_merit::inactive(old,end,end,time(p),capsule,capsule[6],dual[p],rho)) {
                    out.updated[p]=0.;continue;
                }
                membrane::merit::Interval bounded_gap,separation;
                if(!membrane::fem_trajectory_merit::gap(old,end,weights+face*9,time(p),capsule,capsule[6],query,bounded_gap,separation)) return false;
                namespace m=membrane::merit;
                const auto multiplier=physical_dual ? m::Interval(dual[p]) : m::positive(m::Interval(dual[p])-m::Interval(rho)*bounded_gap);
                g=static_cast<double>((bounded_gap.lo+bounded_gap.hi)/2);
                u=static_cast<double>((multiplier.lo+multiplier.hi)/2);
                const auto error=multiplier-m::Interval(u);
                const auto radius=std::max(-error.lo,error.hi);
                u_error=multiplier.hi==0 || radius==0 ? 0. : m::upper_double(m::Interval(0,radius));
                const auto comp=multiplier*bounded_gap;
                out.complementarity=std::max(out.complementarity,m::upper_double(m::Interval(0,std::max(-comp.lo,comp.hi))));
                out.penetration=std::max(out.penetration,m::upper_double(m::Interval(capsule[6])-separation));
                if(!std::isfinite(g) || !std::isfinite(u) || !std::isfinite(u_error)) return false;
            }
            out.updated[p]=u;
            if(!previous) {
                out.penetration=std::max(out.penetration,-query.values[1]);
                out.complementarity=std::max(out.complementarity,std::abs(u*g));
            }
            if(u==0. && u_error==0.) continue; // certified inactive ties need no ordinary Hessian
            const int face=face_index(p);const double t=time(p);
            const auto exact=membrane::embedded_contact::distance(capsule,controls,weights+face*9,capsule[6]);
            if(exact.status!=0) return false;
            for(int i=0;i<9;++i) {
                const int k=nodes[face*3+i/3]*3+i%3;
                const double ji=exact.gradient[i]/r2;
                if(problem.mass[k/3]>0.) out.gradient[k]-=previous ? u*t*ji : u*ji;
                if(previous && problem.mass[k/3]>0.) {
                    const auto bound=membrane::merit::Interval(u_error)*membrane::merit::Interval(std::abs(t*ji));
                    uncertainty[k]=std::nextafter(uncertainty[k]+membrane::merit::upper_double(bound),std::numeric_limits<double>::infinity());
                }
                for(int j=0;j<9;++j) {
                    double block=-u*exact.hessian[i*9+j]/r2+rho*ji*exact.gradient[j]/r2;
                    if(previous) block*=t*t;
                    out.blocks[offset+size_t(p)*81+i*9+j]=block;
                }
            }
        }
        for(double value:out.gradient) if(!std::isfinite(value)) return false;
        for(double value:out.blocks) if(!std::isfinite(value)) return false;
        for(double value:uncertainty) {if(!std::isfinite(value)) return false;out.force_error=std::max(out.force_error,value);}
        return true;
    }
    bool difference(const Problem& problem,const Vec& x,const Vec& y,const Vec& dual,double rho,
                    const ContactState& current,const ContactState& candidate,double& upper) const {
        double original=0.;if(!problem.difference(x,y,original)) return false;
        membrane::merit::Interval value(original);
        for(int p=0;p<pairs();++p) {
            double controls[9],before[9],after[9];local(x,p,controls,before);local(y,p,controls,after);
            const double* capsule=body(p);membrane::merit::Interval term;
            if(previous) {
                double old[9],first[9],last[9];const int face=face_index(p);
                for(int j=0;j<3;++j) for(int a=0;a<3;++a) {
                    const int k=nodes[face*3+j]*3+a;old[j*3+a]=previous[k];first[j*3+a]=x[k];last[j*3+a]=y[k];
                }
                if(current.updated[p]==0. && candidate.updated[p]==0. &&
                   membrane::fem_trajectory_merit::inactive(old,first,last,time(p),capsule,capsule[6],dual[p],rho)) {
                    value=value+membrane::merit::Interval(0);continue;
                }
#ifdef FEM_CONTACT_OBSERVER
                observe_contact_query(true);
#endif
                if(!membrane::fem_trajectory_merit::contact_change(old,first,last,weights+face*9,time(p),capsule,capsule[6],dual[p],rho,term)) return false;
                value=value+term;continue;
            }
            if(current.updated[p]==0. && candidate.updated[p]==0. &&
               membrane::merit::inactive_box(before,after,capsule,capsule[6],dual[p],rho)) {
                // Both full distance evaluations already passed at this same
                // dual/rho. Preserve rounded activation AND the old interval
                // certificate; do not infer inactive Hessians from the box.
                value=value+membrane::merit::Interval(0);continue;
            }
#ifdef FEM_CONTACT_OBSERVER
            observe_contact_query(true);
#endif
            if(!membrane::merit::contact_change(before,after,capsule,capsule[6],dual[p],rho,term)) return false;
            value=value+term;
        }
        upper=std::nextafter(static_cast<double>(value.hi),std::numeric_limits<double>::infinity());
        return std::isfinite(upper);
    }
};

int solve_contact(int n,double* output,const double* inverse,int count,const int* nodes,const double* gradients,
                  const double* areas,double mu,double lambda,double dt,int budget,double tolerance,double gap_tolerance,double comp_tolerance,
                  int grips,const int* grip_nodes,const double* weights,const double* targets,double* reaction,
                  int faces,const int* face_nodes,const double* face_weights,int bodies,const double* capsules,double* contact_dual,double* stats,
                  int layers=1,const double* previous=nullptr,const double* times=nullptr) {
    if(!output || !inverse || !stats || grips<0 || grips>2 || (grips && (!grip_nodes || !weights || !targets || !reaction)) ||
       faces<0 || faces>8192 || bodies<0 || bodies>64 || layers<1 || layers>16 || faces*bodies*layers>65536 ||
       (faces && (!face_nodes || !face_weights)) || (bodies && !capsules) || (faces*bodies && !contact_dual) ||
       !material(mu,lambda) || !std::isfinite(dt) || dt<1e-6 || dt>.1 || budget<0 || budget>1000 ||
       !std::isfinite(tolerance) || tolerance<=0. || !std::isfinite(gap_tolerance) || gap_tolerance<=0. ||
       !std::isfinite(comp_tolerance) || comp_tolerance<=0.) return -1;
    Problem problem;problem.mu=mu;problem.lambda=lambda;
    if(!membrane_fem::cells(n,count,nodes,gradients,areas,problem.cells)) return -1;
    for(int f=0;f<faces;++f) {
        for(int j=0;j<3;++j) if(face_nodes[f*3+j]<0 || face_nodes[f*3+j]>=n) return -1;
        if(face_nodes[f*3]==face_nodes[f*3+1] || face_nodes[f*3+1]==face_nodes[f*3+2] || face_nodes[f*3+2]==face_nodes[f*3]) return -1;
        for(int corner=0;corner<3;++corner) {
            double sum=0.;
            for(int j=0;j<3;++j) {const double v=face_weights[f*9+corner*3+j];if(!std::isfinite(v) || v<0. || v>1.) return -1;sum+=v;}
            if(std::abs(sum-1.)>64.*std::numeric_limits<double>::epsilon()) return -1;
        }
    }
    for(int b=0;b<bodies*layers;++b) {
        for(int j=0;j<6;++j) if(!std::isfinite(capsules[b*7+j]) || std::abs(capsules[b*7+j])>16.) return -1;
        const double r=capsules[b*7+6];if(!std::isfinite(r) || r<=0. || r>.3 || r*r==0.) return -1;
    }
    if(!faces || !bodies) {stats[12]=stats[13]=0.;return solve_grasp(n,output,inverse,count,nodes,gradients,areas,mu,lambda,dt,budget,tolerance,gap_tolerance,grips,grip_nodes,weights,targets,reaction,stats);}
    problem.predicted.assign(output,output+n*3);problem.mass.resize(n);
    std::vector<int> free,map(n*3,-1);
    for(int node=0;node<n;++node) {
        if(!inertia(inverse[node],dt,problem.mass[node])) return -1;
        for(int a=0;a<3;++a) {
            const int k=node*3+a;if(!std::isfinite(output[k]) || std::abs(output[k])>16.) return -1;
            if(inverse[node]>0.) {map[k]=static_cast<int>(free.size());free.push_back(k);}
        }
    }
    const int size=static_cast<int>(free.size()),rows=grips*3;
    Eigen::MatrixXd a=Eigen::MatrixXd::Zero(rows,size);Eigen::VectorXd target(rows),q(size);
    for(int hand=0;hand<grips;++hand) {
        double sum=0.;
        for(int j=0;j<3;++j) {const double w=weights[hand*3+j];if(grip_nodes[hand*3+j]<0 || grip_nodes[hand*3+j]>=n || !std::isfinite(w) || w<0. || w>1.) return -1;sum+=w;}
        if(std::abs(sum-1.)>64.*std::numeric_limits<double>::epsilon()) return -1;
        for(int axis=0;axis<3;++axis) {
            const int row=hand*3+axis;if(!std::isfinite(targets[row]) || std::abs(targets[row])>16.) return -1;target[row]=targets[row];
            for(int j=0;j<3;++j) {const int k=grip_nodes[hand*3+j]*3+axis;const double w=weights[hand*3+j]/sum;
                if(map[k]>=0) a(row,map[k])+=w;else target[row]-=w*problem.predicted[k];}
        }
    }
    Eigen::LDLT<Eigen::MatrixXd> gram_factor;
    Vec x=problem.predicted;double projection_gap=0.;
    if(rows) {
        if(!size) return 4;
        gram_factor.compute(a*a.transpose());if(!positive(gram_factor)) return 4;
        Eigen::MatrixXd weighted=a;for(int j=0;j<size;++j) {q[j]=x[free[j]];weighted.col(j)/=problem.mass[free[j]/3];}
        Eigen::LDLT<Eigen::MatrixXd> projection(weighted*a.transpose());if(!positive(projection)) return 4;
        q+=weighted.transpose()*projection.solve(target-a*q);
        projection_gap=(a*q-target).lpNorm<Eigen::Infinity>();
        if(!q.allFinite() || projection_gap>gap_tolerance) return 2;
        for(int j=0;j<size;++j) x[free[j]]=q[j];
    }
    FineContacts contacts{faces,bodies,face_nodes,face_weights,capsules,layers,previous,times};
    auto pattern=problem.cells;
    for(int p=0;p<contacts.pairs();++p) {Cell cell{};for(int j=0;j<3;++j) cell.node[j]=face_nodes[contacts.face_index(p)*3+j];pattern.push_back(cell);}
    SparseCells system(n,pattern,problem.mass,rows ? &a : nullptr);
    Vec dual(contacts.pairs(),0.),metric(n*3),trial(n*3),direction(n*3);
    Eigen::VectorXd gf(size),balance(size),hold=Eigen::VectorXd::Zero(rows),rhs_gap(rows);
    ContactState state,next;double rho=1.,hold_rho=1.,damping=1e-3,last_violation=std::numeric_limits<double>::infinity();
    double force=std::numeric_limits<double>::infinity(),gap=projection_gap,linear=0.,min_step=1.;
    int iterations=0,evaluations=0,factors=0,status=1,outer=0;
    for(;outer<100;++outer) {
        ++evaluations;if(!contacts.evaluate(problem,x,dual,rho,state)) {status=2;break;}
        // Early infeasible AL models need only inexact minimization. This is
        // not acceptance: the original final force tolerance is checked below.
        const double inner_tolerance=(state.penetration>gap_tolerance || state.complementarity>comp_tolerance) ? std::max(tolerance,1e-6) : tolerance;
        bool inner_done=false,polish_tried=false;
        for(;;) {
            for(int j=0;j<size;++j) {q[j]=x[free[j]];gf[j]=state.gradient[free[j]];}
            balance=gf;
            if(rows) {hold=-gram_factor.solve(a*gf);balance+=a.transpose()*hold;rhs_gap=target-a*q;gap=rhs_gap.lpNorm<Eigen::Infinity>();}
            // Equality projection is nonexpansive in2-norm, not infinity norm.
            force=size ? balance.lpNorm<Eigen::Infinity>()+state.force_error*(rows ? std::sqrt(double(size)) : 1.) : 0.;
            if(!std::isfinite(force) || !std::isfinite(gap) || !hold.allFinite()) {status=2;break;}
            // At a feasible material point, solve for physical multipliers
            // directly instead of amplifying coordinate rounding by another
            // penalty step. The proposed duals get a fresh full evaluation;
            // every original acceptance gate, including final SPD, still applies.
            if(previous && !polish_tried && force>tolerance && force<=std::max(tolerance,1e-6) &&
               gap<=gap_tolerance && state.penetration<=gap_tolerance && state.complementarity<=comp_tolerance) {
                polish_tried=true;std::vector<int> active;
                for(int p=0;p<contacts.pairs();++p) if(state.updated[p]>0.) active.push_back(p);
                if(!active.empty() && active.size()<=128) {
                    Eigen::MatrixXd jac=Eigen::MatrixXd::Zero(size,active.size());bool valid=true;
                    for(size_t column=0;column<active.size();++column) {
                        const int p=active[column],face=contacts.face_index(p);double controls[9],triangle[9];contacts.local(x,p,controls,triangle);
                        const double* body=contacts.body(p);const double r2=body[6]*body[6];
                        const auto exact=membrane::embedded_contact::distance(body,controls,face_weights+face*9,body[6]);
                        if(exact.status!=0) {valid=false;break;}
                        for(int j=0;j<9;++j) {const int k=map[face_nodes[face*3+j/3]*3+j%3];
                            if(k>=0) jac(k,column)+=contacts.time(p)*exact.gradient[j]/r2;}
                    }
                    if(valid && jac.allFinite()) {
                        if(rows) jac-=a.transpose()*gram_factor.solve(a*jac).eval();
                        ++factors;const Eigen::VectorXd correction=jac.completeOrthogonalDecomposition().solve(balance);
                        Vec physical=state.updated;
                        if(!correction.allFinite()) valid=false;
                        else for(size_t j=0;j<active.size();++j) {physical[active[j]]+=correction[j];
                            if(!std::isfinite(physical[active[j]]) || physical[active[j]]<0.) valid=false;}
                        ContactState polished;
                        if(valid) {++evaluations;valid=contacts.evaluate(problem,x,physical,rho,polished,true);}
                        if(valid) {
                            Eigen::VectorXd pg(size),ph=Eigen::VectorXd::Zero(rows),pb;
                            for(int j=0;j<size;++j) pg[j]=polished.gradient[free[j]];
                            pb=pg;if(rows) {ph=-gram_factor.solve(a*pg);pb+=a.transpose()*ph;}
                            const double pf=pb.lpNorm<Eigen::Infinity>()+polished.force_error*(rows?std::sqrt(double(size)):1.);
                            if(std::isfinite(pf) && ph.allFinite() && pf<=tolerance &&
                               polished.penetration<=gap_tolerance && polished.complementarity<=comp_tolerance) {
                                state=std::move(polished);balance=pb;hold=ph;force=pf;inner_done=true;break;
                            }
                        }
                    }
                }
            }
            if(force<=inner_tolerance && gap<=gap_tolerance) {inner_done=true;break;}
            if(iterations>=budget) break;
            for(int k=0;k<n*3;++k) metric[k]=problem.mass[k/3]>0. ? problem.mass[k/3] : 1.;
            for(size_t c=0;c<pattern.size();++c) for(int j=0;j<9;++j) metric[pattern[c].node[j/3]*3+j%3]+=std::abs(state.blocks[c*81+j*9+j]);
            bool solved=false;
            for(int attempt=0;attempt<12;++attempt) {
                ++factors;const int curvature=system.factor(state.blocks,problem.mass,damping,metric,rows ? hold_rho : 0.);
                if(curvature==2) break;
                if(curvature==0) {
                    if(!rows) solved=system.direction(state.gradient,direction,linear);
                    else {
                        Eigen::MatrixXd rhs(size,rows+1),answer;rhs.col(0)=-gf+hold_rho*a.transpose()*rhs_gap;rhs.rightCols(rows)=a.transpose();
                        if(system.solve_matrix(rhs,answer,linear)) {
                            const Eigen::MatrixXd z=answer.rightCols(rows),schur=a*z;Eigen::LDLT<Eigen::MatrixXd> factor(schur);
                            if(positive(factor)) {
                                const Eigen::VectorXd b=a*answer.col(0)-rhs_gap,m=factor.solve(b),step=answer.col(0)-z*m;
                                const double error=(schur*m-b).stableNorm()/std::max(1.,b.stableNorm());
                                if(step.allFinite() && std::isfinite(error) && error<=1e-8) {std::fill(direction.begin(),direction.end(),0.);for(int j=0;j<size;++j) direction[free[j]]=step[j];solved=true;}
                            }
                        }
                    }
                }
                if(solved) break;
                // Stabilize equality-normal curvature in its own augmentation
                // before it forces damping of the unconstrained material modes.
                if(rows) hold_rho=std::min(1e12,hold_rho*10.);
                damping=std::min(1e12,damping*10.);
            }
            if(!solved) {status=2;break;}
            Eigen::VectorXd step(size);for(int j=0;j<size;++j) step[j]=direction[free[j]];
            const double slope=balance.dot(step);if(!(slope<0.) || !std::isfinite(slope)) {status=2;break;}
            bool accepted=false;double fraction=1.;
            for(int line=0;line<32;++line,fraction*=.5) {
                for(int k=0;k<n*3;++k) trial[k]=problem.mass[k/3]>0. ? x[k]+fraction*direction[k] : problem.predicted[k];
                bool bounded=true;for(double v:trial) if(!std::isfinite(v) || std::abs(v)>16.) bounded=false;
                if(!bounded) continue;
                for(int j=0;j<size;++j) {q[j]=trial[free[j]];step[j]=trial[free[j]]-x[free[j]];}
                if(rows && (a*q-target).lpNorm<Eigen::Infinity>()>gap_tolerance) continue;
                ++evaluations;double change=0.;
                const bool compared=contacts.evaluate(problem,trial,dual,rho,next) && contacts.difference(problem,x,trial,dual,rho,state,next,change);
                const double normal_work=rows ? hold.dot(a*step) : 0.;
#ifdef FEM_CONTACT_TRACE
                trace_contact_line(x,trial,dual,rho,iterations,fraction,slope,change,normal_work,compared);
#endif
                if(compared && change+normal_work<=1e-4*fraction*slope) {accepted=true;break;}
            }
            if(!accepted) {status=2;break;}
            x.swap(trial);std::swap(state,next);++iterations;min_step=std::min(min_step,fraction);
            damping=fraction>=.5 ? std::max(1e-12,damping*.25) : std::min(1e12,damping*4.);
        }
        if(!inner_done) break;
        if(force<=tolerance && state.penetration<=gap_tolerance && state.complementarity<=comp_tolerance) {
            for(int attempt=0;attempt<12;++attempt) {
                ++factors;status=system.factor(state.blocks,problem.mass,0.,metric,rows ? hold_rho : 0.);
                if(status==0 || status==2 || !rows) break;hold_rho=std::min(1e12,hold_rho*10.);
            }
            break;
        }
        if(iterations>=budget) break;
        dual=state.updated;
        const double violation=std::max(state.penetration/gap_tolerance,state.complementarity/comp_tolerance);
        if(violation>1. && violation>last_violation*.25) rho=std::min(1e12,rho*10.);
        last_violation=violation;
    }
    stats[0]=state.energy;stats[1]=force;stats[2]=iterations;stats[3]=evaluations;stats[4]=factors;stats[5]=linear;
    stats[6]=min_step;stats[7]=damping;stats[8]=gap;stats[9]=hold_rho;stats[10]=projection_gap;stats[11]=state.force_error;
    stats[12]=state.penetration;stats[13]=state.complementarity;stats[14]=outer;stats[15]=rho;
    if(status==0) {std::copy(x.begin(),x.end(),output);if(rows) std::copy(hold.data(),hold.data()+rows,reaction);std::copy(state.updated.begin(),state.updated.end(),contact_dual);}
    return status;
}
