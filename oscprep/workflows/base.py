import os
import sys
from copy import deepcopy

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from nipype.interfaces.utility import IdentityInterface, Function

from niworkflows.engine.workflows import LiterateWorkflow as Workflow

from bids import BIDSLayout
from oscprep.utils.data_grabber import bids_reader

def _prefix_subjid(label_subjid):

    if not label_subjid.startswith('sub-'):
        label_subjid = f"sub-{label_subjid}"

    return label_subjid

"""
Inputs (use this in arg parser later)
"""
# Mandatory arguments
BIDS_DIR = '/data/schmitz_osc_7T/bids_v1'
SUBJECT_ID = '009'
# Anat arguments
ANAT_PATH = None
## brainmask
BRAINMASK_DIR = f"{BIDS_DIR}/derivatives/brainmask"
ANAT_RESAMPLE_RES = 1.
ANAT_NO_CSF_FLAG = True
MP2RAGE_DENOISE_FACTOR = 8
## Freesurfer
FREESURFER_DIR = f"{BIDS_DIR}/derivatives/freesurfer" 
FREESURFER_SUBJECT_ID = _prefix_subjid(SUBJECT_ID)
## smriprep
SMRIPREP_DERIVATIVES_DIR = f"{BIDS_DIR}/derivatives/smriprep"
# fMRI arguments



# Set-up
bids_util = bids_reader(BIDS_DIR)
layout = BIDSLayout(BIDS_DIR)

if ANAT_PATH is None:
    ANAT_PATH = bids_util.get_t1w_list(SUBJECT_ID)

assert len(ANAT_PATH) == 1, f"Only 1 T1w key-pair is expected.\n{ANAT_PATH}"
ANAT_ACQ, ANAT_FILES = list(ANAT_PATH.items())[0]

# Anat preproc - brainmask
if ANAT_ACQ == 'MP2RAGE':
    from oscprep.workflows.anat.brainmask import init_brainmask_mp2rage_wf
    anat_brainmask_wf = init_brainmask_mp2rage_wf(ANAT_FILES,ANAT_RESAMPLE_RES,ANAT_NO_CSF_FLAG,MP2RAGE_DENOISE_FACTOR)
    import pdb; pdb.set_trace()
elif ANAT_ACQ == 'MPRAGE':
    NotImplemented
else:
    NotImplemented