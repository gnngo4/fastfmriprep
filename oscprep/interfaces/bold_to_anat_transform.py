from nipype.interfaces.base import (
    File, 
    InputMultiObject,
    SimpleInterface,
    TraitedSpec, 
    traits
)

import os

BOLD_TO_T1_BASE = 'space-t1_bold.nii.gz'

def _BoldToT1Transform(bold_path,hmc_mats,bold_to_t1_warp,t1_resampled,repetition_time):
    
    from nipype.interfaces import fsl

    split_bold = fsl.Split(
        dimension='t',
        in_file=bold_path
    )
    res = split_bold.run()
    bold_list = res.outputs.out_files

    vol_t1_bold = []
    assert len(bold_list) == len(hmc_mats), f"hmc mats and splitted bold data are not equal lengths."
    for vol_mat, vol_bold in zip(hmc_mats,bold_list):
        # Combine `vol_mat` with `bold_to_t1_warp``
        convert_warp = fsl.ConvertWarp(
            reference=t1_resampled,
            premat=vol_mat,
            warp1=bold_to_t1_warp
        )
        res = convert_warp.run()
        vol_warp = res.outputs.out_file
        # Apply the new warp to `vol_bold`
        apply_warp = fsl.ApplyWarp(
            in_file=vol_bold,
            ref_file=t1_resampled,
            field_file=vol_warp
        )
        res = apply_warp.run()
        vol_out = res.outputs.out_file

        vol_t1_bold.append(vol_out)

    merge_t1_bolds = fsl.Merge(
        in_files = vol_t1_bold,
        dimension='t',
        output_type='NIFTI_GZ',
        tr=repetition_time,
        merged_file=BOLD_TO_T1_BASE
    )
    merge_t1_bolds.run()
    assert os.path.exists(BOLD_TO_T1_BASE), f"{BOLD_TO_T1_BASE} was not created."

class BoldToT1TransformInputSpec(TraitedSpec):
    bold_path = File(exists=True,desc="bold path",mandatory=True)
    hmc_mats = InputMultiObject(File(exists=True),desc="list of hmc affine mat files",mandatory=True)
    bold_to_t1_warp = File(exists=True,desc="bold to t1 warp",mandatory=True)
    t1_resampled = File(exists=True,desc="t1 resampled to resolution of bold data",mandatory=True)
    repetition_time = traits.Float(desc="repetition time (TR)",mandatory=True)

class BoldToT1TransformOutputSpec(TraitedSpec):
    t1_bold_path = File(exists=True,desc="transformed-to-t1 bold path")

class BoldToT1Transform(SimpleInterface):

    input_spec = BoldToT1TransformInputSpec
    output_spec = BoldToT1TransformOutputSpec

    def _run_interface(self,runtime):

        _BoldToT1Transform(
            self.inputs.bold_path,
            self.inputs.hmc_mats,
            self.inputs.bold_to_t1_warp,
            self.inputs.t1_resampled,
            self.inputs.repetition_time
        )

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["t1_bold_path"] = os.path.abspath(BOLD_TO_T1_BASE)

        return outputs