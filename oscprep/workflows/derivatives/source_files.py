def get_anat_brainmask_source_files(ANAT_ACQ, ANAT_FILES):
    
    if ANAT_ACQ == 'MP2RAGE':
        _path = ANAT_FILES['UNI']
        sub_id = _path[_path.find('sub-'):].split('/')[0]
        ses_id = _path[_path.find('ses-'):].split('/')[0]
        run_id = _path[_path.find('run-'):].split('_')[0]
        t1w_brain = f"{sub_id}/{ses_id}/anat/{sub_id}_{ses_id}_acq-MP2RAGE_{run_id}_desc-brain_T1w.nii.gz"
        t1w_brainmask = f"{sub_id}/{ses_id}/anat/{sub_id}_{ses_id}_acq-MP2RAGE_{run_id}_desc-brain_mask.nii.gz"
        
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