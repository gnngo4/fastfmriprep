import os

from nipype.interfaces import fsl
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_brainmask_mp2rage_wf(
    name='skullstrip_mp2rage_wf'
):
    """
    Skullstrip 7T MP2RAGE image

    Parameters
    ----------

    Inputs
    ------

    Outputs
    -------

    """
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from oscprep.interfaces.custom_synthstrip import SynthStrip
    from oscprep.interfaces.mp2rage_denoise import Mp2rageDenoise

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                'mp2rage',
                'inv1',
                'inv2',
                'denoise_factor', # mp2rage denoising
                'ss_native_no_csf', # synthstrip on native t1w
                'upsample_resolution', # resolution of upsampled t1w
                'ss_up_no_csf', # synthstrip on upsampled t1w
            ]
        ),
        name='inputnode',
    )

    outputnode = pe.Node(
        niu.IdentityInterface(['mp2rage_brain','mp2rage_brainmask']),
        name='outputnode',
    )

    # Denoise MP2RAGE image
    denoise_mp2rage = pe.Node(
        Mp2rageDenoise(),
        name='denoise_mp2rage'
    )

    # Skullstrip MP2RAGE at native resolution
    synthstrip_native = pe.Node(
        SynthStrip(
            out_file='brain.nii.gz',mask_file='mask.nii.gz'
        ),
        name='synthstrip_native',
    )

    # Upsample MP2RAGE
    upsample = pe.Node(
        fsl.FLIRT(
            output_type='NIFTI_GZ',out_file='upsample.nii.gz'
        ),
        name='upsample_mp2rage',
    )

    # Skullstrip MP2RAGE at upsampled resolution
    synthstrip_up = pe.Node(
        SynthStrip(
            out_file='brain.nii.gz',mask_file='mask.nii.gz'
        ),
        name='synthstrip_upsampled',
    )

    # Resample upsampled synthstrip-ed mask to native resolution
    resample_up_mask = pe.Node(
        fsl.ApplyXFM(
            uses_qform=True,out_file='resampled_mask.nii.gz'
        ),
        name='resample_upsampled_mask',
    )

    # Combine masks from `synthstrip_native` and `synthstrip_up`
    combine_masks = pe.Node(
        fsl.MultiImageMaths(
            op_string="-add %s -bin",out_file='combined_mask.nii.gz'
        ),
        name='combine_masks',
    )

    # Return skullstripped t1w using the combined mask
    apply_mask = pe.Node(
        fsl.ApplyMask(
            out_file='brain.nii.gz'
        ),
        name='apply_mask',
    )

    # Connect nodes
    workflow.connect([
        (inputnode, denoise_mp2rage, [
            ('mp2rage','mp2rage'),
            ('inv1','inv1'),
            ('inv2','inv2'),
            ('denoise_factor','factor')
        ]),
        (inputnode, synthstrip_native, [('ss_native_no_csf','no_csf')]),
        (denoise_mp2rage, synthstrip_native, [('mp2rage_denoised_path','in_file')]),
        (denoise_mp2rage, upsample, [
            ('mp2rage_denoised_path','in_file'),
            ('mp2rage_denoised_path','reference')
        ]),
        (inputnode, upsample, [('upsample_resolution','apply_isoxfm')]),
        (inputnode, synthstrip_up, [('ss_up_no_csf','no_csf')]),
        (upsample, synthstrip_up, [('out_file','in_file')]),
        (synthstrip_up, resample_up_mask, [('mask_file','in_file')]),
        (denoise_mp2rage, resample_up_mask, [('mp2rage_denoised_path','reference')]),
        (synthstrip_native, combine_masks, [('mask_file','in_file')]),
        (resample_up_mask, combine_masks, [(('out_file', _listify),'operand_files')]),
        (combine_masks,apply_mask, [('out_file','mask_file')]),
        (denoise_mp2rage, apply_mask, [('mp2rage_denoised_path','in_file')]),
        (combine_masks, outputnode, [('out_file','mp2rage_brainmask')]),
        (apply_mask, outputnode, [('out_file','mp2rage_brain')])
    ])

    return workflow
                
def init_brainmask_mprage_wf():
    pass

def _listify(x):
    return [x]