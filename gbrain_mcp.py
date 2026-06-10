#!/usr/bin/env python3
"""
GBrain MCP Server — exposes semantic memory tools to Claude Code.
Run: python gbrain_mcp.py
"""
import json, sys, os
from gbrain import GBrain

# Resolve vault path
VAULT = os.environ.get("GBRAIN_VAULT", os.path.expanduser("~/Documents/GBrain Vault"))
gb = GBrain(VAULT)


def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    # ── Initialize ──
    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "gbrain", "version": "1.0.0"},
                "capabilities": {"tools": {}}
            }
        }

    # ── List Tools ──
    if method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {"tools": [
                {
                    "name": "gbrain_search",
                    "description": "Semantic search across the knowledge base. Returns ranked results with scores and wikilinks.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "k": {"type": "integer", "default": 5, "description": "Number of results"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "gbrain_keyword",
                    "description": "Keyword/grep search across all notes. Good for exact term matching.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string", "description": "Keyword to grep for"},
                            "k": {"type": "integer", "default": 10}
                        },
                        "required": ["keyword"]
                    }
                },
                {
                    "name": "gbrain_traverse",
                    "description": "Traverse the wikilink graph from a note. Shows nodes and edges up to specified depth.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "note": {"type": "string", "description": "Note name to start traversal"},
                            "depth": {"type": "integer", "default": 2}
                        },
                        "required": ["note"]
                    }
                },
                {
                    "name": "gbrain_index",
                    "description": "Re-index all notes or a specific note into the vector database.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Optional: specific note path to index"}
                        }
                    }
                },
                {
                    "name": "gbrain_backlinks",
                    "description": "Find all notes that link to a given note.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Note title to find backlinks for"}
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "gbrain_stats",
                    "description": "Get vault statistics: total notes, indexed count, disk usage.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "gbrain_recent",
                    "description": "Get recently modified notes, sorted by modification time.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "k": {"type": "integer", "default": 10, "description": "Number of results"}
                        }
                    }
                },
                {
                    "name": "gbrain_orphans",
                    "description": "Find orphaned notes with no backlinks — useful for knowledge graph health.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "gbrain_content",
                    "description": "Get the full content of a note by title.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Note title to retrieve"}
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "gbrain_links",
                    "description": "Get all outgoing wikilinks from a note.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Note title to get links from"}
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "gbrain_broken_links",
                    "description": "Find broken wikilinks — links pointing to non-existent notes. Use to maintain knowledge graph integrity.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
            ]}
        }

    # ── Call Tool ──
    if method == "tools/call":
        tool_name = req["params"]["name"]
        args = req["params"].get("arguments", {})

        try:
            if tool_name == "gbrain_search":
                results = gb.search(args["query"], args.get("k", 5))
                text = "\n\n".join(
                    f"## {r.title} (score: {r.score:.2f})\n{r.content[:500]}\nLinks: {', '.join(r.links[:10])}\nBacklinks: {', '.join(r.backlinks[:10])}"
                    for r in results
                ) or "No results found."
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_keyword":
                results = gb.keyword_search(args["keyword"], args.get("k", 10))
                text = "\n".join(
                    f"- [[{r['title']}]] — {r['excerpt'][:200]}"
                    for r in results
                ) or "No matches."
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_traverse":
                graph = gb.traverse(args["note"], args.get("depth", 2))
                text = json.dumps(graph, ensure_ascii=False, indent=2)
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_index":
                path = args.get("path")
                if path:
                    r = gb.index_one(path)
                else:
                    r = gb.index_all()
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(r)}]}
                }

            elif tool_name == "gbrain_backlinks":
                bl = gb._find_backlinks(args["title"])
                text = "\n".join(f"- [[{b}]]" for b in bl) or "No backlinks found."
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_stats":
                stats = gb.stats()
                text = json.dumps(stats, ensure_ascii=False, indent=2)
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_recent":
                k = args.get("k", 10)
                recent_notes = gb.recent(k)
                text = json.dumps(recent_notes, ensure_ascii=False, indent=2)
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_orphans":
                orphan_list = gb.orphans()
                text = f"Orphaned notes ({len(orphan_list)}):\n"
                text += "\n".join(f"- [[{o['title']}]]" for o in orphan_list) or "No orphans found."
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_content":
                content = gb.get_content(args["title"])
                if content is None:
                    return {
                        "jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -1, "message": f"Note not found: {args['title']}"}
                    }
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": content[:5000]}]}
                }

            elif tool_name == "gbrain_links":
                links = gb.get_links(args["title"])
                text = f"Links from [[{args['title']}]] ({len(links)}):\n"
                text += "\n".join(f"- [[{l}]]" for l in links) or "No outgoing links."
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

            elif tool_name == "gbrain_broken_links":
                broken = gb.broken_links()
                if not broken:
                    text = "No broken wikilinks found. Knowledge graph is healthy."
                else:
                    text = f"Broken wikilinks ({len(broken)}):\n"
                    for b in broken:
                        text += f"  [[{b['source']}]] → [[{b['target']}]] (missing)\n"
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]}
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -1, "message": str(e)}
            }

    # ── Unknown ──
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


# ── STDIO Loop ──
if __name__ == "__main__":
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            req = json.loads(line)
            resp = handle_request(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
        except KeyboardInterrupt:
            break
