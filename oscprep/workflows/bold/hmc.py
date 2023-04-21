from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe


def init_bold_hmc_wf(low_pass_threshold=0, name="bold_hmc_wf"):
    from niworkflows.engine.workflows import (
        LiterateWorkflow as Workflow,
    )

    from nipype.interfaces import fsl

    from niworkflows.interfaces.confounds import NormalizeMotionParams
    from oscprep.interfaces.low_pass_filter_bold import (
        LowPassFilterBold,
    )

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "bold_file",
                "bold_reference",
                "bold_metadata",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=["fsl_affines", "movpar_file", "rmsd_file"]),
        name="outputnode",
    )

    boldbuffer = pe.Node(niu.IdentityInterface(fields=["bold_file"]), name="boldbuffer")

    if low_pass_threshold > 0:
        # Low-pass-filter bold data
        lp_filter_bold = pe.Node(LowPassFilterBold(), name="lp_filter_bold")
        lp_filter_bold.inputs.low_pass_threshold = low_pass_threshold
        workflow.connect(
            [
                (
                    inputnode,
                    lp_filter_bold,
                    [
                        ("bold_file", "bold_path"),
                        (
                            (
                                "bold_metadata",
                                _get_metadata,
                                "RepetitionTime",
                            ),
                            "repetition_time",
                        ),
                    ],
                ),
                (
                    lp_filter_bold,
                    boldbuffer,
                    [("lp_bold_path", "bold_file")],
                ),
            ]
        )
    else:
        workflow.connect([(inputnode, boldbuffer, [("bold_file", "bold_file")])])

    # Head-motion correction
    mcflirt = pe.Node(
        fsl.MCFLIRT(
            save_mats=True,
            save_plots=True,
            save_rms=True,
        ),
        name="mcflirt",
    )

    normalize_motion = pe.Node(
        NormalizeMotionParams(format="FSL"), name="normalize_motion"
    )

    workflow.connect(
        [
            (boldbuffer, mcflirt, [("bold_file", "in_file")]),
            (inputnode, mcflirt, [("bold_reference", "ref_file")]),
            (mcflirt, normalize_motion, [("par_file", "in_file")]),
            (
                mcflirt,
                outputnode,
                [
                    (("rms_files", _pick_rel), "rmsd_file"),
                    ("mat_file", "fsl_affines"),
                ],
            ),
            (
                normalize_motion,
                outputnode,
                [("out_file", "movpar_file")],
            ),
        ]
    )

    return workflow


def _get_metadata(bold_metadata, key):
    return bold_metadata[key]


def _pick_rel(rms_files):
    return rms_files[-1]
