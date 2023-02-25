def run():

    import argparse, os, sys

    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
    from niworkflows.utils.spaces import SpatialReferences,Reference
    from nipype.interfaces import utility as niu
    from nipype.pipeline import engine as pe
    from nipype.interfaces.utility import IdentityInterface
    from bids import BIDSLayout

    """
    computecanada gives a TLS CA certificate bundle error
    Solution:
    https://stackoverflow.com/questions/46119901/python-requests-cant-find-a-folder-with-a-certificate-when-converted-to-exe
    """
    import certifi
    os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(os.path.dirname(sys.argv[0]), certifi.where())

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
    from fmriprep.workflows.bold.stc import init_bold_stc_wf
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
    # mprage
    MPRAGE_SYNTHSTRIP_NO_CSF = args.mprage_synthstrip_no_csf_flag
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
    SDCFLOWS_DIR = f"{DERIV_DIR}/sdcflows"
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
    if not len(BOLD_WHOLEBRAIN_PATHS) == 1:
        print(f"WARNING: There are more than 1 wholebrain bold images.\n{BOLD_WHOLEBRAIN_PATHS}")
        bold_wholebrain = BOLD_WHOLEBRAIN_PATHS[-1]
    else:
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

    # `bold_slab` selection filters
    BOLD_SLAB_PATHS_RUN, BOLD_SLAB_PATHS_SELECT_TASK, BOLD_SLAB_PATHS_SELECT_RUN = [], [], []
    for bold_slab in BOLD_SLAB_PATHS:
        # check if file `bold_slab` is already processed
        processed_flag = False
        source_preproc_slab_bold = get_slab_bold_preproc_source_files(bold_slab)
        for src_k, src_v in source_preproc_slab_bold.items():
            f_exist = os.path.exists(os.path.join(DERIV_DIR,BOLD_PREPROC_DIR.split('/')[-1],src_v))
            if src_v.endswith('.nii.gz') and 'func' in src_v.split('/') and f_exist:
                processed_flag=True
        BOLD_SLAB_PATHS_RUN.append(processed_flag)
        # select `bold_slab` based on `args.select_task`
        task_flag = False
        if args.select_task is None:
            task_flag = True
        if f"_task-{args.select_task}_" in bold_slab:
            task_flag = True
        BOLD_SLAB_PATHS_SELECT_TASK.append(task_flag)
        # select `bold_slab` based on `args.select_run`
        run_flag = False
        if args.select_run is None:
            run_flag = True
        if f"_run-{args.select_run}_" in bold_slab:
            run_flag = True
        BOLD_SLAB_PATHS_SELECT_RUN.append(run_flag)

    """
    Workflow flags
    """
    DERIV_WORKFLOW_FLAGS = {}
    DERIV_WORKFLOW_FLAGS['anat_brainmask'] = os.path.isdir(f"{BRAINMASK_DIR}/{ANAT_SUBJECT_ID}/{ANAT_SESSION_ID}/anat")
    DERIV_WORKFLOW_FLAGS['anat_preproc'] = os.path.isdir(f"{SMRIPREP_DIR}/sub-{SUBJECT_ID}")
    DERIV_WORKFLOW_FLAGS['fmap_preproc'] = os.path.isdir(f"{SDCFLOWS_DIR}/sub-{SUBJECT_ID}/ses-{SESSION_ID}")
    DERIV_WORKFLOW_FLAGS['wholebrain_bold_preproc'] = os.path.isdir(f"{BOLD_PREPROC_DIR}/sub-{SUBJECT_ID}/ses-{SESSION_ID}/wholebrain_bold")
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
    print('----BOLD [Whole Brain]----')
    for p in BOLD_WHOLEBRAIN_PATHS:
        print(p)
    # Slab bold paths
    print('----BOLD [Slab]----')
    if args.slab_bold_quick:
        print('[slab_bold_quick] invoked.\nOnly the first 10 volumes are outputted.')
    for processed_flag,select_task_flag,select_run_flag,p in zip(BOLD_SLAB_PATHS_RUN,BOLD_SLAB_PATHS_SELECT_TASK,BOLD_SLAB_PATHS_SELECT_RUN,BOLD_SLAB_PATHS):
        _s,_t,_r = False,False,False # Not Processed
        if processed_flag:
            _s = True # Processed
        if select_task_flag:
            _t = True # Selected
        if select_run_flag:
            _r = True # Selected
        print(f"[{_s}|{_t}|{_r}] {p}") # Only False | True | True are processed.
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
    workflow_suffix = ''
    if args.anat_flag:
        workflow_suffix = 'anat_only_'
    if args.slab_bold_quick:
        workflow_suffix = 'bold_quick_'
    _OSCPREP_VERSION = str(OSCPREP_VERSION).replace('.','_')
    wf = Workflow(
        name=f'oscprep_sub-{SUBJECT_ID}_session-{SESSION_ID}_{workflow_suffix}v{_OSCPREP_VERSION}',
        base_dir=args.scratch_dir
    )

    """
    Set-up anatomical workflows
    """
    # get brainmask-ed t1w output names
    source_brain, source_brainmask, anat_subj_id, anat_ses_id, anat_run_id = get_anat_brainmask_source_files(ANAT_ACQ, ANAT_FILES) 
    t1w_input = f"{BRAINMASK_DIR}/{source_brain}" # Mandatory argument
    # anat_buffer(s)
    anat_bm_buffer = pe.Node(niu.IdentityInterface(['t1w_brain']),name='anat_brainmask_buffer')
    anat_buffer = pe.Node(
        niu.IdentityInterface(
            [
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
        name='anat_smriprep_buffer'
    )

    if not DERIV_WORKFLOW_FLAGS['anat_brainmask']:
        if ANAT_ACQ == 'MP2RAGE':
            from oscprep.workflows.anat.brainmask import init_brainmask_mp2rage_wf 
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
                (anat_brainmask_derivatives_wf,anat_bm_buffer,[('outputnode.t1w_brain','t1w_brain')])
            ])
        elif ANAT_ACQ == 'MPRAGE':
            from oscprep.workflows.anat.brainmask import init_brainmask_mprage_wf 
            # mp2rage brainmask workflow
            brainmask_wf = init_brainmask_mprage_wf()
            brainmask_inputnode = pe.Node(
                niu.IdentityInterface(
                    [
                        'mprage',
                        'no_csf', # synthstrip on native t1w
                    ]
                ),
                name='brainmask_inputnode'
            )
            brainmask_inputnode.inputs.mprage = ANAT_FILES['T1w']
            brainmask_inputnode.inputs.no_csf = MPRAGE_SYNTHSTRIP_NO_CSF
            # mprage brainmask derivatives workflow
            anat_brainmask_derivatives_wf = init_anat_brainmask_derivatives_wf(
                DERIV_DIR,
                source_brain,
                source_brainmask,
                out_path_base=BRAINMASK_DIR.split('/')[-1]
            )
            # connect
            wf.connect([
                (brainmask_inputnode,brainmask_wf,[
                    ('mprage','inputnode.mprage'),
                    ('no_csf','inputnode.no_csf'),
                ]),
                (brainmask_wf, anat_brainmask_derivatives_wf,[
                    ('outputnode.mprage_brain','inputnode.t1w_brain'),
                    ('outputnode.mprage_brainmask','inputnode.t1w_brainmask')
                ]),
                (anat_brainmask_derivatives_wf,anat_bm_buffer,[('outputnode.t1w_brain','t1w_brain')])
            ])
        else:
            NotImplemented
    else:
        # ``brainmask_wf`` should have produced ``t1w_input``
        anat_bm_buffer.inputs.t1w_brain = t1w_input
        
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
            niu.IdentityInterface(['subjects_dir','subject_id','t1w','t2w','roi','flair']),
            name='anat_preproc_inputnode'
        )
        # anat_preproc inputnode
        anat_preproc_inputnode.inputs.subjects_dir = FREESURFER_DIR
        anat_preproc_inputnode.inputs.subject_id = f"sub-{SUBJECT_ID}"
        # connect
        wf.connect([
            (anat_preproc_inputnode,anat_preproc_wf,[
                ('subjects_dir','inputnode.subjects_dir'),
                ('subject_id','inputnode.subject_id'),
            ]),
            (anat_bm_buffer,anat_preproc_wf,[('t1w_brain','inputnode.t1w')]),
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
         print(f"\n[anat_flag] invoked.\nOnly running anatomical processing pipeline.")
         wf.run()
         return 0

    """
    Set-up fieldmap (fmap) workflows
    """ 
    # fmap_buffer
    fmap_buffer = pe.Node(
        niu.IdentityInterface(
            [
                'fmap_ref', # fmap_wf 
                'fmap', # fmap_wf
            ]
        ),
        name='fmap_buffer'
    )

    if not DERIV_WORKFLOW_FLAGS['fmap_preproc']:
        
        # get fmap given a subject and session id
        # asserts fmap is of PHASEDIFF EstimatorType
        # and only one fmap exists
        fmap_estimators = find_estimators(
            layout=layout,
            subject=SUBJECT_ID,
            sessions=SESSION_ID
        )
        assert len(fmap_estimators) == 1, f"There are {len(fmap_estimators)} fieldmap estimators. Expected is 1."
        assert fmap_estimators[0].method == fm.EstimatorType.PHASEDIFF, f"EstimatorType is {fmap_estimators[0].method}. Expect is {fm.EstimatorType.PHASEDIFF}"
        # Process fieldmap
        fmap_wf = init_fmap_preproc_wf(
            estimators=fmap_estimators,
            omp_nthreads=OMP_NTHREADS,
            output_dir=DERIV_DIR,
            subject=SUBJECT_ID,
            name='fmap_preproc_wf'
        )
        # connect
        wf.connect([
            (fmap_wf,fmap_buffer,[
                (('outputnode.fmap_ref',_get_element,0),'fmap_ref'),
                (('outputnode.fmap',_get_element,0),'fmap'),
            ])
        ])

    else:
        
        # ``fmap_wf`` should produce the following:
        fmap_preproc_base = f"{SDCFLOWS_DIR}/sub-{SUBJECT_ID}/ses-{SESSION_ID}/fmap/sub-{SUBJECT_ID}_ses-{SESSION_ID}_fmapid-auto00000"
        fmap_inputs = {
            'fmap_ref': f"{fmap_preproc_base}_desc-magnitude_fieldmap.nii.gz",
            'fmap': f"{fmap_preproc_base}_desc-preproc_fieldmap.nii.gz",
        }
        # set fmap_buffer inputs
        for _key, _path in fmap_inputs.items():
            assert os.path.exists(_path), f"{_path} does not exist."
            setattr(fmap_buffer.inputs, _key, _path)

    # register anat to fmap
    anat_to_fmap_wf = init_anat_to_fmap(name='reg_anat_to_fmap_wf')
    wf.connect([
        (fmap_buffer,anat_to_fmap_wf,[('fmap_ref','inputnode.fmap_ref')]),
        (anat_buffer,anat_to_fmap_wf,[('fs_t1w_brain','inputnode.anat')]),
    ])
    
    """
    Set-up wholebrain bold workflows
    """
    # get output names for all wholebrain bold related files
    source_preproc_wholebrain_bold = get_wholebrain_bold_preproc_source_files(bold_wholebrain)
    # wholebrain_bold_buffer
    wholebrain_bold_buffer = pe.Node(
        niu.IdentityInterface(
            [
                'distorted_dseg',
                'distorted_boldref',
                'distorted_brainmask',
                'distorted_itk_t1_to_bold',
                'undistorted_dseg',
                'undistorted_fsl_bold_to_t1',
                'undistorted_boldref',
            ]
        ),
        name='wholebrain_bold_buffer'
    )

    if not DERIV_WORKFLOW_FLAGS['wholebrain_bold_preproc']:
    
        """
        brainmask sdc-uncorrected (or distorted) wholebrain bold workflows
        """
        # wholebrain bold inputnode
        wholebrain_bold_inputnode = pe.Node(
            niu.IdentityInterface(['wholebrain_bold']),
            name='bold_wholebrain_inputnode'
        )
        wholebrain_bold_inputnode.inputs.wholebrain_bold = bold_wholebrain
        # get wholebrain bold reference image
        wholebrain_bold_ref_wf = init_bold_ref_wf(
            bold_wholebrain,
            name='wholebrain_bold_reference_wf'
        )
        # get wholebrain bold brainmask
        wholebrain_bold_brainmask_wf = init_bold_wholebrain_brainmask_wf(name='wholebrain_bold_brainmask_wf')
        # save wholebrain bold brainmask in derivative directories
        source_brain, source_brainmask, _, _, _ = get_bold_brainmask_source_files(bold_wholebrain)
        wholebrain_bold_brainmask_derivatives_wf = init_bold_brainmask_derivatives_wf(
            DERIV_DIR,
            source_brain,
            source_brainmask,
            'wholebrain',
            out_path_base=BRAINMASK_DIR.split('/')[-1],
            name='wholebrain_bold_brainmask_derivatives_wf'
        )

        """
        apply fmap to wholebrain bold workflows
        """
        # register fmap to wholebrain bold
        fmap_to_wholebrain_bold_wf = init_fmap_to_wholebrain_bold_wf(name='reg_fmap_to_wholebrain_bold_wf')
        # apply sdc to wholebrain bold
        wholebrain_bold_unwarp_wf = init_bold_sdc_wf(name='wholebrain_bold_unwarp_wf')
        wholebrain_bold_unwarp_wf.inputs.inputnode.bold_metadata = layout.get_metadata(bold_wholebrain)

        """
        register sdc-corrected (or undistorted) wholebrain bold to anat
        """
        wholebrain_bold_to_anat_wf = init_wholebrain_bold_to_anat_wf(name='reg_wholebrain_bold_to_anat_wf')

        # connect
        wf.connect([
            (wholebrain_bold_inputnode,wholebrain_bold_ref_wf,[('wholebrain_bold','inputnode.bold')]),
            (wholebrain_bold_ref_wf,wholebrain_bold_brainmask_wf,[('outputnode.boldref','inputnode.wholebrain_bold')]),
            (anat_buffer,wholebrain_bold_brainmask_wf, [
                ('fsnative2t1w_xfm','inputnode.fsnative2t1w_xfm'),
                ('subjects_dir','inputnode.subjects_dir'),
                ('subject_id','inputnode.subject_id'),
                ('t1w_dseg','inputnode.t1w_dseg'),
                ('fs_t1w_brain','inputnode.t1w_brain'),
                ('t1w_brainmask','inputnode.t1w_brainmask'),
            ]),
            (wholebrain_bold_brainmask_wf,wholebrain_bold_brainmask_derivatives_wf,[
                ('outputnode.brain','inputnode.bold_brain'),
                ('outputnode.brainmask','inputnode.bold_brainmask'),
            ]),
            (anat_to_fmap_wf,fmap_to_wholebrain_bold_wf,[('outputnode.itk_fmap2anat','inputnode.itk_fmap2anat')]),
            (wholebrain_bold_brainmask_wf,fmap_to_wholebrain_bold_wf,[('outputnode.itk_t1_to_bold','inputnode.itk_anat2wholebrainbold')]),
            (fmap_to_wholebrain_bold_wf,wholebrain_bold_unwarp_wf,[('outputnode.itk_fmap2epi','inputnode.fmap2epi_xfm')]),
            (fmap_buffer,wholebrain_bold_unwarp_wf,[
                ('fmap_ref','inputnode.fmap_ref'),
                ('fmap','inputnode.fmap'),
            ]),
            (wholebrain_bold_brainmask_wf,wholebrain_bold_unwarp_wf,[
                ('outputnode.brain','inputnode.target_ref'),
                ('outputnode.brain','inputnode.target_mask'),
            ]),
            (wholebrain_bold_unwarp_wf,wholebrain_bold_to_anat_wf,[('outputnode.undistorted_bold','inputnode.undistorted_bold')]),
            (anat_buffer,wholebrain_bold_to_anat_wf,[
                ('fsnative2t1w_xfm','inputnode.fsnative2t1w_xfm'),
                ('subjects_dir','inputnode.subjects_dir'),
                ('subject_id','inputnode.subject_id'),
                ('t1w_dseg','inputnode.t1w_dseg'),
                ('fs_t1w_brain','inputnode.t1w_brain'),
            ]),
        ])

        """
        save wholebrain bold reference data to derivative directories
        """
        wholebrain_bold_preproc_derivatives_wf = init_wholebrain_bold_preproc_derivatives_wf(
            DERIV_DIR,
            source_preproc_wholebrain_bold['sub_id'],
            source_preproc_wholebrain_bold['ses_id'],
            source_preproc_wholebrain_bold['bold_ref'],
            source_preproc_wholebrain_bold['wholebrain_bold_to_t1_mat'],
            source_preproc_wholebrain_bold['wholebrain_bold_to_t1_svg'],
            source_preproc_wholebrain_bold['distorted_boldref'],
            source_preproc_wholebrain_bold['distorted_brainmask'],
            source_preproc_wholebrain_bold['distorted_dseg'],
            source_preproc_wholebrain_bold['distorted_itk_bold_to_t1'],
            source_preproc_wholebrain_bold['distorted_itk_t1_to_bold'],
            source_preproc_wholebrain_bold['undistorted_itk_bold_to_t1'],
            source_preproc_wholebrain_bold['undistorted_itk_t1_to_bold'],
            source_preproc_wholebrain_bold['undistorted_fsl_bold_to_t1'],
            source_preproc_wholebrain_bold['undistorted_fsl_t1_to_bold'],
            source_preproc_wholebrain_bold['undistorted_dseg'],
            source_preproc_wholebrain_bold['undistorted_spacet1_boldref'],
            source_preproc_wholebrain_bold['undistorted_boldref'],
            workflow_name_base='wholebrain_bold',
            out_path_base=BOLD_PREPROC_DIR.split('/')[-1],
        )

        # connect
        wf.connect([
            (wholebrain_bold_to_anat_wf,wholebrain_bold_preproc_derivatives_wf,[
                ('outputnode.undistorted_bold_to_t1','inputnode.bold_ref'),
                ('outputnode.fsl_wholebrain_bold_to_t1','inputnode.wholebrain_bold_to_t1_mat'),
            ]),
            (wholebrain_bold_to_anat_wf,wholebrain_bold_preproc_derivatives_wf,[
                ('outputnode.out_report','inputnode.wholebrain_bold_to_t1_svg')
            ]),
            (wholebrain_bold_brainmask_wf,wholebrain_bold_preproc_derivatives_wf,[
                ('outputnode.dseg','inputnode.distorted_dseg'),
                ('outputnode.brain','inputnode.distorted_boldref'),
                ('outputnode.brainmask','inputnode.distorted_brainmask'),
                ('outputnode.itk_t1_to_bold','inputnode.distorted_itk_t1_to_bold'),
            ]),
            (wholebrain_bold_to_anat_wf,wholebrain_bold_preproc_derivatives_wf,[
                ('outputnode.undistorted_bold_dseg','inputnode.undistorted_dseg'),
                ('outputnode.fsl_wholebrain_bold_to_t1','inputnode.undistorted_fsl_bold_to_t1'),
            ]),
            (wholebrain_bold_unwarp_wf,wholebrain_bold_preproc_derivatives_wf,[
                ('outputnode.undistorted_bold','inputnode.undistorted_boldref'),
            ]),
        ])

        """
        connect wholebrain bold buffer
        """
        wf.connect([
            (wholebrain_bold_brainmask_wf,wholebrain_bold_buffer,[
                ('outputnode.dseg','distorted_dseg'),
                ('outputnode.brain','distorted_boldref'),
                ('outputnode.brainmask','distorted_brainmask'),
                ('outputnode.itk_t1_to_bold','distorted_itk_t1_to_bold'),
            ]),
            (wholebrain_bold_to_anat_wf,wholebrain_bold_buffer,[
                ('outputnode.undistorted_bold_dseg','undistorted_dseg'),
                ('outputnode.fsl_wholebrain_bold_to_t1','undistorted_fsl_bold_to_t1'),
            ]),
            (wholebrain_bold_unwarp_wf,wholebrain_bold_buffer,[
                ('outputnode.undistorted_bold','undistorted_boldref'),
            ]),
        ])
    
    else:
        
        # wholebrain bold workflows should produce the following:
        wholebrain_bold_inputs = {
            'distorted_dseg': f"{BOLD_PREPROC_DIR}/{source_preproc_wholebrain_bold['distorted_dseg']}",
            'distorted_boldref': f"{BOLD_PREPROC_DIR}/{source_preproc_wholebrain_bold['distorted_boldref']}",
            'distorted_brainmask': f"{BOLD_PREPROC_DIR}/{source_preproc_wholebrain_bold['distorted_brainmask']}",
            'distorted_itk_t1_to_bold': f"{BOLD_PREPROC_DIR}/{source_preproc_wholebrain_bold['distorted_itk_t1_to_bold']}",
            'undistorted_dseg': f"{BOLD_PREPROC_DIR}/{source_preproc_wholebrain_bold['undistorted_dseg']}",
            'undistorted_fsl_bold_to_t1': f"{BOLD_PREPROC_DIR}/{source_preproc_wholebrain_bold['undistorted_fsl_bold_to_t1']}",
            'undistorted_boldref': f"{BOLD_PREPROC_DIR}/{source_preproc_wholebrain_bold['undistorted_boldref']}",
        }
        # set wholebrain_bold_buffer inputs
        for _key, _path in wholebrain_bold_inputs.items():
            assert os.path.exists(_path), f"{_path} does not exist."
            setattr(wholebrain_bold_buffer.inputs, _key, _path)

    """
    Set-up slab bold workflows
    """
    for bold_idx, (processed_flag,select_task_flag,select_run_flag,bold_slab) in enumerate(zip(
        BOLD_SLAB_PATHS_RUN,
        BOLD_SLAB_PATHS_SELECT_TASK,
        BOLD_SLAB_PATHS_SELECT_RUN,
        BOLD_SLAB_PATHS
        )):
        
        """
        check if file `bold_slab` is processed and not selected, otherwise skip
        """
        if processed_flag or not select_task_flag or not select_run_flag:
            continue

        """
        init run information
        """
        # workflow labels
        bold_slab_rel_path = bold_slab.split('/')[-1]
        task = bold_slab_rel_path[bold_slab_rel_path.find('task-'):].split('_')[0]
        run = bold_slab_rel_path[bold_slab_rel_path.find('run-'):].split('_')[0]
        bold_slab_base = f"slab_bold_{task}_{run}"
        # get metadata
        metadata = layout.get_metadata(bold_slab)
        # slab bold inputnode
        slab_inputnode = pe.Node(
            niu.IdentityInterface(['slab_bold']),
            name=f'{bold_slab_base}_inputnode'
        )
        slab_inputnode.inputs.slab_bold = bold_slab
        # get slab bold reference image
        slab_bold_ref_wf = init_bold_ref_wf(
            bold_slab,
            name=f'{bold_slab_base}_reference_wf'
        )
        """
        apply some minimal preprocessing steps
        - slice-timing correction (stc)
        - head-motion correction (hmc)
        """
        # stc
        assert bool(metadata["SliceTiming"]), f"SliceTiming metadata is unavailable."
        slab_bold_stc_wf = init_bold_stc_wf(
            metadata=metadata,
            name=f'{bold_slab_base}_stc_wf'
        )
        slab_bold_stc_wf.inputs.inputnode.skip_vols = 0
        # hmc
        assert bool(metadata["RepetitionTime"]), f"RepetitionTime metadata is unavailable."
        slab_bold_hmc_wf = init_bold_hmc_wf(
            low_pass_threshold=BOLD_HMC_LOWPASS_THRESHOLD,
            name=f'{bold_slab_base}_hmc_wf'
        )
        slab_bold_hmc_wf.inputs.inputnode.bold_metadata = metadata
        # connect
        wf.connect([
            (slab_inputnode,slab_bold_ref_wf,[('slab_bold','inputnode.bold')]),
            (slab_inputnode,slab_bold_stc_wf,[('slab_bold','inputnode.bold_file')]),
            (slab_inputnode,slab_bold_hmc_wf,[('slab_bold','inputnode.bold_file')]),
            (slab_bold_ref_wf,slab_bold_hmc_wf,[('outputnode.boldref','inputnode.bold_reference')])
        ])
        
        """
        brainmask sdc-uncorrected (or distorted) slab bold workflows
        """
        # get slab bold brainmask
        slab_bold_brainmask_wf = init_bold_slab_brainmask_wf(name=f'{bold_slab_base}_brainmask_wf')
        # save slab bold brainmask in derivative directories
        source_brain, source_brainmask, _, _, _ = get_bold_brainmask_source_files(bold_slab)
        slab_bold_brainmask_derivatives_wf = init_bold_brainmask_derivatives_wf(
            DERIV_DIR,
            source_brain,
            source_brainmask,
            bold_slab_base,
            out_path_base=BRAINMASK_DIR.split('/')[-1],
            name=f'{bold_slab_base}_brainmask_derivatives_wf'
        )
        
        
        """
        apply fmap to wholebrain bold workflows
        """
        # register fmap to slab bold workflow
        fmap_to_slab_bold_wf = init_fmap_to_slab_bold_wf(name=f'reg_fmap_to_{bold_slab_base}_wf')
        # apply sdc to wholebrain bold
        slab_bold_unwarp_wf = init_bold_sdc_wf(name=f'{bold_slab_base}_unwarp_wf')
        slab_bold_unwarp_wf.inputs.inputnode.bold_metadata = metadata
        
        """
        register sdc-corrected slab bold to sdc-corrected wholebrain bold
        """
        slab_bold_to_wholebrain_bold_wf = init_slab_bold_to_wholebrain_bold_wf(
            bold2t1w_dof=6,
            use_bbr=True,
            name=f'reg_{bold_slab_base}_to_wholebrain_bold_wf'
        )
        
        # connect
        wf.connect([
            (slab_bold_ref_wf,slab_bold_brainmask_wf,[('outputnode.boldref','inputnode.slab_bold')]),
            (wholebrain_bold_buffer,slab_bold_brainmask_wf,[
                # Use wholebrain bold brainmask to perform slab bold brainmasking
                ('distorted_dseg','inputnode.wholebrain_bold_dseg'),
                ('distorted_boldref','inputnode.wholebrain_bold'),
                ('distorted_brainmask','inputnode.wholebrain_bold_brainmask'),
            ]),
            (slab_bold_brainmask_wf,slab_bold_brainmask_derivatives_wf,[
                ('outputnode.brain','inputnode.bold_brain'),
                ('outputnode.brainmask','inputnode.bold_brainmask'),
            ]),
            (anat_to_fmap_wf,fmap_to_slab_bold_wf,[('outputnode.itk_fmap2anat','inputnode.itk_fmap2anat')]),
            # use distorted wholebrain bold to slab bold affine to bring fmap to slab bold space
            (wholebrain_bold_buffer,fmap_to_slab_bold_wf,[
                ('distorted_itk_t1_to_bold','inputnode.itk_anat2wholebrainbold')]),
            (slab_bold_brainmask_wf,fmap_to_slab_bold_wf,[
                ('outputnode.itk_t1_to_bold','inputnode.itk_wholebrainbold2slabbold')]),
            (fmap_to_slab_bold_wf,slab_bold_unwarp_wf,[('outputnode.itk_fmap2epi','inputnode.fmap2epi_xfm')]),
            (fmap_buffer,slab_bold_unwarp_wf,[
                ('fmap_ref','inputnode.fmap_ref'),
                ('fmap','inputnode.fmap'),
            ]),
            (slab_bold_brainmask_wf,slab_bold_unwarp_wf,[
                ('outputnode.brain','inputnode.target_ref'),
                ('outputnode.brain','inputnode.target_mask'),
            ]),
            (wholebrain_bold_buffer,slab_bold_to_wholebrain_bold_wf,[
                ('undistorted_dseg','inputnode.undistorted_wholebrain_bold_dseg'),
            ]),
            (wholebrain_bold_buffer,slab_bold_to_wholebrain_bold_wf,[
                ('undistorted_boldref','inputnode.undistorted_wholebrain_bold'),
            ]),
            (slab_bold_unwarp_wf,slab_bold_to_wholebrain_bold_wf,[
                ('outputnode.undistorted_bold','inputnode.undistorted_slab_bold')
            ])
        ])
        
        """
        Merge and apply transforms
        """
        # merge sdc warp (slab-bold), 
        # slab bold to wholebrain bold affine, 
        # and wholebrain bold to anat affine
        # into a single warp
        merge_transforms_wf = init_fsl_merge_transforms_wf(name=f"{bold_slab_base}_merge_transforms_wf")
        # get slab bold brainmask in t1 space
        trans_slab_bold_brainmask_to_anat_wf = init_undistort_bold_slab_brainmask_to_t1_wf(name=f"trans_{bold_slab_base}_brainmask_to_t1")
        # apply all transformations to slab bold
        trans_slab_bold_to_anat_wf = init_apply_bold_to_anat_wf(
            slab_bold_quick=args.slab_bold_quick,
            name=f"trans_{bold_slab_base}_to_t1_wf"
        )
        trans_slab_bold_to_anat_wf.inputs.inputnode.bold_metadata = metadata
        
        # connect
        wf.connect([
            (slab_bold_to_wholebrain_bold_wf,merge_transforms_wf,[
                ('outputnode.fsl_slab_bold_to_wholebrain_bold','inputnode.slab2wholebrain_aff')
            ]),
            (wholebrain_bold_buffer,merge_transforms_wf,[
                ('undistorted_fsl_bold_to_t1','inputnode.wholebrain2anat_aff')
            ]),
            (slab_bold_unwarp_wf,merge_transforms_wf,[('outputnode.sdc_warp','inputnode.slab_sdc_warp')]),
            (anat_buffer,merge_transforms_wf,[('fs_t1w_brain','inputnode.reference')]),
            (slab_bold_brainmask_wf,merge_transforms_wf,[('outputnode.brain','inputnode.source')]),
            (slab_bold_brainmask_wf,trans_slab_bold_brainmask_to_anat_wf,[('outputnode.brainmask','inputnode.slab_bold_brainmask')]),
            (merge_transforms_wf,trans_slab_bold_brainmask_to_anat_wf,[
                ('outputnode.slab2anat_warp','inputnode.t1_warp'),
                ('outputnode.reference_resampled','inputnode.t1_resampled'),
            ]),
            (merge_transforms_wf,trans_slab_bold_to_anat_wf,[
                ('outputnode.slab2anat_warp','inputnode.bold_to_t1_warp'),
                ('outputnode.reference_resampled','inputnode.t1_resampled'),
            ]),
            (slab_bold_hmc_wf,trans_slab_bold_to_anat_wf,[('outputnode.fsl_affines','inputnode.fsl_hmc_affines')]),
            (slab_bold_stc_wf,trans_slab_bold_to_anat_wf,[('outputnode.stc_file','inputnode.bold_file')]),
            (slab_bold_ref_wf,trans_slab_bold_to_anat_wf,[('outputnode.boldref','inputnode.bold_ref')]),
            (trans_slab_bold_to_anat_wf,trans_slab_bold_brainmask_to_anat_wf,[('outputnode.t1_space_boldref','inputnode.t1_boldref')])
        ])
        
        """
        Confounds
        """
        from oscprep.workflows.bold.confounds import init_bold_confs_wf
        slab_bold_confs_wf = init_bold_confs_wf(
            mem_gb = 8,
            metadata=metadata,
            freesurfer=True,
            regressors_all_comps=False,
            regressors_dvars_th=1.5,
            regressors_fd_th=.5,
            name=f"{bold_slab_base}_confs_wf"
        )
        slab_bold_confs_wf.inputs.inputnode.skip_vols = 0
        slab_bold_confs_wf.inputs.inputnode.t1_bold_xform = 'identity'
        # connect
        wf.connect([
            (trans_slab_bold_brainmask_to_anat_wf,slab_bold_confs_wf,[('outputnode.t1_brainmask','inputnode.bold_mask')]),
            (trans_slab_bold_to_anat_wf,slab_bold_confs_wf,[('outputnode.t1_space_bold','inputnode.bold')]),
            (slab_bold_hmc_wf,slab_bold_confs_wf,[
                ('outputnode.movpar_file','inputnode.movpar_file'),
                ('outputnode.rmsd_file','inputnode.rmsd_file'),
            ]),
            (anat_buffer,slab_bold_confs_wf,[
                ('t1w_tpms','inputnode.t1w_tpms'),
                ('t1w_brainmask','inputnode.t1w_mask'),
            ]),
        ])
        
        """
        save slab preproc bold data to derivative directories
        """
        source_preproc_slab_bold = get_slab_bold_preproc_source_files(bold_slab)
        slab_bold_preproc_derivatives_wf = init_slab_bold_preproc_derivatives_wf(
            DERIV_DIR,
            source_preproc_slab_bold['sub_id'],
            source_preproc_slab_bold['ses_id'],
            source_preproc_slab_bold['bold_ref'],
            source_preproc_slab_bold['bold_brainmask'],
            source_preproc_slab_bold['bold_preproc'],
            source_preproc_slab_bold['bold_confounds'],
            source_preproc_slab_bold['bold_roi_svg'],
            source_preproc_slab_bold['bold_acompcor_csf'],
            source_preproc_slab_bold['bold_acompcor_wm'],
            source_preproc_slab_bold['bold_acompcor_wmcsf'],
            source_preproc_slab_bold['bold_tcompcor'],
            source_preproc_slab_bold['bold_crownmask'],
            source_preproc_slab_bold['bold_hmc'],
            source_preproc_slab_bold['bold_sdc_warp'],
            source_preproc_slab_bold['slab_bold_to_wholebrain_bold_mat'],
            source_preproc_slab_bold['slab_bold_to_wholebrain_bold_svg'],
            source_preproc_slab_bold['slab_bold_to_t1_warp'],
            bold_slab_base,
            out_path_base=BOLD_PREPROC_DIR.split('/')[-1],
        )
        
        # connect
        wf.connect([
            (trans_slab_bold_to_anat_wf,slab_bold_preproc_derivatives_wf,[
                ('outputnode.t1_space_boldref','inputnode.bold_ref'),
                ('outputnode.t1_space_bold','inputnode.bold_preproc'),
            ]),
            (trans_slab_bold_brainmask_to_anat_wf,slab_bold_preproc_derivatives_wf,[('outputnode.t1_brainmask','inputnode.bold_brainmask')]),
            (slab_bold_confs_wf,slab_bold_preproc_derivatives_wf,[
                ('outputnode.confounds_file','inputnode.bold_confounds'),
                (('outputnode.acompcor_masks',_get_element,0),'inputnode.bold_acompcor_csf'),
                (('outputnode.acompcor_masks',_get_element,1),'inputnode.bold_acompcor_wm'),
                (('outputnode.acompcor_masks',_get_element,2),'inputnode.bold_acompcor_wmcsf'),
                ('outputnode.tcompcor_mask','inputnode.bold_tcompcor'),
                ('outputnode.crown_mask','inputnode.bold_crownmask'),
                ('outputnode.rois_plot','inputnode.bold_roi_svg'),
            ]),
            (slab_bold_hmc_wf,slab_bold_preproc_derivatives_wf,[('outputnode.fsl_affines','inputnode.bold_hmc')]),
            (slab_bold_unwarp_wf,slab_bold_preproc_derivatives_wf,[('outputnode.sdc_warp','inputnode.bold_sdc_warp')]),
            (slab_bold_to_wholebrain_bold_wf,slab_bold_preproc_derivatives_wf,[
                ('outputnode.fsl_slab_bold_to_wholebrain_bold','inputnode.slab_bold_to_wholebrain_bold_mat'),
                ('outputnode.out_report','inputnode.slab_bold_to_wholebrain_bold_svg')
            ]),
            (merge_transforms_wf,slab_bold_preproc_derivatives_wf,[('outputnode.slab2anat_warp','inputnode.slab_bold_to_t1_warp')]),
        ])

    wf.run()

def _get_element(_list,element_idx):
    return _list[element_idx]

if __name__ == "__main__":
    run()
