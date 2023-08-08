import os

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe


def init_bold_ref_wf(
    bold, split_vol_id=0, pca_denoise=False, name="get_bold_reference_wf"
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
    from niworkflows.engine.workflows import (
        LiterateWorkflow as Workflow,
    )

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(["bold"]),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(["boldref"]),
        name="outputnode",
    )

    sbref = bold.replace("_bold.nii.gz", "_sbref.nii.gz")
    if os.path.exists(sbref):
        # fmt: off
        workflow.connect([
            (inputnode, outputnode, [(("bold", _get_sbref), "boldref")]),
        ])
        # fmt: on

        return workflow

    else:
        from nipype.interfaces.fsl.utils import Split

        split_bold = pe.Node(
            Split(dimension="t", out_base_name="split_bold_"),
            name="split_bold",
        )

        if pca_denoise:
            from oscprep.interfaces.pca_denoise import PCADenoise

            pca_denoise_bold = pe.Node(
                PCADenoise(),
                name="pca_denoise",
            )
            # fmt: off
            workflow.connect([
                (inputnode, pca_denoise_bold, [("bold", "bold_path")]),
                (pca_denoise_bold, split_bold, [("mppca_path", "in_file")])
            ])
            # fmt: on

        else:
            # fmt: off
            workflow.connect([
                (inputnode, split_bold, [("bold", "in_file")]),
            ])
            # fmt: on

        # fmt: off
        workflow.connect([
            (split_bold, outputnode, [(("out_files", _get_split_volume, split_vol_id), "boldref")]),
        ])
        # fmt: on

        return workflow


def _get_sbref(bold):
    return bold.replace("_bold.nii.gz", "_sbref.nii.gz")


def _get_split_volume(out_files, vol_id):
    return out_files[vol_id]
