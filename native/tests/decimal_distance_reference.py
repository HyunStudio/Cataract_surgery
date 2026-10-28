"""Independent active-set quadratic reference, using 80-digit Decimal arithmetic."""
from decimal import Decimal as D,localcontext
from itertools import combinations

def decimal(value): return D.from_float(float(value))
def dot(a,b): return sum((x*y for x,y in zip(a,b)),D(0))

def solve(matrix,rhs):
    rows=[list(row)+[value] for row,value in zip(matrix,rhs)]
    scale=max((abs(value) for row in matrix for value in row),default=D(1))
    for col in range(len(rhs)):
        pivot=max(range(col,len(rows)),key=lambda row:abs(rows[row][col]))
        if abs(rows[pivot][col])<max(D('1e-75'),scale*D('1e-65')): return None
        rows[col],rows[pivot]=rows[pivot],rows[col]
        divisor=rows[col][col]; rows[col]=[value/divisor for value in rows[col]]
        for row in range(len(rows)):
            if row==col: continue
            factor=rows[row][col]
            rows[row]=[a-factor*b for a,b in zip(rows[row],rows[col])]
    return [row[-1] for row in rows]

def squared_distance(axis,triangle):
    with localcontext() as ctx:
        ctx.prec=80
        axis=[[decimal(value) for value in axis[i:i+3]] for i in (0,3)]
        triangle=[[decimal(value) for value in triangle[i:i+3]] for i in (0,3,6)]
        origin=[a-b for a,b in zip(triangle[0],axis[0])]
        columns=[[triangle[i][k]-triangle[0][k] for k in range(3)] for i in (1,2)]
        moving=axis[0]!=axis[1]
        if moving: columns.append([axis[0][k]-axis[1][k] for k in range(3)])
        n=len(columns)
        inequalities=[([D(1),D(0)]+([D(0)] if moving else []),D(0)),
                      ([D(0),D(1)]+([D(0)] if moving else []),D(0)),
                      ([D(-1),D(-1)]+([D(0)] if moving else []),D(-1))]
        if moving: inequalities.extend([([D(0),D(0),D(1)],D(0)),([D(0),D(0),D(-1)],D(-1))])
        hessian=[[dot(a,b) for b in columns] for a in columns]
        gradient=[dot(column,origin) for column in columns]
        answers=[]
        for count in range(n+1):
            for active in combinations(inequalities,count):
                matrix=[row[:]+[a[i] for a,_ in active] for i,row in enumerate(hessian)]
                matrix.extend([row[:]+[D(0)]*count for row,_ in active])
                candidate=solve(matrix,[-value for value in gradient]+[value for _,value in active])
                if candidate is None: continue
                candidate=candidate[:n]
                if any(dot(row,candidate)<bound-D('1e-60') for row,bound in inequalities): continue
                delta=[origin[k]+sum((columns[j][k]*candidate[j] for j in range(n)),D(0)) for k in range(3)]
                answers.append(dot(delta,delta))
        if not answers: raise ArithmeticError("No feasible active-set reference")
        return +min(answers)

def contact_merit(axis,triangle,radius,multiplier,penalty):
    with localcontext() as ctx:
        ctx.prec=80
        g=squared_distance(axis,triangle)/decimal(radius*radius)-1
        lam,rho=decimal(multiplier),decimal(penalty)
        return +(-lam*g+rho*g*g/2 if lam-rho*g>0 else -lam*lam/(2*rho))

def complete_merit(request,point,reactions,penalty):
    """Full captured objective; inactive AABBs are independently certified here."""
    with localcontext() as ctx:
        ctx.prec=80
        xyz=[[decimal(value) for value in point[i:i+3]] for i in range(0,len(point),3)]
        predicted=list(map(decimal,request['predicted'])); stiffness=decimal(1/request['alpha'])
        energy=D(0)
        for vertex,inverse in enumerate(request['inverse']):
            if inverse>0:
                energy+=decimal(1/inverse)*sum(((xyz[vertex][k]-predicted[3*vertex+k])**2 for k in range(3)),D(0))/2
        for a,b,rest in zip(request['a'],request['b'],request['rest']):
            delta=[x-y for x,y in zip(xyz[a],xyz[b])]
            energy+=stiffness*(dot(delta,delta).sqrt()-decimal(rest))**2/2
        count=len(request['capsules'])//7; rho=decimal(penalty)
        for face in range(len(request['triangles'])//3):
            ids=request['triangles'][3*face:3*face+3]; vertices=[xyz[index] for index in ids]
            for body in range(count):
                capsule=request['capsules'][7*body:7*body+7]; radius2=decimal(capsule[6]*capsule[6])
                axis=[[decimal(value) for value in capsule[i:i+3]] for i in (0,3)]
                lam=decimal(reactions.get(str(face*count+body),0.))
                lower=sum((max(D(0),min(v[k] for v in vertices)-max(a[k] for a in axis),min(a[k] for a in axis)-max(v[k] for v in vertices))**2 for k in range(3)),D(0))
                if lower>radius2*(1+lam/rho)+D('1e-60'):
                    energy-=lam*lam/(2*rho)
                else:
                    triangle=[point[3*vertex+k] for vertex in ids for k in range(3)]
                    energy+=contact_merit(capsule[:6],triangle,capsule[6],float(lam),penalty)
        return +energy
