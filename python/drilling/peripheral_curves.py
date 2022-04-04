from ..snap.t3mlite import Mcomplex
from ..snap.t3mlite import simplex, Tetrahedron

from collections import deque

def install_peripheral_curves(start_tet : Tetrahedron):
    _install_meridian(start_tet)
    _install_longitude(start_tet)

def _install_meridian(start_tet : Tetrahedron):
    tet = start_tet
    while True:
        for f in [ simplex.F2, simplex.F1, simplex.F2, simplex.F3 ]:
            tet.PeripheralCurves[0][tet.orientation][simplex.V0][f] = -1
            tet = tet.Neighbor[f]
            tet.PeripheralCurves[0][tet.orientation][simplex.V0][f] = +1
        if tet is start_tet:
            break

def _has_meridian(tet : Tetrahedron):
    for sheet in tet.PeripheralCurves[0]:
        for v in sheet[simplex.V0].values():
            if v != 0:
                return True
    return False

def _walk_tet_to_face(start_tet, tet_to_face):
    tet = start_tet
    while True:
        f = tet_to_face[tet]

        tet.PeripheralCurves[1][tet.orientation][simplex.V0][f] = -1
        tet = tet.Neighbor[f]
        tet.PeripheralCurves[1][tet.orientation][simplex.V0][f] = +1
        if tet is start_tet:
            break

def _install_longitude(start_tet : Tetrahedron):

    tet0 = start_tet.Neighbor[simplex.F1]
    tet1 = start_tet
    tet2 = start_tet.Neighbor[simplex.F2]
    tet3 = tet2.Neighbor[simplex.F3]

    if _has_meridian(tet0):
        raise Exception(
            "F1-neighbor of start_tet not expected to have meridian.")
    if not _has_meridian(tet1):
        raise Exception(
            "start_tet expected to have meridian.")
    if not _has_meridian(tet2):
        raise Exception(
            "F2-neighbor of start_tet expected to have meridian.")
    if _has_meridian(tet3):
        raise Exception(
            "F3-enighbor of F2-neighbor of start_tet not expected to have "
            "meridian.")

    visited_tet_to_face = { tet2 : simplex.F3,
                            tet1 : simplex.F2 }
    pending_tets = deque([( tet0,  simplex.F1)])
    while True:
        tet, entry_f = pending_tets.popleft()
        if tet in visited_tet_to_face:
            continue
        visited_tet_to_face[tet] = entry_f
        if tet is tet3:
            break
        for f in [ simplex.F1, simplex.F2, simplex.F3 ]:
            neighbor = tet.Neighbor[f]
            if f != entry_f and not _has_meridian(neighbor):
                pending_tets.append((neighbor, f))
                
    _walk_tet_to_face(start_tet, visited_tet_to_face)