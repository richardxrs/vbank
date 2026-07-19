#!/usr/bin/env python3
import argparse
import json
import os
import sys
import random
import socket
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pathlib import Path

socket.setdefaulttimeout(8)

DATA_DIR = os.path.expanduser("~/.local/share/vbank")
DATA_FILE = os.path.join(DATA_DIR, "words.json")


# ── Data layer ──────────────────────────────────────────────────────────

def load_words():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_words(words):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)

def fetch_definition(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "vbank/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data and isinstance(data, list):
                entry = data[0]
                meanings = entry.get("meanings", [])
                defs, syns = [], set()
                for m in meanings:
                    for d in m.get("definitions", []):
                        defs.append(d.get("definition", ""))
                    for s in m.get("synonyms", []):
                        syns.add(s)
                return {"definitions": defs[:3], "synonyms": list(syns)[:5]}
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

def add_word(phrase):
    words = load_words()
    if any(w["phrase"].lower() == phrase.lower() for w in words):
        return None, "already exists"
    entry = {"phrase": phrase, "added": datetime.now().isoformat()}
    info = fetch_definition(phrase)
    if info:
        entry["definitions"] = info["definitions"]
        entry["synonyms"] = info["synonyms"]
    else:
        entry["definitions"] = []
        entry["synonyms"] = []
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


# ── CLI commands (unchanged) ────────────────────────────────────────────

def cmd_add(args):
    phrase = " ".join(args.phrase)
    entry, err = add_word(phrase)
    if err:
        print(f"'{phrase}' already exists.")
        return
    print(f"✓ Added '{phrase}'")
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
    TUI_AVAILABLE = True
except ImportError:
    TUI_AVAILABLE = False


if TUI_AVAILABLE:

    class WordDetailScreen(ModalScreen):
        def __init__(self, word):
            super().__init__()
            self.word = word

        def compose(self):
            w = self.word
            lines = [f"[bold]{w['phrase']}[/]"]
            if w.get("chinese"):
                lines.append(f"\nChinese: {w['chinese']}")
            if w.get("definitions"):
                lines.append("\nDefinitions:")
                for i, d in enumerate(w["definitions"], 1):
                    lines.append(f"  {i}. {d}")
            if w.get("synonyms"):
                lines.append(f"\nSynonyms: {', '.join(w['synonyms'])}")
            lines.append(f"\nAdded: {w['added'][:10]}")
            yield Static("\n".join(lines))
            yield Button("Close", variant="primary", id="close")

        def on_button_pressed(self, event):
            self.dismiss()

    class AddWordScreen(ModalScreen):
        def compose(self):
            yield Static("[bold]Add a word[/]\n")
            yield Input(placeholder="Enter a word or phrase...", id="word_input")
            yield Static("", id="status")
            yield Horizontal(
                Button("Cancel", variant="default", id="cancel"),
                Button("Add", variant="primary", id="add", disabled=True),
            )

        def on_input_submitted(self, event):
            self.fetch_word_info(event.value.strip())

        def on_button_pressed(self, event):
            if event.button.id == "cancel":
                self.dismiss()
            elif event.button.id == "add":
                phrase = self.query_one("#word_input", Input).value.strip()
                phrase = self._pending_phrase if hasattr(self, '_pending_phrase') else phrase
                entry, err = add_word(phrase)
                if err:
                    self.query_one("#status", Static).update(f"[red]{err}[/]")
                else:
                    self.dismiss(entry)

        @work(thread=True)
        async def fetch_word_info(self, phrase):
            if not phrase:
                return
            status = self.query_one("#status", Static)
            status.update("[yellow]Fetching info...[/]")
            info = fetch_definition(phrase)
            chinese = fetch_chinese(phrase)
            lines = []
            if info:
                lines.append(f"[green]Definition:[/] {'; '.join(info['definitions'][:2])}")
                if info["synonyms"]:
                    lines.append(f"[green]Synonyms:[/] {', '.join(info['synonyms'][:4])}")
            else:
                lines.append("[red]No definition found.[/]")
            lines.append(f"[green]Chinese:[/] {chinese if chinese else '(none)'}")
            status.update("\n".join(lines))
            btn = self.query_one("#add", Button)
            btn.disabled = False
            self._pending_phrase = phrase

    class ReviewScreen(Screen):
        def __init__(self, words):
            super().__init__()
            self.words = words
            self.index = 0
            self.known = 0
            self.revealed = False

        def compose(self):
            yield Header()
            yield Static("", id="word_display")
            yield Static("", id="answer_display")
            yield Static("", id="progress")
            yield Horizontal(
                Button("Know It", variant="success", id="know"),
                Button("Don't Know", variant="error", id="dont_know"),
                Button("Quit Review", variant="default", id="quit"),
            )
            yield Footer()

        def on_mount(self):
            self.show_current()

        def show_current(self):
            if self.index >= len(self.words):
                self.show_result()
                return
            w = self.words[self.index]
            self.query_one("#word_display", Static).update(
                f"\n[b]{w['phrase']}[/]\n\nPress [i]Space[/i] to reveal answer"
            )
            self.query_one("#answer_display", Static).update("")
            self.query_one("#progress", Static).update(
                f"Word {self.index + 1} of {len(self.words)} | Known: {self.known}"
            )
            self.query_one("#know", Button).disabled = True
            self.query_one("#dont_know", Button).disabled = True
            self.revealed = False

        def reveal(self):
            if self.revealed or self.index >= len(self.words):
                return
            w = self.words[self.index]
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
            if event.button.id == "know":
                self.known += 1
                self.index += 1
                self.show_current()
            elif event.button.id == "dont_know":
                self.index += 1
                self.show_current()
            elif event.button.id == "quit":
                self.dismiss(None)

        def on_key(self, event):
            if event.key == "space":
                self.reveal()

        def show_result(self):
            total = len(self.words)
            pct = self.known * 100 // total if total else 0
            self.query_one("#word_display", Static).update(
                f"\n[b]Done![/]\n\nScore: {self.known}/{total} ({pct}%)"
            )
            self.query_one("#answer_display", Static).update("")
            self.query_one("#progress", Static).update("")
            self.query_one("#know", Button).disabled = True
            self.query_one("#dont_know", Button).disabled = True

    class StatsScreen(ModalScreen):
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

    class WordListScreen(Screen):
        BINDINGS = [
            Binding("a", "add_word", "Add"),
            Binding("d", "delete_word", "Delete"),
            Binding("r", "review", "Review"),
            Binding("s", "show_stats", "Stats"),
            Binding("q", "quit", "Quit"),
            Binding("enter", "show_detail", "Detail"),
        ]

        def compose(self):
            yield Header()
            yield DataTable(id="word_table")
            yield Footer()

        def on_mount(self):
            self.refresh_table()

        def refresh_table(self):
            table = self.query_one("#word_table", DataTable)
            table.clear()
            table.columns.clear()
            table.add_columns("#", "Word", "Chinese", "Definition", "Added")
            words = load_words()
            for i, w in enumerate(words, 1):
                def_text = w["definitions"][0][:60] + "..." if w.get("definitions") and len(w["definitions"][0]) > 60 else (w["definitions"][0] if w.get("definitions") else "")
                table.add_row(
                    str(i),
                    w["phrase"],
                    w.get("chinese", "")[:30],
                    def_text,
                    w["added"][:10],
                )

        def action_add_word(self):
            def on_add(result):
                if result:
                    self.refresh_table()
            self.app.push_screen(AddWordScreen(), on_add)

        def action_delete_word(self):
            table = self.query_one("#word_table", DataTable)
            row_index = table.cursor_row
            if row_index is None:
                return
            rows = table.get_row_at(row_index)
            phrase = str(rows[1])
            delete_word(phrase)
            self.refresh_table()

        def action_review(self):
            words = load_words()
            if not words:
                return
            sample = random.sample(words, min(10, len(words)))
            self.app.push_screen(ReviewScreen(sample))

        def action_show_stats(self):
            self.app.push_screen(StatsScreen())

        def action_show_detail(self):
            table = self.query_one("#word_table", DataTable)
            row_index = table.cursor_row
            if row_index is None:
                return
            rows = table.get_row_at(row_index)
            phrase = str(rows[1])
            words = load_words()
            for w in words:
                if w["phrase"] == phrase:
                    self.app.push_screen(WordDetailScreen(w))
                    break

        def action_quit(self):
            self.app.exit()

    class SATVocabApp(App):
        TITLE = "vbank"
        SCREENS = {"wordlist": WordListScreen}

        def on_mount(self):
            self.push_screen("wordlist")

    def run_tui():
        app = SATVocabApp()
        app.run()


# ── Entry point ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) == 1 and TUI_AVAILABLE:
        run_tui()
        return

    p = argparse.ArgumentParser(description="vbank - SAT Vocabulary")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("add", help="Add a phrase")
    a.add_argument("phrase", nargs="+")

    sub.add_parser("list", help="List all words")

    r = sub.add_parser("review", help="Review words")
    r.add_argument("-n", "--count", type=int, default=5)

    d = sub.add_parser("delete", help="Delete a phrase")
    d.add_argument("phrase", nargs="+")

    sub.add_parser("stats", help="Show stats")

    args = p.parse_args()
    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "review":
        cmd_review(args)
    elif args.cmd == "delete":
        cmd_delete(args)
    elif args.cmd == "stats":
        cmd_stats(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
