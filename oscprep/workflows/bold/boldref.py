import os

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_boldref_wf(
    bold,
    split_vol_id=0,
    name='get_bold_reference_wf'
):
    """
    Get the bold reference image corresponding
    to the 4D bold image

    Parameters
    ----------

    Inputs
    ------

    Outputs
    -------

    """
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(['bold']),
        name='inputnode',
    )

    outputnode = pe.Node(
        niu.IdentityInterface(['boldref']),
        name='outputnode',
    )

    sbref = bold.replace('_bold.nii.gz','_sbref.nii.gz')
    if os.path.exists(sbref):

        workflow.connect([(inputnode, outputnode, [(('bold',_get_sbref),'boldref')])])

        return workflow

    else:

        from nipype.interfaces.fsl.utils import Split

        split_bold = pe.Node(
            Split(
                dimension='t',
                out_base_name='split_bold_'
            ),
            name='split_bold'
        )

        workflow.connect([
            (inputnode, split_bold, [('bold','in_file')]),
            (split_bold, outputnode, [(('out_files',_get_split_volume,split_vol_id),'boldref')])
        ])
        
        return workflow


def _get_sbref(bold):

    return bold.replace('_bold.nii.gz','_sbref.nii.gz')

def _get_split_volume(out_files,vol_id):

    return out_files[vol_id]