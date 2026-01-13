---
title: 'WAND (Working-memory Adaptive-fatigue with N-back Difficulty): A Modular Software Suite for Cognitive Fatigue Research'
authors:
  - name: Brodie E. Mangan 
    orcid: 0009-0002-8466-5423
    affiliation: 1
affiliations:
  - name: University of Stirling 
    index: 1
    ror: 045wgfr59
date: 12 June 2025 
tags:
  - cognitive fatigue
  - working memory
  - N-back
  - PsychoPy
  - open source software
  - active fatigue
  - cognitive load
  - experimental psychology
bibliography: paper.bib 
repository: https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction
archive:
  doi: 10.5281/zenodo.15389892
---

# Summary

WAND (Working-memory Adaptive-fatigue with N-back Difficulty) is an open-source PsychoPy [@peirce2019psychopy2] software suite for cognitive fatigue research. It provides a modular N-back framework to classify performance, calibrate stable baselines via plateau detection (mitigating learning effects), and systematically induce active fatigue using varied N-back tasks with integrated distractors. This MIT-licensed paper outlines WAND's design and use.

# Statement of Need

Cognitive fatigue research is limited by the frequent conflation of "passive fatigue" (arousal reduction from monotony) with "active fatigue" (neural overload from sustained, effortful engagement) [@holroyd2024controllosphere; @pessiglione2025origins], which impairs the ability to link behavioural decrements with specific neurophysiological correlates [@bernhardt2019differentiating], and by traditional N-back paradigms that inadequately induce fatigue due to learning effects, static difficulty, and biased designs [@hopstaken2015multifaceted]. This impairs robust study of active fatigue.

WAND offers a modular PsychoPy framework for researchers in cognitive science, psychology, and neuroergonomics to reliably induce and investigate active fatigue. It addresses key methodological gaps by:

- **Addressing Methodological Gaps**: Offering an integrated solution to induce active fatigue by systematically controlling for concurrent confounds like task learning, static difficulty, and arousal reduction.

- **Explicitly Separating Key Phases**: The software integrates distinct phases for participant classification (based on baseline N-back capacity), performance calibration (including plateau detection), and fatigue induction. This structured approach enhances the precision of fatigue measurement.

- **Novel Feature Integration**: Implementing, to our knowledge, the first open-source dynamic behavioural plateauing for N-back tasks, and incorporating periodic visual distractors (~8% of trials) during induction to sustain load and model micro-interruptions.

- **Supporting Replicable and Progressive Research**: Supporting transparent, replicable, and extensible fatigue research through open science principles, suitable for behavioural and neuroimaging studies.

WAND thus provides an integrated platform with innovative techniques to overcome key limitations in active fatigue research. WAND is currently being used at the University of Stirling to investigate behavioural correlates of working memory fatigue. Its modular structure enables researchers to adapt or use parts of the protocol independently to suit specific research questions examining the behavioural and EEG (electroencephalography) correlates of fatigue induced by sustained high cognitive load, with adaptable experimental parameters and instructions facilitating focused investigations into the mechanisms and manifestations of cognitive fatigue.

# Implementation and Architecture

WAND is implemented in Python, utilising Psychopy, and comprises two sequential phases, managed by distinct scripts (WAND_practice_plateau.py for familiarisation/calibration, WAND_full_induction.py for induction):

## Initial Familiarisation and Competency Check
Participants are familiarised with N-back mechanics via practice on Spatial and Dual N-back tasks (fixed at Level 2). An optional 'slow mode' (50% reduced speed) aids initial onboarding, with progression to normal speed upon achieving basic competency (e.g., an accuracy of 65% or greater in one slow-mode block). Further progression requires meeting a performance threshold at normal speed (e.g., 65% accuracy averaged across the two Level 2 practice blocks for each task type). Written instructions and demonstrations clarify task demands. This prepares participants for Sequential N-back calibration.

## Plateau Detection and Calibration Phase
This phase uses the Sequential N-back task to establish a stable performance baseline and classify N-back capacity. Researchers can set a starting N-level (e.g., 2 or 3), with an optional 'slow mode' available. At normal speed, participants may progress to a higher N-level (e.g., from Level 2 to 3 if accuracy exceeds 82% over two consecutive blocks). Adaptive N-back blocks continue until three out of five consecutive blocks exhibit an accuracy variance of 7% or less, indicating a stable performance plateau.
This N-level is then used for the fatigue induction. Block-level feedback is provided to the participant during this calibration/plateauing phase.

## Fatigue Induction Task
This session (~65-70 minutes) induces fatigue via an extended, alternating sequence of N-back tasks, using the calibrated Sequential N-back N-level:

Sequential N-back Blocks (e.g., 5 blocks): Run at the fixed calibrated N-level with features like periodic visual distractors (if enabled).

Adaptive Spatial and Dual N-back Blocks (e.g., 4 blocks each): Incorporate dynamic N-level adjustments (up to 3 changes per block) and block level progressive timing compression to maintain high cognitive load.

Subjective fatigue measures (fatigue, effort, attention, overwhelmed) are collected at intervals, and short breaks are provided. Detailed performance is logged, and optional EEG synchronisation is supported.

# Key Design Features and Innovations

WAND’s novelty lies in its integrated approach to overcoming key limitations in cognitive fatigue research:

- **Varied N-back Protocol**: Combines Spatial, Dual, and Sequential N-back tasks targeting core non-verbal working memory circuits. This multi-task design maintains sustained cognitive load while mitigating boredom, redundancy, and learning effects. Adaptive modifications (e.g., difficulty, timing) are applied to Spatial and Dual variants, preserving the Sequential variant for primary fatigue measurement.

- **Performance-Based Stratification**: Calibrates N-back difficulty to each participant’s baseline capacity, improving sensitivity to fatigue-induced performance changes.

- **Dynamic Plateau Detection**: Implements a rolling-window average and variance threshold to identify stable performance plateaus, mitigating training effects.

- **Micro-Disruption via Visual Distractors**: Injects distractor trials within the Sequential N-back to simulate real-world interference and probe inhibitory control under load.

- **Sophisticated Performance Metrics**: Captures d-prime, A-prime, accuracy, reaction time, and lapse rate, allowing for granular signal detection and behavioural fatigue tracking.

# Availability

- **Operating System**: Platform-independent (Windows, macOS, Linux) via PsychoPy.
- **Programming Language**: Python (3.8.x), utilising the PsychoPy library.
- **Dependencies**: Core dependencies are specified in the `requirements.txt` file to ensure a reproducible environment. Key packages include:
  - `psychopy==2024.1.4`
  - `numpy==1.24.4` 
  - `scipy==1.9.3`
  - `pandas==2.0.3`
  - `wxPython==4.2.1`
  - `pyglet==1.5.27`
  
- **Repository**: [https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction](https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction)
- **License**: MIT License


## Installation

Clone the repository and install dependencies via:

```bash
git clone https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction.git
cd WAND-practice-and-fatigue-induction
pip install -r requirements.txt
``` 

# Acknowledgements

I thank Dr Dimitrios Kourtis and Dr Simone Tomaz for their supervision. I am also deeply grateful to Mr Dario Riccomini for his invaluable support throughout this project. This work was supported by The Institute of Advanced Studies at the University of Stirling. 

# References
---