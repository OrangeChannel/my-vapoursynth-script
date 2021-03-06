"""TODO: One-line module synopsis <73 char ending in a ('.')."""
__all__ = ['stpresso', 'spresso', 'stpresso_mc', 'splicev1', 'fluxsmooth_tmc',
           'mvfrc', 'xs_usm']
__author__ = 'xyx98'
__date__ = '27 November 2019'
__credits__ = """Didée for the original stpresso, spresso, nonlin_usm functions.
SilaSurfer for original AviSynth fluxsmooth_tmc.
Bloax for inspiring sharpen_detail.
mawen1250's AviSynth textsub16 script for inspiring textsub.
mawen1250 for the original mwenhance.
Leak and RazorbladeByte for AviSynth's LazyDering.
HolyWu for original Overlay/InterFrame function.
Dave <orangechannel@pm.me> for refactoring code.
"""

import re
from functools import partial
from typing import Dict

import havsfunc as haf
import muvsfunc as muf
import mvsfunc as mvf
from vsutil import *


# TODO: typehints
def stpresso(clip: vs.VideoNode, limit=3, bias=24, rg_mode=4, tthr=12,
             tlimit=3, tbias=49, back=1) -> vs.VideoNode:
    """TODO: One-line synopsis (<73 char) ending in a '.'.

    The goal of stpresso (Spatio-Temporal Pressdown) is
    to "dampen the grain just a little, to keep the original look,
    and make it fast". In other words it makes a video more
    compressible without losing detail and original grain structure.

    stpresso is recommended for content up to 720p because
    "the spatial part might be a bit too narrow for 1080p encoding
    (since it's only a 3x3 kernel)".

    Differences from original:
    * high depth support
    * automatically adjust parameters to fit into different depth
    * you have less choice in rg_mode

    :param clip: input clip
        :bit depth: TODO
        :color family: TODO
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param limit: spatial limit: the spatial part won't change a
                  pixel more than this (Default value = 3)
    :param bias: percentage of the spatial filter that will apply
                 (Default value = 24)
    :param rg_mode: RemoveGrain mode to use (Default value = 4)
    :param tthr: temporal threshold for FluxSmooth
                 (Default value = 12)
        Can be set "a good bit bigger" than usual.
    :param tlimit: temporal filter won't change a pixel more than
                   this (Default value = 3)
    :param tbias: percentage of the temporal filter that will apply
                  (Default value = 49)
    :param back: after all changes have been calculated,
                 reduce all pixel changes by this value
                 (Default value = 1)
        Shift "back" towards original value.
    :return: processed clip
    """
    depth = clip.format.bits_per_sample

    lim1 = round(limit * 100.0 / bias - 1.0) if limit > 0 \
        else round(100.0 / bias)
    lim1 = scale(lim1, depth)

    lim2 = 1 if limit < 0 else limit
    lim2 = scale(lim2, depth)

    bk = scale(back, depth)

    tlim1 = round(tlimit * 100.0 / tbias - 1.0) if tlimit > 0 \
        else round(100.0 / tbias)
    tlim1 = scale(tlim1, depth)

    tlim2 = 1 if tlimit < 0 else tlimit
    tlim2 = scale(tlim2, depth)

    bzz = core.rgvs.RemoveGrain(clip, rg_mode)

    if limit < 0:
        expr = 'x y - abs ' + str(lim1) + ' < x x ' + str(scale(1, depth)) + \
               ' x y - x y - abs / * - ?'

        texpr = 'x y - abs ' + str(tlim1) + ' < x x ' + \
                str(scale(1, depth)) + ' x y - x y - abs / * - ?'
    else:
        expr = 'x y - abs ' + str(scale(1, depth)) + ' < x x ' + str(lim1) + \
               ' + y < x ' + str(lim2) + ' + x ' + str(lim1) + ' - y > x ' + \
               str(lim2) + ' - x ' + str(scale(100, depth)) + ' ' + \
               str(bias) + ' - * y ' + str(bias) + ' * + ' + \
               str(scale(100, depth)) + ' / ? ? ?'

        texpr = 'x y - abs ' + str(scale(1, depth)) + ' < x x ' + \
                str(tlim1) + ' + y < x ' + str(tlim2) + ' + x ' + \
                str(tlim1) + ' - y > x ' + str(tlim2) + ' - x ' + \
                str(scale(100, depth)) + ' ' + str(bias) + ' - * y ' + \
                str(bias) + ' * + ' + str(scale(100, depth)) + ' / ? ? ?'

    l = []  # TODO: rename ambiguous variables
    for i in range(3):
        c = core.std.ShufflePlanes(clip, i, colorfamily=vs.GRAY)
        b = core.std.ShufflePlanes(bzz, i, colorfamily=vs.GRAY)
        o = core.std.Expr([c, b], expr)
        l.append(o)

    if tthr:
        st = core.flux.SmoothT(bzz, temporal_threshold=tthr, planes=[0, 1, 2])
        diff = core.std.MakeDiff(bzz, st, [0, 1, 2])
        last = core.std.ShufflePlanes(l, [0, 0, 0], colorfamily=vs.YUV)
        diff2 = core.std.MakeDiff(last, diff, [0, 1, 2])
        for i in range(3):
            c = l[i]
            b = core.std.ShufflePlanes(diff2, i, colorfamily=vs.GRAY)
            l[i] = core.std.Expr([c, b], texpr)

    if back:
        bexpr = 'x ' + str(bk) + ' + y < x ' + str(bk) + ' + x ' + str(bk) + \
                ' - y > x ' + str(bk) + ' - y ? ?'
        y = core.std.ShufflePlanes(clip, 0, colorfamily=vs.GRAY)
        l[0] = core.std.Expr([l[0], y], bexpr)

    return core.std.ShufflePlanes(l, [0, 0, 0], colorfamily=vs.YUV)


# TODO: typehints
def spresso(clip: vs.VideoNode, limit=2, bias=25, rg_mode=4, limit_c=4,
            bias_c=50, rg_mode_c=0) -> vs.VideoNode:
    """TODO: One-line synopsis (<73 char) ending in a '.'.

    spresso (Spatial Pressdown) is a purely spatial script designed to
    achieve better compressibility without doing too much harm to the
    original detail.

    spresso was not designed for 1080p processing/encoding; due to its
    3x3 kernel it works better on standard definition (SD) content like
    DVDs and possibly on 720p.

    On noisy DVD/SD sources, compression gain usually is from 2% to 3%
    (light settings -> changes almost invisible) up to 10 to 12%
    (stronger settings -> slight, gentle softening, not very obvious).

    Differences from original:
    * high depth support
    * automatically adjust parameters to fit into different depth
    * you have less choice in rg_mode

    :param clip: input clip
        :bit depth: TODO
        :color family: TODO
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param limit: limit the maximum change for any given pixel
                  (Default value = 2)
    :param bias: something like "aggessivity" (Default value = 25)
        '20' is a very light setting, '33' is already quite strong.
    :param rg_mode: RemoveGrain mode for the luma (Y) channel
                    (Default value = 4)
        The default of "4" is the best in most cases.
        Mode 19 and 20 might work better in other cases.
        If set to 0, luma will be copied from the input clip.
    :param limit_c: same as limit but for chroma (Default value = 4)
    :param bias_c: same as bias but for chroma (Default value = 50)
    :param rg_mode_c: RemoveGrain mode for the chroma channels
                      (Default value = 0)
        By default the chroma is simply copied from the input clip.
        To process chroma, set rg_mode_c=4
        (or 19, 20, or any other compatible mode).
    :return: processed clip
    """
    depth = clip.format.bits_per_sample

    lim1 = round(limit * 100.0 / bias - 1.0) if limit > 0 \
        else round(100.0 / bias)
    lim1 = scale(lim1, depth)

    lim2 = 1 if limit < 0 else limit
    lim2 = scale(lim2, depth)

    lim1c = round(limit_c * 100.0 / bias_c - 1.0) if limit > 0 \
        else round(100.0 / bias_c)
    lim1c = scale(lim1c, depth)

    lim2c = 1 if limit < 0 else limit
    lim2c = scale(lim2c, depth)

    if limit < 0:
        expr = 'x y - abs ' + str(lim1) + ' < x x ' + str(scale(1, depth)) + \
               ' x y - x y - abs / * - ?'
    else:
        expr = 'x y - abs ' + str(scale(0, depth)) + ' <= x x ' + str(lim1) + \
               ' + y < x ' + str(lim2) + ' + x ' + str(lim1) + ' - y > x ' + \
               str(lim2) + ' - x ' + str(scale(100, depth)) + ' ' + \
               str(bias) + ' - * y ' + str(bias) + ' * + ' + \
               str(scale(100, depth)) + ' / ? ? ?'

    if limit_c < 0:
        expr_c = 'x y - abs ' + str(lim1c) + ' < x x ' + \
                 str(scale(1, depth)) + ' x y - x y - abs / * - ?'
    else:
        expr_c = 'x y - abs ' + str(scale(0, depth)) + ' <= x x ' + \
                 str(lim1c) + ' + y < x ' + str(lim2c) + ' + x ' + \
                 str(lim1c) + ' - y > x ' + str(lim2c) + ' - x ' + \
                 str(scale(100, depth)) + ' ' + str(bias_c) + ' - * y ' + \
                 str(bias_c) + ' * + ' + str(scale(100, depth)) + ' / ? ? ?'

    rg = core.rgvs.RemoveGrain(clip, [rg_mode, rg_mode_c])

    y = core.std.Expr([plane(clip, 0), plane(rg, 0)], expr)
    u = plane(clip, 1) if rg_mode_c == 0 \
        else core.std.Expr([plane(clip, 1), plane(rg, 1)], expr_c)
    v = plane(clip, 2) if rg_mode_c == 0 \
        else core.std.Expr([plane(clip, 2), plane(rg, 2)], expr_c)

    return core.std.ShufflePlanes([y, u, v], [0, 0, 0], colorfamily=vs.YUV)


# TODO: typehints
def stpresso_mc(clip: vs.VideoNode, limit=3, bias=24, rg_mode=4, tthr=12,
                tlimit=3, tbias=49, back=1, s_p: Dict = None, a_p: Dict = None,
                c_p: Dict = None) -> vs.VideoNode:
    """TODO: One-line synopsis (<73 char) ending in a '.'.

    :param clip: input clip
        :bit depth: TODO
        :color family: TODO
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param limit: TODO: explain (Default value = 3)
    :param bias: TODO: explain (Default value = 24)
    :param rg_mode: TODO: explain (Default value = 4)
    :param tthr: TODO: explain (Default value = 12)
    :param tlimit: TODO: explain (Default value = 3)
    :param tbias: TODO: explain (Default value = 49)
    :param back: TODO: explain (Default value = 1)
    :param s_p: TODO: explain (Default value = {})
    :param a_p: TODO: explain (Default value = {})
    :param c_p: TODO: explain (Default value = {})
    :return: processed clip
    """
    s_p = {} if not s_p else s_p
    a_p = {} if not a_p else a_p
    c_p = {} if not c_p else c_p

    depth = clip.format.bits_per_sample

    lim1 = round(limit * 100.0 / bias - 1.0) if limit > 0 \
        else round(100.0 / bias)
    lim1 = scale(lim1, depth)

    lim2 = 1 if limit < 0 else limit
    lim2 = scale(lim2, depth)

    bk = scale(back, depth)

    tlim1 = round(tlimit * 100.0 / tbias - 1.0) if tlimit > 0 \
        else round(100.0 / tbias)
    tlim1 = scale(tlim1, depth)

    tlim2 = 1 if tlimit < 0 else tlimit
    tlim2 = scale(tlim2, depth)

    bzz = core.rgvs.RemoveGrain(clip, rg_mode)

    if limit < 0:
        expr = 'x y - abs ' + str(lim1) + ' < x x ' + str(scale(1, depth)) + \
               ' x y - x y - abs / * - ?'

        texpr = 'x y - abs ' + str(tlim1) + ' < x x ' + \
                str(scale(1, depth)) + ' x y - x y - abs / * - ?'
    else:
        expr = 'x y - abs ' + str(scale(1, depth)) + ' < x x ' + str(lim1) + \
               ' + y < x ' + str(lim2) + ' + x ' + str(lim1) + ' - y > x ' + \
               str(lim2) + ' - x ' + str(scale(100, depth)) + ' ' + \
               str(bias) + ' - * y ' + str(bias) + ' * + ' + \
               str(scale(100, depth)) + ' / ? ? ?'

        texpr = 'x y - abs ' + str(scale(1, depth)) + ' < x x ' + \
                str(tlim1) + ' + y < x ' + str(tlim2) + ' + x ' + \
                str(tlim1) + ' - y > x ' + str(tlim2) + ' - x ' + \
                str(scale(100, depth)) + ' ' + str(bias) + ' - * y ' + \
                str(bias) + ' * + ' + str(scale(100, depth)) + ' / ? ? ?'

    l = []  # TODO: rename ambiguous variables
    for i in range(3):
        c = core.std.ShufflePlanes(clip, i, colorfamily=vs.GRAY)
        b = core.std.ShufflePlanes(bzz, i, colorfamily=vs.GRAY)
        o = core.std.Expr([c, b], expr)
        l.append(o)

    if tthr:
        st = fluxsmooth_tmc(bzz, tthr, s_p, a_p, c_p, [0, 1, 2])
        diff = core.std.MakeDiff(bzz, st, [0, 1, 2])
        last = core.std.ShufflePlanes(l, [0, 0, 0], colorfamily=vs.YUV)
        diff2 = core.std.MakeDiff(last, diff, [0, 1, 2])
        for i in range(3):
            c = l[i]
            b = core.std.ShufflePlanes(diff2, i, colorfamily=vs.GRAY)
            l[i] = core.std.Expr([c, b], texpr)

    if back:
        bexpr = 'x ' + str(bk) + ' + y < x ' + str(bk) + ' + x ' + str(bk) + \
                ' - y > x ' + str(bk) + ' - y ? ?'
        y = core.std.ShufflePlanes(clip, 0, colorfamily=vs.GRAY)
        l[0] = core.std.Expr([l[0], y], bexpr)

    return core.std.ShufflePlanes(l, [0, 0, 0], colorfamily=vs.YUV)


def splicev1(clip: List[vs.VideoNode], num: List[int] = None,
             den: List[int] = None, tc_out: str = "tc v1.txt"):
    """Splices clips with different fps and output timecodes v1.

    :param clip: input clips
        :bit depth: TODO
        :color family: TODO
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param num: clips' fps numerators
    :param den: clips' fps denominators
    :param tc_out: outfile.txt
    :return: TODO
    """
    num = [] if not num else num
    den = [] if not den else den

    clip_len = len(clip)
    num_len = len(num)
    den_len = len(den)

    if clip_len > num_len:
        for i in range(num_len, clip_len):
            num.append(None)

    if clip_len > den_len:
        for i in range(den_len, clip_len):
            den.append(None)

    for i in range(clip_len):
        if num[i] is None:
            num[i] = clip[i].fps_num
            den[i] = clip[i].fps_den
        elif den[i] is None:
            if num[i] > 10000:
                den[i] = 1001
            else:
                den[i] = 1

    fps = []
    for i in range(clip_len):
        fps.append(float(num[i]) / den[i])

    fnum = [i.num_frames for i in clip]
    for i in range(1, clip_len):
        fnum[i] += fnum[i - 1]

    tc = open(tc_out, 'w')
    tc.write('# timecode format v1\nassume ' + str(fps[0]) + '\n')
    for i in range(1, clip_len):
        tc.write(str(fnum[i - 1]) + ',' + str(fnum[i] - 1) + ',' +
                 str(fps[i]) + '\n')
    tc.close()

    last = clip[0]
    for i in range(1, clip_len):
        last += clip[i]

    return core.std.AssumeFPS(last, fpsnum=num[0], fpsden=den[0])


# TODO: typehints
def fluxsmooth_tmc(src: vs.VideoNode, tthr=12, s_p: Dict = None,
                   a_p: Dict = None, c_p: Dict = None,
                   planes: List[int] = None) -> vs.VideoNode:
    """TODO: One-line synopsis (<73 char) ending in a '.'.

    port from https://forum.doom9.org/showthread.php?s=d58237a359f5b1f2ea45591cceea5133&p=1572664#post1572664

    :param src: input clip
        :bit depth: TODO
        :color family: TODO
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param tthr: TODO: explain (Default value = 12)
    :param s_p: TODO: explain (Default value = None)
    :param a_p: TODO: explain (Default value = None)
    :param c_p: TODO: explain (Default value = None)
    :param planes: TODO: explain (Default value = None)
    :return: processed clip
    """
    s_p = {} if not s_p else s_p
    a_p = {} if not a_p else a_p
    c_p = {} if not c_p else c_p

    planes = [0, 1, 2] if not planes else planes

    super_p = {'pel':   2,
               'sharp': 1,
               }
    analyse_p = {'truemotion': False,
                 'delta':      1,
                 'blksize':    16,
                 'overlap':    8,
                 }

    s = {**super_p, **s_p}
    a = {**analyse_p, **a_p}

    sup = core.mv.Super(src, **s)

    bv = core.mv.Analyse(sup, isb=True, **a)
    fv = core.mv.Analyse(sup, isb=False, **a)
    bc = core.mv.Compensate(src, sup, bv, **c_p)
    fc = core.mv.Compensate(src, sup, fv, **c_p)

    il = core.std.Interleave([fc, src, bc])

    fs = core.flux.SmoothT(il, temporal_threshold=tthr, planes=planes)

    return core.std.SelectEvery(fs, 3, 1)


# TODO: typehints
def mvfrc(clip: vs.VideoNode, it=140, scp=15, num: int = 60000,
          den: int = 1001, preset: str = 'fast', pel=2, block: bool = True,
          flow_mask=None, block_mode=None, blksize=8, blksizev=8, search=None,
          truemotion: bool = True, searchparam=2, overlap=0, dct=0,
          blend: bool = True, bad_sad=10000, badrange=24, divide=0, mblur=15) \
        -> vs.VideoNode:
    """Changes fps by mvtools with motion interpolation.

    :param clip: input clip
        :bit depth: TODO
        :color family: TODO
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param it: TODO: explain (Default value = 140)
    :param scp: TODO: explain (Default value = 15)
    :param num: TODO: explain (Default value = 60000)
    :param den: TODO: explain (Default value = 1001)
    :param preset: TODO: explain (Default value = 'fast')
    :param pel: TODO: explain (Default value = 2)
    :param block: TODO: explain (Default value = True)
    :param flow_mask: TODO: explain (Default value = None)
    :param block_mode: TODO: explain (Default value = None)
    :param blksize: TODO: explain (Default value = 8)
    :param blksizev: TODO: explain (Default value = 8)
    :param search: TODO: explain (Default value = None)
    :param truemotion: TODO: explain (Default value = True)
    :param searchparam: TODO: explain (Default value = 2)
    :param overlap: TODO: explain (Default value = 0)
    :param dct: TODO: explain (Default value = 0)
    :param blend: TODO: explain (Default value = True)
    :param bad_sad: TODO: explain (Default value = 10000)
    :param badrange: TODO: explain (Default value = 24)
    :param divide: TODO: explain (Default value = 0)
    :param mblur: TODO: explain (Default value = 15)
    :return: processed clip
    """
    if not isinstance(clip, vs.VideoNode):
        raise TypeError('mvfrc: This is not a clip!')

    if preset == 'fast':
        pnum = 0
    elif preset == 'medium':
        pnum = 1
    elif preset == 'slow':
        pnum = 2
    else:
        raise TypeError('mvfrc: preset should be fast, medium, or slow')

    if search is None:
        search = [0, 3, 3][pnum]
    if block_mode is None:
        block_mode = [0, 0, 3][pnum]
    if flow_mask is None:
        flow_mask = [0, 0, 2][pnum]

    anal_params = {
        'overlap':     overlap,
        'overlapv':    overlap,
        'search':      search,
        'dct':         dct,
        'truemotion':  truemotion,
        'blksize':     blksize,
        'blksizev':    blksizev,
        'searchparam': searchparam,
        'badsad':      bad_sad,
        'badrange':    badrange,
        'divide':      divide
    }

    bofp = {  # block or flow params
        'thscd1': it,
        'thscd2': int(scp * 255 / 100),
        'blend':  blend,
        'num':    num,
        'den':    den
    }

    sup = core.mv.Super(clip, pel=pel, sharp=2, rfilter=4)
    bvec = core.mv.Analyse(sup, isb=True, **anal_params)
    fvec = core.mv.Analyse(sup, isb=False, **anal_params)

    if clip.fps_num / clip.fps_den > num / den:
        clip = core.mv.FlowBlur(clip, sup, bvec, fvec, blur=mblur)

    if block:
        clip = core.mv.BlockFPS(clip, sup, bvec, fvec, **bofp, mode=block_mode)
    else:
        clip = core.mv.FlowFPS(clip, sup, bvec, fvec, **bofp, mask=flow_mask)

    return clip


# TODO: typehints
def xs_usm(src: vs.VideoNode = None,
           blur: Union[int, List[int], vs.VideoNode] = 11, limit=1, elast=4,
           maskclip: vs.VideoNode = None, planes: List[int] = None) \
        -> vs.VideoNode:
    """xyx98's simple unsharp mask.

    :param src: input clip
        :bit depth: TODO
        :color family: TODO
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param blur: way to get blurclip default means RemoveGrain(mode=11)
                 (Default value = 11)
        you can also use a list like [1,2,1,2,4,2,1,2,1],
        means Convolution(matrix=[1,2,1,2,4,2,1,2,1])
        or you can input a blur clip made by yourself
    :param limit: way to limit the sharp resault (Default value = 1)
        =0 no limit
        >0 use limitfilter thr=limit
        <0 use repair(mode=-limit)
    :param elast: elast in LimitFilter, only for limit>0
                  (Default value = 4)
    :param maskclip: you can input your own mask to merge result and
                     source if needed (Default value = None)
    :param planes: setting which plane or planes to be processed;
                   defaults to [0] which means only process Y plane
                   (Default value = None)
    :return
    """
    planes = [0] if not planes else planes
    is_gray = src.format.color_family == vs.GRAY

    def _usm(clip=None, blur_=11, limit_=1, elast_=4, maskclip_=None):
        if isinstance(blur_, int):
            blurclip = core.rgvs.RemoveGrain(clip, blur_)
        elif isinstance(blur_, list):
            blurclip = core.std.Convolution(clip, matrix=blur_, planes=0)
        else:
            blurclip = blur_
        diff = core.std.MakeDiff(clip, blurclip, planes=0)
        sharp = core.std.MergeDiff(clip, diff, planes=0)

        if limit_ == 0:
            lt = sharp
        elif limit_ > 0:
            lt = mvf.LimitFilter(sharp, clip, thr=limit_, elast=elast_)
        else:
            lt = core.rgvs.Repair(sharp, clip, -limit_)

        if isinstance(maskclip_, vs.VideoNode):
            return core.std.MaskedMerge(lt, clip, maskclip_, planes=0)
        else:
            return lt

    if is_gray:
        return _usm(src, blur, limit, elast, maskclip)

    li = []
    for i in range(3):
        if i in planes:
            a = _usm(plane(src, i), blur, limit, elast,
                     None if not maskclip else plane(maskclip, i))
        else:
            a = plane(src, i)
        li.append(a)

    return core.std.ShufflePlanes(li, [0, 0, 0], vs.YUV)


# TODO: typehints
def sharpen_detail(src: vs.VideoNode, limit=4, thr=32) -> vs.VideoNode:
    """TODO: One-line synopsis (<73 char) ending in a '.'.

    ideas comes from : https://forum.doom9.org/showthread.php?t=163598
    but it's not a port, because their is no asharp in VapourSynth,
    so I adjust sharpener

    :param src: input clip
        :bit depth: TODO
        :color family: YUV, GRAY
        :float precision: TODO
        :sample type: TODO
        :subsampling: TODO
    :param limit:
    :param thr:
    :return: processed clip
    """
    c_format = src.format.color_family
    depth = src.format.bits_per_sample

    if c_format == vs.YUV:
        clip = plane(src, 0)
    elif c_format == vs.GRAY:
        clip = src
    else:
        raise TypeError('sharpen_detail: only supports YUV/GRAY clips')

    thr = thr * depth / 8
    bia = 128 * depth / 8
    blur = core.rgvs.RemoveGrain(clip, 19)

    mask = core.std.Expr([clip, blur], 'x y - ' + str(thr) + ' * ' +
                         str(bia) + ' +')
    mask = core.rgvs.RemoveGrain(mask, 2)
    mask = inpand(mask, mode='both')
    mask = core.std.Deflate(mask)

    sharp = xs_usm(clip, blur=[1] * 25, limit=limit)
    last = core.std.MaskedMerge(sharp, clip, mask, planes=0)

    if c_format == vs.YUV:
        return core.std.ShufflePlanes([last, src], [0, 1, 2], vs.YUV)

    return last


# TODO: typehints
def textsub(clip: vs.VideoNode, file, charset=None, fps=None, vfr=None,
            mod: bool = False, matrix: str = None) -> vs.VideoNode:
    """It's a port from avs script—textsub16 by mawen1250.

    Can support high bit and yuv444&yuv422,but not rgb
    Not recommended for yuv420p8
    ,but have some differences
    ---------------------------
    input,file,charset,fps,vfr: same in vsfilter

    :param clip: input clip
        :bit depth: 8, 9, 10, 12, 14, 16
        :color family: YUV
        :float precision: TODO
        :sample type: TODO
        :subsampling: 420, 422, 444
    :param file: TODO: explain
    :param charset: TODO: explain (Default value = None)
    :param fps: TODO: explain (Default value = None)
    :param vfr: TODO: explain (Default value = None)
    :param mod: chooses whether to use vsfiler (F) or vsfiltermod (T)
                (Default value = False)
    :param matrix: TODO: explain (Default value = None)
    :return: processed clip
    """
    def _m(a, b):
        if a <= 1024 and b <= 576:
            return '601'
        elif a <= 2048 and b <= 1536:
            return '709'
        else:
            return '2020'

    width = clip.width
    height = clip.height
    bit = clip.format.bits_per_sample
    u = core.std.ShufflePlanes(clip, 1, colorfamily=vs.GRAY)
    c_w = u.width
    c_h = u.height
    w = width / c_w
    h = height / c_h

    if w == 1 and h == 1:
        f = vs.YUV444P16
        s = 0
    elif w == 2 and h == 1:
        f = vs.YUV422P16
        s = 0.5
    elif w == 2 and h == 2:
        f = vs.YUV420P16
        s = 0.25
    else:
        TypeError('textsub16: Only supports YUV420 YUV422 YUV444')

    if not matrix:
        matrix = _m(width, height)

    def _vsmode(clip_, file_, charset_, fps_, vfr_, mod_):
        if not mod_:
            last_ = core.vsf.TextSub(clip_, file_, charset_, fps_, vfr_)
        else:
            last_ = core.vsfm.TextSubMod(clip_, file_, charset_, fps_, vfr_)

        return core.std.Cache(last_, make_linear=True)

    def _mske(a, b, depth):
        expr = 'x y - abs 1 < 0 255 ?'
        last_ = core.std.Expr([a, b], [expr] * 3)

        return core.fmtc.bitdepth(last_, bits=depth)

    src8 = core.resize.Bilinear(clip, format=vs.YUV420P8)
    sub8 = _vsmode(src8, file, charset, fps, vfr, mod)

    mask = _mske(src8, sub8, bit)

    mask_y = core.std.ShufflePlanes(mask, 0, colorfamily=vs.GRAY)
    mask_u = core.std.ShufflePlanes(mask, 1, colorfamily=vs.GRAY)
    mask_u = core.resize.Bilinear(mask_u, width, height, src_left=s)
    mask_v = core.std.ShufflePlanes(mask, 2, colorfamily=vs.GRAY)
    mask_v = core.resize.Bilinear(mask_v, width, height, src_left=s)

    mask = mvf.Max(mvf.Max(mask_y, mask_u), mask_v)
    mask = core.std.Inflate(mask)

    mask_c = core.resize.Bilinear(mask, c_w, c_h, src_left=-s)
    # TODO: src_width=c_w, src_height=c_h ???

    if w == 1 and h == 1:
        mask = core.std.ShufflePlanes(mask, [0, 0, 0], colorfamily=vs.YUV)
    else:
        mask = core.std.ShufflePlanes([mask, mask_c], [0, 0, 0],
                                      colorfamily=vs.YUV)

    rgb = core.resize.Bilinear(clip, format=vs.RGB24, matrix_in_s=matrix)

    sub = _vsmode(rgb, file, charset, fps, vfr, mod)
    sub = core.resize.Bilinear(sub, format=f, matrix_s=matrix)
    sub = mvf.Depth(sub, depth=bit)

    return core.std.MaskedMerge(clip, sub, mask=mask, planes=[0, 1, 2])

def LazyDering(src,depth=32,diff=8,thr=32):
    """
    LazyDering
    -----------------------------
    port from avs script by Leak&RazorbladeByte
    LazyDering tries to clean up slight ringing around edges by applying aWarpSharp2 only to areas where the difference is small enough so detail isn't destroyed.
    LazyDering it's a modified version of aWarpSharpDering.
    """
    bit = src.format.bits_per_sample
    Y = getplane(src,0)
    sharped = core.warp.AWarpSharp2(Y,depth=depth)
    diff_mask =  core.std.Expr([Y,sharped], "x y - x y > *").std.Levels(0,scale(diff,bit),0.5,scale(255,bit),0)
    luma_mask = core.std.Deflate(Y).std.Levels(scale(16,bit),scale(16+thr,bit),0.5,0,scale(255,bit))
    masks = core.std.Expr([luma_mask,diff_mask], "x y * {} /".format(scale(255,bit))).std.Deflate()
    merge = core.std.MaskedMerge(Y,sharped, mask=masks)
    return core.std.ShufflePlanes([merge,src],[0,1,2], colorfamily=vs.YUV)

def SADring(src,ring_r=2,warp_arg={},warpclip=None,edge_r=2,show_mode=0):
    """
    Simple Awarpsharp2 Dering
    ---------------------------------------
    ring_r: (int)range of ring,higher means more area around edge be set as ring in ringmask,deflaut is 2.Sugest use the smallest value which can dering well
    warp_arg: (dict)set your own args for AWarpSharp2,should be dict. e.g.
    warpclip: (clip)aim to allow you input a own warped clip instead internal warped clip,but I think a rightly blurred clip may also useful
    edge_r: (int)if the non-ring area between nearly edge can't be preserved well,try increase it's value
    show_mode:  0 :output the result 1: edgemask 2: ringmask 3: warped clip
    """
    arg={'depth':16,'type':0}
    w_a = {**arg,**warp_arg}
    isGray = src.format.color_family == vs.GRAY
    clip = src if isGray else getplane(src,0)
    ####warp
    warp = core.warp.AWarpSharp2(clip,**w_a) if warpclip is None else warpclip
    ####mask
    edgemask = core.tcanny.TCanny(clip,mode=0, op=1)
    edgemask = expand(edgemask,cycle=edge_r)
    edgemask = core.std.Deflate(edgemask)
    edgemask = inpand(edgemask,cycle=edge_r)
    #
    mask = expand(edgemask,cycle=ring_r+1)
    mask = inpand(mask,cycle=1)
    #
    ringmask = core.std.Expr([edgemask,mask], ["y x -"])
    ####
    merge = core.std.MaskedMerge(clip, warp, ringmask)
    last = merge if isGray else core.std.ShufflePlanes([merge,src],[0,1,2], colorfamily=vs.YUV)
    ####
    if show_mode not in [0,1,2,3]:
        raise ValueError("")
    if show_mode==0:
        return last
    elif show_mode==1:
        return edgemask
    elif show_mode==2:
        return ringmask
    elif show_mode==3:
        return warp
    else:
        raise ValueError("")

def NonlinUSM(src,z=6.0,pow=1.6,str=1.0,rad=9,ldmp=0.001):
    """
    NonlinUSM
    --------------------------------
    port from avs script writen by Didée
    Non-linear Unsharp Masking, uses a wide-range Gaussian instead of a small-range kernel.
    Like most sharpeners, this script only processes luma, chroma channels are simply
    copied from the input clip.
    --------------------------------
    Parameters:
    z = 6.0 (float) zero point 
    pow = 1.6 (float) power
    str = 1.0 (float) strength 
    rad = 9.0 (float) radius for "gauss" 
    ldmp = 0.001 (float) damping for very small differences 
    ---------------------------------
    Examples:
    NonlinUSM(src,pow=4)                          ## enhance: for low bitrate sources
    NonlinUSM(src,z=3, pow=4.0, str=1, rad=6)     ## enhance less
    NonlinUSM(src,z=3, str=0.5, rad=9, pow=1)     ## enhance less
    
    NonlinUSM(src,z=3, str=2.5, rad=0.6)          ## sharpen: less noise
    NonlinUSM(src,z=6, pow=1.0, str=1, rad=6)     ## unsharp 
    
    NonlinUSM(src,pow=1.0, rad=2, str=0.7)        ## "smoothen" for noisy sources
    NonlinUSM(src,pow=1.0, rad=18, str=0.5)       ## smear: soft glow
    
    NonlinUSM(src,z=6, pow=4.0, str=1, rad=36)    ## local contrast 
    NonlinUSM(src,z=6, pow=1.0, str=1, rad=36)    ## local contrast 
    NonlinUSM(src,z=16, pow=4.0, str=18, rad=6)   ## B+W psychedelic 
    NonlinUSM(src,z=16, pow=2.0, str=2, rad=36)   ## solarized
    NonlinUSM(src,z=16, pow=4.0, str=3, rad=6)    ## sepia/artistic
    """
    bit = src.format.bits_per_sample
    width  = src.width
    height = src.height
    isGray = src.format.color_family == vs.GRAY
    clip = src if isGray else getplane(src,0)
    g=core.resize.Bicubic(clip,haf.m4(width/rad),haf.m4(height/rad),filter_param_a=1/3, filter_param_b=1/3).resize.Bicubic(width,height,filter_param_a=1, filter_param_b=0)
    expr="x x y - abs {bs} / {z} / 1 {pow} / pow {z} * {str} * x y - {bs} / dup * * x y - {bs} / dup * {ldmp} + / x y - * {bs} / x y - abs {bs} / 0.001 + / {bs} * +".format(bs=2**(bit-8),z=z,pow=pow,str=str,ldmp=ldmp)
    Ylast = core.std.Expr([clip,g], [expr])
    last = Ylast if isGray else core.std.ShufflePlanes([Ylast,src],[0,1,2], colorfamily=vs.YUV)
    return last

def SAdeband(src,thr=128,f3kdb_arg={},smoothmask=0,Sdbclip=None,Smask=None,tvrange=True):
    """
    Simple Adaptive Debanding
    -------------------------------------
    thr: only pixel less then will be processed(only affect luma)，default is 128 and vaule is based on 8bit
    f3kdb_arg:use a dict to set parameters of f3kdb
    smoothmask: -1: don't smooth the mask; 0: use removegrain mode11;
                         1: use removegrain mode20; 2: use removegrain mode19
                  a list :use Convolution,and this list will be the matrix
                       default is 0
    Sdbclip: input and use your own debanded clip,must be 16bit
    Smask:input and use your own mask clip,must be 16bit,and 0 means don't process
    tvrange: set false if your clip is pcrange
    """
    clip = src if src.format.bits_per_sample==16 else core.fmtc.bitdepth(src,bits=16)
    db = core.f3kdb.Deband(clip,output_depth=16,**f3kdb_arg) if Sdbclip is None else Sdbclip
    expr = "x {thr} > 0 65535 x {low} - 65535 * {thr} {low} - / - ?".format(thr=scale(thr),low=scale(16) if tvrange else 0)
    mask = core.std.Expr(clip,[expr,'',''])
    if smoothmask==-1:
        mask = mask
    elif smoothmask==0:
        mask = core.rgvs.RemoveGrain(mask,[11,0,0])
    elif smoothmask==1:
        mask = core.rgvs.RemoveGrain(mask,[20,0,0])
    elif smoothmask==2:
        mask = core.rgvs.RemoveGrain(mask,[19,0,0])
    elif isinstance(smoothmask,list):
        mask = core.std.Convolution(mask,matrix=smoothmask,planes=[0])
    else:
        raise TypeError("")
    merge = core.std.MaskedMerge(clip, db, mask, planes=0)
    return core.std.ShufflePlanes([merge,db],[0,1,2], colorfamily=vs.YUV)

def vfrtocfr(clip=None,tc=None,num=None,den=1,blend=False):
    """
    vfrtocfr
    --------------------------------
    clip: input clip
    tc: input timecodes,only support tcv2
    num,den: output fps=num/den
    blend: True means blend the frames instead of delete or copy , default is False
    """
    def tclist(f):
        A=open(f,"r")
        B=re.sub(r'(.\n)*# timecode format v2(.|\n)*\n0',r'0',A.read(),count=1)
        A.close()
        C=B.split()
        T=[]
        for i in C:
            T.append(int(float(i)))
        return T
    #################
    vn = clip.num_frames
    vtc = tclist(tc)
    cn = int(vtc[-1]*num/den/1000)
    ctc = [int(1000*den/num)*i for i in range(0,cn+1)]
    cc = clip[0]
    for i in range(1,cn+1):
        for j in range(1,vn+1):
            if ctc[i]<vtc[1]:
                cc += clip[0]
            elif ctc[i]>=vtc[j] and ctc[i]<vtc[j+1]:
                if blend == False:
                    cl=clip[j-1] if (ctc[i]-vtc[j])>(vtc[j+1]-ctc[i]) else clip[j]
                else:
                    cl=core.std.Merge(clip[j-1],clip[j],weight=(ctc[i]-vtc[j])/(vtc[j+1]-vtc[j]))
                cc += cl
    last = core.std.AssumeFPS(cc,fpsnum=num,fpsden=den)
    return core.std.Cache(last, make_linear=True)

def getPictType(clip,txt=None,show=True):
    """
    getPictType
    """
    sclip=core.std.PlaneStats(clip, plane=0)
    log = txt is not None
    if log:
        t = open(txt,'w')
    def __type(n, f, clip, core):
        ptype = str(f.props._PictType)[2]
        if log:
            t.write(str(n)+","+ptype)
            t.write('\n')
        if show:
            return core.text.Text(clip, "PictType:"+ptype)
        else:
            return clip
        if log:
            t.close()
    last = core.std.FrameEval(clip, functools.partial(__type, clip=clip,core=core),prop_src=sclip)
    return last

def FIFP(src,mode=0,tff=True,mi=40,blockx=16,blocky=16,cthresh=8,chroma=False,metric=1,tc=True,_pass=1,opencl=False,device=-1):
    """
    Fix Interlanced Frames in Progressive video
    ---------------------------------------
    analyze setting:
    vfm_mode: set the mode of vfm,default:5
    mi: set the mi of vfm,default:40
    cthresh: set the cthresh of vfm,default:8
    blockx,blocky:set the blockx/blocky of vfm,default:16
    ---------------------------------------
    deinterlace args:
    opencl: if True,use nnedi3cl;else use znedi3
    device: set device for nnedi3cl
    tff: true means Top field first,False means Bottom field first,default:True
    ---------------------------------------
    mode args:
    mode = 0:
           interlaced frames will be deinterlaced in the same fps
    mode = 1:
           interlaced frames will be deinterlaced in double fps,and output timecodes to create a vfr video
           need 2 pass
       _pass:
           1:analyze pass
           2:encode pass,can output timecodes
       tc:if True，will output timecodes,suggest set True only when finally encode,default:True
    ---------------------------------------
    notice:
       analyze.csv will be created when mode=1,_pass=1,you can check and revise it，then use in pass 2
    """
    clip = src if src.format.bits_per_sample==8 else core.fmtc.bitdepth(src,bits=8,dmode=8)
    order = 1 if tff else 0
    
    dect = core.tdm.IsCombed(clip,cthresh=cthresh,blockx=blockx,blocky=blocky,chroma=chroma,mi=mi,metric=metric)

    if mode==0:
        deinterlace = core.nnedi3cl.NNEDI3CL(src, field=order,device=device) if opencl else core.znedi3.nnedi3(src, field=order)
        ###
        def postprocess(n, f, clip, de):
            if f.props['_Combed'] == 1:
                return de
            else:
                return clip
        ###
        last=core.std.FrameEval(src, functools.partial(postprocess, clip=src, de=deinterlace), prop_src=dect)
        last=core.std.Cache(last, make_linear=True)
        return last
    elif mode==1:
        if _pass==1:
            t = open("analyze.csv",'w')
            t.write("frame,combed\n")
            def analyze(n, f, clip):
                t.write(str(n)+","+str(f.props['_Combed'])+"\n")
                return clip
                t.close()
            last=core.std.FrameEval(dect, functools.partial(analyze, clip=dect),prop_src=dect)
            last=core.std.Cache(last, make_linear=True)
            return last
        elif _pass==2:
            lenlst=len(src)
            num=src.fps_num
            den=src.fps_den
            c=open("analyze.csv","r")
            tmp=c.read().split("\n")[1:lenlst]
            lst=[None]*len(tmp)
            for i in tmp:
                i=i.split(",")
                lst[int(i[0])]=int(i[1])
            c.close()
            lenlst=len(lst)
            
            #tc
            if tc:
                c=open("timecodes.txt","w")
                c.write("# timecode format v2\n0\n")
                b=1000/num*den
                for i in range(lenlst):
                    if lst[i]==0:
                        c.write(str(int((i+1)*b))+"\n")
                    elif lst[i]==1:
                        c.write(str(int((i+0.5)*b))+"\n"+str(int((i+1)*b))+"\n")
                    else:
                        raise ValueError("")
                c.close()
            
            #deinterlace
            deinterlace = core.nnedi3cl.NNEDI3CL(src, field=order+2,device=device) if opencl else core.znedi3.nnedi3(src, field=order+2)
            src= core.std.Interleave([src,src])
            def postprocess(n,clip, de):
                if lst[n//2]==0:
                    return clip
                else:
                    return de
            dl=core.std.FrameEval(src, functools.partial(postprocess, clip=src, de=deinterlace))
            di=core.std.Cache(di, make_linear=True)
            tlist=[]
            for i in range(lenlst):
                if lst[i]==0:
                    tlist.append(2*i)
                else:
                    tlist.append(2*i)
                    tlist.append(2*i+1)
            last = core.std.SelectEvery(dl,lenlst*2,tlist)
            return last#core.std.AssumeFPS(last,src)
        else:
            ValueError("pass must be 1 or 2")
    else:
        raise ValueError("mode must be 0 or 1")

def Overlaymod(clipa, clipb, x=0, y=0, alpha=None,aa=False):
    """
    Overlaymod
    -------------------------
    modified overlay by xyx98,
    orginal Overlay by holy in havsfunc
    -------------------------
    difference: mask->alpha,please input the alpha clip read by imwri if needed
                   aa: if is True,use daa in clipb and alpha clip
    """
    if not (isinstance(clipa, vs.VideoNode) and isinstance(clipb, vs.VideoNode)):
        raise TypeError('Overlaymod: This is not a clip')
    if clipa.format.subsampling_w > 0 or clipa.format.subsampling_h > 0:
        clipa_src = clipa
        clipa = core.resize.Point(clipa, format=core.register_format(clipa.format.color_family, clipa.format.sample_type, clipa.format.bits_per_sample, 0, 0).id)
    else:
        clipa_src = None
    if clipb.format.id != clipa.format.id:
        clipb = core.resize.Point(clipb, format=clipa.format.id)
    mask = core.std.BlankClip(clipb, color=[(1 << clipb.format.bits_per_sample) - 1] * clipb.format.num_planes)
    if not isinstance(alpha, vs.VideoNode):
        raise TypeError("Overlaymod: 'alpha' is not a clip")
    if mask.width != clipb.width or mask.height != clipb.height:
        raise TypeError("Overlaymod: 'alpha' must be the same dimension as 'clipb'")

    if aa:
        clipb = haf.daa(clipb)
    # Calculate padding sizes
    l, r = x, clipa.width - clipb.width - x
    t, b = y, clipa.height - clipb.height - y
    # Split into crop and padding values
    cl, pl = min(l, 0) * -1, max(l, 0)
    cr, pr = min(r, 0) * -1, max(r, 0)
    ct, pt = min(t, 0) * -1, max(t, 0)
    cb, pb = min(b, 0) * -1, max(b, 0)
    # Crop and padding
    def cap(clip):
        mask = mvf.GetPlane(clip, 0)
        mask = core.std.CropRel(mask, cl, cr, ct, cb)
        mask = core.std.AddBorders(mask, pl, pr, pt, pb)
        return mask
    clipb = core.std.CropRel(clipb, cl, cr, ct, cb)
    clipb = core.std.AddBorders(clipb, pl, pr, pt, pb)
    # Return padded clip
    mask = cap(mask)
    last = core.std.MaskedMerge(clipa, clipb, mask)
    if alpha is not None:
        alpha=core.fmtc.bitdepth(alpha,bits=clipb.format.bits_per_sample)
        m = 1<<alpha.format.bits_per_sample
        alpha = core.std.Levels(alpha, min_in=16/256*m, max_in=235/256*m, min_out=m-1, max_out=0)
        if aa:
            alpha = haf.daa(alpha)
        mask = cap(alpha)
        last = core.std.MaskedMerge(clipa, last, mask)
    if clipa_src is not None:
        last = core.resize.Point(last, format=clipa_src.format.id)
    return last

def WarpFixChromaBlend(src,thresh=128,blur=3,btype=1,depth=6):
    """
    Warp Fix Chroma Blend
    """
    clip = core.resize.Bicubic(src,format=vs.YUV444P16)
    Y= getplane(clip,0)
    U= getplane(clip,1)
    V= getplane(clip,2)
    mask = core.warp.ASobel(Y, thresh=thresh).warp.ABlur(blur=blur, type=btype)
    Uwarp = core.warp.AWarp(U, mask=mask, depth=depth)
    Vwarp = core.warp.AWarp(V, mask=mask, depth=depth)
    last = core.std.ShufflePlanes([Y,Uwarp,Vwarp], [0,0,0], vs.YUV)
    return core.resize.Bicubic(last,format=src.format.id)

def InterFrame(Input, Preset='Medium', Tuning='Film', NewNum=None, NewDen=1, GPU=True, gpuid=0,InputType='2D', OverrideAlgo=None, OverrideArea=None,
               FrameDouble=False):
    """
    adjusted InterFrame from havsfunc,support 10bit with new svp
    """
    if not isinstance(Input, vs.VideoNode):
        raise TypeError('InterFrame: This is not a clip')

    sw=Input.format.subsampling_w
    sh=Input.format.subsampling_h
    depth= Input.format.bits_per_sample
    if  not sw ==1 and not sh==1 and depth not in [8,10]:
        raise TypeError('InterFrame: input must be yuv420p8 or yuv420p10')
    oInput=Input
    Input = core.fmtc.bitdepth(Input,bits=8)
    # Validate inputs
    Preset = Preset.lower()
    Tuning = Tuning.lower()
    InputType = InputType.upper()
    if Preset not in ['medium', 'fast', 'faster', 'fastest']:
        raise ValueError("InterFrame: '{Preset}' is not a valid preset".format(Preset=Preset))
    if Tuning not in ['film', 'smooth', 'animation', 'weak']:
        raise ValueError("InterFrame: '{Tuning}' is not a valid tuning".format(Tuning=Tuning))
    if InputType not in ['2D', 'SBS', 'OU', 'HSBS', 'HOU']:
        raise ValueError("InterFrame: '{InputType}' is not a valid InputType".format(InputType=InputType))
    
    def InterFrameProcess(clip,oclip):
        # Create SuperString
        if Preset in ['fast', 'faster', 'fastest']:
            SuperString = '{pel:1,'
        else:
            SuperString = '{'
        
        SuperString += 'gpu:1}' if GPU else 'gpu:0}'
        
        # Create VectorsString
        if Tuning == 'animation' or Preset == 'fastest':
            VectorsString = '{block:{w:32,'
        elif Preset in ['fast', 'faster'] or not GPU:
            VectorsString = '{block:{w:16,'
        else:
            VectorsString = '{block:{w:8,'
        
        if Tuning == 'animation' or Preset == 'fastest':
            VectorsString += 'overlap:0'
        elif Preset == 'faster' and GPU:
            VectorsString += 'overlap:1'
        else:
            VectorsString += 'overlap:2'
        
        if Tuning == 'animation':
            VectorsString += '},main:{search:{coarse:{type:2,'
        elif Preset == 'faster':
            VectorsString += '},main:{search:{coarse:{'
        else:
            VectorsString += '},main:{search:{distance:0,coarse:{'
        
        if Tuning == 'animation':
            VectorsString += 'distance:-6,satd:false},distance:0,'
        elif Tuning == 'weak':
            VectorsString += 'distance:-1,trymany:true,'
        else:
            VectorsString += 'distance:-10,'
        
        if Tuning == 'animation' or Preset in ['faster', 'fastest']:
            VectorsString += 'bad:{sad:2000}}}}}'
        elif Tuning == 'weak':
            VectorsString += 'bad:{sad:2000}}}},refine:[{thsad:250,search:{distance:-1,satd:true}}]}'
        else:
            VectorsString += 'bad:{sad:2000}}}},refine:[{thsad:250}]}'
        
        # Create SmoothString
        if NewNum is not None:
            SmoothString = '{rate:{num:' + repr(NewNum) + ',den:' + repr(NewDen) + ',abs:true},'
        elif clip.fps_num / clip.fps_den in [15, 25, 30] or FrameDouble:
            SmoothString = '{rate:{num:2,den:1,abs:false},'
        else:
            SmoothString = '{rate:{num:60000,den:1001,abs:true},'
        if GPU:
            SmoothString+= 'gpuid:'+repr(gpuid)+','
        if OverrideAlgo is not None:
            SmoothString += 'algo:' + repr(OverrideAlgo) + ',mask:{cover:80,'
        elif Tuning == 'animation':
            SmoothString += 'algo:2,mask:{'
        elif Tuning == 'smooth':
            SmoothString += 'algo:23,mask:{'
        else:
            SmoothString += 'algo:13,mask:{cover:80,'
        
        if OverrideArea is not None:
            SmoothString += 'area:{OverrideArea}'.format(OverrideArea=OverrideArea)
        elif Tuning == 'smooth':
            SmoothString += 'area:150'
        else:
            SmoothString += 'area:0'
        
        if Tuning == 'weak':
            SmoothString += ',area_sharp:1.2},scene:{blend:true,mode:0,limits:{blocks:50}}}'
        else:
            SmoothString += ',area_sharp:1.2},scene:{blend:true,mode:0}}'
        
        # Make interpolation vector clip
        Super = core.svp1.Super(clip, SuperString)
        Vectors = core.svp1.Analyse(Super['clip'], Super['data'], clip, VectorsString)
        
        # Put it together
        return core.svp2.SmoothFps(oclip, Super['clip'], Super['data'], Vectors['clip'], Vectors['data'], SmoothString)
    
    # Get either 1 or 2 clips depending on InputType
    if InputType == 'SBS':
        FirstEye = InterFrameProcess(core.std.CropRel(Input, right=Input.width // 2),
                                     core.std.CropRel(oInput, right=Input.width // 2))
        SecondEye = InterFrameProcess(core.std.CropRel(Input, left=Input.width // 2),
                                      core.std.CropRel(oInput, left=Input.width // 2))
        return core.std.StackHorizontal([FirstEye, SecondEye])
    elif InputType == 'OU':
        FirstEye = InterFrameProcess(core.std.CropRel(Input, bottom=Input.height // 2),
                                     core.std.CropRel(oInput, bottom=Input.height // 2))
        SecondEye = InterFrameProcess(core.std.CropRel(Input, top=Input.height // 2),
                                      core.std.CropRel(oInput, top=Input.height // 2))
        return core.std.StackVertical([FirstEye, SecondEye])
    elif InputType == 'HSBS':
        FirstEye = InterFrameProcess(core.std.CropRel(Input, right=Input.width // 2).resize.Spline36(Input.width, Input.height),
                                     core.std.CropRel(oInput, right=oInput.width // 2).resize.Spline36(oInput.width, oInput.height))
        SecondEye = InterFrameProcess(core.std.CropRel(Input, left=Input.width // 2).resize.Spline36(Input.width, Input.height),
                                      core.std.CropRel(oInput, left=oInput.width // 2).resize.Spline36(oInput.width, oInput.height))
        return core.std.StackHorizontal([core.resize.Spline36(FirstEye, Input.width // 2, Input.height),
                                         core.resize.Spline36(SecondEye, Input.width // 2, Input.height)])
    elif InputType == 'HOU':
        FirstEye = InterFrameProcess(core.std.CropRel(Input, bottom=Input.height // 2).resize.Spline36(Input.width, Input.height),
                                     core.std.CropRel(oInput, bottom=oInput.height // 2).resize.Spline36(oInput.width, oInput.height))
        SecondEye = InterFrameProcess(core.std.CropRel(Input, top=Input.height // 2).resize.Spline36(Input.width, Input.height),
                                      core.std.CropRel(oInput, top=oInput.height // 2).resize.Spline36(oInput.width, oInput.height))
        return core.std.StackVertical([core.resize.Spline36(FirstEye, Input.width, Input.height // 2),
                                       core.resize.Spline36(SecondEye, Input.width, Input.height // 2)])
    else:
        return InterFrameProcess(Input,oInput)

def dpidDown(src,width=None,height=None,Lambda=1.0,matrix_in=None,matrix=None,transfer_in="709",transfer=None,
               primaries_in=None,primaries=None,css=None,depth=16,dither_type="error_diffusion",range_in=None,range_out=None):
    """
    dpidDown
    --------------------------------
    use dpid as kernel in Gamma-aware resize，only downscale.
    need CUDA-Enabled GPU
    """
    def M(a,b):
        if a <= 1024 and b <= 576:
            return "170m"
        elif a <= 2048 and b <= 1536:
            return "709"
        else :
            return "2020ncl"
    ##############
    if width is None:
        width = src.width
    if height is None:
        height = src.height
    if width>src.width or height > src.height:
        raise ValueError("")
    isRGB=src.format.color_family==vs.RGB
    if transfer is None:
        transfer=transfer_in
    if matrix is None:
        matrix=M(width,height)
    if isRGB:
        matrix_in="rgb"
    if css is not None:
        css=str(css).lower()
        if css == "444" or css == "4:4:4":
            css = "11"
        elif css == "440" or css == "4:4:0":
            css = "12"
        elif css == "422" or css == "4:2:2":
            css = "21"
        elif css == "420" or css == "4:2:0":
            css = "22"
        elif css == "411" or css == "4:1:1":
            css = "41"
        elif css == "410" or css == "4:1:0":
            css = "42"
        if css not in ["11","12","21","22","41","42","rgb"]:
            raise ValueError("")
    if range_in is None:
        range_in="full" if isRGB else "limited"
    if range_out is None:
        if css is None:
            range_out=range_in
        elif isRGB and css=="rgb":
            range_out=range_in
        elif not isRGB and css!="rgb":
            range_out=range_in
        elif isRGB and css!="rgb":
            range_out="limited"
        else:
            range_out="full"
    range_in=range_in.lower()
    range_out=range_out.lower()
    if range_in=="tv":
        range_in="limited"
    if range_in=="pc":
        range_in="full"
    if range_in not in ["limited","full"]:
        raise ValueError("")
    if range_out=="tv":
        range_out="limited"
    if range_out=="pc":
        range_out="full"
    if range_out not in ["limited","full"]:
        raise ValueError("")
    rgb=core.resize.Bicubic(src,format=vs.RGBS,matrix_in_s=matrix_in,transfer_in_s=transfer_in,primaries_in_s=primaries_in,primaries_s=primaries,range_in_s=range_in)
    lin=core.resize.Bicubic(rgb,format=vs.RGB48,transfer_in_s=transfer_in,transfer_s="linear")
    res=core.dpid.Dpid(lin,width,height,Lambda)
    res=core.resize.Bicubic(res,format=vs.RGBS,transfer_in_s="linear",transfer_s=transfer)
    if not isRGB and css!="rgb":
        st=vs.FLOAT if depth==32 else vs.INTEGER
        if css is None:
            sh=src.format.subsampling_h
            sw=src.format.subsampling_w
        else:
            sh=int(css[0])//2
            sw=int(css[1])//2
        outformat=core.register_format(vs.YUV,st,depth,sh,sw)
        last=core.resize.Bicubic(res,format=vs.YUV444PS,matrix_s=matrix,range_s=range_out)
        last=core.resize.Bicubic(last,format=outformat.id,dither_type=dither_type)
    else:
        if css is None or css=="rgb":
            last=core.resize.Bicubic(res,range_s=range_out)
        else:
            sh=int(css[0])//2
            sw=int(css[1])//2
            st=vs.FLOAT if depth==32 else vs.INTEGER
            outformat=core.register_format(vs.YUV,st,depth,sh,sw)
            last=core.resize.Bicubic(res,format=vs.YUV444PS,matrix_s=matrix,range_s=range_out)
            last=core.resize.Bicubic(last,format=outformat.id,dither_type=dither_type)
    return last

def xTonemap(clip,nominal_luminance=400,exposure=4.5):
    """
    The way I convert hdr to sdr when I rip 'Kimi No Na Wa'(UHDBD HK ver.).
    I'm not sure It suit for other UHDBD
    ###
    nominal_luminance: nominal_luminance when convert to linear RGBS
    exposure: exposure in Mobius,which do the tonemap
    """

    fid=clip.format.id
    clip=core.resize.Spline36(clip=clip, format=vs.RGBS,range_in_s="limited", matrix_in_s="2020ncl", primaries_in_s="2020", primaries_s="2020", transfer_in_s="st2084", transfer_s="linear",dither_type="none", nominal_luminance=nominal_luminance)
    clip=core.tonemap.Mobius(clip,exposure=exposure)
    clip=core.resize.Spline36(clip, format=fid,matrix_s="709", primaries_in_s="2020", primaries_s="709", transfer_in_s="linear", transfer_s="709",dither_type="none")
    clip=core.std.Expr(clip,["x 4096 - 219 * 235 / 4096 +",""])
    return clip

def statsinfo2csv(clip,plane=None,Max=True,Min=True,Avg=False,bits=8,namebase=None):
    """
    write PlaneStats(Max,Min,Avg) to csv
    """

    cbits=clip.format.bits_per_sample
    cfamily=clip.format.color_family
    #########
    def info(clip,t,p):
        statsclip=core.std.PlaneStats(clip, plane=p)
        txt = open(t,'w')
        #############
        head="n"
        head+=",Max" if Max else ""
        head+=",Min" if Min else ""
        head+=",Avg" if Avg else ""
        head+="\n"
        txt.write(head)
        #############
        def write(n, f, clip, core,Max,Min,Avg,bits):
            ma = int(round(f.props.PlaneStatsMax*(1<<bits)/(1<<cbits)))
            mi = int(round(f.props.PlaneStatsMin*(1<<bits)/(1<<cbits)))
            avg=int(round(f.props.PlaneStatsAverage*(1<<bits)))
            ######
            line=str(n)
            line+=(","+str(ma)) if Max else ""
            line+=(","+str(mi)) if Min else ""
            line+=(","+str(avg)) if Avg else ""
            line+="\n"
            txt.write(line)
            ######
            return clip
            txt.close()
        last = core.std.FrameEval(clip,functools.partial(write, clip=clip,core=core,Max=Max,Min=Min,Avg=Avg,bits=bits),prop_src=statsclip)
        return last
    ###############
    if cfamily == vs.YUV:
        pname=('Y','U','V')
    elif cfamily == vs.RGB:
        pname=('R','G','B')
    elif cfamily == vs.GRAY:
        pname=('GRAY')
    else:
        raise ValueError("")
    ###############
    if plane is None:
        if cfamily == vs.GRAY:
            plane = [0]
        else:
            plane=[0,1,2]
    elif isinstance(plane,int):
        plane=[plane]
    elif not isinstance(plane,list,tuple):
        raise TypeError()
    ###############
    for i in plane:
        name= pname[i]+".csv" if namebase is None else namebase+'.'+pname[i]+".csv"
        clip = info(clip,name,i)
    return clip

def XSAA(src,nsize=None,nns=2,qual=None,aamode=-1,maskmode=1,opencl=False,device=-1,linedarken=False,preaa=0):
    """
    xyx98's simple aa function
    only process luma
    ####
    nsize,nnrs,qual: nnedi3 args
    aamode: decide how to aa. 0: merge two deinterlacing fleid ; 1: enlarge video and downscale
    maskmode: 0:no mask ; 1: use the clip before AA to create mask ; 2: use AAed clip to create mask; a video clip: use it as mask
    opencl: if True: use nnedi3cl; else use znedi3
    device:choose device for nnedi3cl
    linedarken: choose whether use FastLineDarkenMOD
    preaa: 0: no pre-AA ;
               1: using LDMerge in muvsfunc for pre-AA,use orginal clip when masked merge with AAed clip
               2: using LDMerge in muvsfunc for pre-AA,use pre-AAed clip when masked merge with AAed clip
    """

    w=src.width
    h=src.height
    if aamode==-1:
        enlarge = False if h>=720 else True
    elif aamode in (0,1):
        enlarge = bool(aamode)
    else:
        raise ValueError("")
    nk="nnedi3cl" if opencl else "znedi3"
    if src.format.color_family==vs.RGB:
        raise TypeError("RGB is unsupported")
    isYUV=src.format.color_family==vs.YUV
    Yclip = getY(src)

    if preaa in (1,2):
        horizontal = core.std.Convolution(Yclip, matrix=[1, 2, 7, 2, 1],mode='h')
        vertical = core.std.Convolution(Yclip, matrix=[1, 2, 7, 2, 1],mode='v')
        clip = muf.LDMerge(horizontal, vertical, Yclip, mrad=1)
    elif preaa ==0:
        clip=Yclip
    else:
        raise ValueError("")
    if enlarge:
        if nsize is None:
            nsize = 1
        if qual is None:
            qual = 2
        aa=nnedi3(clip,dh=True,field=1,nsize=nsize,nns=nns,qual=qual,device=device,mode=nk)
        last=aa.resize.Spline36(w,h)
        t=last
    else:
        if nsize is None:
            nsize = 3
        if qual is None:
            qual = 1
        aa=nnedi3(clip,dh=False,field=3,nsize=nsize,nns=nns,qual=qual,device=device,mode=nk)
        last=core.std.Merge(aa[0::2], aa[1::2])
    #last = last.fmtc.resample(sx=-0.5)
    if linedarken:
        last = haf.FastLineDarkenMOD(last, strength=48, protection=5, luma_cap=191, threshold=5, thinning=0)


    if maskmode==1:
        mask=clip.tcanny.TCanny(1.5, 20.0, 8.0)
        mask=haf.mt_expand_multi(mask, 'losange', planes=[0], sw=1, sh=1)
        if preaa==1:
            clip=Yclip
        last=core.std.MaskedMerge(clip, last, mask)
    elif maskmode==2:
        mask=last.tcanny.TCanny(1.5, 20.0, 8.0)
        mask=haf.mt_expand_multi(mask, 'losange', planes=[0], sw=1, sh=1)
        if preaa==1:
            clip=Yclip
        last=core.std.MaskedMerge(clip, last, mask)
    elif isinstance(maskmode,vs.VideoNode):
        if preaa==1:
            clip=Yclip
        last=core.std.MaskedMerge(clip, last, maskmode)
    if isYUV:
        last = core.std.ShufflePlanes([last,src],[0,1,2], colorfamily=vs.YUV)
    return last

def creditmask(clip,nclip,mode=0):
    """
    use non-credit clip to create mask for credit area
    255(8bit) means credit
    output will be 16bit
    ####
    mode: 0: only use Y to create mask ; 1: use all planes to create mask
              only affect the yuv input
    """

    clip = core.fmtc.bitdepth(clip,bits=16)
    nclip = core.fmtc.bitdepth(nclip,bits=16)
    fid=clip.format.id
    def Graymask(src,nc):
        dif = core.std.Expr([src,nc],["x y - abs 2560 > 65535 0 ?",'','']).rgvs.RemoveGrain(4)
        mask= core.std.Inflate(dif).rgvs.RemoveGrain(11).rgvs.RemoveGrain(11)
        return mask
    if clip.format.color_family==vs.RGB:
        raise TypeError("RGB is unsupported")
    isYUV=clip.format.color_family==vs.YUV
    if not isYUV:
        mask = Graymask(clip,nclip)
        return mask
    else:
        if mode==0:
            mask=Graymask(getY(clip),getY(nclip))
            mask=core.std.ShufflePlanes(mask,[0,0,0], colorfamily=vs.YUV)
        elif mode==1:
            clip=clip.resize.Bicubic(format=vs.YUV444P16)
            nclip=nclip.resize.Bicubic(format=vs.YUV444P16)
            maskY=Graymask(getY(clip),getY(nclip))
            maskU=Graymask(getU(clip),getU(nclip))
            maskV=Graymask(getV(clip),getV(nclip))
            mask=core.std.Expr([maskY,maskU,maskV],"x y max z max")
            mask=core.std.ShufflePlanes(mask,[0,0,0], colorfamily=vs.YUV)
        else:
            raise ValueError("mode must be 0 or 1")
        return mask.resize.Bicubic(format=fid)

def lbdeband(clip:vs.VideoNode,dbit=6):
    """
    low bitdepth deband
    deband for flat area with heavy details through round to low bitdepth,limitfilter and f3kdb
    only procress luma when YUV,no direct support for RGB.
    You need use trim,mask or other way you can to protect the area without heavy banding.
    """

    if src.format.color_family==vs.RGB:
        raise TypeError("RGB is unsupported")
    isGary=clip.format.color_family==vs.GARY
    clip=mvf.Depth(clip,16)
    luma=clip if isGary else getY(clip)
    down=mvf.Depth(luma,dbit,dither=1).f3kdb.Deband(31, 64, 0, 0, 0, 0, output_depth=16)
    deband=mvf.LimitFilter(down, luma, thr=0.2, elast=8.0).f3kdb.Deband(31, 64, 0, 0, 0, 0, output_depth=16).f3kdb.Deband(15, 64, 0, 0, 0, 0, output_depth=16)
    if isGary:
        return deband
    else:
        return core.std.ShufflePlanes([deband,clip], [0,1,2], vs.YUV)

def ssim2csv(clip1,clip2,file="ssim.csv",planes=None, downsample=True, k1=0.01, k2=0.03, fun=None, dynamic_range=1, **depth_args):
    """
    Warp function for ssim in muvsfunc
    Calculate SSIM and write to a csv
    Args:
        clip1: The distorted clip, will be copied to output.

        clip2: Reference clip, must be of the same format and dimension as the "clip1".

        file:  output file name

        plane: (int/list) Specify which planes to be processed. Default is None.

        downsample: (bool) Whether to average the clips over local 2x2 window and downsample by a factor of 2 before calculation.
            Default is True.

        k1, k2: (int) Constants in the SSIM index formula.
            According to the paper, the performance of the SSIM index algorithm is fairly insensitive to variations of these values.
            Default are 0.01 and 0.03.

        fun: (function or float) The function of how the clips are filtered.
            If it is None, it will be set to a gaussian filter whose standard deviation is 1.5. Note that the size of gaussian kernel is different from the one in MATLAB.
            If it is a float, it specifies the standard deviation of the gaussian filter. (sigma in core.tcanny.TCanny)
            According to the paper, the quality map calculated from gaussian filter exhibits a locally isotropic property,
            which prevents the present of undesirable “blocking” artifacts in the resulting SSIM index map.
            Default is None.

        dynamic_range: (float) Dynamic range of the internal float point clip. Default is 1.

        depth_args: (dict) Additional arguments passed to mvf.Depth() in the form of keyword arguments.
            Default is {}.
    """
    isYUV=clip1.format.color_family==vs.YUV
    isRGB=clip1.format.color_family==vs.RGB
    isGRAY=clip1.format.color_family==vs.GRAY
    if isinstance(planes,int):
        planes=[planes]
    if isGRAY:
        clip=muf.SSIM(clip1, clip2, plane=0, downsample=downsample, k1=k1, k2=k2, fun=fun, dynamic_range=dynamic_range, show_map=False, **depth_args)
        txt = open(file,'w')
        txt.write("n,gary\n")
        def tocsv(n, f, clip ,core):
            txt.write(str(n)+","+str(f.props.PlaneSSIM)+"\n")
            return clip
            txt.close()
        last=core.std.FrameEval(clip,functools.partial(tocsv, clip=clip,core=core),prop_src=clip)
    elif isYUV:
        if planes is None:
            planes=[0,1,2]
        Y=muf.SSIM(getY(clip1),getY(clip2),plane=0, downsample=downsample, k1=k1, k2=k2, fun=fun, dynamic_range=dynamic_range, show_map=False, **depth_args) if 0 in planes else getY(clip1)
        U=muf.SSIM(getU(clip1),getU(clip2),plane=0, downsample=downsample, k1=k1, k2=k2, fun=fun, dynamic_range=dynamic_range, show_map=False, **depth_args) if 1 in planes else getU(clip1)
        V=muf.SSIM(getV(clip1),getV(clip2),plane=0, downsample=downsample, k1=k1, k2=k2, fun=fun, dynamic_range=dynamic_range, show_map=False, **depth_args) if 2 in planes else getV(clip1)
        txt = open(file,'w')
        head="n"
        head+=",Y" if 0 in planes else ""
        head+=",U" if 1 in planes else ""
        head+=",V" if 2 in planes else ""
        txt.write(head+"\n")
        def tocsv(n,f,clip,core):
            line=str(n)
            line+=(","+str(f[0].props.PlaneSSIM)) if 0 in planes else ""
            line+=(","+str(f[1].props.PlaneSSIM)) if 1 in planes else ""
            line+=(","+str(f[2].props.PlaneSSIM)) if 2 in planes else ""
            txt.write(line+"\n")
            return clip
            txt.close()
        last=core.std.FrameEval(clip1,functools.partial(tocsv, clip=clip1,core=core),prop_src=[Y,U,V])
    elif isRGB:
        if planes is None:
            planes=[0,1,2]
        R=muf.SSIM(getY(clip1),getY(clip2),plane=0, downsample=downsample, k1=k1, k2=k2, fun=fun, dynamic_range=dynamic_range, show_map=False, **depth_args) if 0 in planes else getY(clip1)
        G=muf.SSIM(getU(clip1),getU(clip2),plane=0, downsample=downsample, k1=k1, k2=k2, fun=fun, dynamic_range=dynamic_range, show_map=False, **depth_args) if 1 in planes else getU(clip1)
        B=muf.SSIM(getV(clip1),getV(clip2),plane=0, downsample=downsample, k1=k1, k2=k2, fun=fun, dynamic_range=dynamic_range, show_map=False, **depth_args) if 2 in planes else getV(clip1)
        txt = open(file,'w')
        head="n"
        head+=",R" if 0 in planes else ""
        head+=",G" if 1 in planes else ""
        head+=",B" if 2 in planes else ""
        txt.write(head+"\n")
        def tocsv(n,f,clip,core):
            line=str(n)
            line+=(","+str(f[0].props.PlaneSSIM)) if 0 in planes else ""
            line+=(","+str(f[1].props.PlaneSSIM)) if 1 in planes else ""
            line+=(","+str(f[2].props.PlaneSSIM)) if 2 in planes else ""
            txt.write(line+"\n")
            return clip
            txt.close()
        last=core.std.FrameEval(clip1,functools.partial(tocsv, clip=clip1,core=core),prop_src=[R,G,B])
    else:
        raise TypeError("unsupport format")
    return last

def GMSD2csv(clip1,clip2,file="GMSD.csv",planes=None, downsample=True,c=0.0026,**depth_args):
    """
    Warp function for GMSD in muvsfunc
    Calculate GMSD and write to a csv

    GMSD is a new effective and efficient image quality assessment (IQA) model, which utilizes the pixel-wise gradient magnitude similarity (GMS)
    between the reference and distorted images combined with standard deviation of the GMS map to predict perceptual image quality.

    The distortion degree of the distorted image will be stored as frame property 'PlaneGMSD' in the output clip.

    The value of GMSD reflects the range of distortion severities in an image.
    The lowerer the GMSD score, the higher the image perceptual quality.
    If "clip1" == "clip2", GMSD = 0.
    
    Args:
        clip1: The distorted clip, will be copied to output.

        clip2: Reference clip, must be of the same format and dimension as the "clip1".

        file:  output file name

        plane: (int/list) Specify which planes to be processed. Default is None.

        downsample: (bool) Whether to average the clips over local 2x2 window and downsample by a factor of 2 before calculation.
            Default is True.

        c: (float) A positive constant that supplies numerical stability.
            According to the paper, for all the test databases, GMSD shows similar preference to the value of c.
            Default is 0.0026.

        depth_args: (dict) Additional arguments passed to mvf.Depth() in the form of keyword arguments.
            Default is {}.
    """
    isYUV=clip1.format.color_family==vs.YUV
    isRGB=clip1.format.color_family==vs.RGB
    isGRAY=clip1.format.color_family==vs.GRAY
    if isinstance(planes,int):
        planes=[planes]
    if isGRAY:
        clip=muf.GMSD(clip1, clip2, plane=0, downsample=downsample, c=c,show_map=False, **depth_args)
        txt = open(file,'w')
        txt.write("n,gary\n")
        def tocsv(n, f, clip ,core):
            txt.write(str(n)+","+str(f.props.PlaneGMSD)+"\n")
            return clip
            txt.close()
        last=core.std.FrameEval(clip,functools.partial(tocsv, clip=clip,core=core),prop_src=clip)
    elif isYUV:
        if planes is None:
            planes=[0,1,2]
        Y=muf.GMSD(getY(clip1),getY(clip2),plane=0, downsample=downsample, c=c, show_map=False, **depth_args) if 0 in planes else getY(clip1)
        U=muf.GMSD(getU(clip1),getU(clip2),plane=0, downsample=downsample, c=c, show_map=False, **depth_args) if 1 in planes else getU(clip1)
        V=muf.GMSD(getV(clip1),getV(clip2),plane=0, downsample=downsample, c=c, show_map=False, **depth_args) if 2 in planes else getV(clip1)
        txt = open(file,'w')
        head="n"
        head+=",Y" if 0 in planes else ""
        head+=",U" if 1 in planes else ""
        head+=",V" if 2 in planes else ""
        txt.write(head+"\n")
        def tocsv(n,f,clip,core):
            line=str(n)
            line+=(","+str(f[0].props.PlaneGMSD)) if 0 in planes else ""
            line+=(","+str(f[1].props.PlaneGMSD)) if 1 in planes else ""
            line+=(","+str(f[2].props.PlaneGMSD)) if 2 in planes else ""
            txt.write(line+"\n")
            return clip
            txt.close()
        last=core.std.FrameEval(clip1,functools.partial(tocsv, clip=clip1,core=core),prop_src=[Y,U,V])
    elif isRGB:
        if planes is None:
            planes=[0,1,2]
        R=muf.GMSD(getY(clip1),getY(clip2),plane=0, downsample=downsample, c=c, show_map=False, **depth_args) if 0 in planes else getY(clip1)
        G=muf.GMSD(getU(clip1),getU(clip2),plane=0, downsample=downsample, c=c, show_map=False, **depth_args) if 1 in planes else getU(clip1)
        B=muf.GMSD(getV(clip1),getV(clip2),plane=0, downsample=downsample, c=c, show_map=False, **depth_args) if 2 in planes else getV(clip1)
        txt = open(file,'w')
        head="n"
        head+=",R" if 0 in planes else ""
        head+=",G" if 1 in planes else ""
        head+=",B" if 2 in planes else ""
        txt.write(head+"\n")
        def tocsv(n,f,clip,core):
            line=str(n)
            line+=(","+str(f[0].props.PlaneGMSD)) if 0 in planes else ""
            line+=(","+str(f[1].props.PlaneGMSD)) if 1 in planes else ""
            line+=(","+str(f[2].props.PlaneGMSD)) if 2 in planes else ""
            txt.write(line+"\n")
            return clip
            txt.close()
        last=core.std.FrameEval(clip1,functools.partial(tocsv, clip=clip1,core=core),prop_src=[R,G,B])
    else:
        raise TypeError("unsupport format")
    return last

def ssharp(clip,chroma=True,mask=False,compare=False):
    """
    slightly sharp through bicubic
    """
    isGRAY=clip.format.color_family==vs.GRAY
    src=clip.fmtc.bitdepth(bits=16)
    w=src.width
    h=src.height
    if chroma and not isGRAY:
        sha = core.fmtc.resample(src,w*2,h*2,kernel='bicubic',a1=-1,a2=6).resize.Lanczos(w,h)
        last=core.rgvs.Repair(sha, src, 13)
        last=mvf.LimitFilter(src, last, thr=1, thrc=0.5, elast=6, brighten_thr=0.5, planes=[0,1,2])
        if mask:
            mask1=src.tcanny.TCanny(0.5, 20.0, 8.0,1).std.Expr("x 30000 < 0 x ?").rgvs.RemoveGrain(4)
            mask1=inpand(expand(mask1,cycle=1),cycle=1)
            mask2=core.std.Expr([last,src],"x y - abs 96 *").rgvs.RemoveGrain(4)
            mask2=core.std.Expr(mask2,"x 30000 < 0 x ?")
            mask=core.std.Expr([mask1,mask2],"x y min")
            last=core.std.MaskedMerge(last, src, mask,[0,1,2])
    elif not chroma:
        srcy=getY(src)
        sha = core.fmtc.resample(srcy,w*2,h*2,kernel='bicubic',a1=-1,a2=6).resize.Lanczos(w, h)
        last=core.rgvs.Repair(sha, srcy, 13)
        last=mvf.LimitFilter(srcy, last, thr=1,elast=6, brighten_thr=0.5, planes=0)
        if mask:
            mask1=srcy.tcanny.TCanny(0.5, 20.0, 8.0,1).std.Expr("x 30000 < 0 x ?").rgvs.RemoveGrain(4)
            mask1=inpand(expand(mask1,cycle=1),cycle=1)
            mask2=core.std.Expr([last,srcy],"x y - abs 96 *").rgvs.RemoveGrain(4)
            mask2=core.std.Expr(mask2,"x 30000 < 0 x ?")
            mask=core.std.Expr([mask1,mask2],"x y min")
            last=core.std.MaskedMerge(last, srcy, mask,0)
        last=core.std.ShufflePlanes([last,src], [0,1,2],colorfamily=vs.YUV)
    elif isGRAY:
        sha = core.fmtc.resample(src,w*2,h*2,kernel='bicubic',a1=-1,a2=6).resize.Lanczos(w,h)
        last=core.rgvs.Repair(sha, src, 13)
        last=mvf.LimitFilter(src, last, thr=1, thrc=0.5, elast=6, brighten_thr=0.5)
        if mask:
            mask1=src.tcanny.TCanny(0.5, 20.0, 8.0,1).std.Expr("x 30000 < 0 x ?").rgvs.RemoveGrain(4)
            mask1=inpand(expand(mask1,cycle=1),cycle=1)
            mask2=core.std.Expr([last,src],"x y - abs 96 *").rgvs.RemoveGrain(4)
            mask2=core.std.Expr(mask2,"x 30000 < 0 x ?")
            mask=core.std.Expr([mask1,mask2],"x y min")
            last=core.std.MaskedMerge(last, src, mask)
    if not compare:
        return last
    else:
        return core.std.Interleave([src.text.Text("src"),last.text.Text("sharp")])

def readmpls(path:str,sfilter='ffms2',cache=None):
    mpls = core.mpls.Read(path)
    if sfilter in ["ffms2","ffms","ff","f","ffvideosource"]:
        if cache is None or cache==0:
            cache=os.path.join(os.getcwd(),'cache')
        elif isinstance(cache,str):
            pass
        elif cache==-1:
            cache=False
        else:
            raise ValueError('unknown cache setting')
        
        if cache:
            clips=[]
            for i in range(mpls['count']):
                clips.append(core.ffms2.Source(source=mpls['clip'][i], cachefile=os.path.join(cache,mpls['filename'][i].decode()+'.ffindex')))
        else:
            clips=[core.ffms2.Source(mpls['clip'][i]) for i in range(mpls['count'])]
    elif sfilter in ['lwi','l','lsmash','l-smash','lsmas','LWLibavSource']:
        clips=[core.lsmas.LWLibavSource(mpls['clip'][i]) for i in range(mpls['count'])]
    else:
        raise ValueError("unknown source filter")
    return core.std.Splice(clips)

def mwaa(clip, aa_y=True, aa_c=False, cs_h=0, cs_v=0, aa_cmask=True, kernel_y=2, kernel_c=1, show=True,opencl=False,device=0):
    """
    Anti-Aliasing function
    Steal from other one's script. Most likely written by mawen1250.
    add opencl support for nnedi3,use znedi3 replace nnedi3
    """
    ## internal functions
    mode="nnedi3cl" if opencl else "znedi3"
    def aa_kernel_vertical(clip):
        clip_blk = clip.std.BlankClip(height=clip.height * 2)
        clip_y = mvf.GetPlane(clip, 0)
        if kernel_y == 2:
            clip_y = clip_y.eedi2.EEDI2(field=1)
        else:
            clip_y = nnedi3(clip_y,field=1, dh=True,device=device)
        clip_u = mvf.GetPlane(clip, 1)
        clip_v = mvf.GetPlane(clip, 2)
        if kernel_c == 2:
            clip_u = clip_u.eedi2.EEDI2(field=1)
            clip_v = clip_v.eedi2.EEDI2(field=1)
        else:
            clip_u = nnedi3(clip_u,field=1, dh=True,device=device)
            clip_v = nnedi3(clip_v,field=1, dh=True,device=device)
        return core.std.ShufflePlanes([clip_y if aa_y else clip_blk, clip_u if aa_c else clip_blk, clip_v if aa_c else clip_blk], [0,0,0] if aa_c else [0,1,2], vs.YUV)

    def aa_resample_vercial(clip, height, chroma_shift=0):
        return clip.fmtc.resample(h=height, sx=0, sy=[-0.5, -0.5 * (1 << clip.format.subsampling_h) - chroma_shift * 2], kernel=["spline36", "bicubic"], a1=0, a2=0.5, planes=[3 if aa_y else 1,3 if aa_c else 1,3 if aa_c else 1])

    ## parameters
    aa_cmask = aa_c and aa_cmask

    ## kernel
    aa = aa_resample_vercial(aa_kernel_vertical(clip.std.Transpose()), clip.width, cs_h)
    aa = aa_resample_vercial(aa_kernel_vertical(aa.std.Transpose()), clip.height, cs_v)

    ## mask
    aamask = clip.tcanny.TCanny(1.5, 20.0, 8.0, planes=[0])
    aamask = haf.mt_expand_multi(aamask, 'losange', planes=[0], sw=1, sh=1)

    ## merge
    if aa_y:
        if aa_c:
            if aa_cmask:
                aa_merge = core.std.MaskedMerge(clip, aa, aamask, [0,1,2], True)
            else:
                aa_merge = core.std.MaskedMerge(clip, aa, aamask, [0], False)
                aa_merge = core.std.ShufflePlanes([aa_merge, aa], [0,1,2], vs.YUV)
        else:
            aa_merge = core.std.MaskedMerge(clip, aa, aamask, [0], False)
    else:
        if aa_c:
            if aa_cmask:
                aa_merge = core.std.MaskedMerge(clip, aa, aamask, [1,2], True)
            else:
                aa_merge = core.std.ShufflePlanes([clip, aa], [0,1,2], vs.YUV)
        else:
            aa_merge = clip

    ## output
    return aamask if show else aa_merge

def mwcfix(clip, kernel=1, restore=5, a=2, grad=2, warp=6, thresh=96, blur=3, repair=1, cs_h=0, cs_v=0):
    """
    chroma restoration
    Steal from other one's script. Most likely written by mawen1250.
    repalce nnedi3 with znedi3

    """
    clip_y = mvf.GetPlane(clip, 0)
    clip_u = mvf.GetPlane(clip, 1)
    clip_v = mvf.GetPlane(clip, 2)

    cssw = clip.format.subsampling_w
    cssh = clip.format.subsampling_h

    if cs_h != 0 or cssw > 0:
        if cssw > 0 and kernel == 1:
            clip_u = mvf.Depth(clip_u, 8)
            clip_v = mvf.Depth(clip_v, 8)
        clip_u = clip_u.std.Transpose()
        clip_v = clip_v.std.Transpose()
        field = 1
        for i in range(cssw):
            if kernel >= 2:
                clip_u = clip_u.eedi2.EEDI2(field=field)
                clip_v = clip_v.eedi2.EEDI2(field=field)
            elif kernel == 1:
                clip_u = clip_u.znedi3.nnedi3(field=field, dh=True)
                clip_v = clip_v.znedi3.nnedi3(field=field, dh=True)
        sy = -cs_h
        clip_u = clip_u.fmtc.resample(h=clip_y.width, sy=sy, center=False, kernel="bicubic", a1=0, a2=0.5)
        clip_v = clip_v.fmtc.resample(h=clip_y.width, sy=sy, center=False, kernel="bicubic", a1=0, a2=0.5)
        clip_u = clip_u.std.Transpose()
        clip_v = clip_v.std.Transpose()

    if cs_v != 0 or cssh > 0:
        if cssh > 0 and kernel == 1:
            clip_u = mvf.Depth(clip_u, 8)
            clip_v = mvf.Depth(clip_v, 8)
        field = 1
        for i in range(clip.format.subsampling_w):
            if kernel >= 2:
                clip_u = clip_u.eedi2.EEDI2(field=field)
                clip_v = clip_v.eedi2.EEDI2(field=field)
            elif kernel == 1:
                clip_u = clip_u.znedi3.nnedi3(field=field, dh=True)
                clip_v = clip_v.znedi3.nnedi3(field=field, dh=True)
            field = 0
        sy = (-0.5 if cssh > 0 and kernel > 0 else 0) - cs_v
        clip_u = clip_u.fmtc.resample(h=clip_y.height, sy=sy, center=True, kernel="bicubic", a1=0, a2=0.5)
        clip_v = clip_v.fmtc.resample(h=clip_y.height, sy=sy, center=True, kernel="bicubic", a1=0, a2=0.5)

    pp_u = clip_u
    pp_v = clip_v

    if restore > 0:
        rst_u = pp_u.knlm.KNLMeansCL(d=0, a=a, s=1, h=restore, rclip=clip_y).rgvs.Repair(pp_u, 13)
        rst_v = pp_v.knlm.KNLMeansCL(d=0, a=a, s=1, h=restore, rclip=clip_y).rgvs.Repair(pp_v, 13)
        low_u = rst_u
        low_v = rst_v
        for i in range(grad):
            low_u = low_u.rgvs.RemoveGrain(20)
            low_v = low_v.rgvs.RemoveGrain(20)
        pp_u = core.std.Expr([pp_u, rst_u, low_u], 'y z - x +')
        pp_v = core.std.Expr([pp_v, rst_v, low_v], 'y z - x +')

    if warp > 0:
        awarp_mask = mvf.Depth(clip_y, 8).warp.ASobel(thresh).warp.ABlur(blur, 1)
        pp_u8 = mvf.Depth(mvf.Depth(pp_u, 8).warp.AWarp(awarp_mask, warp), 16)
        pp_v8 = mvf.Depth(mvf.Depth(pp_v, 8).warp.AWarp(awarp_mask, warp), 16)
        pp_u = mvf.LimitFilter(pp_u, pp_u8, thr=1.0, elast=2.0)
        pp_v = mvf.LimitFilter(pp_v, pp_v8, thr=1.0, elast=2.0)

    if repair > 0:
        pp_u = pp_u.rgvs.Repair(clip_u, repair)
        pp_v = pp_v.rgvs.Repair(clip_v, repair)
    elif repair < 0:
        pp_u = clip_u.rgvs.Repair(pp_u, -repair)
        pp_v = clip_v.rgvs.Repair(pp_v, -repair)

    final = core.std.ShufflePlanes([clip_y, pp_u, pp_v], [0,0,0], vs.YUV)
    final = final.fmtc.resample(csp=clip.format.id, kernel="bicubic", a1=0, a2=0.5)
    return final

def mwlmask(clip, l1=80, h1=96, h2=None, l2=None):
    """
    luma mask
    Steal from other one's script. Most likely written by mawen1250.
    """
    sbitPS = clip.format.bits_per_sample
    black = 0
    white = (1 << sbitPS) - 1
    l1 = l1 << (sbitPS - 8)
    h1 = h1 << (sbitPS - 8)
    if h2 is None: h2 = white
    else: h2 = h2 << (sbitPS - 8)
    if l2 is None: l2 = white
    else: l2 = l2 << (sbitPS - 8)
    
    if h2 >= white:
        expr = '{white}'.format(white=white)
    else:
        expr = 'x {h2} <= {white} x {l2} < x {l2} - {slope2} * {black} ? ?'.format(black=black, white=white, h2=h2, l2=l2, slope2=white / (h2 - l2))
    expr = 'x {l1} <= {black} x {h1} < x {l1} - {slope1} * ' + expr + ' ? ?'
    expr = expr.format(black=black, l1=l1, h1=h1, slope1=white / (h1 - l1))
    
    clip = mvf.GetPlane(clip, 0)
    clip = clip.rgvs.RemoveGrain(4)
    clip = clip.std.Expr(expr)
    return clip

def mwdbmask(clip, chroma=True, sigma=2.5, t_h=1.0, t_l=0.5, yuv444=None, cs_h=0, cs_v=0, lmask=None, sigma2=2.5, t_h2=3.0, t_l2=1.5):
    """
    deband mask
    Steal from other one's script. Most likely written by mawen1250.
    """
    ## clip properties
    yuv420 = clip.format.subsampling_w == 1 and clip.format.subsampling_h == 1
    sw = clip.width
    sh = clip.height
    if yuv444 is None:
        yuv444 = not yuv420
    ## Canny edge detector
    emask = clip.tcanny.TCanny(sigma, t_h, t_l, planes=[0,1,2] if chroma else [0])
    if lmask is not None:
        emask2 = clip.tcanny.TCanny(sigma2, t_h2, t_l2, planes=[0,1,2] if chroma else [0])
        emask = core.std.MaskedMerge(emask, emask2, lmask, [0,1,2] if chroma else [0], True)
    ## apply morphologic filters and merge mask planes
    emaskY = mvf.GetPlane(emask, 0)
    if chroma:
        emaskC = mvf.Max(mvf.GetPlane(emask, 1), mvf.GetPlane(emask, 2))
        if yuv420:
            emaskC = haf.mt_inpand_multi(haf.mt_expand_multi(emaskC, 'losange', sw=3, sh=3), 'rectangle', sw=3, sh=3)
            emaskC = emaskC.fmtc.resample(sw, sh, 0.25 - cs_h / 2, 0 - cs_v / 2, kernel='bilinear', fulls=True)
        else:
            emaskY = mvf.Max(emaskY, emaskC)
    emaskY = haf.mt_inpand_multi(haf.mt_expand_multi(emaskY, 'losange', sw=5, sh=5), 'rectangle', sw=2, sh=2)
    if chroma and yuv420:
        dbmask = mvf.Max(emaskY, emaskC)
    else:
        dbmask = emaskY
    ## convert to final mask, all the planes of which are the same
    if yuv444:
        dbmask = haf.mt_inflate_multi(dbmask, radius=2)
        dbmaskC = dbmask
    else:
        dbmaskC = dbmask.fmtc.resample(sw // 2, sh // 2, -0.5, 0, kernel='bilinear')
        dbmask = haf.mt_inflate_multi(dbmask, radius=2)
    dbmask = core.std.ShufflePlanes([dbmask, dbmaskC, dbmaskC], [0,0,0], vs.YUV)
    return dbmask

def mwenhance(diffClip, chroma=False, Strength=2.0, Szrp8=8, Spwr=4, SdmpLo=4, SdmpHi=48, Soft=0):
    """
    high frequency enhance
    Steal from other one's script. Most likely written by mawen1250.
    use it on your high frequency layer.
    """
    # constant values for sharpening LUT
    sbitPS = diffClip.format.bits_per_sample
    bpsMul8 = 1 << (sbitPS - 8)
    floor = 0
    ceil = (1 << sbitPS) - 1
    neutral = 1 << (sbitPS - 1)
    neutralstr = ' {} '.format(neutral)
    miSpwr = 1 / Spwr
    Szrp = Szrp8 * bpsMul8
    Szrp8Sqr = Szrp8 * Szrp8
    SzrpMulStrength = Szrp * Strength
    Szrp8SqrPlusSdmpLo = Szrp8Sqr + SdmpLo
    SdmpHiEqual0 = SdmpHi == 0
    Szrp8DivSdmpHiPower4Plus1 = 1 if SdmpHiEqual0 else (Szrp8 / SdmpHi) ** 4 + 1
    # function to generate sharpening LUT
    def diffEhFunc(x):
        if x == neutral:
            return x

        diff = x - neutral
        absDiff = abs(diff)
        diff8 = diff / bpsMul8
        absDiff8 = abs(diff8)
        diff8Sqr = diff8 * diff8
        signMul = 1 if diff >= 0 else -1

        res1 = (absDiff / Szrp) ** miSpwr * SzrpMulStrength * signMul
        res2 = diff8Sqr * Szrp8SqrPlusSdmpLo / ((diff8Sqr + SdmpLo) * Szrp8Sqr)
        res3 = 0 if SdmpHiEqual0 else (absDiff8 / SdmpHi) ** 4
        enhanced = res1 * res2 * Szrp8DivSdmpHiPower4Plus1 / (1 + res3)

        return min(ceil, max(floor, round(neutral + enhanced)))
    # apply sharpening LUT and soften the result
    if Strength > 0:
        diffClip = diffClip.std.Lut([0,1,2] if chroma else [0], function=diffEhFunc)
        if Soft > 0:
            diffClipEhSoft = diffClip.rgvs.RemoveGrain([19, 19 if chroma else 0])
            diffClipEhSoft = diffClipEhSoft if Soft >= 1 else core.std.Merge(diffClip, diffClipEhSoft, [1 - Soft, Soft])
            limitDiffExpr = 'x ' + neutralstr + ' - abs y ' + neutralstr + ' - abs <= x y ?'
            diffClip = core.std.Expr([diffClip, diffClipEhSoft], [limitDiffExpr, limitDiffExpr if chroma else ''])
    # output
    return diffClip

def drAA(src,drf=0.5,lraa=True,opencl=False,device=-1,pp=True):
    """
    down resolution Anti-Aliasing for anime with heavy Aliasing
    only process luma
    #######
    drf:set down resolution factor,default is 0.5,range:0.5-1
    lraa:enable XSAA after down resolution,default is True
    opencl:use nnedi3cl and TcannyCL,default is False,means using znedi3 and Tcanny
    device:select device for opencl
    pp:enable post-process,sharpen、linedarken、dering,default is True
    """
    src=src.fmtc.bitdepth(bits=16)
    w=src.width
    h=src.height
    if src.format.color_family==vs.RGB:
        raise TypeError("RGB is unsupported")
    isYUV=src.format.color_family==vs.YUV
    Y = getY(src)
    if not 0.5<=drf<=1:
        raise ValueError("down resolution factor(drf) must between 0.5 and 1")

    ##aa
    aaY=core.resize.Bicubic(Y,int(w*drf),int(h*drf))
    if lraa:
        aaY=XSAA(aaY,aamode=0,preaa=2,maskmode=0,nsize=3,opencl=opencl,device=device)
    if opencl:
        aaY=nnedi3(aaY,field=1,dh=True,dw=True,nsize=3,nns=1,device=device,mode="nnedi3cl")
    else:
        aaY=nnedi3(aaY,field=1,dh=True,nsize=3,nns=1,device=device,mode="znedi3").std.Transpose()
        aaY=nnedi3(aaY,field=1,dh=True,nsize=3,nns=1,device=device,mode="znedi3").std.Transpose()
    if int(w*drf)*2!=w or int(h*drf)*2!=h:
        aaY=core.resize.Spline36(aaY,w,h)

    ##mask
    mask1=core.std.Expr([aaY,Y],["x y - abs 16 * 12288 < 0 65535 ?"]).rgvs.RemoveGrain(3).rgvs.RemoveGrain(11)
    mask2=core.tcanny.TCannyCL(Y, sigma=0, mode=1,op=1,gmmax=30,device=device) if opencl else core.tcanny.TCanny(Y, sigma=0, mode=1,op=1,gmmax=30)
    mask2=core.std.Expr(mask2,"x 14000 < 0 65535 ?").rgvs.RemoveGrain(3).rgvs.RemoveGrain(11)
    mask=core.std.Expr([mask1,mask2],"x y min 256 < 0 65535 ?").rgvs.RemoveGrain(11)

    #pp
    if pp:
        aaY=haf.FastLineDarkenMOD(aaY,strength=96, protection=3, luma_cap=200, threshold=5, thinning=24)
        aaY=xsUSM(aaY)
        aaY=muf.abcxyz(aaY)
        #aaY=SADring(aaY)
        
        low=core.rgvs.RemoveGrain(aaY,11)
        hi=core.std.MakeDiff(aaY, low)
        en=mwenhance(hi,chroma=False,Strength=2.5)
        hi=mvf.LimitFilter(en,hi, thr=0.3, elast=8, brighten_thr=0.15)
        aaY=core.std.MergeDiff(aaY, hi)
        
        

    #merge
    Ylast=core.std.MaskedMerge(Y, aaY, mask)
    if isYUV:
        last= core.std.ShufflePlanes([Ylast,src], [0,1,2], vs.YUV)
    else:
        last= Ylast
    return last

#helper function:


#converting the values in one depth to another
def scale(i,depth_out=16,depth_in=8):
    return i*2**(depth_out-depth_in)

#getplane in YUV
def getplane(clip,i):
    return clip.std.ShufflePlanes(i, colorfamily=vs.GRAY)

def getY(clip):
    return clip.std.ShufflePlanes(0, colorfamily=vs.GRAY)

def getU(clip):
    return clip.std.ShufflePlanes(1, colorfamily=vs.GRAY)

def getV(clip):
    return clip.std.ShufflePlanes(2, colorfamily=vs.GRAY)

#extract all planes
def extractPlanes(clip):
    return tuple(clip.std.ShufflePlanes(x, colorfamily=vs.GRAY) for x in range(clip.format.num_planes))

#show plane in YUV(interger only)
def showY(clip):
    return clip.std.Expr(["",str(scale(128,clip.format.bits_per_sample))])

def showU(clip):
    return clip.std.Expr(["0","",str(scale(128,clip.format.bits_per_sample))])

def showV(clip):
    return clip.std.Expr(["0",str(scale(128,clip.format.bits_per_sample)),""])

def showUV(clip):
    return clip.std.Expr(["0",""])

#inpand/expand
def inpand(clip=None,planes=0,thr=None,mode="square",cycle=1):
    if mode=="square":
        cd=[1,1,1,1,1,1,1,1]
    elif mode=="horizontal":
        cd=[0,0,0,1,1,0,0,0]
    elif mode=="vertical":
        cd=[0,1,0,0,0,0,1,0]
    elif mode=="both":
        cd=[0,1,0,1,1,0,1,0]
    else:
        raise TypeError("")
    last = core.std.Minimum(clip,planes,thr,cd)
    if cycle<=1:
        return last
    else:
        return inpand(last,planes,thr,mode,cycle-1)

def expand(clip=None,planes=0,thr=None,mode="square",cycle=1):
    if mode=="square":
        cd=[1,1,1,1,1,1,1,1]
    elif mode=="horizontal":
        cd=[0,0,0,1,1,0,0,0]
    elif mode=="vertical":
        cd=[0,1,0,0,0,0,1,0]
    elif mode=="both":
        cd=[0,1,0,1,1,0,1,0]
    else:
        raise TypeError("")
    last = core.std.Maximum(clip,planes,thr,cd)
    if cycle<=1:
        return last
    else:
        return expand(last,planes,thr,mode,cycle-1)

def getCSS(w,h):
    css={
        (1,1):"420",
        (1,0):"422",
        (0,0):"444",
        (2,2):"410",
        (2,0):"411",
        (0,1):"440"}
    sub=(w,h)
    if css.get(sub) is None:
        raise ValueError('Unknown subsampling')
    else:
        return css[sub]

def clip2css(clip):
    return getCSS(clip.format.subsampling_w,clip.format.subsampling_h)

def nnedi3(clip,field,dh=False,dw=False,planes=None,nsize=6,nns=1,qual=1,etype=0,pscrn=2,exp=0,
           mode="znedi3",device=-1,list_device=False,info=False):
    mode=mode.lower()
    if mode=="nnedi3":
        return clip.nnedi3.nnedi3(field=field, dh=dh, planes=planes, nsize=nsize, nns=nns, qual=qual, etype=etype, pscrn=pscrn,exp=exp)
    elif mode=="znedi3":
        return clip.znedi3.nnedi3(field=field, dh=dh, planes=planes, nsize=nsize, nns=nns, qual=qual, etype=etype, pscrn=pscrn,exp=exp)
    elif mode=="nnedi3cl":
        return clip.nnedi3cl.NNEDI3CL(field=field, dh=dh, dw=dw, planes=planes, nsize=nsize, nns=nns, qual=qual, etype=etype, pscrn=pscrn,device=device,list_device=list_device,info=info)
    else:
        raise ValueError("Unknown mode,mode must in ['nnedi3','nnedi3cl','znedi3']")


#testing
def xcUSM(src:vs.VideoNode,blur=None,hip=None,lowp=None,pp=None,plane=[0],mask=None,merge="src+hi"):
    """
    USM based sharp function for someone want custom some process detail
    """
    if blur is None:
        blur=functools.partial(core.rgvs.RemoveGrain,mode=11)

    if hip is not None and  not callable(hip):
        raise TypeError("hip must be a function or just be None")

    if lowp is not None and  not callable(lowp):
        raise TypeError("lowp must be a function or just be None")

    if pp is not None and not callable(pp):
        raise TypeError("pp must be a function or just be None")

    if mask is not None and not callable(mask):
        raise TypeError("mask must be a function or just be None")

    if isinstance(plane,int):
        plane=[plane]

    src=src.fmtc.bitdepth(bits=16)
    num_planes= src.format.num_planes

    def usm_core(clip):
        low=blur(clip)
        hi=core.std.MakeDiff(clip,low)

        if hip is not None:
            hi=hip(hi)
        if lowp is not None:
            low=lowp(low)

        if merge=="src+hi":
            last=core.std.MergeDiff(clip,hi)
        elif merge=="low+hi":
            last=core.std.MergeDiff(low,hi)
        else:
            raise ValueError("unknown mode")

        if pp is not None:
            last=pp(last,clip)

        if mask is not None:
            maskclip=mask(clip)
            last=core.std.MaskedMerge(last,clip,maskclip)
            
        return last

    planes=[getplane(src,x) for x in range(num_planes)]
    for i in plane:
        planes[i]=usm_core(planes[i])

    return core.std.ShufflePlanes(planes,[0]*num_planes,src.format.color_family)

# Backwards compatibility -----------------------------------------------------


STPresso = stpresso
SPresso = spresso
STPressoMC = stpresso_mc
FluxsmoothTMC = fluxsmooth_tmc
xsUSM = xs_usm
SharpenDetail = sharpen_detail
