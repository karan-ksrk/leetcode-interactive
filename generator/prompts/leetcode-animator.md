# LeetCode Animator Instruction File

**IMPORTANT:** This is a placeholder. Replace this file with your actual LeetCode-animator skill markdown content from Claude Code.

The user should paste their skill content here. The skill should instruct the AI agent to:

1. Read the problem JSON file provided (via path or inline)
2. Create a fully standalone interactive HTML page explaining the algorithm
3. Write ONLY to the output file path specified
4. Do NOT modify any other files

## Required Page Structure

The generated HTML must contain:

### Header
- LeetCode problem number, difficulty, technique
- Mnemonic (short memorable phrase)
- Brief problem explanation

### Move Cards
- 3-5 algorithmic moves
- Each with color tag, rule, explanation
- Current move highlighted dynamically

### Interactive Stage
- Visual representation (array tiles, graph nodes, grid cells, etc.)
- Animated pointers and labels
- Current element highlighting
- Narration line with `aria-live="polite"`

### Controls
- Play/Pause, Next, Back, Restart buttons
- Speed adjustment (0.5x, 1x, 2x)
- Frame scrubber slider
- Keyboard shortcuts: Space (play), arrows (step), R (restart)

### State Panel
- Shows current algorithm state (hash map, stack, visited set, etc.)
- Progress indicator where relevant

### Code Panel
- Python solution with line numbers
- Current executing lines highlighted
- Matches animation frames exactly

### Why It's Fast
- Key insight explanation
- Time/space complexity
- Comparison with brute force

### Try Another Example
- Preset buttons for common test cases
- Custom input box with validation
- Error messages for invalid input

### Animation Engine
- `build(input)` function: runs the actual algorithm, returns array of frame snapshots
- `show(frameIdx)` function: renders any frame from its snapshot
- Each frame contains: kind, message, pointers, structure state, answers, operation count
- `console.assert` checks for correctness

### Visual Design
- CSS custom properties for colors (light/dark mode)
- Fonts: Bricolage Grotesque (headlines), IBM Plex Sans (body), JetBrains Mono (code)
- Responsive to 400px width
- Respect `prefers-reduced-motion`
- Semantic HTML, accessible focus states

## Example Reference

See `problems/1-two-sum.html` in the same repo for a complete, working example of what the generated HTML should look like.

## How to Use

1. Get your LeetCode-animator skill markdown from Claude Code
2. Replace this file's contents with it
3. Run `python -m generator` → option 1
4. Paste a LeetCode URL
5. Select Claude (or another agent)
6. The agent will generate HTML following your skill's instructions

---

**To fill in this file:**

Copy your skill's markdown content and replace everything above this line.
