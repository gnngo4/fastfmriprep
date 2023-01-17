from nipype.interfaces.base import (
    File, 
    SimpleInterface, 
    TraitedSpec, 
    traits
)

import nibabel as nb
import numpy as np
import os


def _LowPassFilterBold(bold_path, repetition_time, lp=.2):
    """
    """
    import nibabel as nib
    from nilearn import image
    import os

    lp_thr, hp_thr = lp, None

    cleaned_img = image.clean_img(
        bold_path,
        detrend=False,
        standardize=False,
        t_r=repetition_time,
        ensure_finite=True,
        low_pass=lp_thr,
        high_pass=hp_thr,
    )

    save_bold = 'proc-lp_bold.nii.gz'
    nib.save(cleaned_img, save_bold)

class LowPassFilterBoldInputSpec(TraitedSpec):
    bold_path = File(exists=True,desc="bold path",mandatory=True)
    repetition_time = traits.Float(desc="repetition time (TR)",mandatory=True)
    low_pass_threshold=traits.Float(desc="lowpass filtering threshold",mandatory=True)

class LowPassFilterBoldOutputSpec(TraitedSpec):
    lp_bold_path = File(exists=True,desc="lp-filtered bold path")

class LowPassFilterBold(SimpleInterface):
    """
    """
    input_spec = LowPassFilterBoldInputSpec
    output_spec = LowPassFilterBoldOutputSpec

    def _run_interface(self,runtime):

        _LowPassFilterBold(
            self.inputs.bold_path,
            self.inputs.repetition_time,
            lp=self.inputs.low_pass_threshold
        )

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outfile = 'proc-lp_bold.nii.gz'
        outputs["lp_bold_path"] = os.path.abspath(outfile)

        return outputs