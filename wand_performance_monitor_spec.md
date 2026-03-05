# WAND Update: Real-Time Performance Monitoring & Auto-Termination

## Implementation Status (2026-02-28)

This specification has now been implemented with a few deliberate operational decisions:

- Default action in production is `warn_then_terminate` (not researcher prompt).
- The first flag shows a supportive participant-facing pause message; the second flag auto-terminates.
- GUI integration is a dedicated **Edge Case Warnings** page in launcher flow (not embedded in generic options).
- In launcher preset quick-path (e.g., `Standard_WAND_Protocol`), setup pages are skipped and preset mode/schedule are retained through direct confirmation.

## Context

During EEG pilot testing (Study 2), we encountered a participant whose task-state individual alpha frequency was ~7.8 Hz (bottom 5th percentile). Despite passing the practice plateau (72-78% accuracy across 3 practice blocks) and beginning the induction at 85% accuracy, their performance collapsed progressively across the five induction blocks, dropping below 50% by Block 5. D-prime fell to 0.38, and they accumulated 33 missed responses in the final block.

This participant passed every pre-task screening criterion but produced unusable EEG data (no P3, no gamma, no PAC — just noise). The entire ~1-hour EEG session was wasted. This is the first time this has happened across 28 participants in the behavioural study, but with EEG recording time being significantly more costly, we need real-time safeguards.

## Requirements

### 1. Two-Tier Per-Block Performance Monitor

After each **complete main block** of the induction, evaluate performance using task-appropriate criteria:

#### Sequential N-back (Fixed Difficulty)
- **D-prime criterion**: If d' < threshold (default: 1.0), flag the block.
- **Lapse criterion**: If the proportion of missed responses exceeds threshold (default: 20%), flag the block.
- Both criteria are evaluated independently. Either one triggering is sufficient.

#### Spatial & Dual N-back (Adaptive Difficulty)
- **Lapse criterion only**: If the proportion of missed responses across all sub-blocks of the main block exceeds threshold (default: 20%), flag the block.
- Accuracy and d-prime are **not** used for adaptive tasks because transient accuracy drops after difficulty increases (e.g., 2-back → 3-back) are expected behaviour, not disengagement. Lapses (no button press at all) cannot be confounded by difficulty level.

### 2. Behaviour on Trigger

When a criterion is met:

1. **Audio alert**: Play a system beep/chime (multiple beeps) to alert the researcher, who may be in another room during EEG recording.
2. **Visual alert**: Display a prominent on-screen warning to the researcher (not the participant) with:
   - Which criterion was triggered
   - The actual values (e.g., "Block 3: d' = 0.80, below threshold of 1.0")
   - Which task type (Sequential / Spatial / Dual)
3. **Pause**: The experiment pauses and waits for the researcher to acknowledge.
4. The researcher can then choose to:
   - **Continue anyway** (override — useful for pilot testing or if researcher judges participant is still engaged)
   - **End induction early** (gracefully terminate, save all data collected so far, proceed to post-task questionnaires)
5. Log the flag event, the researcher's decision, and timestamp to the session log.

### 3. Configuration

These parameters should be stored in the WAND configuration/params JSON file and be adjustable:

```json
{
  "performance_monitor": {
    "enabled": true,
    "dprime_threshold": 1.0,
    "missed_response_threshold": 0.20,
    "action": "prompt_researcher"
  }
}
```

- `enabled`: Toggle the entire monitoring system on/off (default: true)
- `dprime_threshold`: Minimum acceptable d' per Sequential block (default: 1.0). Set to 0 to disable this criterion. Only applies to Sequential blocks.
- `missed_response_threshold`: Maximum proportion of missed responses per block (default: 0.20 = 20%). Set to 1.0 to disable this criterion. Applies to ALL task types.
- `action`: What happens when triggered. Options:
  - `"prompt_researcher"` — audio alert + visual dialog, let researcher decide (default, recommended)
  - `"auto_terminate"` — automatically end induction (no researcher input needed)
  - `"log_only"` — log the flag but take no action

### 4. GUI Integration (Launcher)

In the WAND launcher GUI, add a section in Page 4 (Options) for "Performance Monitoring" with:

- A checkbox to enable/disable monitoring
- Spinner/input fields for the d' threshold and missed response threshold
- A dropdown for the action mode (prompt / auto-terminate / log only)
- These controls should read from and write to the config
- Tooltips explaining each parameter

### 5. Implementation Notes

#### Sequential Monitoring
- D-prime computed using standard SDT formula: `d' = z(hit_rate) - z(false_alarm_rate)`, with log-linear correction for extreme proportions. Already computed by `summarise_sequential_block()`.
- Lapse rate = `lapses / total_scorable_trials`. Already available in block results.
- Check runs immediately after `save_sequential_results()`.

#### Spatial/Dual Monitoring
- `run_spatial_nback_block` and `run_dual_nback_block` already compute `lapses` and `total_responses` internally but discard them after level adjustment.
- Modify these functions to return lapse count alongside the new N-level: `(new_level, lapses, total_responses)`.
- `run_adaptive_nback_task` accumulates lapses and total responses across all 3 sub-blocks, then computes lapse rate for the full main block.
- Check runs after each complete main block (after all 3 sub-blocks finish).

#### Alert System
- Audio: Use `winsound.Beep()` on Windows (no dependencies). Three rapid beeps to be unmissable.
- Visual: PsychoPy `visual.TextStim` with large red text, researcher presses a key to choose action.
- The alert must be visible to the researcher, NOT the participant — however, since the experiment window is the only display, the alert will appear on the experiment screen. This is acceptable because the experiment is paused.

#### Graceful Termination
- Save all data collected so far.
- Mark in the output CSV/log that the session was terminated early, on which block, and why.
- Proceed to any post-task measures (subjective questionnaires) if configured.

#### Edge Cases
- Monitor disabled (`enabled: false`) → skip all checks.
- Individual thresholds disabled (d'=0 or miss=1.0) → skip that criterion.
- Block skipped via admin key "5" → skip monitor check (no valid data).
- Both criteria triggered on same block → report both values in the alert.
- Researcher overrides and continues → log the override, resume normally, check again after next block.
- `"log_only"` mode → log the flag, no pause, no alert, experiment continues.

### 6. Rationale for Defaults

- **d' < 1.0**: At this level, the participant is barely discriminating targets from non-targets. In our 2-back task, d' of 1.0 corresponds to roughly 65-70% accuracy depending on criterion placement. Below this, working memory maintenance is not reliably occurring, and any EEG measures of WM-related neural activity (PAC, gamma, P3) will be at floor.
- **20% missed responses**: The average participant has ~1.5 missed responses per block (~1%). 20% indicates either disengagement, drowsiness, or inability to sustain attention. Our pilot participant had 33/164 = 20% misses in Block 5.
- **Lapse-only for adaptive tasks**: Accuracy is confounded by difficulty changes in adaptive tasks. A participant moving from 2-back to 3-back will naturally show reduced accuracy — this is the system working, not disengagement. Lapses are difficulty-independent.

### 7. Testing

- Verify that the monitor correctly computes d' and lapse rate after each Sequential block.
- Verify that the monitor correctly computes lapse rate after each Spatial/Dual block.
- Verify that the audio alert plays when a threshold is breached.
- Verify that the visual prompt appears to the researcher when a threshold is breached.
- Verify that "continue" allows the next block to proceed normally.
- Verify that "end induction" saves all data and exits gracefully.
- Verify that the configuration persists across sessions.
- Verify the GUI controls correctly update the config.
- Verify that adaptive difficulty level changes do NOT trigger false positives.
- Verify that disabled thresholds (d'=0, miss=1.0) do not trigger.
- Verify that monitor disabled (`enabled: false`) skips all checks.
