
import os

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

def init_anat2fmap(
    name="anat2fmap_wf"
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

def init_fmap2epi_wholebrain_bold_wf(name="fmap2epi_wholebrain_bold_wf"):

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

def init_fmap2epi_slab_bold_wf(name="fmap2epi_slab_bold_wf"):

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