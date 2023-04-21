from nipype.interfaces.base import (
    File,
    SimpleInterface,
    TraitedSpec,
    traits,
)

import nibabel as nb
import numpy as np
import os


def MP2RAGErobustfunc(INV1, INV2, beta):
    return (np.conj(INV1) * INV2 - beta) / (INV1**2 + INV2**2 + 2 * beta)


def rootsquares_pos(a, b, c):
    return (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)


def rootsquares_neg(a, b, c):
    return (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)


def _MP2RAGEdenoise(mp2rage_path, inv1_path, inv2_path, factor):
    """
    Creates a denoised MP2RAGE nibabel Nifti1Image, `new_MP2RAGEimg`
    Uses the same affine and header information as `mp2rage_path`
    """

    MP2RAGEimg = nb.load(mp2rage_path)
    INV1img = nb.load(inv1_path)
    INV2img = nb.load(inv2_path)

    MP2RAGEimg_img = MP2RAGEimg.get_fdata()
    INV1img_img = INV1img.get_fdata()
    INV2img_img = INV2img.get_fdata()

    if MP2RAGEimg_img.min() >= 0 and MP2RAGEimg_img.max() >= 0.51:
        # converts MP2RAGE to -0.5 to 0.5 scale - assumes that it is getting only positive values
        MP2RAGEimg_img = (
            MP2RAGEimg_img - MP2RAGEimg_img.max() / 2
        ) / MP2RAGEimg_img.max()
        integerformat = 1
    else:
        integerformat = 0

    # computes correct INV1 dataset
    # gives the correct polarity to INV1
    INV1img_img = np.sign(MP2RAGEimg_img) * INV1img_img

    # because the MP2RAGE INV1 and INV2 is a sum of squares data, while the
    # MP2RAGEimg is a phase sensitive coil combination.. some more maths has to
    # be performed to get a better INV1 estimate which here is done by assuming
    # both INV2 is closer to a real phase sensitive combination

    # INV1pos=rootsquares_pos(-MP2RAGEimg.img,INV2img.img,-INV2img.img.^2.*MP2RAGEimg.img);
    INV1pos = rootsquares_pos(
        -MP2RAGEimg_img,
        INV2img_img,
        -(INV2img_img**2) * MP2RAGEimg_img,
    )
    INV1neg = rootsquares_neg(
        -MP2RAGEimg_img,
        INV2img_img,
        -(INV2img_img**2) * MP2RAGEimg_img,
    )

    INV1final = INV1img_img

    INV1final[
        np.absolute(INV1img_img - INV1pos) > np.absolute(INV1img_img - INV1neg)
    ] = INV1neg[np.absolute(INV1img_img - INV1pos) > np.absolute(INV1img_img - INV1neg)]
    INV1final[
        np.absolute(INV1img_img - INV1pos) <= np.absolute(INV1img_img - INV1neg)
    ] = INV1pos[
        np.absolute(INV1img_img - INV1pos) <= np.absolute(INV1img_img - INV1neg)
    ]

    # usually the multiplicative factor shouldn't be greater then 10, but that
    # is not the ase when the image is bias field corrected, in which case the
    # noise estimated at the edge of the imagemight not be such a good measure
    multiplyingFactor = factor
    noiselevel = multiplyingFactor * np.mean(INV2img_img[:, -11:, -11:])

    # % MP2RAGEimgRobustScanner = MP2RAGErobustfunc(INV1img.img, INV2img.img, noiselevel. ^ 2)
    MP2RAGEimgRobustPhaseSensitive = MP2RAGErobustfunc(
        INV1final, INV2img_img, noiselevel**2
    )

    if integerformat == 0:
        MP2RAGEimg_img = MP2RAGEimgRobustPhaseSensitive
    else:
        MP2RAGEimg_img = np.round(4095 * (MP2RAGEimgRobustPhaseSensitive + 0.5))

    # Save image
    MP2RAGEimg_img = nb.casting.float_to_int(MP2RAGEimg_img, "int16")
    new_MP2RAGEimg = nb.Nifti1Image(
        MP2RAGEimg_img, MP2RAGEimg.affine, MP2RAGEimg.header
    )

    return new_MP2RAGEimg


class Mp2rageDenoiseInputSpec(TraitedSpec):
    mp2rage = File(exists=True, desc="mp2rage path", mandatory=True)
    inv1 = File(exists=True, desc="inv1 path", mandatory=True)
    inv2 = File(exists=True, desc="inv2 path", mandatory=True)
    factor = traits.Int(desc="denoising regularization factor", mandatory=True)


class Mp2rageDenoiseOutputSpec(TraitedSpec):
    mp2rage_denoised_path = File(exists=True, desc="mp2rage denoised path")


class Mp2rageDenoise(SimpleInterface):
    """
    Performs mp2rage denoising
    """

    input_spec = Mp2rageDenoiseInputSpec
    output_spec = Mp2rageDenoiseOutputSpec

    def _run_interface(self, runtime):
        mp2ragedenoise_img = _MP2RAGEdenoise(
            self.inputs.mp2rage,
            self.inputs.inv1,
            self.inputs.inv2,
            self.inputs.factor,
        )
        outfile = "mp2rage_denoised.nii.gz"
        nb.save(mp2ragedenoise_img, outfile)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outfile = "mp2rage_denoised.nii.gz"
        outputs["mp2rage_denoised_path"] = os.path.abspath(outfile)

        return outputs
