import os

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_itk_to_fsl_affine_wf(
    name='itk_to_fsl_affine_wf'
):
    """
    Convert affine transformation from itk-to-fsl format.

    Parameters
    ----------

    Inputs
    ------

    Outputs
    -------

    """
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
   
    from oscprep.interfaces.c3 import C3dAffineTool

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                'itk_affine',
                'source',
                'reference'
            ]
        ),
        name='inputnode'
    )

    outputnode = pe.Node(niu.IdentityInterface(['fsl_affine']), name='outputnode')

    itk_to_fsl = pe.Node(C3dAffineTool(ras2fsl=True),name='itk_to_fsl')
    itk_to_fsl.inputs.fsl_transform = 'fsl_affine.mat'

    # Connect
    workflow.connect([
        (inputnode, itk_to_fsl, [
            ('source','source_file'),
            ('reference','reference_file'),
            ('itk_affine','itk_transform')
        ]),
        (itk_to_fsl,outputnode,[('fsl_transform','fsl_affine')])
    ])

    return workflow

def init_fsl_merge_transforms_wf(
    name='fsl_merge_transforms_wf'
):
    """
    Combine the following transformations:
    (1) slab SDC warp
    (2) slab-bold to wholebrain-bold affine
        - affine was generated from images that were sdc-ed
    (3) wholebrain-bold to t1 affine
        - affine was generated fro a wholebrain-bold sdc-ed and a t1 preprocessed with freesurfer

    Parameters
    ----------

    Inputs
    ------

    Outputs
    -------

    """
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from nipype.interfaces import fsl
    from niworkflows.interfaces.nibabel import GenerateSamplingReference
    
    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                'slab_sdc_warp',
                'slab2wholebrain_aff',
                'wholebrain2anat_aff',
                'source',
                'reference'
            ]
        ),
        name='inputnode'
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            [
                'slab2anat_warp',
                'reference_resampled'
            ]
        ),
        name='outputnode'
    )

    slab2wholebrain_aff = pe.Node(
        fsl.ConvertXFM(
            out_file = 'merged_affine.txt',
            concat_xfm = True,
        ),
        name='slab2wholebrain_aff'
    )

    gen_ref = pe.Node(
        GenerateSamplingReference(),
        name='generate_reference'
    )

    slab2wholebrain_warp = pe.Node(
        fsl.ConvertWarp(),
        name='slab2wholebrain_warp'
    )

    # Connect
    workflow.connect([
        (inputnode,slab2wholebrain_aff,[
            ('wholebrain2anat_aff','in_file2'),
            ('slab2wholebrain_aff','in_file')
        ]),
        (inputnode,gen_ref,[
            ('source','moving_image'),
            ('reference','fixed_image')
        ]),
        (gen_ref,slab2wholebrain_warp,[('out_file','reference')]),
        (inputnode,slab2wholebrain_warp,[('slab_sdc_warp','warp1')]),
        (slab2wholebrain_aff,slab2wholebrain_warp,[('out_file','postmat')]),
        (gen_ref,outputnode,[('out_file','reference_resampled')]),
        (slab2wholebrain_warp,outputnode,[('out_file','slab2anat_warp')])
    ])

    return workflow