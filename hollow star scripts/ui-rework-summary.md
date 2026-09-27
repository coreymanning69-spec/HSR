# UI Layout Rework - Message Panel & Draggable Containers

## Overview
Reworked the Hollow Star Reliquary UI to add a dedicated message/error panel with history tracking and draggable containers for Engine Actions and Command/Chat input.

## Changes Made

### 1. State Management (app.js)
- Added `messageHistory: []` to track all messages and errors
- Added `messageHistoryOpen: false` to control panel visibility
- Messages are stored with timestamp and type (note/error)
- Maintains history up to 100 messages (auto-prunes oldest)

### 2. Message Tracking Functions (app.js)
**New Function: `addMessage(text, type)`**
- Logs messages to `state.messageHistory` with timestamp
- Automatically prunes to 100 message limit
- Called automatically when errors occur or actions complete

**Updated Function: `fail(message)`**
- Now calls `addMessage(message, 'error')` in addition to setting error state

### 3. UI Components (app.js)

**New Function: `messagePanel()`**
- Renders a dedicated panel displaying message history
- Shows timestamp and message type for each entry
- Includes header with Close and Clear buttons
- Scrollable history display

**Updated Function: `consoleBar()`**
- Added panel header with hint text
- Added 📋 button to toggle message panel visibility
- Made input more integrated with panel structure

**Updated Function: `actionBar()`**
- Added `data-panel="actions"` attribute for dragging support

### 4. Event Handlers (app.js)

**New Action Handlers:**
- `toggle-messages` - Show/hide message panel
- `close-messages` - Close message panel
- `clear-messages` - Clear message history

**Message Logging Added To:**
- Engine action submission
- Domain feature submission
- Maneuver submission
- Reaction submission

### 5. Dragging Support (app.js)
- Added dragging code in `bind()` function
- Works with any element with `data-panel` attribute
- Uses `.panel-header` as drag handle
- Supports repositioning via mouse drag

### 6. Styling (styles.css)

**Message Panel Styles:**
- Fixed positioning (bottom-right by default)
- Max height 280px with scrollable content
- Dark semi-transparent background with backdrop blur
- Border and styling consistent with game theme

**Message Row Styling:**
- Grid layout: timestamp | message
- Error messages highlighted in red
- Note messages highlighted in gold
- Monospace timestamp font

**Interactive Elements:**
- Cursor changes to "grab" on header hover, "grabbing" while dragging
- Buttons for Clear and Close with hover effects
- Input field with gold focus state

## User Experience

### Message Panel Features
1. **Real-time Tracking** - All actions and errors automatically logged
2. **History** - Maintains last 100 messages with timestamps
3. **Accessible** - Toggle on/off with button in console
4. **Draggable** - Grab header to reposition anywhere on screen
5. **Organized** - Messages color-coded by type (error/note)

### Input Consolidation
- Command/Chat input now serves as central input point
- Quick toggle to message history without losing focus
- Clear visual grouping of input and message areas

### Arrangement Options
- Engine Actions box is now draggable (data-panel="actions")
- Console/Command box is draggable (data-panel="console")
- Message panel is draggable (data-panel="messages")
- Header grab points make dragging intuitive

## Technical Implementation

### Data Flow
1. User takes action → handled in bind() event listeners
2. state.note set with message text
3. addMessage() called to track in history
4. render() updates UI with new message panel if open
5. Dragging works on repositioned panels

### Performance
- Message history pruned to 100 items max
- No DOM recreation on drag (just style updates)
- Efficient message panel rendering

## Future Enhancements
- Save message history to localStorage
- Export message log to file
- Message filtering/search
- Customizable panel sizes and positions
- Theme colors for different message types
- Keyboard shortcuts for panel toggle

## Files Modified
1. `/web/app.js` - Core UI logic and state management
2. `/web/styles.css` - Styling for new panels and dragging
