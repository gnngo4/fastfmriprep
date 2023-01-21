import os

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
    
from niworkflows.engine.workflows import LiterateWorkflow as Workflow

"""
BRAINMASK DIR
"""

def init_anat_brainmask_derivatives_wf(
    output_dir,
    t1w_brain_base,
    t1w_brainmask_base,
    out_path_base='brainmask',
    name='anat_brainmask_derivatives_wf'
):
    
    from niworkflows.interfaces.bids import DerivativesDataSink
    
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(fields=["t1w_brain","t1w_brainmask"]),
        name="inputnode",
    )
    
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["t1w_brain","t1w_brainmask"]),
        name="outputnode",
    )
    
    ds_t1w_brain = pe.Node(
        DerivativesDataSink(base_directory=output_dir, out_path_base=out_path_base, desc="brain", compress=True),
        name="ds_t1w_brain",
        run_without_submitting=True
    )
    ds_t1w_brain.inputs.source_file = f"{output_dir}/{t1w_brain_base}"
    
    ds_t1w_brainmask = pe.Node(
        DerivativesDataSink(base_directory=output_dir, out_path_base=out_path_base, desc="brain", compress=True),
        name="ds_t1w_brainmask",
        run_without_submitting=True
    )
    ds_t1w_brainmask.inputs.source_file = f"{output_dir}/{t1w_brainmask_base}"
    
    workflow.connect([
        (inputnode, ds_t1w_brain, [('t1w_brain','in_file')]),
        (inputnode, ds_t1w_brainmask, [('t1w_brainmask','in_file')]),
        (ds_t1w_brain, outputnode, [('out_file','t1w_brain')]),
        (ds_t1w_brainmask, outputnode, [('out_file','t1w_brainmask')])
    ])
    
    return workflow

def init_bold_brainmask_derivatives_wf(
    output_dir,
    bold_brain_base,
    bold_brainmask_base,
    bold_type,
    out_path_base='brainmask',
    name=None
):
    
    from niworkflows.interfaces.bids import DerivativesDataSink
    from nipype.pipeline import engine as pe

    if name is None:
        name = f'{bold_type}_bold_brainmask_derivatives_wf'
        
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(fields=["bold_brain","bold_brainmask"]),
        name="inputnode",
    )
    
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["bold_brain","bold_brainmask"]),
        name="outputnode",
    )
    
    ds_bold_brain = pe.Node(
        DerivativesDataSink(base_directory=output_dir, out_path_base=out_path_base, desc="brain", compress=True),
        name=f"ds_bold_{bold_type}_brain",
        run_without_submitting=True
    )
    ds_bold_brain.inputs.source_file = f"{output_dir}/{bold_brain_base}"
    
    ds_bold_brainmask = pe.Node(
        DerivativesDataSink(base_directory=output_dir, out_path_base=out_path_base, desc="brain", compress=True),
        name=f"ds_bold_{bold_type}_brainmask",
        run_without_submitting=True
    )
    ds_bold_brainmask.inputs.source_file = f"{output_dir}/{bold_brainmask_base}"
    
    workflow.connect([
        (inputnode, ds_bold_brain, [('bold_brain','in_file')]),
        (inputnode, ds_bold_brainmask, [('bold_brainmask','in_file')]),
        (ds_bold_brain, outputnode, [('out_file','bold_brain')]),
        (ds_bold_brainmask, outputnode, [('out_file','bold_brainmask')])
    ])
    
    return workflow

def init_wholebrain_bold_preproc_derivatives_wf(
    output_dir,
    sub_id,
    ses_id,
    bold_ref_base,
    wholebrain_bold_to_t1_mat_base,
    wholebrain_bold_to_t1_svg_base,
    workflow_name_base='wholebrain_bold',
    out_path_base='bold_preproc',
    name=None
):
    
    from niworkflows.interfaces.bids import DerivativesDataSink
    from nipype.interfaces.io import ExportFile
    from nipype.pipeline import engine as pe

    if name is None:
        name = f'{workflow_name_base}_preproc_derivatives_wf'
        
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(fields=[
            'bold_ref',
            'wholebrain_bold_to_t1_mat',
            'wholebrain_bold_to_t1_svg',
        ]),
        name="inputnode",
    )
    
    # Bold reference image in t1 space
    ds_bold_ref = pe.Node(
        DerivativesDataSink(base_directory=output_dir, out_path_base=out_path_base,compress=True),
        name=f"ds_{workflow_name_base}_bold_reference",
        run_without_submitting=True
    )
    ds_bold_ref.inputs.source_file = f"{output_dir}/{bold_ref_base}"
    
    """
    Transformations
    """
    sub_ses_reg_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/reg"
    sub_ses_figures_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/figures"
    for _dir in [sub_ses_reg_dir,sub_ses_figures_dir]:
        if not os.path.isdir(_dir):
            os.makedirs(_dir)

    ds_wholebrain_to_t1_mat = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{wholebrain_bold_to_t1_mat_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_t1_mat",
        run_without_submitting=True
    )
    
    ds_wholebrain_to_t1_svg = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{wholebrain_bold_to_t1_svg_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_t1_svg",
        run_without_submitting=True
    )

    workflow.connect([
        (inputnode, ds_bold_ref, [('bold_ref','in_file')]),
        (inputnode, ds_wholebrain_to_t1_mat,[('wholebrain_bold_to_t1_mat','in_file')]),
        (inputnode, ds_wholebrain_to_t1_svg,[('wholebrain_bold_to_t1_svg','in_file')]),
    ])
    
    return workflow


def init_slab_bold_preproc_derivatives_wf(
    output_dir,
    sub_id,
    ses_id,
    bold_ref_base,
    bold_brainmask_base,
    bold_preproc_base,
    bold_confounds_base,
    bold_roi_svg_base,
    bold_acompcor_csf_base,
    bold_acompcor_wm_base,
    bold_acompcor_wmcsf_base,
    bold_tcompcor_base,
    bold_crownmask_base,
    bold_hmc_base,
    bold_sdc_warp_base,
    slab_bold_to_wholebrain_bold_mat_base,
    slab_bold_to_wholebrain_bold_svg_base,
    slab_bold_to_t1_warp_base,
    workflow_name_base,
    out_path_base='bold_preproc',
    name=None
):
    
    from niworkflows.interfaces.bids import DerivativesDataSink
    from nipype.interfaces.io import ExportFile
    from nipype.pipeline import engine as pe

    if name is None:
        name = f'{workflow_name_base}_preproc_derivatives_wf'
        
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(fields=[
            'bold_ref',
            'bold_brainmask',
            'bold_preproc',
            'bold_confounds',
            'bold_roi_svg',
            'bold_acompcor_csf',
            'bold_acompcor_wm',
            'bold_acompcor_wmcsf',
            'bold_tcompcor',
            'bold_crownmask',
            'bold_hmc',
            'bold_sdc_warp',
            'slab_bold_to_wholebrain_bold_mat',
            'slab_bold_to_wholebrain_bold_svg',
            'slab_bold_to_t1_warp'
        ]),
        name="inputnode",
    )
    
    # Make directories
    sub_ses_reg_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/reg"
    sub_ses_roi_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/roi"
    sub_ses_figures_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/figures"
    for _dir in [
        sub_ses_reg_dir,
        sub_ses_roi_dir,
        sub_ses_figures_dir
    ]:
        if not os.path.isdir(_dir):
            os.makedirs(_dir)
    
    # Bold reference image in t1 space
    ds_bold_ref = pe.Node(
        DerivativesDataSink(base_directory=output_dir, out_path_base=out_path_base,compress=True),
        name=f"ds_{workflow_name_base}_bold_reference",
        run_without_submitting=True
    )
    ds_bold_ref.inputs.source_file = f"{output_dir}/{bold_ref_base}"
    
    # Bold brainmask image in t1 space
    ds_bold_brainmask = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_brainmask_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_brainmask",
        run_without_submitting=True
    )
    
    # Preprocessed bold in t1 space
    ds_bold_preproc = pe.Node(
        DerivativesDataSink(base_directory=output_dir, out_path_base=out_path_base,compress=True),
        name=f"ds_{workflow_name_base}_bold_preproc",
        run_without_submitting=True
    )
    ds_bold_preproc.inputs.source_file = f"{output_dir}/{bold_preproc_base}"

    """
    Confound files
    """
    ds_bold_confounds = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_confounds_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_confounds",
        run_without_submitting=True
    )
    ds_bold_roi_svg = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_roi_svg_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_roi_svg",
        run_without_submitting=True
    )
    ds_bold_acompcor_csf = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_acompcor_csf_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_acompcor_csf",
        run_without_submitting=True
    )
    ds_bold_acompcor_wm = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_acompcor_wm_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_acompcor_wm",
        run_without_submitting=True
    )
    ds_bold_acompcor_wmcsf = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_acompcor_wmcsf_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_acompcor_wmcsf",
        run_without_submitting=True
    )
    ds_bold_tcompcor = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_tcompcor_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_tcompcor",
        run_without_submitting=True
    )
    ds_bold_crownmask = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_crownmask_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_bold_crownmask",
        run_without_submitting=True
    )
    
    """
    Transformations
    """
    
    '''
    ds_bold_hmc = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_hmc_base}",
        ),
        name=f"ds_{workflow_name_base}_hmc",
        run_without_submitting=True
    )
    '''
    ds_bold_sdc = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_sdc_warp_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_sdc_warp",
        run_without_submitting=True
    )
    ds_slab_to_wholebrain_mat = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slab_bold_to_wholebrain_bold_mat_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_wholebrain_mat",
        run_without_submitting=True
    )
    ds_slab_to_wholebrain_svg = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slab_bold_to_wholebrain_bold_svg_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_wholebrain_svg",
        run_without_submitting=True
    )
    ds_slab_to_t1 = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slab_bold_to_t1_warp_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_t1_warp",
        run_without_submitting=True
    )

    workflow.connect([
        (inputnode, ds_bold_ref, [('bold_ref','in_file')]),
        (inputnode, ds_bold_brainmask, [('bold_brainmask','in_file')]),
        (inputnode, ds_bold_preproc,[('bold_preproc','in_file')]),
        #(inputnode, ds_bold_hmc,[('bold_hmc','in_file')]),
        (inputnode, ds_bold_confounds, [('bold_confounds','in_file')]),
        (inputnode, ds_bold_roi_svg, [('bold_roi_svg','in_file')]),
        (inputnode, ds_bold_acompcor_csf, [('bold_acompcor_csf','in_file')]),
        (inputnode, ds_bold_acompcor_wm, [('bold_acompcor_wm','in_file')]),
        (inputnode, ds_bold_acompcor_wmcsf, [('bold_acompcor_wmcsf','in_file')]),
        (inputnode, ds_bold_tcompcor, [('bold_tcompcor','in_file')]),
        (inputnode, ds_bold_crownmask, [('bold_crownmask','in_file')]),
        (inputnode, ds_bold_sdc,[('bold_sdc_warp','in_file')]),
        (inputnode, ds_slab_to_wholebrain_mat,[('slab_bold_to_wholebrain_bold_mat','in_file')]),
        (inputnode, ds_slab_to_wholebrain_svg,[('slab_bold_to_wholebrain_bold_svg','in_file')]),
        (inputnode, ds_slab_to_t1,[('slab_bold_to_t1_warp','in_file')]),
    ])
    
    return workflow