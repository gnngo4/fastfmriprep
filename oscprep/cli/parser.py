import argparse

def setup_parser():
    """
    Set-up Python's ArgumentParser for oscprep
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--subject_id',
        required=True,
        type=str,
        help='subject ID in the BIDS directory.'
    )
    
    parser.add_argument(
        '--session_id',
        required=True,
        type=str,
        help='session ID in the BIDS directory.'
    )

    parser.add_argument(
        '--bids_dir',
        required=True,
        type=str,
        help='BIDS directory.'
    )

    parser.add_argument(
        '--out_dir',
        required=True,
        type=str,
        help='output directory.'
    )

    parser.add_argument(
        '--scratch_dir',
        default='/tmp',
        type=str,
        help='workflow output directory.'
    )

    parser.add_argument(
        '--omp_nthreads',
        default=8,
        type=int,
        help='number of threads.'
    )

    """
    Config parameters
    """
    # Processing
    parser.add_argument(
        '--info_flag',
        action='store_true',
        help='Print paths to all inputs and expected output directories.'
    )

    parser.add_argument(
        '--anat_flag',
        action='store_true',
        help='[workflows] Enables only anatomical preprocessing workflow.'
    )

    parser.add_argument(
        '--select_task',
        default=None,
        type=str
    )
    
    parser.add_argument(
        '--select_run',
        default=None,
        type=str
    )

    """
    Debug changes
    """
    parser.add_argument(
        '--slab_bold_quick',
        action='store_true',
        help='[debug] Processes all slabs with only the first 10 volumes.'
    )

    # Other
    parser.add_argument(
        '--mp2rage_denoise_factor',
        default=8,
        type=int,
        help='[mp2rage] denoise factor.'
    )

    parser.add_argument(
        '--mp2rage_synthstrip_no_csf_flag',
        action='store_true',
        help='[mp2rage] Enable synthstrip `no_csf` option.'
    )

    parser.add_argument(
        '--mp2rage_synthstrip_res',
        default=1.,
        type=float,
        help='[mp2rage] synthstrip upsample resolution (used to dilate brainmasking).'
    )
    
    parser.add_argument(
        '--mprage_synthstrip_no_csf_flag',
        action='store_true',
        help='[mprage] Enable synthstrip `no_csf` option.'
    )

    parser.add_argument(
        '--bold_hmc_lowpass_threshold',
        default=.2,
        type=float,
        help='[bold-hmc] estimate hmc parameters with lowpass filtered BOLD data (applied to non-filtered data). default=0.2.'
    )
    
    return parser