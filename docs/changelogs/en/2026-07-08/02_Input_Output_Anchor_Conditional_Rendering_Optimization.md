# Input/Output Anchor Conditional Rendering Optimization

## Overview

This update optimizes the rendering logic for node input/output anchors, dynamically controlling anchor visibility based on `config.json` configuration.

## Key Changes

### 1. Input Anchor Conditional Rendering

Modified `ui/canvas/items/anchor_manager.py`:

- Input anchors are not rendered when `listen_upper_file` field is absent in `config.json`
- Input anchors are only displayed when the node has an upstream listening path configured
- Avoids displaying unnecessary input anchors for nodes with no input connections

### 2. Output Anchor Conditional Rendering

Modified `ui/canvas/items/anchor_manager.py`:

- Output anchors are not rendered when `output_file` field is absent in `config.json`
- Output anchors are only displayed when the node has an output file path configured
- Avoids displaying unnecessary output anchors for nodes with no output

### 3. Interaction Handling Optimization

Modified `ui/canvas/items/node_components/interaction_handler.py`:

- Added anchor visibility checks to prevent connecting to invisible anchors
- Ignores operations when users try to drag invisible anchors
- Ensures interaction logic is consistent with rendering logic

## File Changes

| File | Change Type | Description |
|------|------------|-------------|
| `ui/canvas/items/anchor_manager.py` | Modified | Conditional rendering for input/output anchors |
| `ui/canvas/items/node_components/interaction_handler.py` | Modified | Anchor visibility validation |