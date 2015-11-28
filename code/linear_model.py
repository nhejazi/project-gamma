import project_config
import numpy as np
import numpy.linalg as npl
import matplotlib.pyplot as plt
import nibabel as nib
from general_utils import form_cond_filepath, prepare_data_single, prepare_mask
from stimuli_revised import events2neural_std
from conv import conv_target_non_target, conv_std
from gaussian_filter import spatial_smooth
from matplotlib import colors

import pdb

def single_subject_linear_model(standard_source_prefix, cond_filepath_prefix, subject_num, task_num):

  data = prepare_data_single(subject_num, task_num, True, standard_source_prefix)

  n_trs = data.shape[-1] + 5

  cond_filename_003 = form_cond_filepath(subject_num, task_num, "003", cond_filepath_prefix)
  cond_filename_005 = form_cond_filepath(subject_num, task_num, "005", cond_filepath_prefix)
  cond_filename_001 = form_cond_filepath(subject_num, task_num, "001", cond_filepath_prefix)
  cond_filename_004 = form_cond_filepath(subject_num, task_num, "004", cond_filepath_prefix)

  # TODO: put cond007 back to 003
  cond_filename_007 = form_cond_filepath(subject_num, task_num, "007", cond_filepath_prefix)

  target_convolved, nontarget_convolved = conv_target_non_target(n_trs, cond_filename_003, cond_filename_007, TR, tr_divs = 100.0)
  target_convolved, nontarget_convolved = target_convolved[5:], nontarget_convolved[5:]

  block_regressor = events2neural_std(cond_filename_005, TR, n_trs)[5:]

  block_1_cues = conv_std(n_trs, cond_filename_001, TR)[5:]
  block_2_cues = conv_std(n_trs, cond_filename_004, TR)[5:]

  linear_drift = np.linspace(-1, 1, n_trs)
  qudratic_drift = linear_drift ** 2
  qudratic_drift -= np.mean(qudratic_drift)

  linear_drift = linear_drift[5:]
  qudratic_drift = qudratic_drift[5:]

  in_brain_mask, in_brain_tcs = prepare_mask(data, 5000)

  Y = in_brain_tcs.T
  Y_demeaned = Y - np.mean(Y, axis=1).reshape([-1, 1])
  unscaled_cov = Y_demeaned.dot(Y_demeaned.T)
  U, S, V = npl.svd(unscaled_cov)

  X = np.ones((n_trs - 5, 13))
  X[:, 0] = target_convolved
  X[:, 1] = nontarget_convolved
  X[:, 2] = block_regressor
  X[:, 3] = block_1_cues
  X[:, 4] = block_2_cues
  X[:, 5] = linear_drift
  X[:, 6] = qudratic_drift
  X[:, 7] = U[:,0]
  X[:, 8] = U[:,1]
  X[:, 9] = U[:,2]
  X[:, 10] = U[:,3]
  X[:, 11] = U[:,4]
  # 12th column is the intercept

  B = npl.pinv(X).dot(Y)

  rs_squared = []
  for i in range(Y.shape[-1]):
    r_squared = 1 - np.sum((Y[:,i] - X.dot(B[:,i]))**2) * 1.0 / np.sum((Y[:,i] - np.mean(Y[:,i])) ** 2)
    rs_squared.append(r_squared)
  print "mean R squared across all voxels is " + str(np.mean(rs_squared))
  # mean R squared across all voxels is 0.1129. This is too low.

  pdb.set_trace()

  b_vols = np.zeros((data.shape[0:-1] + (13,)))
  b_vols[in_brain_mask, :] = B.T

  pad_thickness = 3
  fwhm = 4

  b_vols_smooth = spatial_smooth(b_vols, in_brain_mask, pad_thickness, fwhm)
  return b_vols_smooth, in_brain_mask, U, Y, data

def plot(b_vols_smooth, in_brain_mask, brain_structure, nice_cmap_values, beta_index, depth):
  b_vols_smooth[~in_brain_mask] = np.nan
  nice_cmap = colors.ListedColormap(nice_cmap_values, 'actc')
  plt.imshow(brain_structure[...,depth], alpha=0.5)
  plt.imshow(b_vols_smooth[...,depth,beta_index], cmap=nice_cmap, alpha=0.5)
  plt.colorbar()
  plt.show()


if __name__ == "__main__":

  # single subject, 0-back

  standard_source_prefix = "/Volumes/G-DRIVE mobile USB/fmri_con/"
  cond_filepath_prefix = "/Volumes/G-DRIVE mobile USB/fmri_non_mni/"
  brain_structure_path = "/Users/fenglin/Downloads/mni_icbm152_csf_tal_nlin_asym_09c_2mm.nii"
  nice_cmap_values_path = "actc.txt"

  subject_num = "011"
  task_num = "001"
  TR = project_config.TR

  plt.rcParams['image.cmap'] = 'gray'
  plt.rcParams['image.interpolation'] = 'nearest'

  brain_structure = nib.load(brain_structure_path).get_data()
  nice_cmap_values = np.loadtxt(nice_cmap_values_path)
  
  b_vols_smooth_0_back, in_brain_mask, U, Y, data = single_subject_linear_model(standard_source_prefix, cond_filepath_prefix, subject_num, task_num)

  # show target betas
  plot(b_vols_smooth_0_back, in_brain_mask, brain_structure, nice_cmap_values, 0, 40)

  # projection of first component
  plt.plot(U[:, 0])
  # plt.show()
  Y_demeaned = Y - np.mean(Y, axis=1).reshape([-1, 1])
  projections = U.T.dot(Y_demeaned)
  projection_vols = np.zeros(data.shape)
  projection_vols[in_brain_mask, :] = projections.T
  plt.imshow(projection_vols[:, :, 40, 0])
  # plt.show()

  # second component
  # this component starts to look like functional features
  plt.plot(U[:, 1])
  # plt.show()
  plt.imshow(projection_vols[:, :, 40, 1])
  # plt.show()

  # single subject, 0-back vs. 2-back

  task_num = "003"

  b_vols_smooth_2_back, in_brain_mask, U, Y, data = single_subject_linear_model(standard_source_prefix, cond_filepath_prefix, subject_num, task_num)

  # show 2-back target betas
  plot(b_vols_smooth_2_back, in_brain_mask, brain_structure, nice_cmap_values, 0, 40)

  # show 2-back target betas - 0-back target betas
  plot(b_vols_smooth_2_back - b_vols_smooth_0_back, in_brain_mask, brain_structure, nice_cmap_values, 0, 40)
