#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  6 10:56:57 2020
Decode left/right block identity from all brain regions
@author: Guido Meijer
"""

from os.path import join
import matplotlib.pyplot as plt
import numpy as np
from brainbox.population import decode
import pandas as pd
import seaborn as sns
from ephys_functions import paths, figure_style, check_trials
import brainbox.io.one as bbone
from oneibl.one import ONE
one = ONE()

# Settings
DOWNLOAD = False
OVERWRITE = False
MIN_CONTRAST = 0.1
PRE_TIME = 0.6
POST_TIME = -0.1
MIN_NEURONS = 20  # min neurons per region
N_NEURONS = 20  # number of neurons to use for decoding
MIN_TRIALS = 300
ITERATIONS = 1000
DECODER = 'bayes'  # bayes, regression or forest
VALIDATION = 'kfold'
NUM_SPLITS = 5
DATA_PATH, FIG_PATH, SAVE_PATH = paths()
FIG_PATH = join(FIG_PATH, 'WholeBrain')

# %%
# Get list of all recordings that have histology
ses_with_hist = one.alyx.rest('sessions', 'list',
                              task_protocol='_iblrig_tasks_ephysChoiceWorld',
                              project='ibl_neuropixel_brainwide',
                              django='subject__actions_sessions__procedures__name,Histology')

decoding_result = pd.DataFrame()
for i in range(len(ses_with_hist)):
    print('Processing session %d of %d' % (i+1, len(ses_with_hist)))

    # Get meta data
    subject = ses_with_hist[i]['url'][-36:]
    
    # Load in data
    eid = ses_with_hist[i]['url'][-36:]
    try:
        spikes, clusters, channels = bbone.load_spike_sorting_with_channel(eid, one=one)
        trials = one.load_object(eid, 'trials')
    except:
        continue

    # Check data integrity
    if check_trials(trials) is False:
        continue

    # Get trial indices of inconsistent trials during left high blocks
    incon_l_block = ((trials.probabilityLeft == 0.8)
                     & (trials.contrastRight > MIN_CONTRAST))
    cons_l_block = ((trials.probabilityLeft == 0.8)
                    & (trials.contrastLeft > MIN_CONTRAST))
    consistent_l = np.zeros(cons_l_block.shape[0])
    consistent_l[cons_l_block == 1] = 1
    consistent_l[incon_l_block == 1] = 2
    
    # Get trial indices of inconsistent trials during right high blocks
    incon_r_block = ((trials.probabilityLeft == 0.2)
                     & (trials.contrastLeft > MIN_CONTRAST))
    cons_r_block = ((trials.probabilityLeft == 0.2)
                    & (trials.contrastRight > MIN_CONTRAST))
    right_times = trials.stimOn_times[(cons_r_block == 1) | (incon_r_block == 1)]
    consistent_r = np.zeros(cons_r_block.shape[0])
    consistent_r[cons_r_block == 1] = 1
    consistent_r[incon_r_block == 1] = 2
              
    # Check for number of trials
    if trials.stimOn_times.shape[0] < MIN_TRIALS:
        continue

    # Decode per brain region
    for p, probe in enumerate(spikes.keys()):
        
        # Check if histology is available
        if not hasattr(clusters[probe], 'acronym'):
            continue       
                
        for r, region in enumerate(np.unique(clusters[probe]['acronym'])):
    
            # Get clusters in this brain region with KS2 label 'good'
            clusters_in_region = clusters[probe].metrics.cluster_id[
                                            (clusters[probe]['acronym'] == region)
                                            & (clusters[probe].metrics.ks2_label == 'good')]
    
            # Check if there are enough neurons in this brain region
            if np.shape(clusters_in_region)[0] < MIN_NEURONS:
                continue
    
            # Select spikes and clusters
            spks_region = spikes[probe].times[np.isin(spikes[probe].clusters,
                                                      clusters_in_region)]
            clus_region = spikes[probe].clusters[np.isin(spikes[probe].clusters,
                                                         clusters_in_region)]
    
            # Decode surprising stimuli on the left
            decode_left = decode(spks_region, clus_region,
                                 trials.stimOn_times[consistent_l != 0],
                                 consistent_l[consistent_l != 0],
                                 pre_time=PRE_TIME, post_time=POST_TIME,
                                 classifier=DECODER, cross_validation=VALIDATION,
                                 num_splits=NUM_SPLITS, n_neurons=N_NEURONS,
                                 iterations=ITERATIONS)
    
            # Shuffle
            shuffle_left = decode(spikes[probe].times, spikes[probe].clusters,
                                  trials.stimOn_times[consistent_l != 0],
                                  consistent_l[consistent_l != 0],
                                  pre_time=PRE_TIME, post_time=POST_TIME,
                                  classifier=DECODER, cross_validation=VALIDATION,
                                  num_splits=NUM_SPLITS, n_neurons=N_NEURONS,
                                  iterations=ITERATIONS, shuffle=True)
    
            # Decode surprising stimuli on the right
            decode_right = decode(spks_region, clus_region,
                                  trials.stimOn_times[consistent_r != 0],
                                  consistent_r[consistent_r != 0],
                                  pre_time=PRE_TIME, post_time=POST_TIME,
                                  classifier=DECODER, cross_validation=VALIDATION,
                                  num_splits=NUM_SPLITS, n_neurons=N_NEURONS,
                                  iterations=ITERATIONS)
    
            # Shuffle
            shuffle_right = decode(spikes[probe].times, spikes[probe].clusters,
                                   trials.stimOn_times[consistent_r != 0],
                                   consistent_r[consistent_r != 0],
                                   pre_time=PRE_TIME, post_time=POST_TIME,
                                   classifier=DECODER, cross_validation=VALIDATION,
                                   num_splits=NUM_SPLITS, n_neurons=N_NEURONS,
                                   iterations=ITERATIONS, shuffle=True)
    
            # Add to dataframe
            decoding_result = decoding_result.append(pd.DataFrame(
                index=[0], data={'subject': ses_with_hist[i]['subject'],
                                 'date': ses_with_hist[i]['start_time'][:10],
                                 'eid': eid,
                                 'probe': probe,
                                 'region': region,
                                 'f1_left': decode_left['f1'].mean(),
                                 'f1_left_shuffle': shuffle_left['f1'].mean(),
                                 'accuracy_left': decode_left['accuracy'].mean(),
                                 'accuracy_left_shuf': shuffle_left['accuracy'].mean(),
                                 'auroc_left': decode_left['auroc'].mean(),
                                 'auroc_left_shuf': shuffle_left['auroc'].mean(),
                                 'f1_rigt': decode_left['f1'].mean(),
                                 'f1_right_shuffle': shuffle_left['f1'].mean(),
                                 'accuracy_right': decode_left['accuracy'].mean(),
                                 'accuracy_right_shuf': shuffle_left['accuracy'].mean(),
                                 'auroc_right': decode_left['auroc'].mean(),
                                 'auroc_right_shuf': shuffle_left['auroc'].mean()}))

    decoding_result.to_csv(join(SAVE_PATH, 'decoding_surprise_regions_%d_neurons' % N_NEURONS))

# %% Plot
decoding_result = pd.read_csv(join(SAVE_PATH, 'decoding_surprise_regions_%d_neurons' % N_NEURONS))
decoding_result['accuracy'] = (decoding_result['accuracy_right']
                               - decoding_result['accuracy_right_shuffle'])

decoding_regions = decoding_result.groupby('region').size()[
                                    decoding_result.groupby('region').size() > 3].reset_index()
decoding_result = decoding_result[decoding_result['region'].isin(decoding_regions['region'])]
decoding_result = decoding_result.sort_values('accuracy', ascending=False)

sort_regions = decoding_result.groupby('region').mean().sort_values(
                                            'accuracy', ascending=False).reset_index()['region']

f, ax1 = plt.subplots(1, 1, figsize=(10, 10))

sns.barplot(x='accuracy', y='region', data=decoding_result, order=sort_regions, ci=68, ax=ax1)
ax1.set(xlabel='Decoding accuracy of inconsistent stimuli (% over chance)', ylabel='')
figure_style(font_scale=1.2)