---
title: 'WAND (Working-memory Adaptive-fatigue with N-back Difficulty): A Modular Software Suite for Cognitive Fatigue Research'
authors:
  - name: Brodie E. Mangan 
    orcid: "0009-0002-8466-5423"
    affiliation: "1"
affiliations:
  - name: University of Stirling 
    index: 1
    ror: "045wgfr59"
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

WAND (Working-memory Adaptive-fatigue with N-back Difficulty) is an open-source PsychoPy [@peirce2019psychopy2] software suite for cognitive fatigue research. It helps researchers calibrate a participant's task-performance capacity, verify that performance has stabilised before fatigue induction, and then run a sustained multi-task N-back protocol designed to induce active cognitive fatigue. The software is distributed as a pip-installable Python package with command-line entry points, a GUI launcher, a drag-and-drop Block Builder, automated smoke tests, configurable EEG trigger support, and CSV outputs containing behavioural and signal-detection metrics.

# Statement of Need

Cognitive fatigue research is limited by the frequent conflation of "passive fatigue" (arousal reduction from monotony) with "active fatigue" (overload from sustained, effortful engagement) [@holroyd2024controllosphere; @pessiglione2025origins]. This distinction matters because passive and active fatigue may have different behavioural and neurophysiological correlates [@bernhardt2019differentiating]. Traditional N-back paradigms are also vulnerable to learning effects, static difficulty, and response-bias confounds, limiting their ability to isolate and induce fatigue-related performance decline [@hopstaken2015multifaceted; @mangan2025missinglink].

WAND is intended for researchers in cognitive psychology, neuroscience, neuroergonomics, and clinical or applied fatigue studies who need a reproducible way to separate familiarisation and ability calibration from the later fatigue-induction phase. It provides a standard protocol for behavioural and EEG-compatible studies while allowing laboratories to customise task composition, timings, breaks, subjective-measure placement, response keys, monitor settings, and performance-safeguard thresholds.

# State of the Field

General experiment frameworks such as PsychoPy [@peirce2019psychopy2] provide powerful stimulus presentation and response-collection primitives, but they do not by themselves define a validated fatigue-induction workflow, adaptive practice-to-plateau calibration, or safeguards for fatigue-specific edge cases. WAND builds on PsychoPy rather than replacing it: the contribution is a domain-specific, packaged protocol for active cognitive fatigue research, with ready-to-run N-back tasks, calibration rules, data logging, GUI configuration, and reproducibility-oriented defaults.

# Software Design

WAND is organised as the `wand_nback` Python package. Installation through `pip install git+https://github.com/brodie-neuro/WAND-practice-and-fatigue-induction.git` exposes entry points for the main GUI (`wand-launcher`), practice calibration (`wand-practice`), full induction (`wand-induction`), an automated quick test (`wand-quicktest`), and EEG trigger testing (`wand-eeg-test`). The launcher guides researchers through study setup, participant ID handling, task selection, timing parameters, fullscreen and random-seed settings, response-key validation, break and subjective-measure counts, and edge-case performance-monitor settings.

The GUI supports two workflow modes. Loading the bundled `Standard_WAND_Protocol` preset skips directly to final confirmation with the canonical schedule. Creating a new study opens the Block Builder, where researchers can construct a protocol visually by placing Sequential, Spatial, Dual, Break, and subjective-measure blocks into a custom order. The same configuration is saved as JSON and read by the task scripts, so GUI and scripted execution share the same runtime settings. Advanced options, including window appearance, colours, response keys, target rates, jitter, performance-monitor behaviour, and parallel-port EEG trigger codes, are stored in `wand_nback/config/params.json`.

The experiment is divided into practice calibration and fatigue induction. During practice, researchers can select normal timing or a slow timing profile in which stimulus and inter-stimulus durations are multiplied by 1.5. Slow-mode onboarding is run at Level 2 until the participant reaches at least 65% accuracy in one 60-trial block, after which practice switches to normal timing. Spatial and Dual competency require two successive normal-speed Level 2 blocks at or above 65% accuracy.

Sequential calibration supports Levels 2-4. The participant's N-level is updated using the mean accuracy from the two most recent scored Sequential blocks at the current N-level: performance at or above 82% promotes the participant from Level 2 to 3 or from Level 3 to 4, while performance below 70% demotes the participant from Level 4 to 3 or from Level 3 to 2. After a promotion, the next block at the new level is treated as familiarisation and is not used for subsequent level-change or plateau decisions. Plateau is reached when the last three scored blocks are at the same N-level and all three fall within 7 percentage points of their three-block mean accuracy.

The induction stage combines Sequential, Spatial, and Dual N-back tasks. Sequential blocks run at the calibrated N-level and can include brief visual distractors. Spatial and Dual blocks adapt within each 4.5-minute block using three sub-blocks, with promotion at or above 82% accuracy and demotion at or below 65%, bounded to Levels 2-4. Spatial and Dual blocks also support progressive timing compression. Subjective ratings of fatigue, effort, attention, and overwhelm are inserted at configured points. Results are saved after each block and at session end, including accuracy, reaction time, lapses, d-prime, A-prime, hit rates, false-alarm rates, and task metadata. A performance monitor can flag low Sequential d-prime or high lapse rates and can log, warn, or terminate according to configuration.

# Research Impact Statement

WAND was developed to operationalise the theoretical link between sustained working memory load and active cognitive fatigue [@mangan2025missinglink]. It has been used in a validation study currently available as a PsyArXiv preprint and under review at PLOS ONE ($N = 27$), where participants showed a significant decline in sensitivity ($d'$) across the induction protocol (Cohen's $d = -0.71$; @mangan2026validation). It is also being used in an ongoing EEG study of active cognitive fatigue. The repository includes installation documentation, example outputs, a quick test for installation verification, community contribution guidelines, and a `pytest` suite covering response keys, task configuration, block ordering, signal-detection metrics, Level 4 calibration, performance monitoring, and launcher logic.

# Acknowledgements

I thank Dr Dimitrios Kourtis and Dr Simone Tomaz for their supervision. I am also deeply grateful to Mr Dario Riccomini for his invaluable support throughout this project. This work was supported by The Institute of Advanced Studies at the University of Stirling. 

# References
---
