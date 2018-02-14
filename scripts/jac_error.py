import os
import numpy as np
from load_error_files import print_error

rtol = 1e-6
atol = 1e-10


def update(err_dict, err, filename=None, **kwargs):
    for name in err:
        if ('amax' in name or 'value' in name) and name != 'jac_threshold_value':
            continue
        assert 'fdjac' not in filename
        if 'nvidia' in filename:
            from time import ctime
            print('Known driver issue:', filename, ctime(os.path.getmtime(filename)))
            continue
        # special handling for threshold
        if name == 'jac_threshold_value':
            sparse = 'sparse' if ('sparse' in filename) else 'dense'
            conp = 'conp' if ('conp' in filename) else 'conv'
            val = err[name]
            name += '_{}_{}'.format(sparse, conp)
            if name in err_dict:
                assert np.isclose(err_dict[name], np.asscalar(val))
            err_dict[name] = np.asscalar(val)
            continue
        err_dict[name] = np.maximum(err_dict[name], err[name])
        if name + '_mean' not in err_dict:
            err_dict[name + '_mean'] = (0., 0.)
        err_dict[name + '_mean'] = (err_dict[name + '_mean'][0] + err[name],
                                    err_dict[name + '_mean'][1] + 1)


def printer(err_dict):
    mean_thr = (0., 0.)
    for name in err_dict:
        if name.endswith('_mean'):
            err_dict[name] = err_dict[name][0] / err_dict[name][1]
        elif 'jac_threshold_value' in name:
            mean_thr = (mean_thr[0] + err_dict[name], mean_thr[1] + 1)
    # print mean threshold
    mean_thr = mean_thr[0] / mean_thr[1]

    print('\n'.join(
        ['{}: {:.15e}'.format(k, v) for k, v in err_dict.items()]))
    print('mean_threshold: {:.15e}'.format(mean_thr))


print_error('jac', update, printer)
