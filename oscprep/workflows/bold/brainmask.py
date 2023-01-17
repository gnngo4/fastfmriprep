import os

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_bold_wholebrain_brainmask_wf(
    omp_nthreads=8,
    name='skullstrip_wholebrain_bold_wf'
):
    """
    Skullstrip wholebrain sbref by using a t1 brainmask
    and a t1-to-wholebrain-bold registration approach

    Parameters
    ----------

    Inputs
    ------

    Outputs
    -------

    """
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
    
    from fmriprep.workflows.bold.registration import init_bbreg_wf
    from niworkflows.interfaces.fixes import FixHeaderApplyTransforms as ApplyTransforms
    from nipype.interfaces.fsl import ApplyMask
    
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                'wholebrain_bold',
                'fsnative2t1w_xfm',
                'subjects_dir',
                'subject_id', #BBRegister
                't1w_dseg',
                't1w_brain',
                't1w_brainmask', # from smriprep
            ]
        ),
        name='inputnode',
    )

    outputnode = pe.Node(
        niu.IdentityInterface(['brain','brainmask','dseg','itk_bold_to_t1','itk_t1_to_bold']),
        name='outputnode',
    )

    # bbreg t1-to-wholebrain-bold
    bbr_wf = init_bbreg_wf(use_bbr=True,bold2t1w_dof=9,bold2t1w_init='register',omp_nthreads=omp_nthreads)

    # transform t1w_brainmask to wholebrain-bold space
    t1brainmask_to_bold = pe.Node(
        ApplyTransforms(
            interpolation="MultiLabel",
            float=True
        ),
        name='wholebrain_bold_brainmask'
    )
    # transform t1w_dseg to wholebrain-bold space
    t1dseg_to_bold = pe.Node(
        ApplyTransforms(
            interpolation="MultiLabel",
            float=True
        ),
        name='wholebrain_bold_dseg'
    )

    # Return skullstripped wholebrain-bold
    apply_mask = pe.Node(
        ApplyMask(
            out_file='brain.nii.gz'
        ),
        name='apply_mask',
    )

    # Connect
    workflow.connect([
        (inputnode, bbr_wf, [
            ('wholebrain_bold','inputnode.in_file'),
            ('fsnative2t1w_xfm','inputnode.fsnative2t1w_xfm'),
            ('subjects_dir','inputnode.subjects_dir'),
            ('subject_id','inputnode.subject_id'),
            ('t1w_dseg','inputnode.t1w_dseg'),
            ('t1w_brain','inputnode.t1w_brain')
        ]),
        (bbr_wf, t1brainmask_to_bold, [('outputnode.itk_t1_to_bold','transforms')]),
        (inputnode, t1brainmask_to_bold, [
            ('t1w_brainmask','input_image'),
            ('wholebrain_bold','reference_image')
        ]),
        (bbr_wf, t1dseg_to_bold, [('outputnode.itk_t1_to_bold','transforms')]),
        (inputnode, t1dseg_to_bold, [
            ('t1w_dseg','input_image'),
            ('wholebrain_bold','reference_image')
        ]),
        (t1brainmask_to_bold, apply_mask, [('output_image','mask_file')]),
        (inputnode, apply_mask, [('wholebrain_bold','in_file')]),
        (bbr_wf, outputnode, [
            ('outputnode.itk_bold_to_t1','itk_bold_to_t1'),
            ('outputnode.itk_t1_to_bold','itk_t1_to_bold')
        ]),
        (apply_mask,outputnode,[('out_file','brain')]),
        (t1brainmask_to_bold,outputnode,[('output_image','brainmask')]),
        (t1dseg_to_bold,outputnode,[('output_image','dseg')])
    ])

    return workflow

def init_bold_slab_brainmask_wf(
    omp_nthreads=8,
    name='skullstrip_slab_bold_wf'
):
    """
    Skullstrip slab sbref by using a t1 brainmask
    and a t1-to-wholebrain-bold-to-slab-bold registration 
    approach

    Parameters
    ----------

    Inputs
    ------

    Outputs
    -------

    """
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
    
    from fmriprep.workflows.bold.registration import init_fsl_bbr_wf
    from niworkflows.interfaces.fixes import FixHeaderApplyTransforms as ApplyTransforms
    from nipype.interfaces.fsl import ApplyMask
    
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                'slab_bold',
                'wholebrain_bold_dseg',
                'wholebrain_bold',
                'wholebrain_bold_brainmask' # Generated from ``init_brainmask_wholebrain_bold_wf``
            ]
        ),
        name='inputnode',
    )

    outputnode = pe.Node(
        niu.IdentityInterface(['brain','brainmask','itk_bold_to_t1','itk_t1_to_bold']), # bold == slab & t1 == wholebrain
        name='outputnode',
    )

    # fsl_bbr slab-bold-to-wholebrain-bold
    fsl_bbr_wf = init_fsl_bbr_wf(use_bbr=True,bold2t1w_dof=6,bold2t1w_init='register',omp_nthreads=omp_nthreads)

    # transform t1w_brainmask to wholebrain-bold space
    boldbrainmask_to_slab = pe.Node(
        ApplyTransforms(
            interpolation="MultiLabel",
            float=True
        ),
        name='slab_bold_brainmask'
    )

    # Return skullstripped slab-bold
    apply_mask = pe.Node(
        ApplyMask(
            out_file='brain.nii.gz'
        ),
        name='apply_mask',
    )
    
    # Connect
    workflow.connect([
        (inputnode, fsl_bbr_wf, [
            ('slab_bold','inputnode.in_file'),
            ('wholebrain_bold_dseg','inputnode.t1w_dseg'),
            ('wholebrain_bold','inputnode.t1w_brain')
        ]),
        (fsl_bbr_wf, boldbrainmask_to_slab, [('outputnode.itk_t1_to_bold','transforms')]),
        (inputnode, boldbrainmask_to_slab, [
            ('wholebrain_bold_brainmask','input_image'),
            ('slab_bold','reference_image')
        ]),
        (boldbrainmask_to_slab, apply_mask, [('output_image','mask_file')]),
        (inputnode, apply_mask, [('slab_bold','in_file')]),
        (fsl_bbr_wf, outputnode, [
            ('outputnode.itk_bold_to_t1','itk_bold_to_t1'),
            ('outputnode.itk_t1_to_bold','itk_t1_to_bold')
        ]),
        (apply_mask,outputnode,[('out_file','brain')]),
        (boldbrainmask_to_slab,outputnode,[('output_image','brainmask')])
    ])

    return workflow
