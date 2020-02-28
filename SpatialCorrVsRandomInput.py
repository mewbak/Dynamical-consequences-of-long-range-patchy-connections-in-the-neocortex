#!/usr/bin/python3
# -*- coding: utf-8 -*-

from modules.stimulusReconstruction import fourier_trans, direct_stimulus_reconstruction
from modules.createStimulus import *
from modules.networkAnalysis import *
from createThesisNetwork import create_network, NETWORK_TYPE

import numpy as np
import matplotlib.pyplot as plt

import nest


VERBOSITY = 0
nest.set_verbosity("M_ERROR")


def main_lr(network_type, shuffle_input=False):
    # load input stimulus
    input_stimulus = image_with_spatial_correlation(
        size_img=(50, 50),
        num_circles=5,
        radius=10,
        background_noise=shuffle_input,
        shuffle=shuffle_input
    )

    input_stimulus = create_image_bar(0, )
    stimulus_fft = fourier_trans(input_stimulus)
    if VERBOSITY > 2:
        plt.imshow(input_stimulus, cmap='gray')
        plt.show()

    # #################################################################################################################
    # Define values
    # #################################################################################################################
    num_receptor = input_stimulus.size
    simulation_time = 1000.
    use_mask = False
    plot_only_eigenspectrum = False
    ignore_weights_adj = True
    cap_s = 1.     # Increased to reduce the effect of the input and to make it easier to investigate the dynamical
                    # consequences of local / lr patchy connections
    receptor_connect_strength = 1.

    (receptor_layer,
     torus_layer,
     adj_rec_sens_mat,
     adj_sens_sens_mat,
     tuning_weight_vector,
     spike_detect) = create_network(
        input_stimulus,
        cap_s=cap_s,
        receptor_connect_strength=receptor_connect_strength,
        ignore_weights_adj=ignore_weights_adj,
        network_type=network_type,
        verbosity=VERBOSITY
    )

    torus_layer_nodes = nest.GetNodes(torus_layer)[0]
    if plot_only_eigenspectrum:
        _, _ = eigenvalue_analysis(
            adj_sens_sens_mat,
            plot=True,
            save_plot=False,
            fig_name="thesis_network_non-zero_connections.png"
        )
        return

    # #################################################################################################################
    # Simulate and retrieve resutls
    # #################################################################################################################
    if VERBOSITY > 0:
        print("\n#####################\tSimulate")
    nest.Simulate(simulation_time)

    # Get network response in spikes
    data_sp = nest.GetStatus(spike_detect, keys="events")[0]
    spikes_s = data_sp["senders"]
    time_s = data_sp["times"]
    if VERBOSITY > 2:
        plt.plot(time_s, spikes_s, "k,")
        plt.show()

    firing_rates = get_firing_rates(spikes_s, torus_layer_nodes, simulation_time)

    if VERBOSITY > 0:
        average_firing_rate = np.mean(firing_rates)
        print("\n#####################\tAverage firing rate: %s \n" % average_firing_rate)

    # #################################################################################################################
    # Reconstruct stimulus
    # #################################################################################################################
    mask = np.ones(firing_rates.shape, dtype='bool')
    if use_mask:
        mask = firing_rates > 0

    # Reconstruct input stimulus
    if VERBOSITY > 0:
        print("\n#####################\tReconstruct stimulus")

    reconstruction = direct_stimulus_reconstruction(
        firing_rates[mask],
        adj_rec_sens_mat,
        tuning_weight_vector
    )
    response_fft = fourier_trans(reconstruction)

    if VERBOSITY > 1:
        from matplotlib.colors import LogNorm
        _, fig = plt.subplots(1, 2)
        fig[0].imshow(np.abs(stimulus_fft), norm=LogNorm(vmin=5))
        fig[1].imshow(np.abs(response_fft), norm=LogNorm(vmin=5))
        _, fig_2 = plt.subplots(1, 2)
        fig_2[0].imshow(reconstruction, cmap='gray')
        fig_2[1].imshow(input_stimulus, cmap='gray')
        plt.show()

    return input_stimulus, reconstruction, firing_rates


def main_mi():
    # Define parameters outside  the loop
    num_trials = 5
    shuffle = [True, False]
    for network_type in list(NETWORK_TYPE.keys()):
        for shuffle_flag in shuffle:
            input_stimuli = []
            reconstructed_stimuli = []
            for _ in range(num_trials):
                nest.ResetKernel()
                input_stimulus, reconstruction, _ = main_lr(network_type, shuffle_input=shuffle_flag)
                input_stimuli.append(input_stimulus.reshape(-1))
                reconstructed_stimuli.append(reconstruction.reshape(-1))

            mutual_information = mutual_information_hist(input_stimuli, reconstructed_stimuli)
            shuffle_string = "random input" if shuffle_flag else "input with spatial correlation"
            print("\n#####################\tMutual Information MI for network type %s and %s: %s \n"
                  % (network_type, shuffle_string, mutual_information))


if __name__ == '__main__':
    # main_lr("local_radial_lr_patchy")
    main_mi()

