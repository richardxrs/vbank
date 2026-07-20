# vbank

A vocabulary bank — save words you don't know with definitions, synonyms, and Chinese translations.

## Install

**Requirements:** Python 3.10+

### Option 1: Clone + pip install (recommended)

```bash
git clone https://github.com/richardxrs/vbank.git
cd vbank
pip install .
```

Now `vbank` is available as a system command.

> **macOS:** use `pip3` instead of `pip`. If SSL errors occur during install,
> first install build tools, then reinstall with build isolation disabled:
> ```bash
> pip3 install setuptools wheel
> pip3 install --no-build-isolation .
> ```
>
> If `vbank` command is not found after install, use `python3 -m vbank`
> instead — it works without any PATH setup. To make `vbank` permanent:
> ```bash
> export PATH="$PATH:$(python3 -m site --user-base)/bin"
> ```

### Option 2: Run directly without installing

```bash
git clone https://github.com/richardxrs/vbank.git
cd vbank
pip install textual
python3 -m vbank
```

### Option 3: Install directly from GitHub (no clone)

```bash
pip install git+https://github.com/richardxrs/vbank.git
```

### Option 4: Arch Linux (with uv)

```bash
uv pip install --system git+https://github.com/richardxrs/vbank.git
```

### Updating

```bash
# If you cloned:
cd vbank && git pull && pip install .

# If you installed via pip+git:
pip install --upgrade git+https://github.com/richardxrs/vbank.git
```

## Uninstall

Remove the package and (optionally) your saved words:

```bash
# Uninstall the command
pip uninstall vbank

# (Optional) Delete your word bank
rm -rf ~/.local/share/vbank
```

If you cloned the repo, you can also delete that folder:

```bash
rm -rf vbank
```

## Usage

If `vbank` doesn't work as a command, use `python3 -m vbank` instead.

```
vbank                  Launch the TUI
vbank add <phrase>     Add a word (fetches info automatically)
vbank list             List all saved words
vbank flashcards -n 10  Quiz with flashcards (unknown words cycle until known)
vbank edit <phrase>    Edit a word's Chinese translation or definitions
vbank delete <phrase>  Remove a word
vbank stats            Show statistics
```

### TUI keybinds

| Key | Action |
|-----|--------|
| `a` | Add word (Enter to fetch + save) |
| `c` | Color-pick the selected word (8 colors) |
| `d` | Delete selected |
| `e` | Edit selected word |
| `r` | Flashcards (all words, unknown cycle until known) |
| `s` | Stats |
| `Space` / `Enter` | Expand/collapse word details |
| `Esc` | Close modals / Cancel |
| `j` / `k` | Navigate up / down (wraps at edges) |
| `1`–`9`… | Type row number to jump directly (buffer resets after 1s) |
| `q` | Quit |

Flashcards show a wrong-word report on quit or when all words are known.

Data is stored at `~/.local/share/vbank/words.json`.
