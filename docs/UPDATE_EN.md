# Update Log

## 2026-06-06

### Bug Fixes

1. **Restart Functionality Fix**
   - Fixed the issue where the confirmation dialog "Nodes are running, do you want to close them?" was not displayed during system restart
   - Added running node detection and confirmation dialog logic in the `_restart_application` method
   - Ensures users can choose to close running nodes or let them continue running in the background

2. **Data Persistence Fix**
   - Optimized canvas layout saving logic to ensure correct saving of node positions, sizes, styles, and other information
   - Enhanced error handling and data recovery capabilities during layout loading
   - Fixed the issue of mismatched node styles and sizes

3. **State Synchronization Fix**
   - Fixed the issue where status information was not updated in real-time after node startup
   - Ensures the node monitoring module correctly acquires and displays status information such as CPU, memory, and running time
   - Optimized the state update signal transmission and processing mechanism

4. **UI Layout Fix**
   - Adjusted the spacing of elements inside nodes to enhance visual experience and operational convenience
   - Optimized the positions of node names, status indicators, language labels, and other elements
   - Adjusted the layout of status display components to avoid element overlap

### Code Optimization

1. **Node Monitoring Module Optimization**
   - Refactored the NodeMonitor class to use QTimer instead of threads for periodic updates
   - Optimized state update logic to reduce unnecessary calculations
   - Enhanced error handling and recovery capabilities

2. **Code Structure Optimization**
   - Moved layout save/load logic to CanvasLayoutMixin
   - Moved color setting methods to CanvasColorsMixin
   - Improved code modularity and maintainability

### Other Improvements

1. **Auto-save Mechanism Optimization**
   - Added debounce mechanism to avoid frequent saving
   - Optimized saving timing to ensure timely saving of layout changes

2. **Logging System Optimization**
   - Added more detailed logging information
   - Optimized log format to improve readability

3. **Error Handling Enhancement**
   - Enhanced handling of various exception situations
   - Provided more user-friendly error prompt messages