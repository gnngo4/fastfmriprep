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
    out_path_base="brainmask",
    name="anat_brainmask_derivatives_wf",
):
    from niworkflows.interfaces.bids import DerivativesDataSink

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["t1w_brain", "t1w_brainmask"]),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=["t1w_brain", "t1w_brainmask"]),
        name="outputnode",
    )

    ds_t1w_brain = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            out_path_base=out_path_base,
            desc="brain",
            compress=True,
        ),
        name="ds_t1w_brain",
        run_without_submitting=True,
    )
    ds_t1w_brain.inputs.source_file = f"{output_dir}/{t1w_brain_base}"

    ds_t1w_brainmask = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            out_path_base=out_path_base,
            desc="brain",
            compress=True,
        ),
        name="ds_t1w_brainmask",
        run_without_submitting=True,
    )
    ds_t1w_brainmask.inputs.source_file = f"{output_dir}/{t1w_brainmask_base}"

    workflow.connect(
        [
            (inputnode, ds_t1w_brain, [("t1w_brain", "in_file")]),
            (
                inputnode,
                ds_t1w_brainmask,
                [("t1w_brainmask", "in_file")],
            ),
            (ds_t1w_brain, outputnode, [("out_file", "t1w_brain")]),
            (
                ds_t1w_brainmask,
                outputnode,
                [("out_file", "t1w_brainmask")],
            ),
        ]
    )

    return workflow


def init_bold_brainmask_derivatives_wf(
    output_dir,
    bold_brain_base,
    bold_brainmask_base,
    bold_type,
    out_path_base="brainmask",
    name=None,
):
    from niworkflows.interfaces.bids import DerivativesDataSink
    from nipype.pipeline import engine as pe

    if name is None:
        name = f"{bold_type}_bold_brainmask_derivatives_wf"

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["bold_brain", "bold_brainmask"]),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=["bold_brain", "bold_brainmask"]),
        name="outputnode",
    )

    ds_bold_brain = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            out_path_base=out_path_base,
            desc="brain",
            compress=True,
        ),
        name=f"ds_bold_{bold_type}_brain",
        run_without_submitting=True,
    )
    ds_bold_brain.inputs.source_file = f"{output_dir}/{bold_brain_base}"

    ds_bold_brainmask = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            out_path_base=out_path_base,
            desc="brain",
            compress=True,
        ),
        name=f"ds_bold_{bold_type}_brainmask",
        run_without_submitting=True,
    )
    ds_bold_brainmask.inputs.source_file = f"{output_dir}/{bold_brainmask_base}"

    workflow.connect(
        [
            (inputnode, ds_bold_brain, [("bold_brain", "in_file")]),
            (
                inputnode,
                ds_bold_brainmask,
                [("bold_brainmask", "in_file")],
            ),
            (ds_bold_brain, outputnode, [("out_file", "bold_brain")]),
            (
                ds_bold_brainmask,
                outputnode,
                [("out_file", "bold_brainmask")],
            ),
        ]
    )

    return workflow


def init_wholebrain_bold_preproc_derivatives_wf(
    output_dir,
    sub_id,
    ses_id,
    bold_ref_base,
    wholebrain_bold_to_t1_mat_base,
    wholebrain_bold_to_t1_svg_base,
    distorted_boldref_base,
    distorted_brainmask_base,
    distorted_dseg_base,
    distorted_itk_bold_to_t1_base,
    distorted_itk_t1_to_bold_base,
    proc_itk_bold_to_t1_base,
    proc_itk_t1_to_bold_base,
    proc_fsl_bold_to_t1_base,
    proc_fsl_t1_to_bold_base,
    proc_dseg_base,
    proc_spacet1_boldref_base,
    proc_boldref_base,
    use_fmaps=True,
    workflow_name_base="wholebrain_bold",
    out_path_base="bold_preproc",
    name=None,
):
    from niworkflows.interfaces.bids import DerivativesDataSink
    from nipype.interfaces.io import ExportFile
    from nipype.pipeline import engine as pe

    if name is None:
        name = f"{workflow_name_base}_preproc_derivatives_wf"

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_ref",
                "wholebrain_bold_to_t1_mat",
                "wholebrain_bold_to_t1_svg",
                "distorted_boldref",  #
                "distorted_brainmask",  #
                "distorted_dseg",  #
                "distorted_itk_bold_to_t1",
                "distorted_itk_t1_to_bold",  #
                "proc_itk_bold_to_t1",
                "proc_itk_t1_to_bold",
                "proc_fsl_bold_to_t1",  #
                "proc_fsl_t1_to_bold",
                "proc_dseg",  #
                "proc_spacet1_boldref",
                "proc_boldref",
            ]
        ),
        name="inputnode",
    )

    # Bold reference image in t1 space
    ds_bold_ref = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            out_path_base=out_path_base,
            compress=True,
        ),
        name=f"ds_{workflow_name_base}_bold_reference",
        run_without_submitting=True,
    )
    ds_bold_ref.inputs.source_file = f"{output_dir}/{bold_ref_base}"

    """
    Transformations
    """
    sub_ses_reg_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/reg"
    sub_ses_figures_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/figures"
    for _dir in [sub_ses_reg_dir, sub_ses_figures_dir]:
        if not os.path.isdir(_dir):
            os.makedirs(_dir)

    ds_wholebrain_to_t1_mat = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{wholebrain_bold_to_t1_mat_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_t1_mat",
        run_without_submitting=True,
    )

    ds_wholebrain_to_t1_svg = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{wholebrain_bold_to_t1_svg_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_t1_svg",
        run_without_submitting=True,
    )

    """
    wholebrain bold preprocessing (prereqs for running slab bold preprocessing)
    """
    sub_ses_wholebrain_bold_dir = (
        f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/wholebrain_bold"
    )
    for _dir in [sub_ses_wholebrain_bold_dir]:
        if not os.path.isdir(_dir):
            os.makedirs(_dir)
        for _subdir in ["distorted"]:
            if not os.path.isdir(f"{_dir}/{_subdir}"):
                os.makedirs(f"{_dir}/{_subdir}")

    ds_distorted_boldref = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{distorted_boldref_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_distorted_boldref",
        run_without_submitting=True,
    )

    ds_distorted_brainmask = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{distorted_brainmask_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_distorted_brainmask",
        run_without_submitting=True,
    )

    ds_distorted_dseg = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{distorted_dseg_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_distorted_dseg",
        run_without_submitting=True,
    )

    """
    ds_distorted_itk_bold_to_t1 = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{distorted_itk_bold_to_t1_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_distorted_itk_bold_to_t1",
        run_without_submitting=True
    )
    """

    ds_distorted_itk_t1_to_bold = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{distorted_itk_t1_to_bold_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_distorted_itk_t1_to_bold",
        run_without_submitting=True,
    )

    """
    ds_proc_itk_bold_to_t1 = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_itk_bold_to_t1_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_proc_itk_bold_to_t1",
        run_without_submitting=True
    )
    """

    """
    ds_proc_itk_t1_to_bold = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_itk_t1_to_bold_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_undistorted_itk_t1_to_bold",
        run_without_submitting=True
    )
    """

    ds_proc_fsl_bold_to_t1 = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_fsl_bold_to_t1_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_proc_fsl_bold_to_t1",
        run_without_submitting=True,
    )

    """
    ds_proc_fsl_t1_to_bold = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_fsl_t1_to_bold_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_proc_fsl_t1_to_bold",
        run_without_submitting=True
    )
    """

    ds_proc_dseg = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_dseg_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_proc_dseg",
        run_without_submitting=True,
    )

    """
    ds_proc_spacet1_boldref = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_spacet1_boldref_base}",
            check_extension=False,
            clobber=True
        ),
        name=f"ds_{workflow_name_base}_proc_spacet1_boldref",
        run_without_submitting=True
    )
    """

    workflow.connect(
        [
            (inputnode, ds_bold_ref, [("bold_ref", "in_file")]),
            (
                inputnode,
                ds_wholebrain_to_t1_mat,
                [("wholebrain_bold_to_t1_mat", "in_file")],
            ),
            (
                inputnode,
                ds_wholebrain_to_t1_svg,
                [("wholebrain_bold_to_t1_svg", "in_file")],
            ),
            (
                inputnode,
                ds_distorted_boldref,
                [("distorted_boldref", "in_file")],
            ),
            (
                inputnode,
                ds_distorted_brainmask,
                [("distorted_brainmask", "in_file")],
            ),
            (
                inputnode,
                ds_distorted_dseg,
                [("distorted_dseg", "in_file")],
            ),
            # (inputnode, ds_distorted_itk_bold_to_t1,[('distorted_itk_bold_to_t1','in_file')]),
            (
                inputnode,
                ds_distorted_itk_t1_to_bold,
                [("distorted_itk_t1_to_bold", "in_file")],
            ),
            # (inputnode, ds_proc_itk_bold_to_t1,[('proc_itk_bold_to_t1','in_file')]),
            # (inputnode, ds_proc_itk_t1_to_bold,[('proc_itk_t1_to_bold','in_file')]),
            (
                inputnode,
                ds_proc_fsl_bold_to_t1,
                [("proc_fsl_bold_to_t1", "in_file")],
            ),
            # (inputnode, ds_proc_fsl_t1_to_bold,[('proc_fsl_t1_to_bold','in_file')]),
            (inputnode, ds_proc_dseg, [("proc_dseg", "in_file")]),
            # (inputnode, ds_proc_spacet1_boldref,[('proc_spacet1_boldref','in_file')]),
        ]
    )

    if use_fmaps:
        ds_proc_boldref = pe.Node(
            ExportFile(
                out_file=f"{output_dir}/{out_path_base}/{proc_boldref_base}",
                check_extension=False,
                clobber=True,
            ),
            name=f"ds_{workflow_name_base}_proc_boldref",
            run_without_submitting=True,
        )

        workflow.connect(
            [
                (
                    inputnode,
                    ds_proc_boldref,
                    [("proc_boldref", "in_file")],
                ),
            ]
        )

    return workflow


def init_slab_reference_bold_preproc_derivatives_wf(
    output_dir,
    sub_id,
    ses_id,
    slabref_to_wholebrain_bold_mat_base,
    slabref_to_wholebrain_bold_svg_base,
    distorted_boldref_base,
    distorted_brainmask_base,
    distorted_itk_slabref_to_wholebrain_bold_base,
    distorted_itk_wholebrain_to_slabref_bold_base,
    proc_itk_slabref_to_wholebrain_bold_base,
    proc_itk_wholebrain_to_slabref_bold_base,
    proc_fsl_slabref_to_wholebrain_bold_base,
    proc_fsl_wholebrain_to_slabref_bold_base,
    proc_boldref_base,
    use_fmaps=True,
    workflow_name_base="slabref_bold",
    out_path_base="bold_preproc",
    name=None,
):
    from nipype.interfaces.io import ExportFile
    from nipype.pipeline import engine as pe

    if name is None:
        name = f"{workflow_name_base}_preproc_derivatives_wf"

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "slabref_to_wholebrain_bold_mat",
                "slabref_to_wholebrain_bold_svg",
                "distorted_boldref",
                "distorted_brainmask",
                "distorted_itk_slabref_to_wholebrain_bold",
                "distorted_itk_wholebrain_to_slabref_bold",
                "proc_itk_slabref_to_wholebrain_bold",
                "proc_itk_wholebrain_to_slabref_bold",
                "proc_fsl_slabref_to_wholebrain_bold",
                "proc_fsl_wholebrain_to_slabref_bold",
                "proc_boldref",
            ]
        ),
        name="inputnode",
    )

    """
    slabref bold preprocessing (prereqs for running slab bold preprocessing)
    """
    sub_ses_slabref_bold_dir = (
        f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/slab_reference_bold"
    )
    for _dir in [sub_ses_slabref_bold_dir]:
        if not os.path.isdir(_dir):
            os.makedirs(_dir)
        for _subdir in ["distorted"]:
            if not os.path.isdir(f"{_dir}/{_subdir}"):
                os.makedirs(f"{_dir}/{_subdir}")

    ds_slabref_to_wholebrain_bold_mat = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slabref_to_wholebrain_bold_mat_base}",
            check_extension=False,
            clobber=True,
        ),
        name=(f"ds_{workflow_name_base}_slabref_to_wholebrain_bold_mat"),
        run_without_submitting=True,
    )

    ds_slabref_to_wholebrain_bold_svg = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slabref_to_wholebrain_bold_svg_base}",
            check_extension=False,
            clobber=True,
        ),
        name=(f"ds_{workflow_name_base}_slabref_to_wholebrain_bold_svg"),
        run_without_submitting=True,
    )

    ds_distorted_boldref = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{distorted_boldref_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_distorted_boldref",
        run_without_submitting=True,
    )

    ds_distorted_brainmask = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{distorted_brainmask_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_distorted_brainmask",
        run_without_submitting=True,
    )

    ds_proc_itk_wholebrain_to_slabref_bold = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_itk_wholebrain_to_slabref_bold_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_proc_itk_wholebrain_to_slabref_bold",
        run_without_submitting=True,
    )

    ds_proc_fsl_slabref_to_wholebrain_bold = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{proc_fsl_slabref_to_wholebrain_bold_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_proc_fsl_slabref_to_wholebrain_bold",
        run_without_submitting=True,
    )

    workflow.connect(
        [
            (
                inputnode,
                ds_slabref_to_wholebrain_bold_mat,
                [("slabref_to_wholebrain_bold_mat", "in_file")],
            ),
            (
                inputnode,
                ds_slabref_to_wholebrain_bold_svg,
                [("slabref_to_wholebrain_bold_svg", "in_file")],
            ),
            (
                inputnode,
                ds_distorted_boldref,
                [("distorted_boldref", "in_file")],
            ),
            (
                inputnode,
                ds_distorted_brainmask,
                [("distorted_brainmask", "in_file")],
            ),
            (
                inputnode,
                ds_proc_fsl_slabref_to_wholebrain_bold,
                [("proc_fsl_slabref_to_wholebrain_bold", "in_file")],
            ),
            (
                inputnode,
                ds_proc_itk_wholebrain_to_slabref_bold,
                [("proc_itk_wholebrain_to_slabref_bold", "in_file")],
            ),
        ]
    )

    if use_fmaps:
        ds_proc_boldref = pe.Node(
            ExportFile(
                out_file=f"{output_dir}/{out_path_base}/{proc_boldref_base}",
                check_extension=False,
                clobber=True,
            ),
            name=f"ds_{workflow_name_base}_proc_boldref",
            run_without_submitting=True,
        )

        workflow.connect(
            [
                (
                    inputnode,
                    ds_proc_boldref,
                    [("proc_boldref", "in_file")],
                ),
            ]
        )

    return workflow


def init_slab_bold_preproc_derivatives_wf(
    output_dir,
    sub_id,
    ses_id,
    bold_ref_base,
    bold_brainmask_base,
    bold_preproc_base,
    cifti_bold_preproc_base,
    cifti_bold_metadata_base,
    bold_confounds_base,
    bold_roi_svg_base,
    bold_acompcor_csf_base,
    bold_acompcor_wm_base,
    bold_acompcor_wmcsf_base,
    bold_tcompcor_base,
    bold_crownmask_base,
    bold_hmc_base,
    bold_sdc_warp_base,
    slab_bold_to_slabref_bold_mat_base,
    slab_bold_to_slabref_bold_svg_base,
    slab_bold_to_t1_warp_base,
    workflow_name_base,
    use_fmaps=True,
    out_path_base="bold_preproc",
    name=None,
):
    from niworkflows.interfaces.bids import DerivativesDataSink
    from nipype.interfaces.io import ExportFile
    from nipype.interfaces.utility import Function
    from nipype.pipeline import engine as pe

    if name is None:
        name = f"{workflow_name_base}_preproc_derivatives_wf"

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_ref",
                "bold_brainmask",
                "bold_preproc",
                "cifti_bold_preproc",
                "cifti_bold_metadata",
                "bold_confounds",
                "bold_roi_svg",
                "bold_acompcor_csf",
                "bold_acompcor_wm",
                "bold_acompcor_wmcsf",
                "bold_tcompcor",
                "bold_crownmask",
                "bold_hmc",
                "bold_sdc_warp",
                "slab_bold_to_slabref_bold_mat",
                "slab_bold_to_slabref_bold_svg",
                "slab_bold_to_t1_warp",
            ]
        ),
        name="inputnode",
    )

    # Make directories
    sub_ses_reg_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/reg"
    sub_ses_roi_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/roi"
    sub_ses_figures_dir = f"{output_dir}/{out_path_base}/{sub_id}/{ses_id}/figures"
    for _dir in [
        sub_ses_reg_dir,
        sub_ses_roi_dir,
        sub_ses_figures_dir,
    ]:
        if not os.path.isdir(_dir):
            os.makedirs(_dir)

    # Bold reference image in t1 space
    ds_bold_ref = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            out_path_base=out_path_base,
            compress=True,
        ),
        name=f"ds_{workflow_name_base}_bold_reference",
        run_without_submitting=True,
    )
    ds_bold_ref.inputs.source_file = f"{output_dir}/{bold_ref_base}"

    # Bold brainmask image in t1 space
    ds_bold_brainmask = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{bold_brainmask_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_brainmask",
        run_without_submitting=True,
    )

    # Preprocessed bold in t1 space
    ds_bold_preproc = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            out_path_base=out_path_base,
            compress=True,
        ),
        name=f"ds_{workflow_name_base}_bold_preproc",
        run_without_submitting=True,
    )
    ds_bold_preproc.inputs.source_file = f"{output_dir}/{bold_preproc_base}"

    # Preprocessed bold resampled to 32k avg surface space
    ds_cifti_bold_preproc = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{cifti_bold_preproc_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_cifti_bold_preproc",
        run_without_submitting=True,
    )

    # Preprocessed bold resampled to 32k avg surface space [metadata]
    ds_cifti_bold_metadata = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{cifti_bold_metadata_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_cifti_bold_metadata",
        run_without_submitting=True,
    )

    """
    Confound files
    """
    ds_bold_confounds = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{bold_confounds_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_confounds",
        run_without_submitting=True,
    )
    ds_bold_roi_svg = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{bold_roi_svg_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_roi_svg",
        run_without_submitting=True,
    )
    ds_bold_acompcor_csf = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_acompcor_csf_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_acompcor_csf",
        run_without_submitting=True,
    )
    ds_bold_acompcor_wm = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_acompcor_wm_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_acompcor_wm",
        run_without_submitting=True,
    )
    ds_bold_acompcor_wmcsf = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{bold_acompcor_wmcsf_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_acompcor_wmcsf",
        run_without_submitting=True,
    )
    ds_bold_tcompcor = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{bold_tcompcor_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_tcompcor",
        run_without_submitting=True,
    )
    ds_bold_crownmask = pe.Node(
        ExportFile(
            out_file=(f"{output_dir}/{out_path_base}/{bold_crownmask_base}"),
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_bold_crownmask",
        run_without_submitting=True,
    )

    """
    Transformations
    """
    ds_bold_hmc = pe.Node(
        interface=Function(
            input_names=["hmc_list", "save_base"],
            output_names=[],
            function=save_slab_bold_hmc,
        ),
        name=f"ds_{workflow_name_base}_hmc",
        run_without_submitting=True,
    )
    ds_bold_hmc.inputs.save_base = f"{output_dir}/{out_path_base}/{bold_hmc_base}"

    ds_slab_to_slabref_mat = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slab_bold_to_slabref_bold_mat_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_slabref_mat",
        run_without_submitting=True,
    )
    ds_slab_to_slabref_svg = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slab_bold_to_slabref_bold_svg_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_slabref_svg",
        run_without_submitting=True,
    )
    ds_slab_to_t1 = pe.Node(
        ExportFile(
            out_file=f"{output_dir}/{out_path_base}/{slab_bold_to_t1_warp_base}",
            check_extension=False,
            clobber=True,
        ),
        name=f"ds_{workflow_name_base}_t1_warp",
        run_without_submitting=True,
    )

    workflow.connect(
        [
            (inputnode, ds_bold_ref, [("bold_ref", "in_file")]),
            (
                inputnode,
                ds_bold_brainmask,
                [("bold_brainmask", "in_file")],
            ),
            (
                inputnode,
                ds_bold_preproc,
                [("bold_preproc", "in_file")],
            ),
            (
                inputnode,
                ds_cifti_bold_preproc,
                [("cifti_bold_preproc", "in_file")],
            ),
            (
                inputnode,
                ds_cifti_bold_metadata,
                [("cifti_bold_metadata", "in_file")],
            ),
            (inputnode, ds_bold_hmc, [("bold_hmc", "hmc_list")]),
            (
                inputnode,
                ds_bold_confounds,
                [("bold_confounds", "in_file")],
            ),
            (
                inputnode,
                ds_bold_roi_svg,
                [("bold_roi_svg", "in_file")],
            ),
            (
                inputnode,
                ds_bold_acompcor_csf,
                [("bold_acompcor_csf", "in_file")],
            ),
            (
                inputnode,
                ds_bold_acompcor_wm,
                [("bold_acompcor_wm", "in_file")],
            ),
            (
                inputnode,
                ds_bold_acompcor_wmcsf,
                [("bold_acompcor_wmcsf", "in_file")],
            ),
            (
                inputnode,
                ds_bold_tcompcor,
                [("bold_tcompcor", "in_file")],
            ),
            (
                inputnode,
                ds_bold_crownmask,
                [("bold_crownmask", "in_file")],
            ),
            (
                inputnode,
                ds_slab_to_slabref_mat,
                [("slab_bold_to_slabref_bold_mat", "in_file")],
            ),
            (
                inputnode,
                ds_slab_to_slabref_svg,
                [("slab_bold_to_slabref_bold_svg", "in_file")],
            ),
            (
                inputnode,
                ds_slab_to_t1,
                [("slab_bold_to_t1_warp", "in_file")],
            ),
        ]
    )

    if use_fmaps:
        ds_bold_sdc = pe.Node(
            ExportFile(
                out_file=f"{output_dir}/{out_path_base}/{bold_sdc_warp_base}",
                check_extension=False,
                clobber=True,
            ),
            name=f"ds_{workflow_name_base}_sdc_warp",
            run_without_submitting=True,
        )

        workflow.connect(
            [
                (
                    inputnode,
                    ds_bold_sdc,
                    [("bold_sdc_warp", "in_file")],
                ),
            ]
        )

    return workflow


def save_slab_bold_hmc(hmc_list, save_base):
    import os
    from nipype.interfaces.io import ExportFile

    if not os.path.isdir(save_base):
        os.makedirs(save_base)

    for ix, vol_affine in enumerate(hmc_list):
        _vol_affine = vol_affine.split("/")[-1]
        ds_vol_affine = ExportFile(out_file=f"{save_base}/{_vol_affine}")
        ds_vol_affine.inputs.in_file = vol_affine
        ds_vol_affine.run()

    tar_file = f"{save_base}.tar.gz"
    tar_cmd = " ".join(
        [
            "tar",
            "-czvf",
            tar_file,
            "-C",
            save_base,
            ".",
            "--remove-files",
        ]
    )
    os.system(tar_cmd)
    assert os.path.exists(tar_file)
