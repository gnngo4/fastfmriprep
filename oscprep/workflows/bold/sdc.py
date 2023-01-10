import os

from pkg_resources import resource_filename as pkgrf

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_coeff2epi_wf(
    omp_nthreads,
    debug=True,
    write_coeff=False,
    name="coeff2epi_wf"
):
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from niworkflows.interfaces.fixes import ApplyTransforms
    
    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["fmap_coeff","fmap_ref","target_ref","fmap2epi_xfm"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["target_ref","fmap_coeff"]
        ),
        name="outputnode"
    )

    fmap2epi = pe.Node(
        ApplyTransforms(invert_transform_flags=[False]),
        name='fmap2epi',
        n_procs=4,
        mem_gb=0.3
    )

    from sdcflows.interfaces.bspline import TransformCoefficients
    # Map the coefficients into the EPI space
    map_coeff = pe.Node(TransformCoefficients(),name="map_coeff")
    map_coeff.interface._always_run=debug

    workflow.connect([
        (inputnode,fmap2epi,[
            ('fmap_ref','input_image'),
            ('target_ref','reference_image'),
            ('fmap2epi_xfm','transforms'),
        ]),
        (fmap2epi,outputnode,[('output_image','target_ref')]),
        (inputnode,map_coeff,[
            ("fmap_coeff","in_coeff"),
            ("fmap_ref","fmap_ref"),
            ("fmap2epi_xfm","transform"),
        ]),
        (map_coeff,outputnode,[("out_coeff","fmap_coeff")])
    ])

    if debug:
        workflow.connect([
            (inputnode, map_coeff,[("target_ref","fmap_target")])
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