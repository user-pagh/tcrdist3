import numpy as np
import pandas as pd
from scipy import sparse

__all__ = ['distance_ecdf',
           'make_ecdf_step']

def _todense(pw, maxd):
    """Make a pairwise distance matrix dense"""
    pw = np.asarray(pw.todense())
    pw[pw == 0] = maxd + 1
    pw[np.diag_indices_from(pw)] = 0
    return pw

def distance_ecdf(pwrect, thresholds=None, weights=None, pseudo_count=0, skip_diag=False):
    """Computes the empirical cumulative distribution function (ECDF) for
    each TCR in a set of target TCRs [rows of pwrect] as the proportion
    of reference TCRs [columns of pwrect] within a distance radius less
    than or equal to a threhold d_i, over a range of
    D = [d_1, d_2, ..., d_i]. The distances between pairs of TCRs in the
    target and reference set are contained in the elements of pwrect.

    Optionally, relative weights can be supplied for each reference TCR.
    These can be TCR counts or other weights andthe ECDF will still
    be a probability on [0, 1].

    Parameters
    ----------
    pwrect : np.ndarray or scipy.sparse.csr_matrix, (clone_df.shape[0], n_ref)
    thresholds : np.ndarray
        Vector of thresholds at which the ECDF should be evaluated.
        By default will use all unique values in pwrect.
    weights : np.ndarray or list, (clone_df.shape[0], )
        Relative weight of each TCR in the reference (column dimension of pwrect)
    pseudo_count : int
        Added to the numerator and denominator at each threshold
        to avoid zero. Useful if end goal is a log-scale plot.
    skip_diag : bool
        Skip counting the diagonal for computing ECDF of seqs against same seqs.

    Returns
    -------
    thresholds : vector, thresholds.shape[0]
    ecdf : vector, thresholds.shape[0]"""
    if weights is None:
        weights = np.ones(pwrect.shape[1])
    else:
        weights = np.asarray(weights)

    if thresholds is None:
        if sparse.issparse(pwrect):
            thresholds = np.unique(pwrect.data)
        else:
            thresholds = np.unique(pwrect[:])
    else:
        thresholds = np.asarray(thresholds)

    """Vectorized and faster, using broadcasting for the <= expression"""
    """ecdf = np.sum((pwrect[:, :, None] <= thresholds[None, None, :]) * \
            weights[None, :, None], axis=1) / np.sum(weights)"""
    
    """Decided not to vectorize in 3D because it can create an array that's
    too big for memory"""
    ecdf = np.zeros((pwrect.shape[0], thresholds.shape[0]))
    sum_weights = np.sum(weights)
    for i in range(pwrect.shape[0]):
        if sparse.issparse(pwrect):
            row = pwrect[i, :]
            numer = np.sum((row.data[:, None] <= thresholds[None, :]) * weights[row.indices, None], axis=0)
        else:
            row = np.reshape(pwrect[i, :], (pwrect.shape[1], 1))
            numer = np.sum((row <= thresholds[None, :]) * weights[:, None], axis=0)
        denom = sum_weights
        if skip_diag:
            numer = numer - weights[i]
            denom = denom - weights[i]
        ecdf[i, :] = (numer + pseudo_count) / (denom + pseudo_count)
    return thresholds, ecdf

def make_ecdf_step(thresholds, ecdf, add_mnx=False, add_mny=False, add_mnmn=False, enforce_mn=False, mn=(0, 0), xjitter=0):
    """Create stepped vector for plotting an ECDF,
    since the ECDF should naturally have discrete steps
    but will not unless they are explictly added prior
    to plotting.

    Takes outputs from distance_ecdf function, but
    is general for creating stepped vectors for plotting.

    Parameters
    ----------
    thresholds : np.ndarray [n_thresholds, ]
        Vector of thresholds
        (typically the x-axis of the plot)
    ecdf : np.ndarray [n_thresholds, ]
        Vector of increasing probabilities
        (typically the y-axis of the plot)
    add_mnmn : bool
        Will add a step to (x=mn[0], y=mn[1]) to complete
        the ECDF.

    Returns
    -------
    x, y : np.ndarray
        Vectors for plotting"""
    y = np.asarray(ecdf)
    t = np.asarray(thresholds)

    if enforce_mn:
        t[t<mn[0]] = mn[0]
        y[y<mn[1]] = mn[1]

    if add_mnx:
        t = np.concatenate(([mn[0]], t.ravel()))
        y = np.concatenate(([y[0]], y.ravel()))
    if add_mny:
        t = np.concatenate(([t[0]], t.ravel()))
        y = np.concatenate(([mn[1]], y.ravel()))

    if add_mnmn:
        t = np.concatenate(([mn[0]], t.ravel()))
        y = np.concatenate(([mn[1]], y.ravel()))

    t = np.concatenate(([t[0]], np.repeat(t[1:].ravel(), 2)))
    y = np.repeat(y.ravel(), 2)[:-1]

    jx = t + (np.random.rand(1) - 0.5) * xjitter
    jx[0] = t[0]
    jx[-1] = t[-1]
    return jx, y

def gmean10(vec, axis=0):
    """Geometric mean which may be useful for
    summarizing many ECDF functions"""
    return 10 ** (np.mean(np.log10(vec), axis=axis))