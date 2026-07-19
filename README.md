# vbank

SAT vocabulary bank — save words you don't know with definitions, synonyms, and Chinese translations.

## Install

```bash
# Install dependencies
pip install textual

# Run directly
./vbank.py

# Or install system-wide
pip install .
```

## Usage

```
vbank                  Launch the TUI
vbank add <phrase>     Add a word (fetches info automatically)
vbank list             List all saved words
vbank review -n 10     CLI quiz mode
vbank delete <phrase>  Remove a word
vbank stats            Show statistics
```

### TUI keybinds

| Key | Action |
|-----|--------|
| `a` | Add word |
| `d` | Delete selected |
| `r` | Review |
| `s` | Stats |
| `Enter` | Word details |
| `q` | Quit |

Data is stored at `~/.local/share/vbank/words.json`.
