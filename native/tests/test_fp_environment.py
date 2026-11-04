"""Runtime enclosure and caller-state preservation across real FPU contexts."""
import ctypes as ct
from decimal import Decimal,localcontext
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


class EnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe=ct.CDLL(str(ROOT/'.tools/native/fp_environment_probe.dll'))
        for name in ('fem_probe_x87','fem_probe_mxcsr'):getattr(cls.probe,name).restype=ct.c_uint
        for name in ('fem_probe_set_x87','fem_probe_set_mxcsr'):getattr(cls.probe,name).argtypes=[ct.c_uint]
        cls.boundary=cls.probe.fem_probe_boundary
        cls.boundary.argtypes=[ct.c_int,ct.c_double,ct.c_double];cls.boundary.restype=ct.c_int

    @staticmethod
    def contexts(original):
        for precision in (0x200,0x300):
            for x87_rounding in (0,1,2,3):
                for sse_rounding in (0,1,2,3):
                    for flush in (0,0x8040):
                        yield ((original[0]&~0xf00)|precision|(x87_rounding<<10),
                               (original[1]&~0xe040)|(sse_rounding<<13)|flush)

    def run_contexts(self,mode):
        p=self.probe;original=(p.fem_probe_x87(),p.fem_probe_mxcsr())
        try:
            for cw,mx in self.contexts(original):
                p.fem_probe_set_x87(cw);p.fem_probe_set_mxcsr(mx)
                result=self.boundary(mode,1.,2.**-54)
                after=(p.fem_probe_x87(),p.fem_probe_mxcsr())
                self.assertEqual(after,(cw,mx),'callee changed caller controls/status')
                self.assertEqual(result,1,f'mode={mode} x87={cw:x} mxcsr={mx:x}')
        finally:p.fem_probe_set_x87(original[0]);p.fem_probe_set_mxcsr(original[1])
        self.assertEqual((p.fem_probe_x87(),p.fem_probe_mxcsr()),original)

    def test_runtime_interval_encloses_small_addend(self):self.run_contexts(0)
    def test_exception_restores_caller(self):self.run_contexts(1)
    def test_early_return_restores_caller(self):self.run_contexts(2)
    def test_nested_boundary_restores_both_levels(self):self.run_contexts(3)

    def test_unscoped_runtime_counterexample_is_real(self):
        p=self.probe;fn=p.fem_probe_raw_interval;fn.argtypes=[ct.c_double,ct.c_double];fn.restype=ct.c_int
        saved=(p.fem_probe_x87(),p.fem_probe_mxcsr())
        try:
            p.fem_probe_set_mxcsr(saved[1]&~0xe040)
            p.fem_probe_set_x87((saved[0]&~0xf00)|0x200)
            low=fn(1.,2.**-54)
            p.fem_probe_set_x87((saved[0]&~0xf00)|0x300)
            extended=fn(1.,2.**-54)
        finally:p.fem_probe_set_x87(saved[0]);p.fem_probe_set_mxcsr(saved[1])
        self.assertEqual((low,extended),(0,1))

    def test_real_distance_guard_and_solver_preserve_caller_modes(self):
        D=ct.POINTER(ct.c_double);I=ct.POINTER(ct.c_int)
        distance=ct.CDLL(str(ROOT/'.tools/native/contact_distance.dll')).membrane_contact_distance
        distance.argtypes=[D,D,ct.c_double,D];distance.restype=ct.c_int
        guard=ct.CDLL(str(ROOT/'.tools/native/contact_guard.dll')).membrane_guard_motion
        guard.argtypes=[ct.c_int,D,D,ct.c_int,I,ct.c_int,I,D,ct.c_int,ct.c_double,D];guard.restype=ct.c_int
        solve=ct.CDLL(str(ROOT/'.tools/native/membrane_fem.dll')).membrane_fem_solve
        solve.argtypes=[ct.c_int,D,D,ct.c_int,I,D,D,ct.c_double,ct.c_double,ct.c_double,ct.c_int,ct.c_double,D];solve.restype=ct.c_int
        merit=ct.CDLL(str(ROOT/'.tools/native/contact_merit_probe.dll')).merit_contact_change
        merit.argtypes=[D,D,D,ct.c_double,ct.c_double,ct.c_double,D];merit.restype=ct.c_int
        triangle=(ct.c_double*9)(0.,0.,0.,1.,0.,0.,0.,0.,1.);segment=(ct.c_double*6)(.2,.3,.4,.2,.3,.4)
        broad=(ct.c_double*9)(-1.,0.,-1.,1.,0.,-1.,0.,0.,1.);ids=(ct.c_int*3)(0,1,2);kinds=(ct.c_int*1)(0)
        clear=(ct.c_double*41)(*([0.,.4,0.]*4+[.1]+[0.]*28))
        crossing=(ct.c_double*41)(*([0.,-.4,0.]*2+[0.,.4,0.]*2+[.1]+[0.]*28))
        inverse=(ct.c_double*3)(0.,4.,7.);basis=(ct.c_double*6)(-1.,1.,0.,-1.,0.,1.);areas=(ct.c_double*1)(.5);dt=1./60.
        lifted=(ct.c_double*9)(0.,.01,0.,1.,.01,0.,0.,.01,1.)
        def query(invalid=False):
            out=(ct.c_double*22)(*([123.]*22));code=distance(None if invalid else segment,triangle,.1,out)
            return code,bytes(out)
        def motion(cross=False):
            out=(ct.c_double*8)();code=guard(3,broad,broad,1,ids,1,kinds,crossing if cross else clear,128,1e-9,out)
            return code,bytes(out)
        def candidate(budget=100,invalid=False):
            x=(ct.c_double*9)(0.,0.,0.,1.06,.03,0.,0.,0.,1.);stats=(ct.c_double*8)()
            code=solve(0 if invalid else 3,x,inverse,1,ids,basis,areas,2.,3.,dt,budget,1e-8,stats)
            return code,bytes(x),bytes(stats)
        def change():
            bounds=(ct.c_double*2)();code=merit(triangle,lifted,segment,.1,100.,1.,bounds)
            return code,bytes(bounds)
        calls=[('distance',query,0),('invalid_distance',lambda:query(True),-1),('clear_guard',motion,0),
               ('crossing_guard',lambda:motion(True),1),('solver',candidate,0),
               ('budget',lambda:candidate(0),1),('invalid_solver',lambda:candidate(invalid=True),-1),('merit',change,0)]
        baseline={name:fn() for name,fn,_ in calls};p=self.probe;original=(p.fem_probe_x87(),p.fem_probe_mxcsr())
        low,high=(ct.c_double*2).from_buffer_copy(baseline['merit'][1])
        with localcontext() as decimal:
            decimal.prec=80;number=Decimal.from_float;r2=number(.1*.1)
            first=number(.3)**2/r2-1;last=(number(.3)-number(.01))**2/r2-1
            true_change=((100-last)**2-(100-first)**2)/2
            self.assertLessEqual(number(low),true_change);self.assertGreaterEqual(number(high),true_change)
        try:
            for cw,mx in self.contexts(original):
                for name,fn,status in calls:
                    p.fem_probe_set_x87(cw);p.fem_probe_set_mxcsr(mx)
                    result=fn();after=(p.fem_probe_x87(),p.fem_probe_mxcsr()&~0x3f)
                    p.fem_probe_set_x87(original[0]);p.fem_probe_set_mxcsr(original[1])
                    self.assertEqual(after,(cw,mx&~0x3f),name)
                    self.assertEqual(result[0],status,name);self.assertEqual(result,baseline[name],name)
        finally:p.fem_probe_set_x87(original[0]);p.fem_probe_set_mxcsr(original[1])


if __name__=='__main__':unittest.main()
