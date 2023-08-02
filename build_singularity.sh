docker build -t oscprep_grayords .
docker tag oscprep_grayords localhost:5000/oscprep_grayords
docker push localhost:5000/oscprep_grayords
rm oscprep_grayords.simg
SINGULARITY_NOHTTPS=1 singularity build oscprep_grayords.simg docker://localhost:5000/oscprep_grayords
