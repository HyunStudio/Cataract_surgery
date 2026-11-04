"""Replay a saved real engine request without redoing its surgical prefix."""
import ctypes as ct
from pathlib import Path
import numpy as np
from test_membrane_fem import D,I


def replay(request, library):
    lib = ct.CDLL(str(Path(library).resolve()))
    fn = lib.membrane_fem_solve_contact
    fn.argtypes = [ct.c_int,D,D,ct.c_int,I,D,D,ct.c_double,ct.c_double,ct.c_double,ct.c_int,
                   ct.c_double,ct.c_double,ct.c_double,ct.c_int,I,D,D,D,ct.c_int,I,D,ct.c_int,D,D,D]
    fn.restype = ct.c_int
    fields = {k:np.ascontiguousarray(v,dtype=np.int32 if k in ('nodes','grip_nodes','face_nodes') else np.float64)
              for k,v in request.items() if isinstance(v,list)}
    x = fields['xyz'].copy();stats = np.full(16,123.)
    reactions = np.full(len(fields['targets']),123.)
    dual = np.full((len(fields['face_nodes'])//3)*(len(fields['capsules'])//7),123.)
    d = lambda k:fields[k].ctypes.data_as(D)
    i = lambda k:fields[k].ctypes.data_as(I)
    status = fn(len(x)//3,x.ctypes.data_as(D),d('inverse'),len(fields['areas']),i('nodes'),d('gradients'),d('areas'),
                request['mu'],request['lambda'],request['dt'],request['budget'],request['force_tolerance'],request['gap_tolerance'],request['complementarity_tolerance'],
                len(fields['targets'])//3,i('grip_nodes'),d('grip_weights'),d('targets'),reactions.ctypes.data_as(D),
                len(fields['face_nodes'])//3,i('face_nodes'),d('face_weights'),len(fields['capsules'])//7,d('capsules'),dual.ctypes.data_as(D),stats.ctypes.data_as(D))
    return status,x,reactions,dual,stats
