"""Classical baseline panel (14 detectors) wrapped from the AnoLLM fork.

4 PyOD (ECOD, PCA, KNN, IForest) + 8 DeepOD (DeepSVDD, REPEN, RDP, RCA, GOAD, NeuTraL,
DeepIsolationForest, SLAD) + 2 custom (ICL, DTECategorical), scored on the same frozen,
subsampled+reweighted eval set as the LLMs. (Built from M1/M2.)
"""
