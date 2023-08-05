import argparse


def setup_parser():
    """
    Set-up Python's ArgumentParser for oscprep
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--subject_id",
        required=True,
        type=str,
        help="subject ID in the BIDS directory.",
    )

    parser.add_argument(
        "--session_id",
        required=True,
        type=str,
        help="session ID in the BIDS directory.",
    )

    parser.add_argument("--bids_dir", required=True, type=str, help="BIDS directory.")

    parser.add_argument("--out_dir", required=True, type=str, help="output directory.")

    parser.add_argument(
        "--scratch_dir",
        default="/tmp",
        type=str,
        help="workflow output directory.",
    )

    parser.add_argument(
        "--omp_nthreads",
        default=8,
        type=int,
        help="number of threads.",
    )

    """
    Config parameters
    """
    # Processing
    parser.add_argument(
        "--info_flag",
        action="store_true",
        help=("Print paths to all inputs and expected output" " directories."),
    )

    parser.add_argument(
        "--anat_flag",
        action="store_true",
        help=("[workflows] Enables only anatomical preprocessing" " workflow."),
    )

    parser.add_argument("--select_task", default=None, type=str)

    parser.add_argument("--select_run", default=None, type=str)

    """
    Debug changes
    """
    parser.add_argument(
        "--slab_bold_quick",
        action="store_true",
        help=("[debug] Processes all slabs with only the first 10" " volumes."),
    )

    # Other
    parser.add_argument(
        "--mp2rage_denoise_factor",
        default=8,
        type=int,
        help="[mp2rage] denoise factor.",
    )

    parser.add_argument(
        "--mp2rage_synthstrip_no_csf_flag",
        action="store_true",
        help="[mp2rage] Enable synthstrip `no_csf` option.",
    )

    parser.add_argument(
        "--mp2rage_synthstrip_res",
        default=1.0,
        type=float,
        help=(
            "[mp2rage] synthstrip upsample resolution (used to dilate" " brainmasking)."
        ),
    )

    parser.add_argument(
        "--mprage_synthstrip_no_csf_flag",
        action="store_true",
        help="[mprage] Enable synthstrip `no_csf` option.",
    )

    parser.add_argument(
        "--bold_ref_vol_idx",
        default=0,
        type=int,
        help=(
            "[bold-ref] Select the slab bold reference volume when a sbref image is not detected. default=0."
        ),
    )

    parser.add_argument(
        "--stc_off",
        action="store_true",
        help=("[bold-stc] Runs preprocessing without" " slice-timing correction."),
    )

    parser.add_argument(
        "--bold_hmc_n4",
        action="store_true",
        help=("[bold-hmc] Enable N4 bias field correction on BOLD data prior to hmc."),
    )

    parser.add_argument(
        "--bold_hmc_cost_function",
        default="normcorr",
        choices=[
            "mutualinfo",
            "woods",
            "corratio",
            "normcorr",
            "normmi",
            "leastsquares",
        ],
        help=("[bold-hmc] MCFLIRT cost-function. default=normcorr."),
    )

    parser.add_argument(
        "--bold_hmc_lowpass_threshold",
        default=0.2,
        type=float,
        help=(
            "[bold-hmc] Estimate hmc parameters with lowpass filtered"
            " BOLD data (applied to non-filtered data). Set to 0 to turn off. default=0.2."
        ),
    )

    parser.add_argument(
        "--fmapless",
        action="store_true",
        help=(
            "[fmap] Runs preprocessing without performing any"
            " susceptibility distortion correction."
        ),
    )

    parser.add_argument(
        "--fmap_gre_fsl",
        action="store_true",
        help=(
            "[fmap] Calculate fieldmap using `fsl_prepare_fieldmap`."
            " default uses sdcflows-generated fieldmap."
        ),
    )

    parser.add_argument(
        "--reg_wholebrain_to_anat_undistorted",
        action="store_true",
        help=(
            "[registration] Estimate wholebrain epi to anat transform"
            " with SDC-corrected images."
        ),
    )

    parser.add_argument(
        "--reg_wholebrain_to_anat_bbr",
        action="store_true",
        help=(
            "[registration] Enable BBR cost function for estimating"
            " wholebrain epi to anat registrations."
        ),
    )

    parser.add_argument(
        "--reg_wholebrain_to_anat_dof",
        default=9,
        type=int,
        help=(
            "[registration] Specify DOF for estimating wholebrain epi"
            " to anat registrations. default=9."
        ),
    )

    parser.add_argument(
        "--reg_slab_to_wholebrain_undistorted",
        action="store_true",
        help=(
            "[registration] Estimate slab to wholebrain epi transform"
            " with SDC-corrected images."
        ),
    )

    parser.add_argument(
        "--reg_slab_to_wholebrain_bbr",
        action="store_true",
        help=(
            "[registration] Enable BBR cost function for estimating"
            " slab to wholebrain epi registrations."
        ),
    )

    parser.add_argument(
        "--reg_slab_to_wholebrain_dof",
        default=6,
        type=int,
        help=(
            "[registration] Specify DOF for estimating slab to"
            " wholebrain epi registrations. default=6."
        ),
    )

    return parser
