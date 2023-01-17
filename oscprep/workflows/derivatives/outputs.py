from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
    
from niworkflows.engine.workflows import LiterateWorkflow as Workflow

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
