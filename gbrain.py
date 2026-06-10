"""
GBrain — Semantic Memory Engine
===============================
- Vector search via Chroma
- Keyword + graph traversal (wikilinks)
- Obsidian vault watcher
- MCP Server integration

Usage:
    from gbrain import GBrain
    gb = GBrain(vault_path="./vault")
    gb.index_all()                    # Index all notes
    results = gb.search("query", k=5) # Search
    graph = gb.traverse("Note Name")  # Graph traversal
"""
import os, re, json, hashlib
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    path: str
    title: str
    content: str
    score: float
    links: List[str] = field(default_factory=list)
    backlinks: List[str] = field(default_factory=list)


class GBrain:
    """Semantic memory engine bridging Obsidian ↔ Chroma."""

    def __init__(self, vault_path: str, chroma_path: str = None):
        self.vault = Path(vault_path)
        self.chroma_path = chroma_path or str(self.vault / ".gbrain_chroma")
        self._client = None
        self._collection = None

    # ── Chroma ─────────────────────────────────────────────

    @property
    def client(self):
        if self._client is None:
            import chromadb
            os.makedirs(self.chroma_path, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.chroma_path)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = self.client.get_collection("gbrain_notes")
            except Exception:
                self._collection = self.client.create_collection(
                    "gbrain_notes",
                    metadata={"hnsw:space": "cosine"}
                )
        return self._collection

    # ── Indexing ───────────────────────────────────────────

    def index_all(self):
        """Index all markdown notes in the vault."""
        notes = list(self.vault.glob("**/*.md"))
        if not notes:
            return {"indexed": 0, "total": 0}

        ids, docs, metas = [], [], []
        for note in notes:
            try:
                content = note.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            title = note.stem
            # Extract wikilinks
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            chunk = f"{title}\n{content[:2000]}"  # chunk first 2000 chars
            doc_id = hashlib.md5(str(note).encode()).hexdigest()[:16]

            ids.append(doc_id)
            docs.append(chunk)
            metas.append({
                "path": str(note),
                "title": title,
                "links": json.dumps(links),
                "char_count": len(content),
            })

        # Upsert in batches
        batch = 50
        for i in range(0, len(ids), batch):
            self.collection.upsert(
                ids=ids[i:i+batch],
                documents=docs[i:i+batch],
                metadatas=metas[i:i+batch],
            )
        return {"indexed": len(ids), "total": len(notes)}

    def index_one(self, filepath: str):
        """Index a single note."""
        note = Path(filepath)
        if not note.exists() or note.suffix != ".md":
            return None
        content = note.read_text(encoding="utf-8", errors="ignore")
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        doc_id = hashlib.md5(str(note).encode()).hexdigest()[:16]

        self.collection.upsert(
            ids=[doc_id],
            documents=[f"{note.stem}\n{content[:2000]}"],
            metadatas=[{
                "path": str(note),
                "title": note.stem,
                "links": json.dumps(links),
                "char_count": len(content),
            }]
        )
        return {"indexed": 1, "path": str(note)}

    # ── Search ─────────────────────────────────────────────

    def search(self, query: str, k: int = 5) -> List[SearchResult]:
        """Vector + keyword mixed search."""
        results = self.collection.query(query_texts=[query], n_results=k)

        items = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            links = json.loads(meta.get("links", "[]"))
            items.append(SearchResult(
                path=meta.get("path", ""),
                title=meta.get("title", ""),
                content=results["documents"][0][i][:500],
                score=1 - results["distances"][0][i] if results["distances"] else 0,
                links=links,
                backlinks=self._find_backlinks(meta.get("title", "")),
            ))
        return items

    def keyword_search(self, keyword: str, k: int = 10) -> List[dict]:
        """Simple keyword grep fallback."""
        results = []
        for note in self.vault.glob("**/*.md"):
            try:
                content = note.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if keyword.lower() in content.lower():
                results.append({
                    "path": str(note),
                    "title": note.stem,
                    "excerpt": self._excerpt(content, keyword),
                })
                if len(results) >= k:
                    break
        return results

    # ── Graph traversal ────────────────────────────────────

    def traverse(self, note_name: str, depth: int = 2) -> dict:
        """Traverse wikilink graph from a note."""
        note_path = self._find_note(note_name)
        if not note_path:
            return {"error": f"Note not found: {note_name}"}

        visited = set()
        graph = {"nodes": [], "edges": []}

        def walk(path: str, d: int, parent: str = None):
            if d > depth or path in visited:
                return
            visited.add(path)

            try:
                content = Path(path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return

            title = Path(path).stem
            links = re.findall(r'\[\[([^\]]+)\]\]', content)

            graph["nodes"].append({"id": title, "path": path, "depth": d})
            if parent:
                graph["edges"].append({"from": parent, "to": title})

            for link in links:
                link_path = self._find_note(link)
                if link_path:
                    walk(link_path, d + 1, title)

        walk(note_path, 1)
        return graph

    # ── Helpers ────────────────────────────────────────────

    def _find_note(self, name: str) -> Optional[str]:
        """Find a note by name or path."""
        # Direct path
        direct = self.vault / f"{name}.md"
        if direct.exists():
            return str(direct)
        # Glob search
        for note in self.vault.glob(f"**/{name}.md"):
            return str(note)
        return None

    def _find_backlinks(self, title: str) -> List[str]:
        """Find notes that link to this title."""
        backlinks = []
        link_pattern = f"[[{title}]]"
        for note in self.vault.glob("**/*.md"):
            if note.stem == title:
                continue
            try:
                if link_pattern in note.read_text(encoding="utf-8", errors="ignore"):
                    backlinks.append(note.stem)
            except Exception:
                pass
        return backlinks

    def _excerpt(self, content: str, keyword: str, radius: int = 60) -> str:
        """Extract a snippet around keyword."""
        idx = content.lower().find(keyword.lower())
        if idx < 0:
            return content[:120] + "..."
        start = max(0, idx - radius)
        end = min(len(content), idx + len(keyword) + radius)
        return ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")

    # ── Extended Tools ─────────────────────────────────────

    def stats(self) -> dict:
        """Vault statistics: note count, indexed count, disk usage."""
        notes = list(self.vault.glob("**/*.md"))
        total_size = sum(n.stat().st_size for n in notes if n.is_file())
        try:
            indexed = self.collection.count()
        except Exception:
            indexed = 0
        return {
            "total_notes": len(notes),
            "indexed_notes": indexed,
            "total_size_kb": round(total_size / 1024, 1),
            "vault_path": str(self.vault),
        }

    def recent(self, k: int = 10) -> List[dict]:
        """Recently modified notes."""
        notes = []
        for note in self.vault.glob("**/*.md"):
            try:
                notes.append({
                    "path": str(note),
                    "title": note.stem,
                    "mtime": note.stat().st_mtime,
                    "size_kb": round(note.stat().st_size / 1024, 1),
                })
            except Exception:
                pass
        notes.sort(key=lambda x: x["mtime"], reverse=True)
        return notes[:k]

    def orphans(self) -> List[dict]:
        """Find notes with zero backlinks (orphan detection)."""
        all_notes = [n.stem for n in self.vault.glob("**/*.md")]
        orphans_list = []
        for title in all_notes:
            bl = self._find_backlinks(title)
            if not bl:
                note_path = self._find_note(title)
                orphans_list.append({
                    "title": title,
                    "path": note_path or "",
                })
        return orphans_list

    def get_content(self, title: str) -> Optional[str]:
        """Get full content of a note by title."""
        note_path = self._find_note(title)
        if not note_path:
            return None
        try:
            return Path(note_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

    def get_links(self, title: str) -> List[str]:
        """Get outgoing wikilinks from a note."""
        note_path = self._find_note(title)
        if not note_path:
            return []
        try:
            content = Path(note_path).read_text(encoding="utf-8", errors="ignore")
            return re.findall(r'\[\[([^\]]+)\]\]', content)
        except Exception:
            return []

    def broken_links(self) -> List[dict]:
        """Find wikilinks pointing to non-existent notes."""
        all_titles = {n.stem for n in self.vault.glob("**/*.md")}
        broken = []
        for note in self.vault.glob("**/*.md"):
            try:
                content = note.read_text(encoding="utf-8", errors="ignore")
                links = re.findall(r'\[\[([^\]]+)\]\]', content)
                for link in links:
                    # Strip aliases like [[target|display]]
                    target = link.split("|")[0].split("#")[0].strip()
                    if target not in all_titles:
                        broken.append({
                            "source": note.stem,
                            "target": target,
                            "source_path": str(note),
                        })
            except Exception:
                pass
        return broken

    # ── File watcher ───────────────────────────────────────

    def watch(self, callback=None):
        """Start filesystem watcher for auto-indexing."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith(".md"):
                    self._index(event.src_path)
            def on_created(self, event):
                if event.src_path.endswith(".md"):
                    self._index(event.src_path)
            def _index(self, path):
                try:
                    self.brain.index_one(path)
                    if callback:
                        callback(path)
                except Exception:
                    pass

        handler = Handler()
        handler.brain = self
        observer = Observer()
        observer.schedule(handler, str(self.vault), recursive=True)
        observer.start()
        return observer


# ── CLI ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    vault = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents/GBrain Vault")
    gb = GBrain(vault)

    cmd = sys.argv[2] if len(sys.argv) > 2 else "index"
    if cmd == "index":
        r = gb.index_all()
        print(f"Indexed {r['indexed']}/{r['total']} notes")
    elif cmd == "search":
        q = sys.argv[3] if len(sys.argv) > 3 else ""
        for item in gb.search(q):
            print(f"[{item.score:.2f}] {item.title} — {item.path}")
    elif cmd == "watch":
        gb.watch(callback=lambda p: print(f"Updated: {p}"))
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopped")
