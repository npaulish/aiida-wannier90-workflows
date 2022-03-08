# -*- coding: utf-8 -*-
"""Functions for processing kpoints."""
import typing as ty
import numpy as np

from aiida import orm


def get_explicit_kpoints(kmesh: orm.KpointsData) -> orm.KpointsData:
    """Work just like `kmesh.pl` of Wannier90.

    :param kmesh: contains a N1 * N2 * N3 mesh
    :type kmesh: aiida.orm.KpointsData
    :raises AttributeError: if kmesh does not contains a mesh
    :return: an explicit list of kpoints
    :rtype: aiida.orm.KpointsData
    """
    try:  # test if it is a mesh
        results = kmesh.get_kpoints_mesh()
    except AttributeError as exc:
        raise ValueError('input does not contain a mesh!') from exc
    else:
        # currently offset is ignored
        mesh = results[0]

        # following is similar to wannier90/kmesh.pl
        totpts = np.prod(mesh)
        weights = np.ones([totpts]) / totpts

        kpoints = np.zeros([totpts, 3])
        ind = 0
        for x in range(mesh[0]):
            for y in range(mesh[1]):
                for z in range(mesh[2]):
                    kpoints[ind, :] = [x / mesh[0], y / mesh[1], z / mesh[2]]
                    ind += 1
        klist = orm.KpointsData()
        klist.set_kpoints(kpoints=kpoints, cartesian=False, weights=weights)
        return klist


def create_kpoints_from_distance(structure: orm.StructureData, distance: ty.Union[float, orm.Float]) -> orm.KpointsData:
    """Create KpointsData from a given distance.

    :param structure: [description]
    :type structure: [type]
    :param distance: [description]
    :type distance: [type]
    :return: [description]
    :rtype: [type]
    """
    kpoints = orm.KpointsData()
    kpoints.set_cell_from_structure(structure)
    if isinstance(distance, orm.Float):
        distance = distance.value
    kpoints.set_kpoints_mesh_from_density(distance, force_parity=False)

    return kpoints


def get_explicit_kpoints_from_distance(
    structure: orm.StructureData, distance: ty.Union[float, orm.Float]
) -> orm.KpointsData:
    """Create an explicit list of kpoints with a given distance.

    :param structure: [description]
    :type structure: [type]
    :param distance: [description]
    :type distance: [type]
    :return: [description]
    :rtype: [type]
    """
    kpoints = create_kpoints_from_distance(structure, distance)
    kpoints = get_explicit_kpoints(kpoints)

    return kpoints


def cartesian_product(*arrays: np.array) -> np.array:
    """Cartesian product.

    :return: _description_
    :rtype: np.array
    """
    la = len(arrays)  # pylint: disable=invalid-name
    dtype = np.result_type(*arrays)
    arr = np.empty([len(a) for a in arrays] + [la], dtype=dtype)
    for i, a in enumerate(np.ix_(*arrays)):  # pylint: disable=invalid-name
        arr[..., i] = a
    return arr.reshape(-1, la)


def get_mesh_from_kpoints(kpoints: orm.KpointsData) -> ty.List:
    """From .

    :param kpoints: contains a N1 * N2 * N3 mesh
    :type kpoints: aiida.orm.KpointsData
    :raises AttributeError: if kmesh does not contains a mesh
    :return: an explicit list of kpoints
    :rtype: aiida.orm.KpointsData
    """
    try:  # test if it is a mesh
        mesh, _ = kpoints.get_kpoints_mesh()
    except AttributeError:
        klist = kpoints.get_kpoints(also_weights=False, cartesian=False)
        mesh = [0, 0, 0]
        kmin = [0, 0, 0]
        kmax = [0, 0, 0]
        # 3 directions
        for i in range(3):
            uniq_kpt = np.sort((np.unique(klist[:, i])))
            kmin[i] = uniq_kpt[0]
            kmax[i] = uniq_kpt[-1]
            mesh[i] = len(uniq_kpt)

        klist_recovered = cartesian_product(*[np.linspace(kmin[_], kmax[_], mesh[_]) for _ in range(3)])
        if not np.allclose(klist, klist_recovered):
            raise ValueError(f'Cannot convert kpoints {kpoints} to a mesh')  # pylint: disable=raise-missing-from

    return mesh


def get_path_from_kpoints(kpoints: orm.KpointsData) -> orm.Dict:
    """Translate bands kpoints path objects.

    From the input `bands_kpoints` (a KpointsData object) of PwBandsWorkChain,
    to the input `kpoint_path` (a Dict object) of Wannier90Calculation.

    :param kpoints: the input KpointsData must contain `labels`.
    :type kpoints: orm.KpointsData
    :return: the returned Dict object contains two keys: `path` and `point_coords`.
    :rtype: orm.Dict
    """
    assert kpoints.labels is not None, '`kpoints` must have `labels`'
    assert len(kpoints.labels) >= 2

    # default in crystal coordinates
    explicit_kpoints = kpoints.get_kpoints()

    # [('GAMMA', 'X'),
    # ('X', 'U'),
    # ('K', 'GAMMA'),
    # ('GAMMA', 'L'),
    # ('L', 'W'),
    # ('W', 'X')]
    path = []
    # {'GAMMA': [0.0, 0.0, 0.0],
    # 'X': [0.5, 0.0, 0.5],
    # 'L': [0.5, 0.5, 0.5],
    # 'W': [0.5, 0.25, 0.75],
    # 'W_2': [0.75, 0.25, 0.5],
    # 'K': [0.375, 0.375, 0.75],
    # 'U': [0.625, 0.25, 0.625]}
    point_coords = {}

    # [(0, 'GAMMA'),
    #  (43, 'X'),
    #  (57, 'U'),
    #  (58, 'K'),
    #  (103, 'GAMMA'),
    #  (140, 'L'),
    #  (170, 'W'),
    #  (191, 'X')]
    for idx, lab in kpoints.labels:
        point_coords[lab] = list(explicit_kpoints[idx])

    prev_idx, prev_lab = kpoints.labels[0]
    for idx, lab in kpoints.labels[1:]:
        segment = (prev_lab, lab)
        if idx != prev_idx + 1:
            path.append(segment)
        prev_idx = idx
        prev_lab = lab

    ret = {'path': path, 'point_coords': point_coords}
    return orm.Dict(dict=ret)
