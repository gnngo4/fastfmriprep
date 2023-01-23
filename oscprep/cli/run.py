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

    # Checkpoint
    if args.info_flag:
         print(f"\n\n[info_flag] invoked.\nExiting.")
         return 0
    
    """
    Initialize workflow
    """
    wf = Workflow(name='oscprep_sub-{SUBJECT_ID}_session-{SESSION_ID}_v{OSCPREP_VERSION}', base_dir=args.scratch_dir)

    """
    Set-up anatomical workflows
    """
    # get brainmask-ed t1w output names
    source_brain, source_brainmask, anat_subj_id, anat_ses_id, anat_run_id = get_anat_brainmask_source_files(ANAT_ACQ, ANAT_FILES) 
    t1w_input = f"{BRAINMASK_DIR}/{source_brain}" # Mandatory argument
    # anat_buffer
    anat_buffer = pe.Node(
        niu.IdentityInterface(
            [
                't1w_brain',
                'fs_t1w_brain', # anat_preproc_wf | t1w_preproc
                't1w_brainmask', # anat_preproc_wf | t1w_mask
                't1w_dseg', # anat_preproc_wf | t1w_dseg
                't1w_tpms', # anat_preproc_wf | t1w_tpms
                'subjects_dir', # anat_preproc_wf | subjects_dir
                'subject_id', # anat_preproc_wf | subject_id
                'fsnative2t1w_xfm', # anat_preproc_wf | fsnative2t1w_xfm
                'std2anat_xfm', # anat_preproc_wf | std2anat_xfm
            ]
        ),
        name='anat_buffer'
    )

    if not DERIV_WORKFLOW_FLAGS['anat_brainmask']:
        if ANAT_ACQ == 'MP2RAGE':
            # mp2rage brainmask workflow
            brainmask_wf = init_brainmask_mp2rage_wf()
            brainmask_inputnode = pe.Node(
                niu.IdentityInterface(
                    [
                        'mp2rage',
                        'inv1',
                        'inv2',
                        'denoise_factor', # mp2rage denoising
                        'ss_native_no_csf', # synthstrip on native t1w
                        'upsample_resolution', # resolution of upsampled t1w
                        'ss_up_no_csf', # synthstrip on upsampled t1w
                    ]
                ),
                name='brainmask_inputnode'
            )
            brainmask_inputnode.inputs.mp2rage = ANAT_FILES['UNI']
            brainmask_inputnode.inputs.inv1 = ANAT_FILES['INV1']
            brainmask_inputnode.inputs.inv2 = ANAT_FILES['INV2']
            brainmask_inputnode.inputs.denoise_factor = MP2RAGE_DENOISE_FACTOR
            brainmask_inputnode.inputs.ss_native_no_csf = MP2RAGE_SYNTHSTRIP_NO_CSF
            brainmask_inputnode.inputs.upsample_resolution = MP2RAGE_SYNTHSTRIP_UPSAMPLE_RESOLUTION
            brainmask_inputnode.inputs.ss_up_no_csf = MP2RAGE_SYNTHSTRIP_NO_CSF
            # mp2rage brainmask derivatives workflow
            anat_brainmask_derivatives_wf = init_anat_brainmask_derivatives_wf(
                DERIV_DIR,
                source_brain,
                source_brainmask,
                out_path_base=BRAINMASK_DIR.split('/')[-1]
            )
            # connect
            wf.connect([
                (brainmask_inputnode,brainmask_wf,[
                    ('mp2rage','inputnode.mp2rage'),
                    ('inv1','inputnode.inv1'),
                    ('inv2','inputnode.inv2'),
                    ('denoise_factor','inputnode.denoise_factor'),
                    ('ss_native_no_csf','inputnode.ss_native_no_csf'),
                    ('upsample_resolution','inputnode.upsample_resolution'),
                    ('ss_up_no_csf','inputnode.ss_up_no_csf')
                ]),
                (brainmask_wf, anat_brainmask_derivatives_wf,[
                    ('outputnode.mp2rage_brain','inputnode.t1w_brain'),
                    ('outputnode.mp2rage_brainmask','inputnode.t1w_brainmask')
                ]),
                (anat_brainmask_derivatives_wf,anat_buffer,[('outputnode.t1w_brain','t1w_brain')])
            ])
        elif ANAT_ACQ == 'MPRAGE':
            NotImplemented
        else:
            NotImplemented
    else:
        # ``brainmask_wf`` should have produced ``t1w_input``
        anat_buffer.inputs.t1w_brain = t1w_input
        
    if not DERIV_WORKFLOW_FLAGS['anat_preproc']:
        
        # smriprep workflow
        anat_preproc_wf = init_anat_preproc_wf(
            bids_root=layout.root,
            existing_derivatives=None,
            freesurfer=True,
            hires=True,
            longitudinal=False,
            t1w=[t1w_input],
            omp_nthreads=OMP_NTHREADS,
            output_dir=DERIV_DIR,
            skull_strip_template=Reference('OASIS30ANTs'),
            spaces=SpatialReferences(spaces=['MNI152NLin2009cAsym', 'fsaverage5']),
            debug=True,
            skull_strip_mode='skip',
            skull_strip_fixed_seed=False
        )
        anat_preproc_inputnode = pe.Node(
            niu.IdentityInterface(['subjects_dir','subject_id','t2w','roi','flair']),
            name='anat_preproc_inputnode'
        )
        anat_preproc_inputnode.inputs.subjects_dir = FREESURFER_DIR
        anat_preproc_inputnode.inputs.subject_id = f"sub-{SUBJECT_ID}"
        # connect
        wf.connect([
            (anat_preproc_inputnode,anat_preproc_wf,[
                ('subjects_dir','inputnode.subjects_dir'),
                ('subject_id','inputnode.subject_id'),
            ]),
            (anat_buffer,anat_preproc_wf,[('t1w_brain','inputnode.t1w')]),
            (anat_preproc_wf,anat_buffer,[
                ('outputnode.subject_id','subject_id'),
                ('outputnode.subjects_dir','subjects_dir'),
                ('outputnode.fsnative2t1w_xfm','fsnative2t1w_xfm'),
                ('outputnode.t1w_preproc','fs_t1w_brain'),
                ('outputnode.t1w_mask','t1w_brainmask'),
                ('outputnode.t1w_dseg','t1w_dseg'),
                ('outputnode.t1w_tpms','t1w_tpms'),
                ('outputnode.std2anat_xfm','std2anat_xfm'),
            ])
        ])
    else:
        
        # ``anat_preproc_wf`` should produce the following:
        anat_preproc_base = f"{SMRIPREP_DIR}/{anat_subj_id}/{anat_ses_id}/anat/{source_brain.split('/')[-1].split('_desc')[0]}"
        anat_inputs = {
            'subject_id': f"sub-{SUBJECT_ID}",
            'subjects_dir': FREESURFER_DIR,
            'fsnative2t1w_xfm': f"{anat_preproc_base}_from-fsnative_to-T1w_mode-image_xfm.txt",
            'fs_t1w_brain': f"{anat_preproc_base}_desc-preproc_T1w.nii.gz",
            't1w_brainmask': f"{anat_preproc_base}_desc-brain_mask.nii.gz",
            't1w_dseg': f"{anat_preproc_base}_desc-brain_dseg.nii.gz",
            't1w_tpms': [
                f"{anat_preproc_base}_label-GM_desc-brain_probseg.nii.gz",
                f"{anat_preproc_base}_label-WM_desc-brain_probseg.nii.gz",
                f"{anat_preproc_base}_label-CSF_desc-brain_probseg.nii.gz",
            ],
            'std2anat_xfm': f"{anat_preproc_base}_from-MNI152NLin2009cAsym_to-T1w_mode-image_xfm.h5"
        }
        
        # set anat_buffer inputs
        for _key, _path in anat_inputs.items():
            
            if _key == 'subject_id': 
                setattr(anat_buffer.inputs,'subject_id',_path)
                continue
                
            if _key == 't1w_tpms':
                assert len(_path) == 3
                for i in _path:
                    assert os.path.exists(i), f"{i} does not exist."
                setattr(anat_buffer.inputs,'t1w_tpms',_path)
                continue
                
            assert os.path.exists(_path), f"{_path} does not exist."
            setattr(anat_buffer.inputs, _key, _path)
    
    # Checkpoint
    if args.anat_flag:
         print(f"\n\n[anat_flag] invoked.\nOnly running anatomical processing pipeline.")
         wf.run()
         return 0

    


def _get_element(_list,element_idx):
    return _list[element_idx]


if __name__ == "__main__":
    run()