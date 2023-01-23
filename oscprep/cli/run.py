def run():
    import argparse, os, sys

    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
    from niworkflows.utils.spaces import SpatialReferences,Reference
    from nipype.interfaces import utility as niu
    from nipype.pipeline import engine as pe
    from nipype.interfaces.utility import IdentityInterface
    from bids import BIDSLayout

    sys.path.insert(1, '/opt/oscprep')
    # utils
    from oscprep.cli.parser import setup_parser
    from oscprep.utils.data_grabber import bids_reader
    # output workflows
    from oscprep.workflows.derivatives.source_files import (
        get_anat_brainmask_source_files,
        get_bold_brainmask_source_files,
        get_wholebrain_bold_preproc_source_files,
        get_slab_bold_preproc_source_files,
    )
    from oscprep.workflows.derivatives.outputs import (
        init_anat_brainmask_derivatives_wf,
        init_bold_brainmask_derivatives_wf,
        init_wholebrain_bold_preproc_derivatives_wf,
        init_slab_bold_preproc_derivatives_wf,
    )
    # anatomical workflows
    from oscprep.workflows.anat.brainmask import init_brainmask_mp2rage_wf 
    from smriprep.workflows.anatomical import init_anat_preproc_wf
    # fieldmap workflows
    from sdcflows import fieldmaps as fm
    from sdcflows.utils.wrangler import find_estimators
    from sdcflows.workflows.base import init_fmap_preproc_wf
    # bold workflows
    from oscprep.workflows.bold.boldref import init_bold_ref_wf
    from oscprep.workflows.bold.brainmask import (
        init_bold_wholebrain_brainmask_wf,
        init_bold_slab_brainmask_wf,
        init_undistort_bold_slab_brainmask_to_t1_wf
    )
    from fmriprep.workflows.bold import init_bold_stc_wf 
    from oscprep.workflows.bold.hmc import init_bold_hmc_wf
    from oscprep.workflows.bold.sdc import init_bold_sdc_wf
    from oscprep.workflows.registration.transforms import (
        init_anat_to_fmap,
        init_fmap_to_wholebrain_bold_wf,
        init_fmap_to_slab_bold_wf,
        init_wholebrain_bold_to_anat_wf,
        init_slab_bold_to_wholebrain_bold_wf
    )
    from oscprep.workflows.registration.apply import (
        init_apply_fmap_to_bold_wf,
        init_apply_bold_to_anat_wf
    )
    from oscprep.workflows.registration.utils import init_fsl_merge_transforms_wf

    # Get argparse arguments
    parser = setup_parser()
    args = parser.parse_args()

    OSCPREP_VERSION = 1.0

    # Subject info
    SUBJECT_ID = args.subject_id
    SESSION_ID = args.session_id

    # Directories
    BIDS_DIR = args.bids_dir
    DERIV_DIR = args.out_dir

    # Other config params
    # nipype param
    OMP_NTHREADS = args.omp_nthreads
    # mp2rage
    MP2RAGE_DENOISE_FACTOR = args.mp2rage_denoise_factor
    MP2RAGE_SYNTHSTRIP_NO_CSF = args.mp2rage_synthstrip_no_csf_flag
    MP2RAGE_SYNTHSTRIP_UPSAMPLE_RESOLUTION = args.mp2rage_synthstrip_res
    # bold
    BOLD_HMC_LOWPASS_THRESHOLD = args.bold_hmc_lowpass_threshold

    """
    Set-up
    """
    # Derivatives created from this pipeline
    BRAINMASK_DIR = f"{DERIV_DIR}/brainmask"
    SMRIPREP_DIR = f"{DERIV_DIR}/smriprep"
    FREESURFER_DIR = f"{DERIV_DIR}/freesurfer"
    BOLD_PREPROC_DIR = f"{DERIV_DIR}/bold_preproc"
    ## Make empty freesurfer directory
    for _dir in [DERIV_DIR,FREESURFER_DIR]:
        if not os.path.isdir(_dir): 
            os.makedirs(_dir)
    ## bids info
    bids_util = bids_reader(BIDS_DIR)
    layout = BIDSLayout(BIDS_DIR)
    ## get anat info - Only 1 T1w image is expected across all sessions
    ANAT_PATH = bids_util.get_t1w_list(SUBJECT_ID)
    assert len(ANAT_PATH) == 1, f"Only 1 T1w key-pair is expected.\n{ANAT_PATH}"
    ANAT_ACQ, ANAT_FILES = list(ANAT_PATH.items())[0]
    ANAT_SUBJECT_ID, ANAT_SESSION_ID = ANAT_FILES[list(ANAT_FILES.keys())[0]].split(BIDS_DIR)[1].split('/')[1:3]
    # get wholebrain bold info
    BOLD_WHOLEBRAIN_PATHS = bids_util.get_bold_list(
        SUBJECT_ID,
        SESSION_ID,
        specific_task='wholebrain',
        full_path_flag=True,
        suffix='bold.nii.gz'
    )
    BOLD_WHOLEBRAIN_PATHS.sort()
    assert len(BOLD_WHOLEBRAIN_PATHS) == 1, f"There are more than 1 wholebrain bold images."
    bold_wholebrain = BOLD_WHOLEBRAIN_PATHS[0]
    # get slab bold info
    NON_SLAB_TASKS = ['reversephase','wholebrain','None']
    BOLD_SLAB_PATHS = bids_util.get_bold_list(
        SUBJECT_ID,
        SESSION_ID,
        ignore_tasks=NON_SLAB_TASKS,
        full_path_flag=True,
        suffix='bold.nii.gz'
    )
    BOLD_SLAB_PATHS.sort()

    """
    Workflow flags
    """
    DERIV_WORKFLOW_FLAGS = {}
    DERIV_WORKFLOW_FLAGS['anat_brainmask'] = os.path.isdir(f"{BRAINMASK_DIR}/{ANAT_SUBJECT_ID}/{ANAT_SESSION_ID}/anat")
    DERIV_WORKFLOW_FLAGS['anat_preproc'] = os.path.isdir(f"{SMRIPREP_DIR}/sub-{SUBJECT_ID}")
    # Print
    print(f"""\n[CONFIG]
SUBJECT_ID: {SUBJECT_ID}
SESSION_ID: {SESSION_ID}

[Directories] 
*BIDS_DIR: {BIDS_DIR}
*DERIV_DIR: {DERIV_DIR}
BRAINMASK_DIR: {BRAINMASK_DIR}
SMRIPREP_DIR: {SMRIPREP_DIR}
FREESURFER_DIR: {FREESURFER_DIR}
BOLD_PREPROC_DIR: {BOLD_PREPROC_DIR}
    """)
    # Anat paths
    print(f'[Paths]\n----ANAT [{ANAT_ACQ}]----')
    for k, q in ANAT_FILES.items():
        print(f'{k}: {q}')
    # Wholebrain bold path
    print(f'----BOLD [Whole Brain]----')
    for p in BOLD_WHOLEBRAIN_PATHS:
        print(p)
    # Slab bold paths
    print(f'----BOLD [Slab]----')
    for p in BOLD_SLAB_PATHS:
        print(p)
    # Workflow flags
    print('\n[Workflows]')
    for k, q in DERIV_WORKFLOW_FLAGS.items():
        print(f"{k}: {q}")

    if args.info_flag:
         print(f"\n\n[info_flag] invoked.\nExiting.")
         return 0
    
    """
    Initialize workflow
    """
    wf = Workflow(name='oscprep_sub-{SUBJECT_ID}_session-{SESSION_ID}_v{OSCPREP_VERSION}', base_dir=args.scratch_dir)


def _get_element(_list,element_idx):
    return _list[element_idx]


if __name__ == "__main__":
        run()