import os
import numpy as np
import yaml
import cantera as ct
from collections import defaultdict
from os.path import join, dirname, abspath, isdir, isfile

script_dir = dirname(abspath(__file__))
error_path = join(script_dir, 'error_checking')


def get_error_files(ftype):
    mechs = [join(error_path, x) for x in os.listdir(
        error_path) if os.path.isdir(join(error_path, x))]

    def __load_from_path(path):
        return [join(path, x) for x in os.listdir(path) if isfile(join(path, x))
                and x.endswith('.npz') and ftype in x]

    # get file list
    files = {}
    for mech in mechs:
        files[mech] = __load_from_path(mech)
        # check for subdirs
        for d in [join(mech, x) for x in os.listdir(mech) if isdir(join(mech, x))]:
            files[mech].extend(__load_from_path(d))

    return files


def add_rxn_specific_inds(mech_info, rxn_type, rxn_str, path):
    # load gas
    gas = ct.Solution(join(path, mech_info['mech']))
    # get fwd reaction indicies
    mech_info['rop_fwd_' + rxn_str] = np.array([i for i, r in enumerate(
        gas.reactions()) if not isinstance(r, rxn_type)])
    # get reversible indicies
    rev_rxns = [i for i, r in enumerate(gas.reactions()) if r.reversible]
    mech_info['rop_rev_' + rxn_str] = np.array([
        i for i, fi in enumerate(rev_rxns)
        if not isinstance(gas.reaction(fi), rxn_type)])


def get_platform(file):
    if 'nvidia' in file:
        return 'nvidia'
    elif 'portable' in file:
        return 'pocl'
    elif 'intel' in file:
        return 'intel'
    else:
        assert '_c_' in file
        return 'openmp'


def run_error_calcs(ftype, updater, per_platform=False):
    files = get_error_files(ftype)
    err_dicts = {}
    platforms = set()
    for mech in files:
        mech_name = os.path.basename(os.path.normpath(mech))
        err_dicts[mech_name] = defaultdict(lambda: 0)

        # get mech info
        mech_info = join(mech, mech_name + '.yaml')
        with open(mech_info, 'r') as file:
            mech_info = yaml.load(file.read())
            if mech_info['n_cheb']:
                add_rxn_specific_inds(mech_info, ct.ChebyshevReaction,
                                      'cheb_inds', mech)
            if mech_info['n_plog']:
                add_rxn_specific_inds(mech_info, ct.PlogReaction, 'plog_inds',
                                      mech)

        for file in files[mech]:
            if per_platform:
                platform = get_platform(file)
                platforms.add(platform)
                if platform not in err_dicts[mech_name]:
                    err_dicts[mech_name][platform] = defaultdict(lambda: 0)
                updater(err_dicts[mech_name][platform], np.load(file),
                        filename=file,
                        mech_info=mech_info)
                continue

            updater(err_dicts[mech_name], np.load(file), filename=file,
                    mech_info=mech_info)

    if per_platform:
        return platforms, err_dicts
    return err_dicts


def print_error(ftype, updater, printer, per_platform=False):
    err_dicts = run_error_calcs(ftype, updater, per_platform=per_platform)
    if per_platform:
        platforms, err_dicts = err_dicts
    mech_arr = ['H2', 'CH4', 'C2H4', 'IC5H11OH']
    for mech in mech_arr:
        print(mech)
        if per_platform:
            for platform in err_dicts[mech]:
                print(platform)
                printer(err_dicts[mech][platform])
            continue
        printer(err_dicts[mech])
