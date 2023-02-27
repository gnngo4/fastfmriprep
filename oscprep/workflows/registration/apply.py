from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_apply_fmap_to_bold_wf(
    use_fsl_gre_fmap=False,
    fmap_metadata=None,
    name="apply_fmap_to_bold_wf"
):
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from niworkflows.interfaces.fixes import ApplyTransforms
    from nipype.interfaces import fsl
    
    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["fmap","fmap_ref","fmap_metadata","target_ref","target_mask","fmap2epi_xfm"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["target_ref","fmap_bold"]
        ),
        name="outputnode"
    )

    # QA for fieldmap-magnitude to epi-space
    fmapmag2epi = pe.Node(
        ApplyTransforms(invert_transform_flags=[False]),
        name='fmapmag2epi',
        n_procs=4,
        mem_gb=0.3
    )
    
    # if `use_fsl_gre_fmap` is True, then fmap 
    # is a phasediff image instead
    fmap2epi = pe.Node(
        ApplyTransforms(invert_transform_flags=[False]),
        name='fmap2epi',
        n_procs=4,
        mem_gb=0.3
    )
    
    # Connect
    workflow.connect([
        (inputnode,fmapmag2epi,[
            ('fmap_ref','input_image'),
            ('target_ref','reference_image'),
            ('fmap2epi_xfm','transforms')
        ]),
        (fmapmag2epi,outputnode,[('output_image','target_ref')]),
        (inputnode,fmap2epi,[
            ('fmap','input_image'),
            ('target_ref','reference_image'),
            ('fmap2epi_xfm','transforms')
        ]),
    ])
    
    if use_fsl_gre_fmap:

        from oscprep.interfaces.fsl_prepare_fieldmap import FSLPrepareFieldmap

        assert fmap_metadata is not None, f"`fmap_metadata` must be specified."
        inputnode.inputs.fmap_metadata = fmap_metadata
        # Mask fmap magnitude image
        mask_fmap_mag = pe.Node(
            fsl.ApplyMask(),
            name='mask_fmap_mag'
        )
        # Generate fmap (rad/s) using fsl_prepare_fieldmap
        prepare_fmap = pe.Node(
            FSLPrepareFieldmap(out_image = 'fmap_rads.nii.gz'),
            name='prepare_fmap',
        )

        # Connect
        workflow.connect([
            (fmapmag2epi,mask_fmap_mag,[('output_image','in_file')]),
            (inputnode,mask_fmap_mag,[('target_mask','mask_file')]),
            (mask_fmap_mag,prepare_fmap,[('out_file','magnitude_image')]),
            (fmap2epi,prepare_fmap,[('output_image','phase_image')]),
            (inputnode,prepare_fmap,[(('fmap_metadata',_get_delta_te),'deltaTE')]),
            (prepare_fmap,outputnode,[('out_image','fmap_bold')])
        ])

    else:

        # Mask fmap
        mask_fmap = pe.Node(
            fsl.ApplyMask(),
            name='mask_fmap'
        )
        # Convert fmap units from Hz to rads
        convert_to_rad = pe.Node(
            fsl.BinaryMaths(
                operation='mul',
                operand_value=6.28
            ),
            name='convert_to_rad'
        )

        # Connect
        workflow.connect([
            (fmap2epi,mask_fmap,[('output_image','in_file')]),
            (inputnode,mask_fmap,[('target_mask','mask_file')]),
            (mask_fmap,convert_to_rad,[('out_file','in_file')]),
            (convert_to_rad,outputnode,[('out_file','fmap_bold')])
        ])

    return workflow

def init_apply_bold_to_anat_wf(
    slab_bold_quick=False,
    name="apply_bold_to_t1_wf"
):
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from oscprep.interfaces.bold_to_anat_transform import BoldToT1Transform
    
    from nipype.interfaces import fsl

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_file",
                "bold_ref",
                "bold_metadata",
                "fsl_hmc_affines",
                "bold_to_t1_warp",
                "t1_resampled"
            ]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["t1_space_bold",'t1_space_boldref']
        ),
        name="outputnode"
    )

    apply_bold_to_t1 = pe.Node(
        BoldToT1Transform(debug=slab_bold_quick),
        name="apply_bold_to_t1"
    )

    apply_bold_ref_to_t1 = pe.Node(
        fsl.ApplyWarp(),
        name='apply_bold_ref_to_t1'
    )

    workflow.connect([
        (inputnode,apply_bold_to_t1,[
            ("bold_file","bold_path"),
            (("bold_metadata",_get_metadata,"RepetitionTime"),"repetition_time"),
            ("fsl_hmc_affines","hmc_mats"),
            ("bold_to_t1_warp","bold_to_t1_warp"),
            ("t1_resampled","t1_resampled")
        ]),
        (apply_bold_to_t1,outputnode,[('t1_bold_path','t1_space_bold')]),
        (inputnode,apply_bold_ref_to_t1,[
            ('bold_ref','in_file'),
            ('t1_resampled','ref_file'),
            ('bold_to_t1_warp','field_file'),
        ]),
        (apply_bold_ref_to_t1,outputnode,[('out_file','t1_space_boldref')])
    ])

    return workflow

def _get_metadata(metadata_dict,_key):

    assert _key in metadata_dict, f"{_key} not found in metadata."

    return metadata_dict[_key]

def _get_delta_te(metadata_dict):

    for _key in ['EchoTime1', 'EchoTime2']:
        assert _key in metadata_dict, f"{_key} not found in metadata."

    delta_te = ( float(metadata_dict['EchoTime2']) - float(metadata_dict['EchoTime1']) ) * 1000

    return delta_te