from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe


def init_bold_wholebrain_brainmask_wf(
    bold2t1w_dof=9,
    use_bbr=True,
    omp_nthreads=8,
    name="skullstrip_wholebrain_bold_wf",
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
    from niworkflows.engine.workflows import (
        LiterateWorkflow as Workflow,
    )

    from fmriprep.workflows.bold.registration import init_bbreg_wf
    from niworkflows.interfaces.fixes import (
        FixHeaderApplyTransforms as ApplyTransforms,
    )
    from nipype.interfaces.fsl import ApplyMask, DilateImage
    from nipype.interfaces.ants import N4BiasFieldCorrection

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                "wholebrain_bold",
                "fsnative2t1w_xfm",
                "subjects_dir",
                "subject_id",  # BBRegister
                "t1w_dseg",
                "t1w_brain",
                "t1w_brainmask",  # from smriprep
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            [
                "brain",
                "brainmask",
                "dseg",
                "itk_bold_to_t1",
                "itk_t1_to_bold",
            ]
        ),
        name="outputnode",
    )

    # n4
    n4_bold = pe.Node(N4BiasFieldCorrection(), name="n4_bias_correct_bold")

    # bbreg t1-to-wholebrain-bold
    bbr_wf = init_bbreg_wf(
        use_bbr=use_bbr,
        bold2t1w_dof=bold2t1w_dof,
        bold2t1w_init="register",
        omp_nthreads=omp_nthreads,
    )

    # transform t1w_brainmask to wholebrain-bold space
    t1brainmask_to_bold = pe.Node(
        ApplyTransforms(interpolation="MultiLabel", float=True),
        name="wholebrain_bold_brainmask",
    )

    # dilate mask
    dilate_mask = pe.Node(
        DilateImage(
            kernel_shape="3D",
            operation="modal",
        ),
        name="dilate_wholebrain_bold_mask",
    )

    # transform t1w_dseg to wholebrain-bold space
    t1dseg_to_bold = pe.Node(
        ApplyTransforms(interpolation="MultiLabel", float=True),
        name="wholebrain_bold_dseg",
    )

    # Return skullstripped wholebrain-bold
    apply_mask = pe.Node(
        ApplyMask(out_file="brain.nii.gz"),
        name="apply_mask",
    )

    # Connect
    workflow.connect(
        [
            (
                inputnode,
                n4_bold,
                [("wholebrain_bold", "input_image")],
            ),
            (
                n4_bold,
                bbr_wf,
                [("output_image", "inputnode.in_file")],
            ),
            (
                inputnode,
                bbr_wf,
                [
                    # ('wholebrain_bold','inputnode.in_file'),
                    (
                        "fsnative2t1w_xfm",
                        "inputnode.fsnative2t1w_xfm",
                    ),
                    ("subjects_dir", "inputnode.subjects_dir"),
                    ("subject_id", "inputnode.subject_id"),
                    ("t1w_dseg", "inputnode.t1w_dseg"),
                    ("t1w_brain", "inputnode.t1w_brain"),
                ],
            ),
            (
                bbr_wf,
                t1brainmask_to_bold,
                [("outputnode.itk_t1_to_bold", "transforms")],
            ),
            (
                inputnode,
                t1brainmask_to_bold,
                [
                    ("t1w_brainmask", "input_image"),
                    ("wholebrain_bold", "reference_image"),
                ],
            ),
            (
                bbr_wf,
                t1dseg_to_bold,
                [("outputnode.itk_t1_to_bold", "transforms")],
            ),
            (
                inputnode,
                t1dseg_to_bold,
                [
                    ("t1w_dseg", "input_image"),
                    ("wholebrain_bold", "reference_image"),
                ],
            ),
            (
                t1brainmask_to_bold,
                dilate_mask,
                [("output_image", "in_file")],
            ),
            (dilate_mask, apply_mask, [("out_file", "mask_file")]),
            (inputnode, apply_mask, [("wholebrain_bold", "in_file")]),
            (
                bbr_wf,
                outputnode,
                [
                    ("outputnode.itk_bold_to_t1", "itk_bold_to_t1"),
                    ("outputnode.itk_t1_to_bold", "itk_t1_to_bold"),
                ],
            ),
            (apply_mask, outputnode, [("out_file", "brain")]),
            (dilate_mask, outputnode, [("out_file", "brainmask")]),
            (t1dseg_to_bold, outputnode, [("output_image", "dseg")]),
        ]
    )

    return workflow


def init_bold_slabref_brainmask_wf(
    bold2t1w_dof=6,
    use_bbr=True,
    omp_nthreads=8,
    name="skullstrip_slab_bold_wf",
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
    from niworkflows.engine.workflows import (
        LiterateWorkflow as Workflow,
    )

    from fmriprep.workflows.bold.registration import init_fsl_bbr_wf
    from niworkflows.interfaces.fixes import (
        FixHeaderApplyTransforms as ApplyTransforms,
    )
    from nipype.interfaces.fsl import ApplyMask
    from nipype.interfaces.ants import N4BiasFieldCorrection

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                "slab_bold",
                "wholebrain_bold_dseg",
                "wholebrain_bold",
                (  # Generated from ``init_brainmask_wholebrain_bold_wf``
                    "wholebrain_bold_brainmask"
                ),
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            ["brain", "brainmask", "itk_bold_to_t1", "itk_t1_to_bold"]
        ),  # bold == slab & t1 == wholebrain
        name="outputnode",
    )

    # n4
    n4_bold = pe.Node(N4BiasFieldCorrection(), name="n4_bias_correct_bold")

    # fsl_bbr slab-bold-to-wholebrain-bold
    fsl_bbr_wf = init_fsl_bbr_wf(
        bold2t1w_dof=bold2t1w_dof,
        use_bbr=use_bbr,
        bold2t1w_init="register",
        omp_nthreads=omp_nthreads,
    )

    # transform wholebrain-bold brainmask to slab-bold space
    boldbrainmask_to_slab = pe.Node(
        ApplyTransforms(interpolation="MultiLabel", float=True),
        name="slab_bold_brainmask",
    )

    # Return skullstripped slab-bold
    apply_mask = pe.Node(
        ApplyMask(out_file="brain.nii.gz"),
        name="apply_mask",
    )

    # Connect
    workflow.connect(
        [
            (inputnode, n4_bold, [("slab_bold", "input_image")]),
            (
                n4_bold,
                fsl_bbr_wf,
                [("output_image", "inputnode.in_file")],
            ),
            (
                inputnode,
                fsl_bbr_wf,
                [
                    # ('slab_bold','inputnode.in_file'),
                    ("wholebrain_bold_dseg", "inputnode.t1w_dseg"),
                    ("wholebrain_bold", "inputnode.t1w_brain"),
                ],
            ),
            (
                fsl_bbr_wf,
                boldbrainmask_to_slab,
                [("outputnode.itk_t1_to_bold", "transforms")],
            ),
            (
                inputnode,
                boldbrainmask_to_slab,
                [
                    ("wholebrain_bold_brainmask", "input_image"),
                    ("slab_bold", "reference_image"),
                ],
            ),
            (
                boldbrainmask_to_slab,
                apply_mask,
                [("output_image", "mask_file")],
            ),
            (inputnode, apply_mask, [("slab_bold", "in_file")]),
            (
                fsl_bbr_wf,
                outputnode,
                [
                    ("outputnode.itk_bold_to_t1", "itk_bold_to_t1"),
                    ("outputnode.itk_t1_to_bold", "itk_t1_to_bold"),
                ],
            ),
            (apply_mask, outputnode, [("out_file", "brain")]),
            (
                boldbrainmask_to_slab,
                outputnode,
                [("output_image", "brainmask")],
            ),
        ]
    )

    return workflow


def init_bold_slab_brainmask_wf(name="skullstrip_slab_bold_wf"):
    """
    Skullstrip slab sbref by using a wholebrain-bold brainmask,
    and a wholebrain-bold-to-slabref-bold-to-slab bold
    registration approach

    Parameters
    ----------

    Inputs
    ------

    Outputs
    -------

    """
    from niworkflows.engine.workflows import (
        LiterateWorkflow as Workflow,
    )

    from niworkflows.interfaces.fixes import (
        FixHeaderApplyTransforms as ApplyTransforms,
    )

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                "slab_bold",
                "wholebrain_bold_brainmask",  # Generated from ``init_brainmask_wholebrain_bold_wf``
                "itk_wholebrain_to_slabref_bold",
                "itk_slabref_to_slab_bold",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(["brainmask"]),
        name="outputnode",
    )

    concat_transforms = pe.Node(
        niu.Function(
            function=_concat_transforms_2,
            input_names=["xfm_1", "xfm_2"],
        ),
        name="concat_transforms",
    )

    # transform wholebrain-bold brainmask to slab-bold space
    boldbrainmask_to_slab = pe.Node(
        ApplyTransforms(interpolation="MultiLabel", float=True),
        name="slab_bold_brainmask",
    )

    # Connect
    workflow.connect(
        [
            (
                inputnode,
                boldbrainmask_to_slab,
                [
                    ("wholebrain_bold_brainmask", "input_image"),
                    ("slab_bold", "reference_image"),
                ],
            ),
            (
                inputnode,
                concat_transforms,
                [
                    ("itk_wholebrain_to_slabref_bold", "xfm_1"),
                    ("itk_slabref_to_slab_bold", "xfm_2"),
                ],
            ),
            (
                concat_transforms,
                boldbrainmask_to_slab,
                [("out", "transforms")],
            ),
            (
                boldbrainmask_to_slab,
                outputnode,
                [("output_image", "brainmask")],
            ),
        ]
    )

    return workflow


def init_undistort_bold_slab_brainmask_to_t1_wf(
    name="undistort_slab_bold_brainmask_to_t1_wf",
):
    from niworkflows.engine.workflows import (
        LiterateWorkflow as Workflow,
    )

    from nipype.interfaces.fsl import (
        Threshold,
        ApplyWarp,
        MultiImageMaths,
    )

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                "slab_bold_brainmask",  # brainmask calculated on distorted bold ref data
                "t1_warp",  # fsl warp includes sdc, and slab bold to t1 affine
                "t1_resampled",  # t1 resampled to bold resolution
                "t1_boldref",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(["t1_brainmask"]),
        name="outputnode",
    )

    apply_warp = pe.Node(ApplyWarp(), name="brainmask_to_t1")

    mask_brainmask = pe.Node(
        Threshold(
            thresh=0.5,
            args="-bin -dilF",
        ),
        name="mask_t1_brainmask",
    )

    refine_brainmask = pe.Node(
        MultiImageMaths(op_string="-mul %s -bin"),
        name="refine_brainmask",
    )

    # connect
    workflow.connect(
        [
            (
                inputnode,
                apply_warp,
                [
                    ("slab_bold_brainmask", "in_file"),
                    ("t1_warp", "field_file"),
                    ("t1_resampled", "ref_file"),
                ],
            ),
            (apply_warp, mask_brainmask, [("out_file", "in_file")]),
            (
                mask_brainmask,
                refine_brainmask,
                [("out_file", "in_file")],
            ),
            (
                inputnode,
                refine_brainmask,
                [(("t1_boldref", _listify), "operand_files")],
            ),
            (
                refine_brainmask,
                outputnode,
                [("out_file", "t1_brainmask")],
            ),
        ]
    )

    return workflow


def _listify(x):
    return [x]


def _concat_transforms_2(xfm_1, xfm_2):
    return [xfm_2, xfm_1]
