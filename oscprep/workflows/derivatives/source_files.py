def get_anat_brainmask_source_files(ANAT_ACQ, ANAT_FILES):
    
    if ANAT_ACQ == 'MP2RAGE':
        _path = ANAT_FILES['UNI']
        sub_id = _path[_path.find('sub-'):].split('/')[0]
        ses_id = _path[_path.find('ses-'):].split('/')[0]
        run_id = _path[_path.find('run-'):].split('_')[0]
        t1w_brain = f"{sub_id}/{ses_id}/anat/{sub_id}_{ses_id}_acq-MP2RAGE_{run_id}_desc-brain_T1w.nii.gz"
        t1w_brainmask = f"{sub_id}/{ses_id}/anat/{sub_id}_{ses_id}_acq-MP2RAGE_{run_id}_desc-brain_mask.nii.gz"
        
        return t1w_brain, t1w_brainmask, sub_id, ses_id, run_id
    
    elif ANAT_ACQ == 'MPRAGE':
        _path = ANAT_FILES['T1w']
        sub_id = _path[_path.find('sub-'):].split('/')[0]
        ses_id = _path[_path.find('ses-'):].split('/')[0]
        run_id = _path[_path.find('run-'):].split('_')[0]
        t1w_brain = f"{sub_id}/{ses_id}/anat/{sub_id}_{ses_id}_acq-MPRAGE_{run_id}_desc-brain_T1w.nii.gz"
        t1w_brainmask = f"{sub_id}/{ses_id}/anat/{sub_id}_{ses_id}_acq-MPRAGE_{run_id}_desc-brain_mask.nii.gz"

        return t1w_brain, t1w_brainmask, sub_id, ses_id, run_id

    else:
        NotImplemented

def get_bold_brainmask_source_files(bold_path):
    
    sub_id = bold_path[bold_path.find('sub-'):].split('/')[0]
    ses_id = bold_path[bold_path.find('ses-'):].split('/')[0]
    run_id = bold_path[bold_path.find('run-'):].split('_')[0]
    bold_brain = f"{sub_id}/{ses_id}/func/{bold_path.split('/')[-1].replace('bold.nii.gz','desc-brain_bold.nii.gz')}"
    bold_brainmask = f"{sub_id}/{ses_id}/func/{bold_path.split('/')[-1].replace('bold.nii.gz','desc-brain_mask.nii.gz')}"

    return bold_brain, bold_brainmask, sub_id, ses_id, run_id

def get_wholebrain_bold_preproc_source_files(bold_path):

    sub_id = bold_path[bold_path.find('sub-'):].split('/')[0]
    ses_id = bold_path[bold_path.find('ses-'):].split('/')[0]
    run_id = bold_path[bold_path.find('run-'):].split('_')[0]
    # bold
    bold_ref = f"{sub_id}/{ses_id}/func/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','space-T1w_boldref.nii.gz')}"
    # transforms
    wholebrain_bold_to_t1_mat = f"{sub_id}/{ses_id}/reg/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','from-wholebrain_to-T1w_xfm.mat')}"
    # report 
    wholebrain_bold_to_t1_svg = f"{sub_id}/{ses_id}/figures/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','from-wholebrain_to-T1w.svg')}"
    # distorted
    # brainmask wf
    distorted_boldref = f"{sub_id}/{ses_id}/wholebrain_bold/distorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','boldref.nii.gz')}"
    distorted_brainmask = f"{sub_id}/{ses_id}/wholebrain_bold/distorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','brainmask.nii.gz')}"
    distorted_dseg = f"{sub_id}/{ses_id}/wholebrain_bold/distorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','dseg.nii.gz')}"
    distorted_itk_bold_to_t1 = f"{sub_id}/{ses_id}/wholebrain_bold/distorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','from-wholebrain_to-t1_xfm.itk.txt')}"
    distorted_itk_t1_to_bold = f"{sub_id}/{ses_id}/wholebrain_bold/distorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','from-t1_to-wholebrain_xfm.itk.txt')}"
    # undistorted
    # to_anat_wf
    undistorted_itk_bold_to_t1 = f"{sub_id}/{ses_id}/wholebrain_bold/undistorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','proc-sdc_from-wholebrain_to-t1_xfm.itk.txt')}"
    undistorted_itk_t1_to_bold = f"{sub_id}/{ses_id}/wholebrain_bold/undistorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','proc-sdc_from-t1_to-wholebrain_xfm.itk.txt')}"
    undistorted_fsl_bold_to_t1 = f"{sub_id}/{ses_id}/wholebrain_bold/undistorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','proc-sdc_from-wholebrain_to-t1_xfm.fsl.mat')}"
    undistorted_fsl_t1_to_bold = f"{sub_id}/{ses_id}/wholebrain_bold/undistorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','proc-sdc_from-t1_to-wholebrain_xfm.fsl.mat')}"
    undistorted_dseg = f"{sub_id}/{ses_id}/wholebrain_bold/undistorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','proc-sdc_dseg.nii.gz')}"
    undistorted_spacet1_boldref = f"{sub_id}/{ses_id}/wholebrain_bold/undistorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','space-T1w_proc-sdc_boldref.nii.gz')}"
    # sdc_wf
    undistorted_boldref = f"{sub_id}/{ses_id}/wholebrain_bold/undistorted/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','proc-sdc_boldref.nii.gz')}"

    return {
        "sub_id": sub_id,
        "ses_id": ses_id,
        "run_id": run_id,
        "bold_ref": bold_ref,
        "wholebrain_bold_to_t1_mat": wholebrain_bold_to_t1_mat,
        "wholebrain_bold_to_t1_svg": wholebrain_bold_to_t1_svg,
        "distorted_boldref": distorted_boldref,
        "distorted_brainmask": distorted_brainmask,
        "distorted_dseg": distorted_dseg,
        "distorted_itk_bold_to_t1": distorted_itk_bold_to_t1,
        "distorted_itk_t1_to_bold": distorted_itk_t1_to_bold,
        "undistorted_itk_bold_to_t1": undistorted_itk_bold_to_t1,
        "undistorted_itk_t1_to_bold": undistorted_itk_t1_to_bold,
        "undistorted_fsl_bold_to_t1": undistorted_fsl_bold_to_t1,
        "undistorted_fsl_t1_to_bold": undistorted_fsl_t1_to_bold,
        "undistorted_dseg": undistorted_dseg,
        "undistorted_spacet1_boldref": undistorted_spacet1_boldref,
        "undistorted_boldref": undistorted_boldref,
    }

def get_slab_bold_preproc_source_files(bold_path):

    sub_id = bold_path[bold_path.find('sub-'):].split('/')[0]
    ses_id = bold_path[bold_path.find('ses-'):].split('/')[0]
    run_id = bold_path[bold_path.find('run-'):].split('_')[0]
    # bold
    bold_ref = f"{sub_id}/{ses_id}/func/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','space-T1w_boldref.nii.gz')}"
    bold_brainmask = f"{sub_id}/{ses_id}/func/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','space-T1w_desc-boldref_brainmask.nii.gz')}"
    bold_preproc = f"{sub_id}/{ses_id}/func/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','space-T1w_desc-preproc_bold.nii.gz')}"
    # confounds
    bold_confounds = f"{sub_id}/{ses_id}/func/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','confounds.tsv')}"
    # rois
    bold_roi_svg = f"{sub_id}/{ses_id}/figures/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','desc-confound_roi.svg')}"
    bold_acompcor_csf = f"{sub_id}/{ses_id}/roi/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','desc-confound_roi-csf_aCompCor.nii.gz')}"
    bold_acompcor_wm = f"{sub_id}/{ses_id}/roi/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','desc-confound_roi-wm_aCompCor.nii.gz')}"
    bold_acompcor_wmcsf = f"{sub_id}/{ses_id}/roi/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','desc-confound_roi-wmcsf_aCompCor.nii.gz')}"
    bold_tcompcor = f"{sub_id}/{ses_id}/roi/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','desc-confound_tCompCor.nii.gz')}"
    bold_crownmask = f"{sub_id}/{ses_id}/roi/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','desc-confound_crownmask.nii.gz')}"
    # transforms
    slab_bold_hmc_mats = f"{sub_id}/{ses_id}/reg/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','_hmc.mats')}"
    slab_bold_sdc_warp = f"{sub_id}/{ses_id}/reg/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','sdc_warp.nii.gz')}"
    slab_bold_to_wholebrain_bold_mat = f"{sub_id}/{ses_id}/reg/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','from-slab_to-wholebrain_xfm.mat')}"
    slab_bold_to_wholebrain_bold_svg = f"{sub_id}/{ses_id}/figures/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','from-slab_to-wholebrain.svg')}"
    slab_bold_to_t1_warp = f"{sub_id}/{ses_id}/reg/{bold_path.split('/')[-1].replace('part-mag_bold.nii.gz','from-slab_to-T1w_warp.nii.gz')}"

    return {
        "sub_id": sub_id,
        "ses_id": ses_id,
        "run_id": run_id,
        "bold_ref": bold_ref,
        "bold_brainmask": bold_brainmask,
        "bold_preproc": bold_preproc,
        "bold_confounds": bold_confounds,
        "bold_roi_svg": bold_roi_svg,
        "bold_acompcor_csf": bold_acompcor_csf,
        "bold_acompcor_wm": bold_acompcor_wm,
        "bold_acompcor_wmcsf": bold_acompcor_wmcsf,
        "bold_tcompcor": bold_tcompcor,
        "bold_crownmask": bold_crownmask,
        "bold_hmc": slab_bold_hmc_mats,
        "bold_sdc_warp": slab_bold_sdc_warp,
        "slab_bold_to_wholebrain_bold_mat": slab_bold_to_wholebrain_bold_mat,
        "slab_bold_to_wholebrain_bold_svg": slab_bold_to_wholebrain_bold_svg,
        "slab_bold_to_t1_warp": slab_bold_to_t1_warp
    }