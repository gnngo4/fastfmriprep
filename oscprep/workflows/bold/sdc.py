import os

from pkg_resources import resource_filename as pkgrf

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_bold_sdc_wf(
    use_fsl_gre_fmap=False,
    fmap_metadata=None,
    name="bold_sdc_wf",
):
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from oscprep.workflows.registration.apply import init_apply_fmap_to_bold_wf
    from nipype.interfaces import fsl
    
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["bold_metadata","fmap","fmap_ref","target_ref","target_mask","fmap2epi_xfm"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["sdc_warp","undistorted_bold"]
        ),
        name="outputnode"
    )

    apply_fmap_to_bold_wf = init_apply_fmap_to_bold_wf(
        use_fsl_gre_fmap=use_fsl_gre_fmap,
        fmap_metadata=fmap_metadata
    )

    get_vsm = pe.Node(
        fsl.FUGUE(
            save_shift=True,
        ),
        name="get_vsm"
    )

    vsm_to_warp = pe.Node(
        fsl.ConvertWarp(
            abswarp=True,
            output_type = "NIFTI_GZ"
        ),
        name='vsm_to_warp'
    )

    unwarp_bold = pe.Node(
        fsl.ApplyWarp(),
        name='unwarp_bold'
    )
    
    # Connect
    workflow.connect([
        (inputnode,apply_fmap_to_bold_wf,[
            ('fmap2epi_xfm','inputnode.fmap2epi_xfm'),
            ('fmap_ref','inputnode.fmap_ref'),
            ('fmap','inputnode.fmap'),
            ('target_ref','inputnode.target_ref'),
            ('target_ref','inputnode.target_mask')
        ]),
        (apply_fmap_to_bold_wf,get_vsm,[('outputnode.fmap_bold','fmap_in_file')]),
        (inputnode,get_vsm,[
            ('target_ref','in_file'),
            (('bold_metadata',_get_metadata,"EffectiveEchoSpacing"),'dwell_time'),
        ]),
        (inputnode,vsm_to_warp,[
            ('target_ref','reference'),
            (('bold_metadata',_get_fsl_shift_direction),'shift_direction')
        ]),
        (get_vsm,vsm_to_warp,[('shift_out_file','shift_in_file')]),
        (vsm_to_warp,outputnode,[('out_file','sdc_warp')]),
        (inputnode,unwarp_bold,[
            ('target_ref','in_file'),
            ('target_ref','ref_file')
        ]),
        (vsm_to_warp,unwarp_bold,[('out_file','field_file')]),
        (unwarp_bold,outputnode,[('out_file','undistorted_bold')]),
    ])

    return workflow

def _get_metadata(metadata_dict,_key):

    assert _key in metadata_dict, f"{_key} not found in metadata."

    return metadata_dict[_key]

def _get_fsl_shift_direction(metadata_dict):
    
    assert 'PhaseEncodingDirection' in metadata_dict, f"PhaseEncodingDirection not found in metadata."

    pe_dir = metadata_dict['PhaseEncodingDirection']
    fsl_pe_mappings = {
        'i': 'x',
        'i-': 'x-',
        'j': 'y',
        'j-': 'y-',
        'k': 'z',
        'k-': 'z-',
    }

    return fsl_pe_mappings[pe_dir]
