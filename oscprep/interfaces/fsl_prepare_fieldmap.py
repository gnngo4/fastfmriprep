from nipype.interfaces.base import (
    CommandLine,
    CommandLineInputSpec,
    File,
    TraitedSpec,
    traits,
)

import os

class FSLPrepareFieldmapInputSpec(CommandLineInputSpec):
    phase_image = File(argstr='%s', exists=True, mandatory=True, position=0, desc='phasediff image')
    magnitude_image = File(argstr='%s', exists=True, mandatory=True, position=1, desc='skullstripped magnitude image')
    out_image = File(argstr='%s', position=2, desc='skullstripped fieldmap image (rad/s)')
    deltaTE = traits.Float(argstr='%s', mandatory=True,position=3,desc='echo time difference (ms)')

class FSLPrepareFieldmapOutputSpec(TraitedSpec):
    out_image = File(desc='skullstripped fieldmap image (rad/s)')

class FSLPrepareFieldmap(CommandLine):
    _cmd = 'fsl_prepare_fieldmap SIEMENS'
    input_spec = FSLPrepareFieldmapInputSpec
    output_spec = FSLPrepareFieldmapOutputSpec

    def _list_outputs(self):

        _outputs = {
            'out_image': os.path.abspath(self.inputs.out_image),
        }

        return _outputs