from nipype.interfaces.base import (
    File,
    SimpleInterface,
    TraitedSpec,
    traits,
)

import os


def _PCADenoise(bold_path, n_components=10, outfile="mppca.nii.gz"):
    import nibabel as nib
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    img = nib.load(bold_path)
    data = img.get_fdata()
    x, y, z, n_tps = data.shape
    data_reshaped = data.reshape(-1, n_tps)
    # standardize the data
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_reshaped)
    # Apply MPPCA using PCA
    num_components = n_components  # Number of principal components
    pca = PCA(n_components=num_components)
    data_mppca = pca.fit_transform(data_scaled)
    # Inverse transform to reconstruct the data
    data_reconstructed = pca.inverse_transform(data_mppca)
    data_reconstructed = scaler.inverse_transform(data_reconstructed)
    # Reshape the reconstructed data back to 4D
    data_reconstructed = data_reconstructed.reshape(x, y, z, n_tps)

    nib.save(
        nib.Nifti1Image(data_reconstructed, affine=img.affine, header=img.header),
        outfile,
    )


class PCADenoiseInputSpec(TraitedSpec):
    bold_path = File(exists=True, desc="bold path", mandatory=True)
    n_components = traits.Int(desc="number of PCA components", mandatory=False)


class PCADenoiseOutputSpec(TraitedSpec):
    mppca_path = File(exists=True, desc="PCA denoised bold path")


class PCADenoise(SimpleInterface):
    input_spec = PCADenoiseInputSpec
    output_spec = PCADenoiseOutputSpec

    def _run_interface(self, runtime):
        _PCADenoise(self.inputs.bold_path)

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outfile = "mppca.nii.gz"
        outputs["mppca_path"] = os.path.abspath(outfile)

        return outputs
