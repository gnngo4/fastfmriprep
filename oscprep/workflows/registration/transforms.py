
import os

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_anat_to_fmap(
    name="reg_anat_to_fmap_wf"
):
    
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from nipype.interfaces import fsl, c3
    
    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["anat","fmap_ref"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["itk_anat2fmap","itk_fmap2anat"]
        ),
        name="outputnode"
    )

    flt = pe.Node(
        fsl.FLIRT(
            out_file='anat2fmap.nii.gz',
            dof=6
        ),
        name='flirt_anat2fmap'
    )
    fsl2itk_fwd = pe.Node(
        c3.C3dAffineTool(
            fsl2ras=True,
            itk_transform=True
        ),
        name='fsl2itk_fwd'
    )

    invt_flt_transform = pe.Node(
        fsl.ConvertXFM(invert_xfm=True),
        name='flirt_invt_xfm'
    )
    fsl2itk_invt = pe.Node(
        c3.C3dAffineTool(
            fsl2ras=True,
            itk_transform=True
        ),
        name='fsl2itk_invt'
    )

    workflow.connect([
        (inputnode,flt,[
            ('anat','in_file'),
            ('fmap_ref','reference')
        ]),
        (inputnode,fsl2itk_fwd,[
            ('anat','source_file'),
            ('fmap_ref','reference_file')
        ]),
        (flt,fsl2itk_fwd,[('out_matrix_file','transform_file')]),
        (fsl2itk_fwd,outputnode,[('itk_transform','itk_anat2fmap')]),
        (flt,invt_flt_transform,[('out_matrix_file','in_file')]),
        (inputnode,fsl2itk_invt,[
            ('fmap_ref','source_file'),
            ('anat','reference_file')
        ]),
        (invt_flt_transform,fsl2itk_invt,[('out_file','transform_file')]),
        (fsl2itk_invt,outputnode,[('itk_transform','itk_fmap2anat')])
    ])

    return workflow

def init_fmap_to_wholebrain_bold_wf(name="reg_fmap_to_wholebrain_bold_wf"):

    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from nipype.interfaces import ants

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=["itk_anat2wholebrainbold","itk_fmap2anat"]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["itk_fmap2epi"]
        ),
        name="outputnode"
    )

    tfm_to_txt = pe.Node(
        niu.Function(function=_tfm_to_txt, input_names=["source"]),
        name="tfm_to_txt"
    )

    concat_transforms = pe.Node(
        niu.Function(function=_concat_transforms_2, input_names=["xfm_1","xfm_2"]),
        name="concat_transforms"
    )

    compose_transform = pe.Node(
        ants.ComposeMultiTransform(dimension=3),
        name='compose_transform'
    )

    workflow.connect([
        (inputnode,concat_transforms,[('itk_fmap2anat','xfm_1')]),
        (inputnode,tfm_to_txt,[('itk_anat2wholebrainbold','source')]),
        (tfm_to_txt,concat_transforms,[('out','xfm_2')]),
        (tfm_to_txt,compose_transform,[(('out',_add_reference_flag),'reference_image')]),
        (concat_transforms,compose_transform,[('out','transforms')]),
        (compose_transform,outputnode,[('output_transform','itk_fmap2epi')]),
    ])

    return workflow

def init_fmap_to_slab_bold_wf(name="reg_fmap_to_slab_bold_wf"):

    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from nipype.interfaces import ants

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "itk_wholebrainbold2slabbold",
                "itk_anat2wholebrainbold",
                "itk_fmap2anat"
            ]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["itk_fmap2epi"]
        ),
        name="outputnode"
    )

    wholebrainbold_tfm_to_txt = pe.Node(
        niu.Function(function=_tfm_to_txt, input_names=["source"]),
        name="wholebrainbold_tfm_to_txt"
    )
    
    slabbold_tfm_to_txt = pe.Node(
        niu.Function(function=_tfm_to_txt, input_names=["source"]),
        name="slabbold_tfm_to_txt"
    )

    concat_transforms = pe.Node(
        niu.Function(function=_concat_transforms_3, input_names=["xfm_1","xfm_2","xfm_3"]),
        name="concat_transforms"
    )

    compose_transform = pe.Node(
        ants.ComposeMultiTransform(dimension=3),
        name='compose_transform'
    )

    workflow.connect([
        (inputnode,concat_transforms,[('itk_fmap2anat','xfm_1')]),
        (inputnode,wholebrainbold_tfm_to_txt,[('itk_anat2wholebrainbold','source')]),
        (wholebrainbold_tfm_to_txt,concat_transforms,[('out','xfm_2')]),
        (inputnode,slabbold_tfm_to_txt,[('itk_wholebrainbold2slabbold','source')]),
        (slabbold_tfm_to_txt,concat_transforms,[('out','xfm_3')]),
        (slabbold_tfm_to_txt,compose_transform,[(('out',_add_reference_flag),'reference_image')]),
        (concat_transforms,compose_transform,[('out','transforms')]),
        (compose_transform,outputnode,[('output_transform','itk_fmap2epi')]),
    ])

    return workflow

def init_wholebrain_bold_to_anat_wf(omp_nthreads=8,name="reg_wholebrain_bold_to_anat_bold_wf"):

    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from oscprep.workflows.registration.utils import init_itk_to_fsl_affine_wf
    from fmriprep.workflows.bold.registration import init_bbreg_wf
    
    from niworkflows.interfaces.fixes import ApplyTransforms

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "fsnative2t1w_xfm",
                "subjects_dir",
                "subject_id",
                "t1w_dseg",
                "t1w_brain",
                "undistorted_bold",
            ]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "itk_wholebrain_bold_to_t1",
                "itk_t1_to_wholebrain_bold",
                "fsl_wholebrain_bold_to_t1",
                "fsl_t1_to_wholebrain_bold",
                "undistorted_bold_dseg"
            ]
        ),
        name="outputnode"
    )

    wholebrain_bold_to_anat = init_bbreg_wf(
        use_bbr=True,
        bold2t1w_dof=9,
        bold2t1w_init='register',
        omp_nthreads=omp_nthreads,
        name='reg_wholebrain_bold_to_anat'
    )

    dseg_to_wholebrain_bold = pe.Node(
        ApplyTransforms(
            invert_transform_flags=[False],
            interpolation='MultiLabel'
        ),
        name='dseg_to_undistorted_wholebrain_bold'
    )

    fwd_itk_to_fsl = init_itk_to_fsl_affine_wf(name='itk2fsl_wholebrain_bold_to_t1')
    inv_itk_to_fsl = init_itk_to_fsl_affine_wf(name='itk2fsl_t1_to_wholebrain_bold')

    workflow.connect([
        (inputnode, wholebrain_bold_to_anat,[
            ('fsnative2t1w_xfm','inputnode.fsnative2t1w_xfm'),
            ('subjects_dir','inputnode.subjects_dir'),
            ('subject_id','inputnode.subject_id'),
            ('t1w_dseg','inputnode.t1w_dseg'),
            ('t1w_brain','inputnode.t1w_brain'),
            ('undistorted_bold','inputnode.in_file')
        ]),
        (inputnode, dseg_to_wholebrain_bold,[
            ('t1w_dseg','input_image'),
            ('undistorted_bold','reference_image')
        ]),
        (wholebrain_bold_to_anat, dseg_to_wholebrain_bold,[('outputnode.itk_t1_to_bold','transforms')]),
        (dseg_to_wholebrain_bold, outputnode, [('output_image','undistorted_bold_dseg')]),
        (wholebrain_bold_to_anat,outputnode,[
            ('outputnode.itk_bold_to_t1','itk_wholebrain_bold_to_t1'),
            ('outputnode.itk_t1_to_bold','itk_t1_to_wholebrain_bold')
        ]),
        (inputnode, fwd_itk_to_fsl,[
            ('undistorted_bold','inputnode.source'),
            ('t1w_brain','inputnode.reference')
        ]),
        (wholebrain_bold_to_anat,fwd_itk_to_fsl,[('outputnode.itk_bold_to_t1','inputnode.itk_affine')]),
        (fwd_itk_to_fsl,outputnode,[('outputnode.fsl_affine','fsl_wholebrain_bold_to_t1')]),
        (inputnode, inv_itk_to_fsl,[
            ('undistorted_bold','inputnode.reference'),
            ('t1w_brain','inputnode.source')
        ]),
        (wholebrain_bold_to_anat,inv_itk_to_fsl,[('outputnode.itk_t1_to_bold','inputnode.itk_affine')]),
        (inv_itk_to_fsl,outputnode,[('outputnode.fsl_affine','fsl_t1_to_wholebrain_bold')])
    ])

    return workflow

def init_slab_bold_to_wholebrain_bold_wf(omp_nthreads=8, name="reg_slab_bold_to_wholebrain_bold_wf"):

    from niworkflows.engine.workflows import LiterateWorkflow as Workflow

    from oscprep.workflows.registration.utils import init_itk_to_fsl_affine_wf
    from fmriprep.workflows.bold.registration import init_fsl_bbr_wf

    workflow = Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "undistorted_wholebrain_bold",
                "undistorted_wholebrain_bold_dseg",
                "undistorted_slab_bold",
            ]
        ),
        name="inputnode"
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "itk_slab_bold_to_wholebrain_bold",
                "itk_wholebrain_bold_to_slab_bold",
                "fsl_slab_bold_to_wholebrain_bold",
                "fsl_wholebrain_bold_to_slab_bold",
            ]
        ),
        name="outputnode"
    )

    slab_bold_to_wholebrain_bold = init_fsl_bbr_wf(
        use_bbr=True,
        bold2t1w_dof=6,
        bold2t1w_init='register',
        omp_nthreads=omp_nthreads,
        name='reg_slab_bold_to_wholebrain_bold'
    )

    fwd_itk_to_fsl = init_itk_to_fsl_affine_wf(name='itk2fsl_slab_bold_to_wholebrain_bold')
    inv_itk_to_fsl = init_itk_to_fsl_affine_wf(name='itk2fsl_wholebrain_bold_to_slab_bold')

    workflow.connect([
        (inputnode, slab_bold_to_wholebrain_bold,[
            ('undistorted_wholebrain_bold','inputnode.t1w_brain'),
            ('undistorted_wholebrain_bold_dseg','inputnode.t1w_dseg'),
            ('undistorted_slab_bold','inputnode.in_file')
        ]),
        (slab_bold_to_wholebrain_bold,outputnode,[
            ('outputnode.itk_bold_to_t1','itk_slab_bold_to_wholebrain_bold'),
            ('outputnode.itk_t1_to_bold','itk_whole_bold_to_slab_bold')
        ]),
        (inputnode, fwd_itk_to_fsl,[
            ('undistorted_slab_bold','inputnode.source'),
            ('undistorted_wholebrain_bold','inputnode.reference')
        ]),
        (slab_bold_to_wholebrain_bold,fwd_itk_to_fsl,[('outputnode.itk_bold_to_t1','inputnode.itk_affine')]),
        (fwd_itk_to_fsl,outputnode,[('outputnode.fsl_affine','fsl_slab_bold_to_wholebrain_bold')]),
        (inputnode, inv_itk_to_fsl,[
            ('undistorted_wholebrain_bold','inputnode.reference'),
            ('undistorted_slab_bold','inputnode.source')
        ]),
        (slab_bold_to_wholebrain_bold,inv_itk_to_fsl,[('outputnode.itk_t1_to_bold','inputnode.itk_affine')]),
        (inv_itk_to_fsl,outputnode,[('outputnode.fsl_affine','fsl_wholebrain_bold_to_slab_bold')])
    ])

    return workflow


def _tfm_to_txt(source):

    import shutil, os

    destination = "affine.txt"
    shutil.copyfile(source,destination)

    return os.path.abspath(destination)

def _add_reference_flag(_path):

    return f"-R {_path}"

def _concat_transforms_2(xfm_1,xfm_2):
    return [xfm_2,xfm_1]

def _concat_transforms_3(xfm_1,xfm_2,xfm_3):
    return [xfm_3,xfm_2,xfm_1]
