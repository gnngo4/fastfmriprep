from nipype.interfaces.base import (
    CommandLine,
    CommandLineInputSpec,
    File,
    TraitedSpec,
    traits,
)

class SynthStripInputSpec(CommandLineInputSpec):
    in_file = File(exists=True, mandatory=True, argstr='-i %s', position=0, desc='input image')
    out_file = File(argstr='-o %s', position=1, desc='output skull-stripped image')
    mask_file = File(argstr='-m %s', position=2, desc='output binary mask of skull-stripped image')
    no_csf = traits.Bool(mandatory=False, argstr='--no-csf', position=3, desc='option to remove csf')

class SynthStripOutputSpec(TraitedSpec):
    out_file = File(desc='output skull-stripped image (if generated)')
    mask_file = File(desc='output binary mask of skull-stripped image (if generated)')

class SynthStrip(CommandLine):
    _cmd = 'mri_synthstrip'
    input_spec = SynthStripInputSpec
    output_spec = SynthStripOutputSpec

    def _list_outputs(self):

    return {
        'out_file': self.inputs.out_file,
        'mask_file': self.inputs.mask_file
    }