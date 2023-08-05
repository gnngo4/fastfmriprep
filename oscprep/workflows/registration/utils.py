from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from nipype.interfaces.ants import N4BiasFieldCorrection
from nipype.interfaces.fsl.utils import Split, Merge
import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util


def init_apply_n4_to_bold(name="apply_n4_to_bold_wf"):
    """
    N4 Bias-field correct each volume in a bold acquisition.

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

    workflow = Workflow(name=name)

    inputnode = pe.Node(niu.IdentityInterface(["bold"]), name="inputnode")
    outputnode = pe.Node(niu.IdentityInterface(["n4_bold"]), name="outputnode")

    split_bold = pe.Node(Split(dimension="t"), name="split_bold")
    n4_correction = pe.MapNode(
        N4BiasFieldCorrection(dimension=3),
        iterfield=["input_image"],
        name="n4_correction",
    )
    merge_bold = pe.Node(Merge(dimension="t"), name="merge_bold")

    # fmt: off
    workflow.connect([
        (inputnode, split_bold, [("bold", "in_file")]),
        (split_bold, n4_correction, [("out_files", "input_image")]),
        (n4_correction, merge_bold, [("output_image", "in_files")]),
        (merge_bold, outputnode, [("merged_file", "n4_bold")])
    ])
    # fmt: on

    return workflow


def init_itk_to_fsl_affine_wf(name="itk_to_fsl_affine_wf"):
    """
    Convert affine transformation from itk-to-fsl format.

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

    from oscprep.interfaces.c3_to_fsl import C3dAffineTool

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(["itk_affine", "source", "reference"]),
        name="inputnode",
    )

    outputnode = pe.Node(niu.IdentityInterface(["fsl_affine"]), name="outputnode")

    itk_to_fsl = pe.Node(C3dAffineTool(ras2fsl=True), name="itk_to_fsl")
    itk_to_fsl.inputs.fsl_transform = "fsl_affine.mat"

    # Connect
    workflow.connect(
        [
            (
                inputnode,
                itk_to_fsl,
                [
                    ("source", "source_file"),
                    ("reference", "reference_file"),
                    ("itk_affine", "itk_transform"),
                ],
            ),
            (
                itk_to_fsl,
                outputnode,
                [("fsl_transform", "fsl_affine")],
            ),
        ]
    )

    return workflow


def init_fsl_merge_transforms_wf(use_fmaps, name="fsl_merge_transforms_wf"):
    """
    Combine the following transformations:
    (1) slab SDC warp
    (2) slab-bold to slabref-bold affine
    (2) slabref-bold to wholebrain-bold affine
    (3) wholebrain-bold to t1 affine


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

    from nipype.interfaces import fsl
    from niworkflows.interfaces.nibabel import (
        GenerateSamplingReference,
    )

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            [
                "slab_sdc_warp",
                "slab2slabref_aff",
                "slabref2wholebrain_aff",
                "wholebrain2anat_aff",
                "source",
                "reference",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(["slab2anat_warp", "reference_resampled"]),
        name="outputnode",
    )

    slab2wholebrain_aff = pe.Node(
        fsl.ConvertXFM(
            out_file="merged_affine.txt",
            concat_xfm=True,
        ),
        name="slab2wholebrain_aff",
    )

    slab2anat_aff = pe.Node(
        fsl.ConvertXFM(
            out_file="merged_affine.txt",
            concat_xfm=True,
        ),
        name="slab2anat_aff",
    )

    gen_ref = pe.Node(GenerateSamplingReference(), name="generate_reference")

    slab2anat_warp = pe.Node(fsl.ConvertWarp(), name="slab2anat_warp")

    # Connect
    # fmt: off
    workflow.connect([
        (inputnode, slab2wholebrain_aff, [
            ("slabref2wholebrain_aff", "in_file2"),
            ("slab2slabref_aff", "in_file"),
        ]),
        (inputnode, slab2anat_aff, [("wholebrain2anat_aff", "in_file2")]),
        (slab2wholebrain_aff, slab2anat_aff, [("out_file", "in_file")]),
        (inputnode, gen_ref, [
            ("source", "moving_image"),
            ("reference", "fixed_image"),
        ]),
        (gen_ref, slab2anat_warp, [("out_file", "reference")]),
        (slab2anat_aff, slab2anat_warp, [("out_file", "postmat")]),
        (gen_ref, outputnode, [("out_file", "reference_resampled")]),
        (slab2anat_warp, outputnode, [("out_file", "slab2anat_warp")])
    ])
    # fmt: on

    if use_fmaps:
        # fmt: off
        workflow.connect([
            (inputnode, slab2anat_warp, [("slab_sdc_warp", "warp1")])
        ])
        # fmt: on

    return workflow
