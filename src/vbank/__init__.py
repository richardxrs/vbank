#!/usr/bin/env python3
import argparse
import json
import os
import sys
import random
import subprocess
import urllib.parse
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.local/share/vbank")
DATA_FILE = os.path.join(DATA_DIR, "words.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


# ── Data layer ──────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def load_words():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_words(words):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)

def fetch_definition(word):
    q = urllib.parse.quote(word)
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{q}"
    try:
        res = subprocess.run(["curl", "-s", "--max-time", "8", url],
                           capture_output=True, text=True, timeout=12)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                meanings = entry.get("meanings", [])
                defs, syns, types, examples = [], set(), set(), []
                for m in meanings:
                    pos = m.get("partOfSpeech", "")
                    if pos:
                        types.add(pos)
                    for d in m.get("definitions", []):
                        defs.append(d.get("definition", ""))
                        ex = d.get("example")
                        if ex:
                            examples.append(ex)
                    for s in m.get("synonyms", []):
                        syns.add(s)
                return {
                    "definitions": defs[:3],
                    "synonyms": list(syns)[:5],
                    "types": list(types),
                    "examples": examples[:3],
                }
    except Exception:
        return None

def fetch_datamuse(word):
    q = urllib.parse.quote(word)
    url = f"https://api.datamuse.com/words?sp={q}&md=d&max=1"
    try:
        res = subprocess.run(["curl", "-s", "--max-time", "6", url],
                           capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            if data and len(data) > 0 and data[0].get("defs"):
                defs = [d.split("\t", 1)[1] if "\t" in d else d for d in data[0]["defs"]]
                types = [t for t in data[0].get("tags", []) if t in ("adj","n","v","adv","pron","prep","conj","interj")]
                return {"definitions": defs[:3], "synonyms": [], "types": types, "examples": [], "source": "Datamuse"}
    except Exception:
        return None

def fetch_chinese(word):
    q = urllib.parse.quote(word)
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|zh-CN"
    try:
        res = subprocess.run(["curl", "-s", "--max-time", "6", url],
                           capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            trans = data.get("responseData", {}).get("translatedText")
            return trans if trans else None
    except Exception:
        return None

def add_word(phrase, silent=False):
    words = load_words()
    if any(w["phrase"].lower() == phrase.lower() for w in words):
        return None, "already exists"
    entry = {"phrase": phrase, "added": datetime.now().isoformat()}
    info = fetch_definition(phrase)
    if info:
        entry["definitions"] = info["definitions"]
        entry["synonyms"] = info["synonyms"]
        entry["types"] = info["types"]
        entry["examples"] = info["examples"]
    else:
        fallback = fetch_datamuse(phrase)
        if fallback:
            entry["definitions"] = fallback["definitions"]
            entry["synonyms"] = fallback["synonyms"]
            entry["types"] = fallback["types"]
            entry["examples"] = fallback["examples"]
            entry["source"] = fallback["source"]
            if not silent:
                print(f"  (definition from {fallback['source']})")
        else:
            entry["definitions"] = []
            entry["synonyms"] = []
            entry["types"] = []
            entry["examples"] = []
    chinese = fetch_chinese(phrase)
    entry["chinese"] = chinese if chinese else ""
    words.append(entry)
    save_words(words)
    return entry, None

def delete_word(phrase):
    words = load_words()
    new = [w for w in words if w["phrase"].lower() != phrase.lower()]
    if len(new) == len(words):
        return False
    save_words(new)
    return True

def edit_word(phrase, chinese=None, definitions=None, synonyms=None):
    words = load_words()
    for w in words:
        if w["phrase"].lower() == phrase.lower():
            if chinese is not None:
                w["chinese"] = chinese
            if definitions is not None:
                w["definitions"] = definitions
            if synonyms is not None:
                w["synonyms"] = synonyms
            save_words(words)
            return w
    return None


# ── CLI commands (unchanged) ────────────────────────────────────────────

def cmd_add(args):
    phrase = " ".join(args.phrase)
    entry, err = add_word(phrase)
    if err:
        print(f"'{phrase}' already exists.")
        return
    print(f"✓ Added '{phrase}'")
    if entry.get("types"):
        print(f"  Type: {', '.join(entry['types'])}")
    if entry.get("definitions"):
        print(f"  Def: {'; '.join(entry['definitions'][:1])}")
    if entry.get("synonyms"):
        print(f"  Syn: {', '.join(entry['synonyms'][:3])}")
    if entry.get("chinese"):
        print(f"  CN:  {entry['chinese']}")

def cmd_list(args):
    words = load_words()
    if not words:
        print("Empty.")
        return
    print(f"Word Bank ({len(words)}):\n")
    for i, w in enumerate(words, 1):
        print(f"  {i}. {w['phrase']}")
        if w.get("chinese"):
            print(f"     CN: {w['chinese']}")
        print()

def cmd_review(args):
    words = load_words()
    if not words:
        print("Empty.")
        return
    sample = random.sample(words, min(args.count, len(words)))
    known = 0
    for w in sample:
        print(f"\nWord: {w['phrase']}")
        input("  [Enter] to reveal...")
        if w.get("chinese"):
            print(f"  CN: {w['chinese']}")
        if w.get("definitions"):
            print(f"  Def: {'; '.join(w['definitions'][:2])}")
        if w.get("synonyms"):
            print(f"  Syn: {', '.join(w['synonyms'][:3])}")
        if input("  Know? (y/n): ").strip().lower() == "y":
            known += 1
    if sample:
        print(f"\nScore: {known}/{len(sample)} ({known * 100 // len(sample)}%)")

def cmd_delete(args):
    phrase = " ".join(args.phrase)
    print("✓ Removed." if delete_word(phrase) else "Not found.")

def cmd_stats(args):
    words = load_words()
    print(f"Total: {len(words)}")
    if words:
        print(f"Oldest: {words[0]['phrase']} ({words[0]['added'][:10]})")
        print(f"Newest: {words[-1]['phrase']} ({words[-1]['added'][:10]})")

def cmd_edit(args):
    phrase = " ".join(args.phrase)
    words = load_words()
    w = None
    for entry in words:
        if entry["phrase"].lower() == phrase.lower():
            w = entry
            break
    if not w:
        print(f"'{phrase}' not found.")
        return
    print(f"Editing '{w['phrase']}':\n")
    changed = False
    cn = input(f"Chinese [{w.get('chinese', '')}]: ").strip()
    if cn:
        w["chinese"] = cn
        changed = True
    print("Definitions (leave blank to keep):")
    for i, d in enumerate(w.get("definitions", []), 1):
        new_d = input(f"  {i}. [{d}]: ").strip()
        if new_d:
            w["definitions"][i - 1] = new_d
            changed = True
    try:
        while True:
            new_def = input(f"  {len(w.get('definitions', [])) + 1}. [new]: ").strip()
            if not new_def:
                break
            w.setdefault("definitions", []).append(new_def)
            changed = True
    except (EOFError, KeyboardInterrupt):
        pass
    syn = input(f"Synonyms [{', '.join(w.get('synonyms', []))}]: ").strip()
    if syn:
        w["synonyms"] = [s.strip() for s in syn.split(",") if s.strip()]
        changed = True
    if changed:
        save_words(words)
        print(f"✓ Updated '{phrase}'")
    else:
        print("No changes made.")


# ── TUI ─────────────────────────────────────────────────────────────────

try:
    from textual.app import App, ComposeResult
    from textual.screen import Screen, ModalScreen
    from textual.widgets import (
        DataTable, Input, Static, Button, Header, Footer, Label, TextArea
    )
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, ScrollableContainer
    from textual import work
    from textual.reactive import reactive
    from rich.text import Text
    TUI_AVAILABLE = True
except ImportError:
    TUI_AVAILABLE = False


if TUI_AVAILABLE:

    class WordDetailScreen(ModalScreen):
        BINDINGS = [Binding("escape", "close", "Close")]

        def __init__(self, word):
            super().__init__()
            self.word = word

        def compose(self):
            w = self.word
            lines = [f"[bold]{w['phrase']}[/]"]
            if w.get("types"):
                lines.append(f"\nType: {', '.join(w['types'])}")
            if w.get("chinese"):
                lines.append(f"\nChinese: {w['chinese']}")
            if w.get("definitions"):
                lines.append("\nDefinitions:")
                for i, d in enumerate(w["definitions"], 1):
                    lines.append(f"  {i}. {d}")
            if w.get("examples"):
                lines.append("\nExamples:")
                for ex in w["examples"]:
                    lines.append(f"  • {ex}")
            if w.get("synonyms"):
                lines.append(f"\nSynonyms: {', '.join(w['synonyms'])}")
            lines.append(f"\nAdded: {w['added'][:10]}")
            yield Static("\n".join(lines))
            yield Button("Close", variant="primary", id="close")

        def on_button_pressed(self, event):
            self.dismiss()

        def action_close(self):
            self.dismiss()

    class EditWordScreen(ModalScreen):
        BINDINGS = [Binding("escape", "cancel", "Cancel")]

        def __init__(self, word):
            super().__init__()
            self.word = word

        def compose(self):
            w = self.word
            yield Static(f"[bold]Editing: {w['phrase']}[/]\n")
            yield Label("Chinese:")
            yield Input(value=w.get("chinese", ""), id="chinese_input")
            yield Label("Definitions (one per line):")
            defs = w.get("definitions", [])
            for i, d in enumerate(defs):
                yield Input(value=d, id=f"def_{i}")
            yield Input(placeholder="New definition...", id="def_new")
            yield Label("Synonyms (comma-separated):")
            yield Input(value=", ".join(w.get("synonyms", [])), id="synonyms_input")
            yield Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Save", variant="primary", id="save"),
            )

        def action_cancel(self):
            self.dismiss()

        def on_button_pressed(self, event):
            if event.button.id == "cancel":
                self.dismiss()
            elif event.button.id == "save":
                w = self.word
                cn = self.query_one("#chinese_input", Input).value.strip()
                if cn:
                    w["chinese"] = cn
                defs = []
                for i in range(len(w.get("definitions", []))):
                    inp = self.query_one(f"#def_{i}", Input)
                    v = inp.value.strip()
                    if v:
                        defs.append(v)
                new_def = self.query_one("#def_new", Input).value.strip()
                if new_def:
                    defs.append(new_def)
                if defs:
                    w["definitions"] = defs
                syn = self.query_one("#synonyms_input", Input).value.strip()
                if syn:
                    w["synonyms"] = [s.strip() for s in syn.split(",") if s.strip()]
                words = load_words()
                for entry in words:
                    if entry["phrase"].lower() == w["phrase"].lower():
                        entry.update(w)
                        break
                save_words(words)
                self.dismiss(True)

    class AddWordScreen(ModalScreen):
        BINDINGS = [Binding("escape", "cancel", "Cancel")]

        def compose(self):
            yield Static("[bold]Add a word[/]\n")
            yield Input(placeholder="Enter a word or phrase...", id="word_input")
            yield Static("", id="status")
            yield Button("Cancel", variant="default", id="cancel")

        def on_button_pressed(self, event):
            self.dismiss()

        def action_cancel(self):
            self.dismiss()

        def on_input_submitted(self, event):
            phrase = event.value.strip()
            if not phrase:
                return
            status = self.query_one("#status", Static)
            status.update("[yellow]Fetching and adding...[/]")
            self.fetch_and_add(phrase)

        @work(thread=True)
        async def fetch_and_add(self, phrase):
            entry, err = add_word(phrase)
            if err:
                self.app.call_from_thread(self.query_one("#status", Static).update, f"[red]{phrase}[/] already exists.")
                return
            self.app.call_from_thread(self.dismiss, entry)

    class SearchScreen(ModalScreen):
        BINDINGS = [Binding("escape", "cancel", "Cancel")]

        def compose(self):
            yield Static("[bold]Search words[/]\n")
            yield Input(placeholder="Type to search (Enter to confirm)...", id="search_input")

        def on_mount(self):
            self.query_one("#search_input", Input).focus()

        def on_input_submitted(self, event):
            self.dismiss(event.value.strip())

        def action_cancel(self):
            self.dismiss(None)

    class WrongWordsScreen(ModalScreen):
        BINDINGS = [Binding("escape", "close", "Close")]

        def __init__(self, known, total, wrong):
            super().__init__()
            self.known = known
            self.total = total
            self.wrong = wrong

        def compose(self):
            pct = self.known * 100 // self.total if self.total else 0
            lines = [f"[bold]Score: {self.known}/{self.total} ({pct}%)[/]\n"]
            if self.wrong:
                lines.append("[red]Words to review:[/]\n")
                for w in self.wrong:
                    cn = f" — {w.get('chinese', '')}" if w.get("chinese") else ""
                    lines.append(f"  • {w['phrase']}{cn}")
            else:
                lines.append("[green]All correct![/]")
            yield Static("\n".join(lines))
            yield Button("Close", variant="primary", id="close")

        def on_button_pressed(self, event):
            self.dismiss()

        def action_close(self):
            self.dismiss()

    class FlashcardsScreen(Screen):
        def __init__(self, words):
            super().__init__()
            self.queue = list(words)
            self.total = len(words)
            self.known = 0
            self.answered = 0
            self.revealed = False
            self.wrong = []

        def compose(self):
            yield Header()
            yield Static("", id="word_display")
            yield Static("", id="answer_display")
            yield Static("", id="progress")
            yield Horizontal(
                Button("Know It", variant="success", id="know"),
                Button("Don't Know", variant="error", id="dont_know"),
                Button("Quit", variant="default", id="quit"),
            )
            yield Footer()

        def on_mount(self):
            self.show_current()

        def show_current(self):
            if not self.queue:
                self.show_result()
                return
            w = self.queue[0]
            self.query_one("#word_display", Static).update(
                f"\n[b]{w['phrase']}[/]\n\nPress [i]Space[/i] to reveal answer"
            )
            self.query_one("#answer_display", Static).update("")
            self.query_one("#progress", Static).update(
                f"Remaining: {len(self.queue)} | Known: {self.known} | Answered: {self.answered}"
            )
            self.query_one("#know", Button).disabled = True
            self.query_one("#dont_know", Button).disabled = True
            self.revealed = False

        def reveal(self):
            if self.revealed or not self.queue:
                return
            w = self.queue[0]
            lines = []
            if w.get("chinese"):
                lines.append(f"Chinese: {w['chinese']}")
            if w.get("definitions"):
                lines.append(f"Definitions:")
                for i, d in enumerate(w["definitions"], 1):
                    lines.append(f"  {i}. {d}")
            if w.get("synonyms"):
                lines.append(f"Synonyms: {', '.join(w['synonyms'])}")
            self.query_one("#answer_display", Static).update("\n".join(lines))
            self.query_one("#know", Button).disabled = False
            self.query_one("#dont_know", Button).disabled = False
            self.revealed = True

        def on_button_pressed(self, event):
            if not self.queue:
                return
            if event.button.id == "know":
                self.known += 1
                self.answered += 1
                self.queue.pop(0)
                self.show_current()
            elif event.button.id == "dont_know":
                self.answered += 1
                w = self.queue.pop(0)
                self.wrong.append(w)
                self.queue.append(w)
                self.show_current()
            elif event.button.id == "quit":
                self.dismiss({"known": self.known, "total": self.answered, "wrong": self.wrong})

        def on_key(self, event):
            if event.key == "space":
                self.reveal()

        def show_result(self):
            self.dismiss({"known": self.known, "total": self.answered, "wrong": self.wrong})

    class StatsScreen(ModalScreen):
        BINDINGS = [Binding("escape", "close", "Close")]

        def compose(self):
            words = load_words()
            lines = []
            lines.append("[bold]Statistics[/]\n")
            lines.append(f"Total words: [green]{len(words)}[/]")
            if words:
                lines.append(f"Oldest: {words[0]['phrase']} ({words[0]['added'][:10]})")
                lines.append(f"Newest: {words[-1]['phrase']} ({words[-1]['added'][:10]})")
                lines.append(f"With definitions: {sum(1 for w in words if w.get('definitions'))}")
                lines.append(f"With Chinese: {sum(1 for w in words if w.get('chinese'))}")
                lines.append(f"With synonyms: {sum(1 for w in words if w.get('synonyms'))}")
            yield Static("\n".join(lines))
            yield Button("Close", variant="primary", id="close")

        def on_button_pressed(self, event):
            self.dismiss()

        def action_close(self):
            self.dismiss()

    class ColorPickerScreen(ModalScreen):
        BINDINGS = [Binding("escape", "close", "Cancel")]

        def __init__(self, current_color=""):
            super().__init__()
            self.current_color = current_color
            self.palette = [
                ("None", ""),
                ("Red", "red"),
                ("Green", "green"),
                ("Yellow", "yellow"),
                ("Blue", "blue"),
                ("Magenta", "magenta"),
                ("Cyan", "cyan"),
                ("White", "white"),
            ]

        def compose(self):
            yield Static("[bold]Pick a color for this word[/]\n")
            for name, code in self.palette:
                marker = "●" if code else "○"
                style = f"[{code}]{marker} {name}[/]" if code else f"{marker} {name}"
                yield Button(style, id=code or "none", variant="default")
            yield Button("Cancel", variant="default", id="cancel")

        def on_button_pressed(self, event):
            if event.button.id == "cancel":
                self.dismiss(None)
            else:
                self.dismiss(event.button.id)

        def action_close(self):
            self.dismiss(None)

    class WordListScreen(Screen):
        BINDINGS = [
            Binding("a", "add_word", "Add"),
            Binding("c", "color_word", "Color"),
            Binding("d", "delete_word", "Delete"),
            Binding("e", "edit_word", "Edit"),
            Binding("f", "search", "Search"),
            Binding("r", "flashcards", "Flashcards"),
            Binding("s", "show_stats", "Stats"),
            Binding("q", "quit", "Quit"),
            Binding("enter", "show_detail", "Detail"),
            Binding("space", "show_detail", "Expand"),
            Binding("j", "cursor_down", "Down", show=False),
            Binding("k", "cursor_up", "Up", show=False),
        ]

        def compose(self):
            yield Header()
            yield Static("", id="filter_bar")
            yield DataTable(id="word_table")
            yield Footer()

        def refresh_table(self):
            table = self.query_one("#word_table", DataTable)
            table.clear()
            table.columns.clear()
            table.add_columns("#", "Word", "Type", "Chinese", "Definition", "Synonyms", "Added")
            words = load_words()
            fb = self.query_one("#filter_bar", Static)
            if self.search_filter:
                words = [w for w in words if self.search_filter.lower() in w["phrase"].lower() or self.search_filter.lower() in w.get("chinese", "").lower()]
                fb.update(f"[yellow]🔍 filtered: '{self.search_filter}' ({len(words)} matches) — press f again to clear[/]")
                fb.display = True
            else:
                fb.update("")
                fb.display = False
            for i, w in enumerate(words, 1):
                def_text = w["definitions"][0][:50] + "..." if w.get("definitions") and len(w["definitions"][0]) > 50 else (w["definitions"][0] if w.get("definitions") else "")
                syn_text = ", ".join(w["synonyms"][:3])[:40] if w.get("synonyms") else ""
                typ_text = ", ".join(w.get("types", []))
                word_cell = Text(w["phrase"], style=w.get("color", "")) if w.get("color") else w["phrase"]
                table.add_row(
                        str(i),
                        word_cell,
                        typ_text,
                        w.get("chinese", "")[:25],
                        def_text,
                        syn_text,
                        w["added"][:10],
                    )

        def action_add_word(self):
            def on_add(result):
                if result:
                    self.refresh_table()
            self.app.push_screen(AddWordScreen(), on_add)

        def action_delete_word(self):
            table = self.query_one("#word_table", DataTable)
            if table.row_count == 0:
                return
            row_index = table.cursor_row
            if row_index is None or not table.is_valid_row_index(row_index):
                return
            rows = table.get_row_at(row_index)
            phrase = str(rows[1])
            delete_word(phrase)
            self.refresh_table()

        def action_edit_word(self):
            table = self.query_one("#word_table", DataTable)
            if table.row_count == 0:
                return
            row_index = table.cursor_row
            if row_index is None or not table.is_valid_row_index(row_index):
                return
            rows = table.get_row_at(row_index)
            phrase = str(rows[1])
            words = load_words()
            for w in words:
                if w["phrase"].lower() == phrase.lower():
                    def on_edit(result):
                        if result:
                            self.refresh_table()
                    self.app.push_screen(EditWordScreen(w), on_edit)
                    break

        def action_color_word(self):
            table = self.query_one("#word_table", DataTable)
            if table.row_count == 0:
                return
            row_index = table.cursor_row
            if row_index is None or not table.is_valid_row_index(row_index):
                return
            rows = table.get_row_at(row_index)
            phrase = str(rows[1])
            words = load_words()
            for w in words:
                if w["phrase"].lower() == phrase.lower():
                    def on_color(color):
                        if color is None:
                            return
                        w["color"] = color if color else ""
                        save_words(words)
                        self.refresh_table()
                    self.app.push_screen(ColorPickerScreen(w.get("color", "")), on_color)
                    break

        def action_flashcards(self):
            words = load_words()
            if not words:
                return
            def on_flashcards_done(result):
                if result:
                    self.app.push_screen(WrongWordsScreen(result["known"], result["total"], result["wrong"]))
            self.app.push_screen(FlashcardsScreen(words), on_flashcards_done)

        def action_show_stats(self):
            self.app.push_screen(StatsScreen())

        def action_search(self):
            if self.search_filter:
                self.search_filter = ""
                self.refresh_table()
                return
            def on_search(term):
                if term is None:
                    return
                self.search_filter = term
                self.refresh_table()
            self.app.push_screen(SearchScreen(), on_search)

        def action_show_detail(self):
            table = self.query_one("#word_table", DataTable)
            if table.row_count == 0:
                return
            row_index = table.cursor_row
            if row_index is None or not table.is_valid_row_index(row_index):
                return
            rows = table.get_row_at(row_index)
            phrase = str(rows[1])
            words = load_words()
            for w in words:
                if w["phrase"] == phrase:
                    self.app.push_screen(WordDetailScreen(w))
                    break

        def on_mount(self):
            self.digit_buffer = ""
            self.digit_timer = None
            self.search_filter = ""
            self.query_one("#filter_bar", Static).display = False
            self.refresh_table()

        def on_key(self, event):
            if event.key.isdigit():
                self.digit_buffer += event.key
                if self.digit_timer:
                    self.digit_timer.reset()
                from textual.timer import Timer
                self.digit_timer = self.set_timer(1.0, self.clear_digit_buffer)
                table = self.query_one("#word_table", DataTable)
                if table.row_count == 0:
                    return
                target = int(self.digit_buffer) - 1
                rows = load_words()
                if 0 <= target < len(rows) and table.is_valid_row_index(target):
                    table.move_cursor(row=target)
                event.stop()
            else:
                self.clear_digit_buffer()

        def clear_digit_buffer(self):
            self.digit_buffer = ""

        def action_cursor_down(self):
            table = self.query_one("#word_table", DataTable)
            rows = load_words()
            if not rows:
                return
            cur = table.cursor_row if table.cursor_row is not None else -1
            if cur >= len(rows) - 1:
                table.move_cursor(row=0)
            else:
                table.action_cursor_down()

        def action_cursor_up(self):
            table = self.query_one("#word_table", DataTable)
            rows = load_words()
            if not rows:
                return
            cur = table.cursor_row if table.cursor_row is not None else 0
            if cur <= 0:
                table.move_cursor(row=len(rows) - 1)
            else:
                table.action_cursor_up()

        def action_quit(self):
            self.app.exit()

    class SATVocabApp(App):
        TITLE = "vbank"
        SCREENS = {"wordlist": WordListScreen}

        def on_mount(self):
            cfg = load_config()
            theme = cfg.get("theme")
            if theme:
                self.theme = theme
            self.push_screen("wordlist")

        def watch_theme(self, old, new):
            cfg = load_config()
            cfg["theme"] = new
            save_config(cfg)

    def run_tui():
        app = SATVocabApp()
        app.run()


# ── Entry point ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) == 1 and TUI_AVAILABLE:
        run_tui()
        return

    p = argparse.ArgumentParser(description="vbank - vocabulary bank")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("add", help="Add a phrase")
    a.add_argument("phrase", nargs="+")

    sub.add_parser("list", help="List all words")

    d = sub.add_parser("delete", help="Delete a phrase")
    d.add_argument("phrase", nargs="+")

    sub.add_parser("stats", help="Show stats")

    e = sub.add_parser("edit", help="Edit a word's Chinese or definitions")
    e.add_argument("phrase", nargs="+")

    fc = sub.add_parser("flashcards", help="Quiz yourself with flashcards (unknown words cycle until known)")
    fc.add_argument("-n", "--count", type=int, default=5)

    r = sub.add_parser("review", help="Alias for flashcards")
    r.add_argument("-n", "--count", type=int, default=5)

    args = p.parse_args()
    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd in ("review", "flashcards"):
        cmd_review(args)
    elif args.cmd == "delete":
        cmd_delete(args)
    elif args.cmd == "stats":
        cmd_stats(args)
    elif args.cmd == "edit":
        cmd_edit(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
