import os

from pkg_resources import resource_filename as pkgrf

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_sdc_unwarp_wf(
    name="sdc_unwarp_wf",
):
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from nipype.interfaces import fsl
    
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["bold_metadata","distorted_bold","fmap"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["sdc_warp","undistorted_bold"]
        ),
        name="outputnode"
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
        (inputnode,get_vsm,[
            ('distorted_bold','in_file'),
            ('fmap','fmap_in_file'),
            (('bold_metadata',_get_metadata,"EffectiveEchoSpacing"),'dwell_time'),
        ]),
        (inputnode,vsm_to_warp,[
            ('distorted_bold','reference'),
            (('bold_metadata',_get_fsl_shift_direction),'shift_direction')
        ]),
        (get_vsm,vsm_to_warp,[('shift_out_file','shift_in_file')]),
        (vsm_to_warp,outputnode,[('out_file','sdc_warp')]),
        (inputnode,unwarp_bold,[
            ('distorted_bold','in_file'),
            ('distorted_bold','ref_file')
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


def init_apply_fmap2epi_wf(
    omp_nthreads,
    name="fmap2epi_wf"
):
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from niworkflows.interfaces.fixes import ApplyTransforms
    from nipype.interfaces import fsl
    
    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["fmap","fmap_ref","target_ref","target_mask","fmap2epi_xfm"]
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
    
    fmap2epi = pe.Node(
        ApplyTransforms(invert_transform_flags=[False]),
        name='fmap2epi',
        n_procs=4,
        mem_gb=0.3
    )

    mask_fmap = pe.Node(
        fsl.ApplyMask(),
        name='mask_fmap'
    )

    convert_to_rad = pe.Node(
        fsl.BinaryMaths(
            operation='mul',
            operand_value=6.28
        ),
        name='convert_to_rad'
    )

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
        (fmap2epi,mask_fmap,[('output_image','in_file')]),
        (inputnode,mask_fmap,[('target_mask','mask_file')]),
        (mask_fmap,convert_to_rad,[('out_file','in_file')]),
        (convert_to_rad,outputnode,[('out_file','fmap_bold')])
    ])

    return workflow

def init_wholebrain_bold_syn_preprocessing_wf(name="syn_wholebrain_bold_preprocessing_wf"):
    """
    DEPRECATED
    """

    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from niworkflows.interfaces.fixes import ApplyTransforms
    from niworkflows.interfaces.nibabel import GenerateSamplingReference
    
    workflow = Workflow(name=name)
    
    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                'boldref',
                'in_meta', # metadata correspond to boldref's bold info
                'boldref_mask',
                'in_anat',
                'mask_anat',
                'anat2wholebrainbold_xfm',
                'std2anat_xfm',
            ]
        ),
        name='inputnode',
    )

    outputnode = pe.Node(
        niu.IdentityInterface(['epi_ref','epi_mask','anat_ref','anat_mask','sd_prior']),
        name='outputnode',
    )

    # Mapping & preparing prior knowledge
    # Concatenate transform files:
    # 1) MNI -> anat; 2)
    transform_list = pe.Node(
        niu.Merge(3),
        name="transform_list",
        mem_gb=8,
        run_without_submitting=True
    )
    
    transform_list.inputs.in3 = pkgrf(
        "sdcflows", "data/fmap_atlas_2_MNI152NLin2009cAsym_affine.mat"
    )
    prior2epi = pe.Node(
        ApplyTransforms(
            invert_transform_flags=[False,False,False],
            input_image=pkgrf("sdcflows","data/fmap_atlas.nii.gz"),
        ),
        name="prior2epi",
        n_procs=4,
        mem_gb=0.3,
    )
    anat2epi = pe.Node(
        ApplyTransforms(invert_transform_flags=[False]),
        name='anat2epi',
        n_procs=4,
        mem_gb=0.3
    )
    mask2epi = pe.Node(
        ApplyTransforms(invert_transform_flags=[False], interpolation="MultiLabel"),
        name="mask2epi",
        n_procs=4,
        mem_gb=0.3
    )
    mask_dtype = pe.Node(
        niu.Function(function=_set_dtype, input_names=["in_file","dtype"]),
        name="mask_dtype"
    )
    mask_dtype.inputs.dtype = "uint8"

    merge_output = pe.Node(
        niu.Function(function=_merge_meta),
        name="merge_output",
        run_without_submitting=True,
    )

    sampling_ref = pe.Node(GenerateSamplingReference(), name="sampling_ref")

    # Connect
    workflow.connect([
        (inputnode, sampling_ref, [
            ("boldref","fixed_image"),
            ("in_anat","moving_image")
        ]),
        (inputnode, transform_list, [
            ("std2anat_xfm", "in2"),
            ("anat2wholebrainbold_xfm","in1")
        ]),
        (sampling_ref,prior2epi,[("out_file","reference_image")]),
        (transform_list,prior2epi,[("out","transforms")]),
        (prior2epi,outputnode,[("output_image","sd_prior")]),
        (sampling_ref,anat2epi,[("out_file","reference_image")]),
        (inputnode,anat2epi,[
            ("in_anat","input_image"),
            ("anat2wholebrainbold_xfm","transforms")
        ]),
        (anat2epi,outputnode,[("output_image","anat_ref")]),
        (sampling_ref,mask2epi,[("out_file","reference_image")]),
        (inputnode,mask2epi,[
            ("mask_anat","input_image"),
            ("anat2wholebrainbold_xfm","transforms")
        ]),
        (mask2epi,mask_dtype,[("output_image","in_file")]),
        (mask_dtype,outputnode,[("out","anat_mask")]),
        (inputnode,outputnode,[("boldref_mask","epi_mask")]),
        (inputnode,merge_output,[
            ('in_meta','meta_list'),
            ('boldref','epi_ref')
        ]),
        (merge_output,outputnode,[("out","epi_ref")])
    ])

    return workflow

def _set_dtype(in_file, dtype="int16"):
    """Change the dtype of an image."""
    import numpy as np
    import nibabel as nb

    img = nb.load(in_file)
    if img.header.get_data_dtype() == np.dtype(dtype):
        return in_file

    from nipype.utils.filemanip import fname_presuffix

    out_file = fname_presuffix(in_file, suffix=f"_{dtype}")
    hdr = img.header.copy()
    hdr.set_data_dtype(dtype)
    img.__class__(img.dataobj, img.affine, hdr).to_filename(out_file)
    return out_file

def _merge_meta(epi_ref, meta_list):
    """Prepare a tuple of EPI reference and metadata."""
    return (epi_ref,meta_list[0])